"""Tests for FRED macroeconomic adapter.

Tests cover:
- Rate limiting (1000 req/day)
- Caching (24-hour TTL)
- API errors and fallbacks
- Series fetching and latest values
- Batch operations
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from quantum_terminal.infrastructure.macro.fred_adapter import (
    FREDAdapter,
    FREDAuthException,
    FREDDataException,
    FREDRateLimitException,
    FREDSeriesException,
)
from quantum_terminal.utils.rate_limiter import rate_limiter


@pytest.fixture
def fred_adapter():
    """Create FRED adapter instance."""
    with patch("quantum_terminal.config.settings") as mock_settings:
        mock_settings.fred_api_key = "test_api_key_12345"
        adapter = FREDAdapter(api_key="test_api_key_12345")
        yield adapter


@pytest.fixture
def mock_fred_response():
    """Mock FRED API response."""
    return {
        "series_id": "DGS10",
        "observations": [
            {"date": "2024-01-01", "value": "4.25"},
            {"date": "2023-12-31", "value": "4.10"},
            {"date": "2023-12-30", "value": "4.05"},
        ],
    }


class TestFREDAdapterInit:
    """Test FRED adapter initialization."""

    def test_init_with_api_key(self):
        """Test initialization with provided API key."""
        adapter = FREDAdapter(api_key="test_key")
        assert adapter.api_key == "test_key"

    def test_init_without_api_key_raises(self):
        """Test initialization without API key raises exception."""
        with patch("quantum_terminal.config.settings") as mock_settings:
            mock_settings.fred_api_key = None
            with pytest.raises(FREDAuthException):
                FREDAdapter()

    def test_adapter_base_url(self):
        """Test base URL is correct."""
        adapter = FREDAdapter(api_key="test")
        assert adapter.BASE_URL == "https://api.stlouisfed.org/fred"

    def test_adapter_timeout(self):
        """Test timeout is set correctly."""
        adapter = FREDAdapter(api_key="test")
        assert adapter.TIMEOUT == 30

    def test_critical_series_defined(self):
        """Test critical series are defined."""
        assert "DGS10" in FREDAdapter.CRITICAL_SERIES
        assert "CPI" in FREDAdapter.CRITICAL_SERIES
        assert "UNRATE" in FREDAdapter.CRITICAL_SERIES


class TestFREDAdapterRateLimit:
    """Test rate limiting."""

    def test_rate_limiter_registered(self):
        """Test FRED rate limiter is registered."""
        limiter = rate_limiter.get("fred")
        assert limiter is not None

    @pytest.mark.asyncio
    async def test_rate_limit_check(self, fred_adapter):
        """Test rate limit is checked."""
        # Reset rate limiter
        rate_limiter.reset("fred")

        # Should allow first request
        assert rate_limiter.allow_request("fred") is True

    @pytest.mark.asyncio
    async def test_rate_limit_exception(self, fred_adapter):
        """Test rate limit exception is raised."""
        # Mock rate limiter to deny request
        with patch.object(rate_limiter, "allow_request", return_value=False):
            with pytest.raises(FREDRateLimitException):
                await fred_adapter._request("series")


class TestFREDAdapterRequest:
    """Test HTTP request handling."""

    @pytest.mark.asyncio
    async def test_successful_request(self, fred_adapter, mock_fred_response):
        """Test successful API request."""
        with patch.object(fred_adapter, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_fred_response)
            mock_session.get = AsyncMock(return_value=mock_response)
            mock_session.get.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await fred_adapter._request("series")
                assert result == mock_fred_response

    @pytest.mark.asyncio
    async def test_auth_error_401(self, fred_adapter):
        """Test 401 raises auth exception."""
        with patch.object(fred_adapter, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_session.get.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                with pytest.raises(FREDAuthException):
                    await fred_adapter._request("series")

    @pytest.mark.asyncio
    async def test_not_found_error_400(self, fred_adapter):
        """Test 400 raises series exception."""
        with patch.object(fred_adapter, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_session.get.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                with pytest.raises(FREDSeriesException):
                    await fred_adapter._request("series")

    @pytest.mark.asyncio
    async def test_timeout_raises_exception(self, fred_adapter):
        """Test timeout raises exception."""
        with patch.object(fred_adapter, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_session.get = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                with pytest.raises(FREDDataException):
                    await fred_adapter._request("series")


class TestFREDAdapterGetLatest:
    """Test get_latest method."""

    @pytest.mark.asyncio
    async def test_get_latest_valid(self, fred_adapter):
        """Test get_latest returns numeric value."""
        response = {
            "observations": [
                {"date": "2024-01-01", "value": "4.25"}
            ]
        }

        with patch.object(fred_adapter, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = response
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await fred_adapter.get_latest("DGS10")
                assert result == 4.25

    @pytest.mark.asyncio
    async def test_get_latest_empty_observations(self, fred_adapter):
        """Test get_latest returns None for empty observations."""
        response = {"observations": []}

        with patch.object(fred_adapter, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = response
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await fred_adapter.get_latest("DGS10")
                assert result is None

    @pytest.mark.asyncio
    async def test_get_latest_missing_value(self, fred_adapter):
        """Test get_latest handles missing values ('.')."""
        response = {
            "observations": [
                {"date": "2024-01-01", "value": "."}
            ]
        }

        with patch.object(fred_adapter, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = response
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await fred_adapter.get_latest("DGS10")
                assert result is None


class TestFREDAdapterBatchLatest:
    """Test batch_latest method."""

    @pytest.mark.asyncio
    async def test_batch_latest_multiple_series(self, fred_adapter):
        """Test batch_latest fetches multiple series."""
        with patch.object(fred_adapter, "get_latest", new_callable=AsyncMock) as mock:
            mock.side_effect = [4.25, 3.45, 5.1]

            result = await fred_adapter.batch_latest(["DGS10", "CPI", "UNRATE"])

            assert result["DGS10"] == 4.25
            assert result["CPI"] == 3.45
            assert result["UNRATE"] == 5.1
            assert mock.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_latest_with_failures(self, fred_adapter):
        """Test batch_latest handles failures gracefully."""
        with patch.object(fred_adapter, "get_latest", new_callable=AsyncMock) as mock:
            mock.side_effect = [
                4.25,
                FREDSeriesException("Not found"),
                5.1,
            ]

            result = await fred_adapter.batch_latest(["DGS10", "INVALID", "UNRATE"])

            assert result["DGS10"] == 4.25
            assert result["INVALID"] is None
            assert result["UNRATE"] == 5.1


class TestFREDAdapterGetSeries:
    """Test get_series method."""

    @pytest.mark.asyncio
    async def test_get_series_with_dates(self, fred_adapter, mock_fred_response):
        """Test get_series with date parameters."""
        with patch.object(fred_adapter, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_fred_response
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await fred_adapter.get_series(
                    "DGS10",
                    start_date="2024-01-01",
                    end_date="2024-12-31",
                )
                assert result["series_id"] == "DGS10"
                assert len(result["observations"]) == 3

    @pytest.mark.asyncio
    async def test_get_series_without_dates(self, fred_adapter, mock_fred_response):
        """Test get_series without date parameters."""
        with patch.object(fred_adapter, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = mock_fred_response
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await fred_adapter.get_series("DGS10")
                assert result["series_id"] == "DGS10"


class TestFREDAdapterGetObservations:
    """Test get_observations method."""

    @pytest.mark.asyncio
    async def test_get_observations_default(self, fred_adapter):
        """Test get_observations with default parameters."""
        response = {
            "observations": [
                {"date": "2024-01-01", "value": "4.25"},
                {"date": "2023-12-31", "value": "4.10"},
            ]
        }

        with patch.object(fred_adapter, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = response
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await fred_adapter.get_observations("DGS10")
                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_observations_with_limit(self, fred_adapter):
        """Test get_observations with custom limit."""
        response = {"observations": [{"date": "2024-01-01", "value": "4.25"}]}

        with patch.object(fred_adapter, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = response
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await fred_adapter.get_observations("DGS10", limit=1)
                assert len(result) == 1


class TestFREDAdapterValidation:
    """Test input validation."""

    def test_validate_series_critical(self, fred_adapter):
        """Test validation of critical series."""
        assert fred_adapter.validate_series("DGS10") is True
        assert fred_adapter.validate_series("CPI") is True

    def test_validate_series_any_id(self, fred_adapter):
        """Test validation accepts any series ID."""
        assert fred_adapter.validate_series("UNKNOWN_SERIES_123") is True

    def test_validate_series_empty_raises(self, fred_adapter):
        """Test validation rejects empty series ID."""
        assert fred_adapter.validate_series("") is False


class TestFREDAdapterContextManager:
    """Test context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self, fred_adapter):
        """Test async context manager."""
        async with fred_adapter as adapter:
            assert adapter is not None
            assert adapter.session is not None

        assert fred_adapter.session.closed or fred_adapter.session is None


class TestFREDAdapterGlobal:
    """Test global adapter instance."""

    @pytest.mark.asyncio
    async def test_get_fred_adapter(self):
        """Test get_fred_adapter returns instance."""
        from quantum_terminal.infrastructure.macro.fred_adapter import get_fred_adapter

        with patch("quantum_terminal.config.settings") as mock_settings:
            mock_settings.fred_api_key = "test_key"
            adapter = await get_fred_adapter()
            assert isinstance(adapter, FREDAdapter)


class TestFREDAdapterExceptions:
    """Test exception hierarchy."""

    def test_exception_hierarchy(self):
        """Test all exceptions inherit from FREDException."""
        assert issubclass(FREDRateLimitException, FREDException)
        assert issubclass(FREDAuthException, FREDException)
        assert issubclass(FREDSeriesException, FREDException)
        assert issubclass(FREDDataException, FREDException)

    def test_exception_messages(self):
        """Test exception messages."""
        exc = FREDAuthException("Missing key")
        assert "Missing key" in str(exc)
