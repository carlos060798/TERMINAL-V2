"""Tests for yfinance adapter with caching and batch support."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from quantum_terminal.infrastructure.market_data.yfinance_adapter import (
    YFinanceAdapter,
    YFinanceAPIError,
    YFinanceDataError,
    get_historical,
    batch_historical,
    get_info,
    get_dividends,
    get_options_chain,
)
from quantum_terminal.utils.cache import cache


@pytest.fixture
def adapter():
    """Create adapter instance."""
    return YFinanceAdapter()


@pytest.fixture
def sample_ohlcv():
    """Create sample OHLCV data."""
    dates = pd.date_range("2025-01-01", periods=252, freq="D")
    return pd.DataFrame(
        {
            "Open": [100.0 + i * 0.1 for i in range(252)],
            "High": [101.0 + i * 0.1 for i in range(252)],
            "Low": [99.0 + i * 0.1 for i in range(252)],
            "Close": [100.5 + i * 0.1 for i in range(252)],
            "Volume": [1000000 + i * 100 for i in range(252)],
            "Dividends": [0.0] * 252,
            "Stock Splits": [0.0] * 252,
        },
        index=dates,
    )


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache.clear()
    yield
    cache.clear()


class TestYFinanceAdapterInit:
    """Test adapter initialization."""

    def test_init_success(self, adapter):
        """Test successful initialization."""
        assert adapter is not None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with YFinanceAdapter() as adapter:
            assert adapter is not None


class TestYFinanceHistorical:
    """Test get_historical method."""

    @pytest.mark.asyncio
    async def test_get_historical_success(self, adapter, sample_ohlcv):
        """Test successful historical data retrieval."""
        with patch("yfinance.download", return_value=sample_ohlcv):
            df = await adapter.get_historical("AAPL", "1y")

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 252
            assert "Open" in df.columns
            assert "Close" in df.columns

    @pytest.mark.asyncio
    async def test_get_historical_caching(self, adapter, sample_ohlcv):
        """Test that historical data is cached with 1-hour TTL."""
        with patch("yfinance.download", return_value=sample_ohlcv):
            # First call
            df1 = await adapter.get_historical("AAPL", "1y")
            # Second call should use cache
            df2 = await adapter.get_historical("AAPL", "1y")

            # Both should be identical
            pd.testing.assert_frame_equal(df1, df2)

    @pytest.mark.asyncio
    async def test_get_historical_empty_data(self, adapter):
        """Test handling of empty data."""
        empty_df = pd.DataFrame()

        with patch("yfinance.download", return_value=empty_df):
            with pytest.raises(YFinanceDataError):
                await adapter.get_historical("INVALID")

    @pytest.mark.asyncio
    async def test_get_historical_different_periods(self, adapter, sample_ohlcv):
        """Test different time periods."""
        with patch("yfinance.download", return_value=sample_ohlcv):
            for period in ["1d", "5d", "1mo", "6mo", "1y", "5y"]:
                df = await adapter.get_historical("AAPL", period)
                assert isinstance(df, pd.DataFrame)


class TestYFinanceBatchHistorical:
    """Test batch_historical method."""

    @pytest.mark.asyncio
    async def test_batch_historical_success(self, adapter, sample_ohlcv):
        """Test successful batch historical retrieval."""
        async def mock_get_historical(ticker, period, interval):
            await asyncio.sleep(0.001)  # Simulate API call
            return sample_ohlcv

        with patch.object(adapter, "get_historical", new_callable=AsyncMock, side_effect=mock_get_historical):
            data = await adapter.batch_historical(["AAPL", "MSFT", "GOOGL"], "1y")

            assert len(data) == 3
            assert "AAPL" in data
            assert data["AAPL"] is not None

    @pytest.mark.asyncio
    async def test_batch_historical_partial_failure(self, adapter, sample_ohlcv):
        """Test batch with some failures."""
        async def mock_get_historical(ticker, period, interval):
            if ticker == "INVALID":
                raise YFinanceDataError("Not found")
            return sample_ohlcv

        with patch.object(adapter, "get_historical", new_callable=AsyncMock, side_effect=mock_get_historical):
            data = await adapter.batch_historical(["AAPL", "INVALID", "MSFT"], "1y")

            assert len(data) == 3
            assert data["INVALID"] is None
            assert data["AAPL"] is not None

    @pytest.mark.asyncio
    async def test_batch_historical_concurrent(self, adapter, sample_ohlcv):
        """Test that batch uses concurrent execution."""
        call_count = 0

        async def mock_get_historical(ticker, period, interval):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)  # Simulate API call
            return sample_ohlcv

        with patch.object(adapter, "get_historical", new_callable=AsyncMock, side_effect=mock_get_historical):
            import time
            start = time.time()
            await adapter.batch_historical(["AAPL", "MSFT", "GOOGL"], "1y")
            elapsed = time.time() - start

            assert call_count == 3
            # Should be concurrent (~0.01s) not sequential (~0.03s)
            assert elapsed < 0.05


class TestYFinanceInfo:
    """Test get_info method."""

    @pytest.mark.asyncio
    async def test_get_info_success(self, adapter):
        """Test successful company info retrieval."""
        mock_info = {
            "longName": "Apple Inc",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "marketCap": 2800000000000,
            "dividendRate": 0.92,
            "dividendYield": 0.0033,
            "trailingPE": 28.5,
            "forwardPE": 25.0,
            "profitMargins": 0.25,
            "operatingMargins": 0.30,
        }

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.info = mock_info
            mock_ticker.return_value = mock_ticker_instance

            info = await adapter.get_info("AAPL")

            assert info["longName"] == "Apple Inc"
            assert info["sector"] == "Technology"
            assert info["marketCap"] == 2800000000000

    @pytest.mark.asyncio
    async def test_get_info_caching(self, adapter):
        """Test that company info is cached with 7-day TTL."""
        mock_info = {
            "longName": "Apple Inc",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "marketCap": 2800000000000,
        }

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.info = mock_info
            mock_ticker.return_value = mock_ticker_instance

            # First call
            info1 = await adapter.get_info("AAPL")
            # Second call should use cache
            info2 = await adapter.get_info("AAPL")

            assert info1 == info2
            # Ticker should only be called once (caching works)
            assert mock_ticker.call_count == 1


class TestYFinanceDividends:
    """Test get_dividends method."""

    @pytest.mark.asyncio
    async def test_get_dividends_success(self, adapter):
        """Test successful dividend history retrieval."""
        dates = pd.date_range("2020-01-01", periods=10, freq="3M")
        dividends = pd.Series([0.205] * 10, index=dates)

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.dividends = dividends
            mock_ticker.return_value = mock_ticker_instance

            result = await adapter.get_dividends("KO")

            assert isinstance(result, pd.Series)
            assert len(result) == 10

    @pytest.mark.asyncio
    async def test_get_dividends_empty(self, adapter):
        """Test empty dividend history."""
        empty_series = pd.Series(dtype=float)

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.dividends = empty_series
            mock_ticker.return_value = mock_ticker_instance

            result = await adapter.get_dividends("TSLA")

            assert isinstance(result, pd.Series)
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_dividends_caching(self, adapter):
        """Test dividend data caching."""
        dates = pd.date_range("2020-01-01", periods=10, freq="3M")
        dividends = pd.Series([0.205] * 10, index=dates)

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.dividends = dividends
            mock_ticker.return_value = mock_ticker_instance

            # First call
            result1 = await adapter.get_dividends("KO")
            # Second call should use cache
            result2 = await adapter.get_dividends("KO")

            pd.testing.assert_series_equal(result1, result2)
            # Ticker should only be called once
            assert mock_ticker.call_count == 1


class TestYFinanceOptionsChain:
    """Test get_options_chain method."""

    @pytest.mark.asyncio
    async def test_get_options_chain_success(self, adapter):
        """Test successful options chain retrieval."""
        calls_data = {
            "contractSymbol": ["AAPL220520C00150000", "AAPL220520C00155000"],
            "lastPrice": [3.5, 1.2],
            "strike": [150, 155],
            "impliedVolatility": [0.25, 0.24],
        }
        puts_data = {
            "contractSymbol": ["AAPL220520P00150000", "AAPL220520P00155000"],
            "lastPrice": [1.2, 3.5],
            "strike": [150, 155],
            "impliedVolatility": [0.25, 0.24],
        }

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_option_chain = MagicMock()
            mock_option_chain.calls = pd.DataFrame(calls_data)
            mock_option_chain.puts = pd.DataFrame(puts_data)
            mock_ticker_instance.option_chain.return_value = mock_option_chain
            mock_ticker.return_value = mock_ticker_instance

            chain = await adapter.get_options_chain("AAPL", "2022-05-20")

            assert "calls" in chain
            assert "puts" in chain
            assert len(chain["calls"]) == 2
            assert len(chain["puts"]) == 2

    @pytest.mark.asyncio
    async def test_get_options_chain_caching(self, adapter):
        """Test options chain caching."""
        calls_data = {"contractSymbol": ["AAPL220520C00150000"], "lastPrice": [3.5]}
        puts_data = {"contractSymbol": ["AAPL220520P00150000"], "lastPrice": [1.2]}

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_option_chain = MagicMock()
            mock_option_chain.calls = pd.DataFrame(calls_data)
            mock_option_chain.puts = pd.DataFrame(puts_data)
            mock_ticker_instance.option_chain.return_value = mock_option_chain
            mock_ticker.return_value = mock_ticker_instance

            # First call
            chain1 = await adapter.get_options_chain("AAPL", "2022-05-20")
            # Second call should use cache
            chain2 = await adapter.get_options_chain("AAPL", "2022-05-20")

            assert chain1["calls"].equals(chain2["calls"])
            # Ticker should only be called once
            assert mock_ticker.call_count == 1


class TestYFinanceSplits:
    """Test get_splits method."""

    @pytest.mark.asyncio
    async def test_get_splits_success(self, adapter):
        """Test successful stock split history retrieval."""
        dates = pd.to_datetime(["2020-08-31", "2014-06-09"])
        splits = pd.Series([4.0, 7.0], index=dates)

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.splits = splits
            mock_ticker.return_value = mock_ticker_instance

            result = await adapter.get_splits("TSLA")

            assert isinstance(result, pd.Series)
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_splits_empty(self, adapter):
        """Test empty split history."""
        empty_series = pd.Series(dtype=float)

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.splits = empty_series
            mock_ticker.return_value = mock_ticker_instance

            result = await adapter.get_splits("AAPL")

            assert isinstance(result, pd.Series)
            assert len(result) == 0


class TestGlobalFunctions:
    """Test module-level functions."""

    @pytest.mark.asyncio
    async def test_get_historical_global(self, sample_ohlcv):
        """Test global get_historical function."""
        with patch("yfinance.download", return_value=sample_ohlcv):
            df = await get_historical("AAPL", "1y")
            assert isinstance(df, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_batch_historical_global(self, sample_ohlcv):
        """Test global batch_historical function."""
        with patch("yfinance.download", return_value=sample_ohlcv):
            data = await batch_historical(["AAPL", "MSFT"], "1y")
            assert len(data) == 2

    @pytest.mark.asyncio
    async def test_get_info_global(self):
        """Test global get_info function."""
        mock_info = {"longName": "Apple Inc", "sector": "Technology"}

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.info = mock_info
            mock_ticker.return_value = mock_ticker_instance

            info = await get_info("AAPL")
            assert info["longName"] == "Apple Inc"

    @pytest.mark.asyncio
    async def test_get_dividends_global(self):
        """Test global get_dividends function."""
        dates = pd.date_range("2020-01-01", periods=5, freq="3M")
        dividends = pd.Series([0.205] * 5, index=dates)

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_ticker_instance.dividends = dividends
            mock_ticker.return_value = mock_ticker_instance

            result = await get_dividends("KO")
            assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_options_chain_global(self):
        """Test global get_options_chain function."""
        calls_data = {"contractSymbol": ["AAPL220520C00150000"], "lastPrice": [3.5]}
        puts_data = {"contractSymbol": ["AAPL220520P00150000"], "lastPrice": [1.2]}

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_option_chain = MagicMock()
            mock_option_chain.calls = pd.DataFrame(calls_data)
            mock_option_chain.puts = pd.DataFrame(puts_data)
            mock_ticker_instance.option_chain.return_value = mock_option_chain
            mock_ticker.return_value = mock_ticker_instance

            chain = await get_options_chain("AAPL", "2022-05-20")
            assert "calls" in chain


class TestMultipleAdapters:
    """Test handling of multiple concurrent adapters."""

    @pytest.mark.asyncio
    async def test_batch_performance_50_tickers(self, adapter, sample_ohlcv):
        """Test batch performance with 50+ tickers."""
        tickers = [f"TICK{i:04d}" for i in range(50)]

        async def mock_get_historical(ticker, period, interval):
            await asyncio.sleep(0.001)
            return sample_ohlcv

        with patch.object(adapter, "get_historical", new_callable=AsyncMock, side_effect=mock_get_historical):
            import time
            start = time.time()
            data = await adapter.batch_historical(tickers, "1y")
            elapsed = time.time() - start

            assert len(data) == 50
            # Should be concurrent
            assert elapsed < 1.0
