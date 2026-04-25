"""Tests for Tiingo adapter with rate limiting, caching, and batch support."""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from quantum_terminal.infrastructure.market_data.tiingo_adapter import (
    TiingoAdapter,
    TiingoAPIError,
    TiingoRateLimitError,
    TiingoHTTPError,
    get_historical,
    batch_historical,
    get_metadata,
    get_latest_quote,
)
from quantum_terminal.utils.cache import cache
from quantum_terminal.utils.rate_limiter import rate_limiter


@pytest.fixture
def adapter():
    """Create adapter instance with mock API key."""
    with patch.dict(os.environ, {"TIINGO_API_KEY": "test_key"}):
        return TiingoAdapter()


@pytest.fixture
def sample_historical():
    """Create sample historical data."""
    return [
        {
            "date": "2025-01-01",
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "volume": 1000000,
            "adjClose": 100.5,
        },
        {
            "date": "2025-01-02",
            "open": 100.5,
            "high": 101.5,
            "low": 99.5,
            "close": 101.0,
            "volume": 1100000,
            "adjClose": 101.0,
        },
    ]


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter before each test."""
    rate_limiter.reset("tiingo")
    yield
    rate_limiter.reset("tiingo")


class TestTiingoAdapterInit:
    """Test adapter initialization."""

    def test_init_with_api_key(self):
        """Test initialization with provided API key."""
        adapter = TiingoAdapter(api_key="test_key_123")
        assert adapter.api_key == "test_key_123"

    def test_init_from_environment(self):
        """Test initialization from environment variable."""
        with patch.dict(os.environ, {"TIINGO_API_KEY": "env_key"}):
            adapter = TiingoAdapter()
            assert adapter.api_key == "env_key"

    def test_init_without_api_key(self):
        """Test initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="TIINGO_API_KEY"):
                TiingoAdapter()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with TiingoAdapter(api_key="test") as adapter:
            assert adapter.session is not None
        assert adapter.session.closed


class TestTiingoHistorical:
    """Test get_historical method."""

    @pytest.mark.asyncio
    async def test_get_historical_success(self, adapter, sample_historical):
        """Test successful historical data retrieval."""
        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=sample_historical):
            df = await adapter.get_historical("AAPL")

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 2
            assert "Close" in df.columns
            assert df.loc[df.index[0], "Close"] == 100.5

    @pytest.mark.asyncio
    async def test_get_historical_with_dates(self, adapter, sample_historical):
        """Test historical data with date range."""
        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=sample_historical):
            df = await adapter.get_historical("AAPL", "2025-01-01", "2025-01-31")

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 2

    @pytest.mark.asyncio
    async def test_get_historical_caching(self, adapter, sample_historical):
        """Test that historical data is cached with 1-hour TTL."""
        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=sample_historical):
            # First call
            df1 = await adapter.get_historical("AAPL")
            # Second call should use cache
            df2 = await adapter.get_historical("AAPL")

            # _get should only be called once
            adapter._get.assert_called_once()

            pd.testing.assert_frame_equal(df1, df2)

    @pytest.mark.asyncio
    async def test_get_historical_empty_data(self, adapter):
        """Test handling of empty data."""
        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=[]):
            with pytest.raises(TiingoAPIError):
                await adapter.get_historical("INVALID")

    @pytest.mark.asyncio
    async def test_get_historical_rate_limit(self, adapter):
        """Test rate limit enforcement."""
        rate_limiter.get("tiingo").tokens = 0

        with pytest.raises(TiingoRateLimitError):
            await adapter.get_historical("AAPL")


