"""Tests for FMP adapter with rate limiting, caching, and batch support."""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from quantum_terminal.infrastructure.market_data.fmp_adapter import (
    FMPAdapter,
    FMPAPIError,
    FMPRateLimitError,
    FMPHTTPError,
    get_ratios,
    get_key_metrics,
    get_company_profile,
    get_peers,
    batch_profiles,
)
from quantum_terminal.utils.cache import cache
from quantum_terminal.utils.rate_limiter import rate_limiter


@pytest.fixture
def adapter():
    """Create adapter instance with mock API key."""
    with patch.dict(os.environ, {"FMP_API_KEY": "test_key"}):
        return FMPAdapter()


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter before each test."""
    rate_limiter.reset("fmp")
    yield
    rate_limiter.reset("fmp")


class TestFMPAdapterInit:
    """Test adapter initialization."""

    def test_init_with_api_key(self):
        """Test initialization with provided API key."""
        adapter = FMPAdapter(api_key="test_key_123")
        assert adapter.api_key == "test_key_123"

    def test_init_from_environment(self):
        """Test initialization from environment variable."""
        with patch.dict(os.environ, {"FMP_API_KEY": "env_key"}):
            adapter = FMPAdapter()
            assert adapter.api_key == "env_key"

    def test_init_without_api_key(self):
        """Test initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="FMP_API_KEY"):
                FMPAdapter()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with FMPAdapter(api_key="test") as adapter:
            assert adapter.session is not None
        assert adapter.session.closed


class TestFMPRatios:
    """Test get_ratios method."""

    @pytest.mark.asyncio
    async def test_get_ratios_success(self, adapter):
        """Test successful ratios retrieval."""
        mock_response = [
            {
                "peRatio": 28.5,
                "pbRatio": 35.2,
                "psRatio": 8.5,
                "roe": 0.90,
                "roa": 0.16,
                "debtRatio": 0.15,
                "currentRatio": 1.2,
                "quickRatio": 0.9,
                "operatingProfitMargin": 0.30,
            }
        ]

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            ratios = await adapter.get_ratios("AAPL")

            assert ratios["peRatio"] == 28.5
            assert ratios["roe"] == 0.90
            assert ratios["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_get_ratios_caching(self, adapter):
        """Test that ratios are cached with 1-day TTL."""
        mock_response = [{"peRatio": 28.5, "roe": 0.90}]

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            # First call
            ratios1 = await adapter.get_ratios("AAPL")
            # Second call should use cache
            ratios2 = await adapter.get_ratios("AAPL")

            # _get should only be called once
            adapter._get.assert_called_once()

            assert ratios1 == ratios2

    @pytest.mark.asyncio
    async def test_get_ratios_empty_response(self, adapter):
        """Test handling of empty response."""
        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=[]):
            with pytest.raises(FMPAPIError):
                await adapter.get_ratios("INVALID")

    @pytest.mark.asyncio
    async def test_get_ratios_dict_response(self, adapter):
        """Test handling of dict response (not list)."""
        mock_response = {"peRatio": 28.5, "roe": 0.90}

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            ratios = await adapter.get_ratios("AAPL")

            assert ratios["peRatio"] == 28.5


class TestFMPKeyMetrics:
    """Test get_key_metrics method."""

    @pytest.mark.asyncio
    async def test_get_key_metrics_success(self, adapter):
        """Test successful metrics retrieval."""
        mock_response = [
            {
                "marketCap": 2800000000000,
                "sharesOutstanding": 16500000000,
                "bookValue": 27.5,
                "tangibleBookValue": 25.0,
                "eps": 5.61,
                "bvps": 3.28,
                "pbRatio": 35.2,
                "peRatio": 28.5,
            }
        ]

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            metrics = await adapter.get_key_metrics("AAPL")

            assert metrics["marketCap"] == 2800000000000
            assert metrics["eps"] == 5.61

    @pytest.mark.asyncio
    async def test_get_key_metrics_caching(self, adapter):
        """Test metrics caching."""
        mock_response = [{"marketCap": 2800000000000, "eps": 5.61}]

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            # First call
            metrics1 = await adapter.get_key_metrics("AAPL")
            # Second call should use cache
            metrics2 = await adapter.get_key_metrics("AAPL")

            adapter._get.assert_called_once()
            assert metrics1 == metrics2

    @pytest.mark.asyncio
    async def test_get_key_metrics_empty(self, adapter):
        """Test handling of empty metrics response."""
        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=[]):
            with pytest.raises(FMPAPIError):
                await adapter.get_key_metrics("INVALID")


