"""Tests for Finnhub adapter with rate limiting, caching, and error handling."""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quantum_terminal.infrastructure.market_data.finnhub_adapter import (
    FinnhubAdapter,
    FinnhubAPIError,
    FinnhubRateLimitError,
    FinnhubHTTPError,
    FinnhubConnectionError,
    batch_quotes,
    get_quote,
)
from quantum_terminal.utils.cache import cache
from quantum_terminal.utils.rate_limiter import rate_limiter


@pytest.fixture
def adapter():
    """Create adapter instance with mock API key."""
    with patch.dict(os.environ, {"FINNHUB_API_KEY": "test_key"}):
        return FinnhubAdapter()


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter before each test."""
    rate_limiter.reset("finnhub")
    yield
    rate_limiter.reset("finnhub")


class TestFinnhubAdapterInit:
    """Test adapter initialization."""

    def test_init_with_api_key(self):
        """Test initialization with provided API key."""
        adapter = FinnhubAdapter(api_key="test_key_123")
        assert adapter.api_key == "test_key_123"

    def test_init_from_environment(self):
        """Test initialization from environment variable."""
        with patch.dict(os.environ, {"FINNHUB_API_KEY": "env_key"}):
            adapter = FinnhubAdapter()
            assert adapter.api_key == "env_key"

    def test_init_without_api_key(self):
        """Test initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="FINNHUB_API_KEY"):
                FinnhubAdapter()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with FinnhubAdapter(api_key="test") as adapter:
            assert adapter.session is not None
        assert adapter.session.closed