class TestTiingoBatchHistorical:
    """Test batch_historical method."""

    @pytest.mark.asyncio
    async def test_batch_historical_success(self, adapter, sample_historical):
        """Test successful batch historical retrieval."""
        async def mock_get_historical(ticker, start_date, end_date):
            await asyncio.sleep(0.001)
            return pd.DataFrame(sample_historical)

        with patch.object(adapter, "get_historical", new_callable=AsyncMock, side_effect=mock_get_historical):
            data = await adapter.batch_historical(["AAPL", "MSFT", "GOOGL"])

            assert len(data) == 3
            assert "AAPL" in data
            assert data["AAPL"] is not None

    @pytest.mark.asyncio
    async def test_batch_historical_partial_failure(self, adapter, sample_historical):
        """Test batch with some failures."""
        async def mock_get_historical(ticker, start_date, end_date):
            if ticker == "INVALID":
                raise TiingoAPIError("Not found")
            return pd.DataFrame(sample_historical)

        with patch.object(adapter, "get_historical", new_callable=AsyncMock, side_effect=mock_get_historical):
            data = await adapter.batch_historical(["AAPL", "INVALID", "MSFT"])

            assert len(data) == 3
            assert data["INVALID"] is None
            assert data["AAPL"] is not None

    @pytest.mark.asyncio
    async def test_batch_historical_concurrent(self, adapter, sample_historical):
        """Test concurrent execution."""
        async def mock_get_historical(ticker, start_date, end_date):
            await asyncio.sleep(0.01)
            return pd.DataFrame(sample_historical)

        with patch.object(adapter, "get_historical", new_callable=AsyncMock, side_effect=mock_get_historical):
            import time
            start = time.time()
            await adapter.batch_historical(["AAPL", "MSFT", "GOOGL"])
            elapsed = time.time() - start

            # Should be concurrent (~0.01s) not sequential (~0.03s)
            assert elapsed < 0.05