class TestFMPCompanyProfile:
    """Test get_company_profile method."""

    @pytest.mark.asyncio
    async def test_get_company_profile_success(self, adapter):
        """Test successful profile retrieval."""
        mock_response = [
            {
                "companyName": "Apple Inc",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "country": "US",
                "marketCap": 2800000000000,
                "employees": 164000,
                "website": "https://www.apple.com",
            }
        ]

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            profile = await adapter.get_company_profile("AAPL")

            assert profile["companyName"] == "Apple Inc"
            assert profile["sector"] == "Technology"

    @pytest.mark.asyncio
    async def test_get_company_profile_caching(self, adapter):
        """Test profile caching with 7-day TTL."""
        mock_response = [
            {
                "companyName": "Apple Inc",
                "sector": "Technology",
                "industry": "Consumer Electronics",
            }
        ]

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            # First call
            profile1 = await adapter.get_company_profile("AAPL")
            # Second call should use cache
            profile2 = await adapter.get_company_profile("AAPL")

            adapter._get.assert_called_once()
            assert profile1 == profile2


class TestFMPPeers:
    """Test get_peers method."""

    @pytest.mark.asyncio
    async def test_get_peers_success(self, adapter):
        """Test successful peers retrieval."""
        mock_response = ["MSFT", "GOOGL", "NVDA", "META"]

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            peers = await adapter.get_peers("AAPL")

            assert len(peers) == 4
            assert "MSFT" in peers

    @pytest.mark.asyncio
    async def test_get_peers_dict_response(self, adapter):
        """Test handling of dict response."""
        mock_response = {"peersList": ["MSFT", "GOOGL", "NVDA"]}

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            peers = await adapter.get_peers("AAPL")

            assert len(peers) == 3

    @pytest.mark.asyncio
    async def test_get_peers_caching(self, adapter):
        """Test peers caching."""
        mock_response = ["MSFT", "GOOGL"]

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            # First call
            peers1 = await adapter.get_peers("AAPL")
            # Second call should use cache
            peers2 = await adapter.get_peers("AAPL")

            adapter._get.assert_called_once()
            assert peers1 == peers2

    @pytest.mark.asyncio
    async def test_get_peers_empty(self, adapter):
        """Test empty peers response."""
        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=None):
            peers = await adapter.get_peers("AAPL")

            assert peers == []


class TestFMPBatchProfiles:
    """Test batch_profiles method."""

    @pytest.mark.asyncio
    async def test_batch_profiles_success(self, adapter):
        """Test successful batch profile retrieval."""
        mock_responses = [
            {
                "companyName": "Apple Inc",
                "sector": "Technology",
                "industry": "Consumer Electronics",
            },
            {
                "companyName": "Microsoft Corp",
                "sector": "Technology",
                "industry": "Software",
            },
        ]

        async def mock_get_profile(ticker):
            await asyncio.sleep(0.001)
            return mock_responses[0] if ticker == "AAPL" else mock_responses[1]

        with patch.object(adapter, "get_company_profile", new_callable=AsyncMock, side_effect=mock_get_profile):
            profiles = await adapter.batch_profiles(["AAPL", "MSFT"])

            assert len(profiles) == 2
            assert "AAPL" in profiles
            assert profiles["AAPL"]["companyName"] == "Apple Inc"

    @pytest.mark.asyncio
    async def test_batch_profiles_partial_failure(self, adapter):
        """Test batch with some failures."""
        async def mock_get_profile(ticker):
            if ticker == "INVALID":
                raise FMPAPIError("Not found")
            return {"companyName": ticker, "sector": "Technology"}

        with patch.object(adapter, "get_company_profile", new_callable=AsyncMock, side_effect=mock_get_profile):
            profiles = await adapter.batch_profiles(["AAPL", "INVALID", "MSFT"])

            assert len(profiles) == 3
            assert "error" in profiles["INVALID"]
            assert profiles["AAPL"]["companyName"] == "AAPL"

    @pytest.mark.asyncio
    async def test_batch_profiles_concurrent(self, adapter):
        """Test concurrent execution."""
        call_times = []

        async def mock_get_profile(ticker):
            call_times.append(ticker)
            await asyncio.sleep(0.01)
            return {"companyName": ticker}

        with patch.object(adapter, "get_company_profile", new_callable=AsyncMock, side_effect=mock_get_profile):
            import time
            start = time.time()
            await adapter.batch_profiles(["AAPL", "MSFT", "GOOGL"])
            elapsed = time.time() - start

            # Should be concurrent
            assert elapsed < 0.05


