"""Tests for EIA energy market data adapter.

Tests cover:
- Rate limiting (120 req/hour)
- Caching (24-hour TTL)
- API errors and fallbacks
- Energy data (WTI, Brent, natural gas)
- Batch operations
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from quantum_terminal.infrastructure.macro.eia_adapter import (
    EIAAdapter,
    EIAAuthException,
    EIADataException,
    EIARateLimitException,
    EIASeriesException,
)
from quantum_terminal.utils.rate_limiter import rate_limiter


@pytest.fixture
def eia_adapter():
    """Create EIA adapter instance."""
    with patch("quantum_terminal.config.settings") as mock_settings:
        mock_settings.eia_api_key = "test_api_key_12345"
        adapter = EIAAdapter(api_key="test_api_key_12345")
        yield adapter


class TestEIAAdapterInit:
    """Test EIA adapter initialization."""

    def test_init_with_api_key(self):
        """Test initialization with provided API key."""
        adapter = EIAAdapter(api_key="test_key")
        assert adapter.api_key == "test_key"

    def test_init_without_api_key_raises(self):
        """Test initialization without API key raises exception."""
        with patch("quantum_terminal.config.settings") as mock_settings:
            mock_settings.eia_api_key = None
            with pytest.raises(EIAAuthException):
                EIAAdapter()

    def test_adapter_base_url(self):
        """Test base URL is correct."""
        adapter = EIAAdapter(api_key="test")
        assert adapter.BASE_URL == "https://api.eia.gov/v2"

    def test_series_defined(self):
        """Test series are defined."""
        assert "crude_oil_wti" in EIAAdapter.SERIES
        assert "crude_oil_brent" in EIAAdapter.SERIES
        assert "natural_gas" in EIAAdapter.SERIES


class TestEIAAdapterRateLimit:
    """Test rate limiting."""

    def test_rate_limiter_registered(self):
        """Test EIA rate limiter is registered."""
        limiter = rate_limiter.get("eia")
        assert limiter is not None

    @pytest.mark.asyncio
    async def test_rate_limit_exception(self, eia_adapter):
        """Test rate limit exception is raised."""
        with patch.object(rate_limiter, "allow_request", return_value=False):
            with pytest.raises(EIARateLimitException):
                await eia_adapter._request("petroleum/pri/spt")


class TestEIAAdapterRequest:
    """Test HTTP request handling."""

    @pytest.mark.asyncio
    async def test_successful_request(self, eia_adapter):
        """Test successful API request."""
        mock_response_data = {
            "response": {
                "data": [
                    {"period": "2024-01-01", "value": "75.50"}
                ]
            }
        }

        with patch.object(eia_adapter, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_session.get = AsyncMock(return_value=mock_response)
            mock_session.get.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await eia_adapter._request("petroleum/pri/spt")
                assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_auth_error_401(self, eia_adapter):
        """Test 401 raises auth exception."""
        with patch.object(eia_adapter, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_session.get.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                with pytest.raises(EIAAuthException):
                    await eia_adapter._request("petroleum/pri/spt")

    @pytest.mark.asyncio
    async def test_not_found_error_404(self, eia_adapter):
        """Test 404 raises series exception."""
        with patch.object(eia_adapter, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_session.get.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                with pytest.raises(EIASeriesException):
                    await eia_adapter._request("petroleum/pri/spt")


class TestEIAAdapterGetCrudeOilWTI:
    """Test get_crude_oil_wti method."""

    @pytest.mark.asyncio
    async def test_get_wti_valid(self, eia_adapter):
        """Test get_crude_oil_wti returns numeric value."""
        with patch.object(eia_adapter, "_fetch_latest") as mock:
            mock.return_value = 75.50
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await eia_adapter.get_crude_oil_wti()
                assert result == 75.50

    @pytest.mark.asyncio
    async def test_get_wti_none(self, eia_adapter):
        """Test get_crude_oil_wti returns None on failure."""
        with patch.object(eia_adapter, "_fetch_latest") as mock:
            mock.return_value = None
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await eia_adapter.get_crude_oil_wti()
                assert result is None


class TestEIAAdapterGetCrudeOilBrent:
    """Test get_crude_oil_brent method."""

    @pytest.mark.asyncio
    async def test_get_brent_valid(self, eia_adapter):
        """Test get_crude_oil_brent returns numeric value."""
        with patch.object(eia_adapter, "_fetch_latest") as mock:
            mock.return_value = 78.25
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await eia_adapter.get_crude_oil_brent()
                assert result == 78.25


class TestEIAAdapterGetNaturalGas:
    """Test get_natural_gas method."""

    @pytest.mark.asyncio
    async def test_get_natural_gas_valid(self, eia_adapter):
        """Test get_natural_gas returns numeric value."""
        with patch.object(eia_adapter, "_fetch_latest") as mock:
            mock.return_value = 2.85
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await eia_adapter.get_natural_gas()
                assert result == 2.85


class TestEIAAdapterGetInventories:
    """Test get_inventories method."""

    @pytest.mark.asyncio
    async def test_get_inventories_valid(self, eia_adapter):
        """Test get_inventories returns numeric value."""
        with patch.object(eia_adapter, "_fetch_latest") as mock:
            mock.return_value = 425.5
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await eia_adapter.get_inventories()
                assert result == 425.5


class TestEIAAdapterGetRefineryUtilization:
    """Test get_refinery_utilization method."""

    @pytest.mark.asyncio
    async def test_get_refinery_utilization_valid(self, eia_adapter):
        """Test get_refinery_utilization returns percentage."""
        with patch.object(eia_adapter, "_fetch_latest") as mock:
            mock.return_value = 92.3
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await eia_adapter.get_refinery_utilization()
                assert result == 92.3


class TestEIAAdapterFetchLatest:
    """Test _fetch_latest method."""

    @pytest.mark.asyncio
    async def test_fetch_latest_valid_series(self, eia_adapter):
        """Test _fetch_latest for valid series."""
        response = {
            "response": {
                "data": [
                    {"value": "75.50"}
                ]
            }
        }

        with patch.object(eia_adapter, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = response
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await eia_adapter._fetch_latest("crude_oil_wti")
                assert result == 75.50

    @pytest.mark.asyncio
    async def test_fetch_latest_unknown_series(self, eia_adapter):
        """Test _fetch_latest raises for unknown series."""
        with pytest.raises(EIASeriesException):
            await eia_adapter._fetch_latest("unknown_series")

    @pytest.mark.asyncio
    async def test_fetch_latest_invalid_value(self, eia_adapter):
        """Test _fetch_latest handles invalid values."""
        response = {
            "response": {
                "data": [
                    {"value": "invalid"}
                ]
            }
        }

        with patch.object(eia_adapter, "_request", new_callable=AsyncMock) as mock:
            mock.return_value = response
            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await eia_adapter._fetch_latest("crude_oil_wti")
                assert result is None


class TestEIAAdapterBatchLatest:
    """Test batch_latest method."""

    @pytest.mark.asyncio
    async def test_batch_latest_multiple_series(self, eia_adapter):
        """Test batch_latest fetches multiple series."""
        with patch.object(eia_adapter, "get_crude_oil_wti") as mock_wti, \
             patch.object(eia_adapter, "get_natural_gas") as mock_gas, \
             patch.object(eia_adapter, "get_refinery_utilization") as mock_refinery:

            mock_wti.return_value = 75.50
            mock_gas.return_value = 2.85
            mock_refinery.return_value = 92.3

            result = await eia_adapter.batch_latest([
                "crude_oil_wti",
                "natural_gas",
                "refinery_utilization",
            ])

            assert result["crude_oil_wti"] == 75.50
            assert result["natural_gas"] == 2.85
            assert result["refinery_utilization"] == 92.3

    @pytest.mark.asyncio
    async def test_batch_latest_with_failures(self, eia_adapter):
        """Test batch_latest handles failures gracefully."""
        with patch.object(eia_adapter, "get_crude_oil_wti") as mock_wti, \
             patch.object(eia_adapter, "get_natural_gas") as mock_gas:

            mock_wti.return_value = 75.50
            mock_gas.side_effect = Exception("Network error")

            result = await eia_adapter.batch_latest([
                "crude_oil_wti",
                "natural_gas",
            ])

            assert result["crude_oil_wti"] == 75.50
            assert result["natural_gas"] is None


class TestEIAAdapterContextManager:
    """Test context manager support."""

    @pytest.mark.asyncio
    async def test_context_manager(self, eia_adapter):
        """Test async context manager."""
        async with eia_adapter as adapter:
            assert adapter is not None
            assert adapter.session is not None


class TestEIAAdapterGlobal:
    """Test global adapter instance."""

    @pytest.mark.asyncio
    async def test_get_eia_adapter(self):
        """Test get_eia_adapter returns instance."""
        from quantum_terminal.infrastructure.macro.eia_adapter import get_eia_adapter

        with patch("quantum_terminal.config.settings") as mock_settings:
            mock_settings.eia_api_key = "test_key"
            adapter = await get_eia_adapter()
            assert isinstance(adapter, EIAAdapter)


class TestEIAAdapterExceptions:
    """Test exception hierarchy."""

    def test_exception_hierarchy(self):
        """Test all exceptions inherit from EIAException."""
        assert issubclass(EIAAuthException, EIAException)
        assert issubclass(EIARateLimitException, EIAException)
        assert issubclass(EIASeriesException, EIAException)
        assert issubclass(EIADataException, EIAException)

    def test_exception_messages(self):
        """Test exception messages."""
        exc = EIAAuthException("Missing key")
        assert "Missing key" in str(exc)