class TestTiingoMetadata:
    """Test get_metadata method."""

    @pytest.mark.asyncio
    async def test_get_metadata_success(self, adapter):
        """Test successful metadata retrieval."""
        mock_response = {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "exchange": "NASDAQ",
            "startDate": "1980-12-12",
            "endDate": "2025-01-15",
            "dataType": "daily",
            "sessionStart": "09:30",
            "sessionEnd": "16:00",
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            metadata = await adapter.get_metadata("AAPL")

            assert metadata["ticker"] == "AAPL"
            assert metadata["exchange"] == "NASDAQ"

    @pytest.mark.asyncio
    async def test_get_metadata_caching(self, adapter):
        """Test metadata caching with 7-day TTL."""
        mock_response = {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "exchange": "NASDAQ",
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            # First call
            metadata1 = await adapter.get_metadata("AAPL")
            # Second call should use cache
            metadata2 = await adapter.get_metadata("AAPL")

            adapter._get.assert_called_once()
            assert metadata1 == metadata2


class TestTiingoLatestQuote:
    """Test get_latest_quote method."""

    @pytest.mark.asyncio
    async def test_get_latest_quote_success(self, adapter):
        """Test successful latest quote retrieval."""
        mock_response = {
            "last": 150.5,
            "lastSalePrice": 150.5,
            "lastSaleTime": "2025-01-15T16:00:00.000Z",
            "lastUpdated": "2025-01-15T16:00:00.000Z",
            "bid": 150.4,
            "ask": 150.6,
            "bidSize": 1000,
            "askSize": 2000,
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            quote = await adapter.get_latest_quote("AAPL")

            assert quote["ticker"] == "AAPL"
            assert quote["last"] == 150.5
            assert quote["bid"] == 150.4

    @pytest.mark.asyncio
    async def test_get_latest_quote_caching(self, adapter):
        """Test quote caching with 1-minute TTL."""
        mock_response = {
            "last": 150.5,
            "lastSalePrice": 150.5,
            "bid": 150.4,
            "ask": 150.6,
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            # First call
            quote1 = await adapter.get_latest_quote("AAPL")
            # Second call should use cache
            quote2 = await adapter.get_latest_quote("AAPL")

            adapter._get.assert_called_once()
            assert quote1 == quote2

    @pytest.mark.asyncio
    async def test_get_latest_quote_invalid_response(self, adapter):
        """Test handling of invalid response."""
        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=[]):
            with pytest.raises(TiingoAPIError):
                await adapter.get_latest_quote("AAPL")


class TestTiingoAPIGetMethod:
    """Test internal _get method."""

    @pytest.mark.asyncio
    async def test_get_rate_limit_exceeded(self, adapter):
        """Test rate limit enforcement."""
        rate_limiter.get("tiingo").tokens = 0

        with pytest.raises(TiingoRateLimitError):
            await adapter._get("daily/AAPL")

    @pytest.mark.asyncio
    async def test_get_http_error(self, adapter):
        """Test HTTP error handling."""
        import aiohttp

        with patch.object(adapter, "session", MagicMock()):
            mock_response = MagicMock()
            mock_response.status = 404
            adapter.session.get.return_value.__aenter__.return_value = mock_response

            with pytest.raises(TiingoHTTPError):
                await adapter._get("daily/INVALID")

    @pytest.mark.asyncio
    async def test_get_connection_error(self, adapter):
        """Test connection error handling."""
        import aiohttp

        adapter.session = MagicMock()
        adapter.session.get.side_effect = aiohttp.ClientError("Connection failed")

        with pytest.raises(TiingoAPIError):
            await adapter._get("daily/AAPL")


class TestGlobalFunctions:
    """Test module-level functions."""

    @pytest.mark.asyncio
    async def test_get_historical_global(self, sample_historical):
        """Test global get_historical function."""
        with patch("quantum_terminal.infrastructure.market_data.tiingo_adapter.TiingoAdapter.get_historical", new_callable=AsyncMock, return_value=pd.DataFrame(sample_historical)):
            df = await get_historical("AAPL")
            assert isinstance(df, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_batch_historical_global(self, sample_historical):
        """Test global batch_historical function."""
        expected = {
            "AAPL": pd.DataFrame(sample_historical),
            "MSFT": pd.DataFrame(sample_historical),
        }

        with patch("quantum_terminal.infrastructure.market_data.tiingo_adapter.TiingoAdapter.batch_historical", new_callable=AsyncMock, return_value=expected):
            data = await batch_historical(["AAPL", "MSFT"])
            assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_metadata_global(self):
        """Test global get_metadata function."""
        mock_metadata = {
            "ticker": "AAPL",
            "exchange": "NASDAQ",
        }

        with patch("quantum_terminal.infrastructure.market_data.tiingo_adapter.TiingoAdapter.get_metadata", new_callable=AsyncMock, return_value=mock_metadata):
            metadata = await get_metadata("AAPL")
            assert metadata["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_get_latest_quote_global(self):
        """Test global get_latest_quote function."""
        mock_quote = {
            "ticker": "AAPL",
            "last": 150.5,
            "bid": 150.4,
        }

        with patch("quantum_terminal.infrastructure.market_data.tiingo_adapter.TiingoAdapter.get_latest_quote", new_callable=AsyncMock, return_value=mock_quote):
            quote = await get_latest_quote("AAPL")
            assert quote["last"] == 150.5


class TestMultipleAdapters:
    """Test handling of multiple adapters."""

    @pytest.mark.asyncio
    async def test_batch_performance_50_tickers(self, adapter, sample_historical):
        """Test batch performance with 50+ tickers."""
        tickers = [f"TICK{i:04d}" for i in range(50)]

        async def mock_historical(ticker, start_date, end_date):
            await asyncio.sleep(0.001)
            return pd.DataFrame(sample_historical)

        with patch.object(adapter, "get_historical", new_callable=AsyncMock, side_effect=mock_historical):
            import time
            start = time.time()
            data = await adapter.batch_historical(tickers)
            elapsed = time.time() - start

            assert len(data) == 50
            # Should be concurrent
            assert elapsed < 1.0