class TestFMPAPIGetMethod:
    """Test internal _get method."""

    @pytest.mark.asyncio
    async def test_get_rate_limit_exceeded(self, adapter):
        """Test rate limit enforcement."""
        rate_limiter.get("fmp").tokens = 0

        with pytest.raises(FMPRateLimitError):
            await adapter._get("quote")

    @pytest.mark.asyncio
    async def test_get_http_error(self, adapter):
        """Test HTTP error handling."""
        import aiohttp

        with patch.object(adapter, "session", MagicMock()):
            mock_response = MagicMock()
            mock_response.status = 404
            adapter.session.get.return_value.__aenter__.return_value = mock_response

            with pytest.raises(FMPHTTPError):
                await adapter._get("quote")

    @pytest.mark.asyncio
    async def test_get_connection_error(self, adapter):
        """Test connection error handling."""
        import aiohttp

        adapter.session = MagicMock()
        adapter.session.get.side_effect = aiohttp.ClientError("Connection failed")

        with pytest.raises(Exception):  # ConnectionError wrapped in try-catch
            await adapter._get("quote")


class TestGlobalFunctions:
    """Test module-level functions."""

    @pytest.mark.asyncio
    async def test_get_ratios_global(self):
        """Test global get_ratios function."""
        mock_response = [{"peRatio": 28.5}]

        with patch("quantum_terminal.infrastructure.market_data.fmp_adapter.FMPAdapter.get_ratios", new_callable=AsyncMock, return_value=mock_response[0]):
            ratios = await get_ratios("AAPL")
            assert ratios["peRatio"] == 28.5

    @pytest.mark.asyncio
    async def test_get_key_metrics_global(self):
        """Test global get_key_metrics function."""
        mock_response = {"marketCap": 2800000000000}

        with patch("quantum_terminal.infrastructure.market_data.fmp_adapter.FMPAdapter.get_key_metrics", new_callable=AsyncMock, return_value=mock_response):
            metrics = await get_key_metrics("AAPL")
            assert metrics["marketCap"] == 2800000000000

    @pytest.mark.asyncio
    async def test_batch_profiles_global(self):
        """Test global batch_profiles function."""
        expected = {
            "AAPL": {"companyName": "Apple Inc"},
            "MSFT": {"companyName": "Microsoft Corp"},
        }

        with patch("quantum_terminal.infrastructure.market_data.fmp_adapter.FMPAdapter.batch_profiles", new_callable=AsyncMock, return_value=expected):
            profiles = await batch_profiles(["AAPL", "MSFT"])
            assert len(profiles) == 2


class TestMultipleAdapters:
    """Test handling of multiple adapters."""

    @pytest.mark.asyncio
    async def test_batch_performance_50_tickers(self, adapter):
        """Test batch performance with 50+ tickers."""
        tickers = [f"TICK{i:04d}" for i in range(50)]

        async def mock_profile(ticker):
            await asyncio.sleep(0.001)
            return {"companyName": ticker, "sector": "Technology"}

        with patch.object(adapter, "get_company_profile", new_callable=AsyncMock, side_effect=mock_profile):
            import time
            start = time.time()
            profiles = await adapter.batch_profiles(tickers)
            elapsed = time.time() - start

            assert len(profiles) == 50
            # Should be concurrent
            assert elapsed < 1.0