class TestFinnhubQuote:
    """Test get_quote method."""

    @pytest.mark.asyncio
    async def test_get_quote_success(self, adapter):
        """Test successful quote retrieval."""
        mock_response = {
            "c": 150.5,
            "b": 150.4,
            "a": 150.6,
            "h": 152.0,
            "l": 149.0,
            "o": 150.0,
            "pc": 149.8,
            "t": 1680000000,
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            quote = await adapter.get_quote("AAPL")

            assert quote["ticker"] == "AAPL"
            assert quote["price"] == 150.5
            assert quote["bid"] == 150.4
            assert quote["ask"] == 150.6

    @pytest.mark.asyncio
    async def test_get_quote_caching(self, adapter):
        """Test that quotes are cached with 1-minute TTL."""
        mock_response = {"c": 150.5, "b": 150.4, "a": 150.6, "t": 1680000000}

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            # First call
            quote1 = await adapter.get_quote("AAPL")
            # Second call should use cache
            quote2 = await adapter.get_quote("AAPL")

            # _get should only be called once
            adapter._get.assert_called_once()

            assert quote1 == quote2

    @pytest.mark.asyncio
    async def test_get_quote_rate_limit(self, adapter):
        """Test rate limit enforcement."""
        # Exhaust rate limit
        rate_limiter.get("finnhub").tokens = 0

        with pytest.raises(FinnhubRateLimitError):
            await adapter.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_get_quote_http_error(self, adapter):
        """Test HTTP error handling."""
        with patch.object(
            adapter, "_get", new_callable=AsyncMock, side_effect=FinnhubHTTPError("400: Bad request")
        ):
            with pytest.raises(FinnhubAPIError):
                await adapter.get_quote("INVALID")

    @pytest.mark.asyncio
    async def test_get_quote_missing_api_key(self, adapter):
        """Test handling of invalid API key."""
        with patch.object(adapter, "_get", new_callable=AsyncMock, side_effect=FinnhubAPIError("Invalid API key")):
            with pytest.raises(FinnhubAPIError):
                await adapter.get_quote("AAPL")


class TestFinnhubBatchQuotes:
    """Test batch_quotes method."""

    @pytest.mark.asyncio
    async def test_batch_quotes_success(self, adapter):
        """Test successful batch quote retrieval."""
        mock_responses = [
            {"c": 150.5, "b": 150.4, "a": 150.6, "t": 1680000000},  # AAPL
            {"c": 300.0, "b": 299.9, "a": 300.1, "t": 1680000000},  # MSFT
            {"c": 2800.0, "b": 2799.5, "a": 2800.5, "t": 1680000000},  # GOOGL
        ]

        with patch.object(adapter, "get_quote", new_callable=AsyncMock, side_effect=mock_responses):
            quotes = await adapter.batch_quotes(["AAPL", "MSFT", "GOOGL"])

            assert len(quotes) == 3
            assert "AAPL" in quotes
            assert quotes["AAPL"]["price"] == 150.5

    @pytest.mark.asyncio
    async def test_batch_quotes_partial_failure(self, adapter):
        """Test batch quotes with some failures."""
        async def mock_get_quote(ticker):
            if ticker == "INVALID":
                raise FinnhubAPIError("Not found")
            return {"c": 100.0, "t": 1680000000}

        with patch.object(adapter, "get_quote", new_callable=AsyncMock, side_effect=mock_get_quote):
            quotes = await adapter.batch_quotes(["AAPL", "INVALID", "MSFT"])

            assert len(quotes) == 3
            assert "error" in quotes["INVALID"]
            assert quotes["AAPL"]["price"] == 100.0

    @pytest.mark.asyncio
    async def test_batch_quotes_concurrent(self, adapter):
        """Test that batch quotes uses concurrent execution."""
        call_times = []

        async def mock_get_quote(ticker):
            call_times.append(ticker)
            await asyncio.sleep(0.01)  # Simulate API call
            return {"c": 100.0, "t": 1680000000}

        with patch.object(adapter, "get_quote", new_callable=AsyncMock, side_effect=mock_get_quote):
            import time
            start = time.time()
            await adapter.batch_quotes(["AAPL", "MSFT", "GOOGL"])
            elapsed = time.time() - start

            # Should be ~0.01s (concurrent) not ~0.03s (sequential)
            assert elapsed < 0.05


class TestFinnhubCompanyProfile:
    """Test get_company_profile method."""

    @pytest.mark.asyncio
    async def test_company_profile_success(self, adapter):
        """Test successful company profile retrieval."""
        mock_response = {
            "name": "Apple Inc",
            "exchange": "NASDAQ",
            "finnhubIndustry": "Technology",
            "marketCapitalization": 2800000,
            "country": "US",
            "currency": "USD",
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            profile = await adapter.get_company_profile("AAPL")

            assert profile["name"] == "Apple Inc"
            assert profile["sector"] == "Technology"
            assert profile["country"] == "US"

    @pytest.mark.asyncio
    async def test_company_profile_caching(self, adapter):
        """Test that company profiles are cached with 7-day TTL."""
        mock_response = {
            "name": "Apple Inc",
            "exchange": "NASDAQ",
            "finnhubIndustry": "Technology",
            "marketCapitalization": 2800000,
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            # First call
            profile1 = await adapter.get_company_profile("AAPL")
            # Second call should use cache
            profile2 = await adapter.get_company_profile("AAPL")

            # _get should only be called once
            adapter._get.assert_called_once()

            assert profile1 == profile2


class TestFinnhubEarningsCalendar:
    """Test get_earnings_calendar method."""

    @pytest.mark.asyncio
    async def test_earnings_calendar_success(self, adapter):
        """Test successful earnings calendar retrieval."""
        mock_response = {
            "earningsCalendar": [
                {
                    "ticker": "AAPL",
                    "date": "2026-05-15",
                    "epsEstimate": 1.25,
                    "epsActual": 1.30,
                },
                {
                    "ticker": "MSFT",
                    "date": "2026-05-20",
                    "epsEstimate": 2.50,
                    "epsActual": None,
                },
            ]
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            earnings = await adapter.get_earnings_calendar("2026-01-01", "2026-12-31")

            assert len(earnings) == 2
            assert earnings[0]["ticker"] == "AAPL"
            assert earnings[0]["epsActual"] == 1.30

    @pytest.mark.asyncio
    async def test_earnings_calendar_empty(self, adapter):
        """Test empty earnings calendar response."""
        mock_response = {"earningsCalendar": []}

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            earnings = await adapter.get_earnings_calendar()

            assert earnings == []


class TestFinnhubAPIGetMethod:
    """Test internal _get method."""

    @pytest.mark.asyncio
    async def test_get_success(self, adapter):
        """Test successful API call."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"c": 150.5})
            mock_get.return_value.__aenter__.return_value = mock_response

            with patch.object(adapter, "session") as mock_session:
                mock_session.get.return_value.__aenter__.return_value = mock_response

                result = await adapter._get("quote", {"symbol": "AAPL"})

                assert result["c"] == 150.5

    @pytest.mark.asyncio
    async def test_get_connection_error(self, adapter):
        """Test connection error handling."""
        import aiohttp

        with patch.object(
            adapter,
            "session",
            MagicMock(side_effect=aiohttp.ClientError("Connection refused")),
        ):
            adapter.session = MagicMock()
            adapter.session.get.side_effect = aiohttp.ClientError("Connection refused")

            with pytest.raises(FinnhubConnectionError):
                await adapter._get("quote")

    @pytest.mark.asyncio
    async def test_get_rate_limit_exceeded(self, adapter):
        """Test rate limit exceeded response."""
        rate_limiter.get("finnhub").tokens = 0

        with pytest.raises(FinnhubRateLimitError):
            await adapter._get("quote")


class TestGlobalFunctions:
    """Test module-level functions."""

    @pytest.mark.asyncio
    async def test_get_quote_global(self):
        """Test global get_quote function."""
        mock_response = {"c": 150.5, "b": 150.4, "a": 150.6, "t": 1680000000}

        with patch("quantum_terminal.infrastructure.market_data.finnhub_adapter.FinnhubAdapter.get_quote", new_callable=AsyncMock, return_value=mock_response):
            quote = await get_quote("AAPL")
            assert quote["c"] == 150.5

    @pytest.mark.asyncio
    async def test_batch_quotes_global(self):
        """Test global batch_quotes function."""
        expected = {
            "AAPL": {"c": 150.5, "t": 1680000000},
            "MSFT": {"c": 300.0, "t": 1680000000},
        }

        with patch("quantum_terminal.infrastructure.market_data.finnhub_adapter.FinnhubAdapter.batch_quotes", new_callable=AsyncMock, return_value=expected):
            quotes = await batch_quotes(["AAPL", "MSFT"])
            assert len(quotes) == 2


class TestMultipleAdapters:
    """Test handling of multiple concurrent adapters."""

    @pytest.mark.asyncio
    async def test_multiple_tickers_performance(self, adapter):
        """Test batch performance with 50+ tickers."""
        tickers = [f"TICK{i:04d}" for i in range(50)]

        async def mock_quote(ticker):
            await asyncio.sleep(0.001)
            return {"ticker": ticker, "price": 100.0 + float(ticker[-4:]), "t": 1680000000}

        with patch.object(adapter, "get_quote", new_callable=AsyncMock, side_effect=mock_quote):
            import time
            start = time.time()
            quotes = await adapter.batch_quotes(tickers)
            elapsed = time.time() - start

            assert len(quotes) == 50
            # Should be concurrent (< 1 second) not sequential (2.5 seconds)
            assert elapsed < 1.0
