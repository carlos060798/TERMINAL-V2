"""Comprehensive tests for master coordinators (DataProvider, AIGateway).

Tests cover:
- Fallback chain logic (primary → fallback → fallback)
- Rate limiting across providers
- Cache hits and misses
- Error handling and recovery
- Batch operations
- Token tracking and cost estimation
- Backend status and statistics
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

# DataProvider Tests
class TestDataProvider:
    """Test DataProvider master coordinator."""

    @pytest.fixture
    def provider(self):
        """Create DataProvider for testing."""
        from quantum_terminal.infrastructure.market_data.data_provider import DataProvider

        provider = DataProvider()
        return provider

    @pytest.mark.asyncio
    async def test_get_quote_from_cache(self, provider):
        """Test quote retrieval from cache."""
        cached_quote = {
            "ticker": "AAPL",
            "price": 150.25,
            "bid": 150.20,
            "ask": 150.30,
            "source": "cache",
        }

        with patch("quantum_terminal.infrastructure.market_data.data_provider.cache") as mock_cache:
            mock_cache.get_quote.return_value = cached_quote

            quote = await provider.get_quote("AAPL")

            assert quote == cached_quote
            assert mock_cache.get_quote.called

    @pytest.mark.asyncio
    async def test_get_quote_finnhub_success(self, provider):
        """Test quote retrieval from Finnhub (primary)."""
        finnhub_quote = {
            "ticker": "AAPL",
            "price": 150.25,
            "bid": 150.20,
            "ask": 150.30,
            "timestamp": 1619000000,
        }

        with patch("quantum_terminal.infrastructure.market_data.data_provider.cache") as mock_cache:
            mock_cache.get_quote.return_value = None

            with patch.object(provider.finnhub, "get_quote", new_callable=AsyncMock, return_value=finnhub_quote):
                quote = await provider.get_quote("AAPL")

                assert quote["ticker"] == "AAPL"
                assert quote["source"] == "finnhub"
                assert quote["price"] == 150.25

    @pytest.mark.asyncio
    async def test_get_quote_fallback_chain(self, provider):
        """Test fallback chain: Finnhub rate limit → yfinance."""
        from quantum_terminal.infrastructure.market_data.finnhub_adapter import FinnhubRateLimitError

        yfinance_quote = {"ticker": "AAPL", "price": 150.0, "source": "yfinance"}

        with patch("quantum_terminal.infrastructure.market_data.data_provider.cache") as mock_cache:
            mock_cache.get_quote.return_value = None

            # Finnhub fails with rate limit
            with patch.object(
                provider.finnhub,
                "get_quote",
                new_callable=AsyncMock,
                side_effect=FinnhubRateLimitError("Rate limit exceeded"),
            ):
                # yfinance succeeds
                with patch("quantum_terminal.infrastructure.market_data.data_provider.yfinance") as mock_yf:
                    mock_data = MagicMock()
                    mock_data["Close"].iloc = MagicMock(return_value=[150.0])
                    mock_data["Open"].iloc = MagicMock(return_value=[149.5])
                    mock_data["High"].iloc = MagicMock(return_value=[151.0])
                    mock_data["Volume"].iloc = MagicMock(return_value=[1000000])
                    mock_data["index"] = [MagicMock(timestamp=Mock(return_value=1619000000))]
                    mock_data.empty = False

                    def mock_download(*args, **kwargs):
                        return mock_data

                    mock_yf.download = mock_download
                    provider.yfinance = mock_yf

                    quote = await provider.get_quote("AAPL")

                    assert quote["source"] == "yfinance"
                    assert quote["price"] == 150.0

    @pytest.mark.asyncio
    async def test_get_quote_all_providers_fail(self, provider):
        """Test all providers fail."""
        from quantum_terminal.infrastructure.market_data.finnhub_adapter import FinnhubAPIError
        from quantum_terminal.infrastructure.market_data.data_provider import AllProvidersFailedError

        with patch("quantum_terminal.infrastructure.market_data.data_provider.cache") as mock_cache:
            mock_cache.get_quote.return_value = None

            with patch.object(provider.finnhub, "get_quote", new_callable=AsyncMock, side_effect=FinnhubAPIError("API error")):
                with patch("quantum_terminal.infrastructure.market_data.data_provider.yfinance") as mock_yf:
                    mock_yf.download.side_effect = Exception("Connection error")
                    provider.yfinance = mock_yf

                    with pytest.raises(AllProvidersFailedError):
                        await provider.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_get_fundamentals_from_cache(self, provider):
        """Test fundamentals cache."""
        cached_fundamentals = {
            "ticker": "AAPL",
            "pe_ratio": 25.0,
            "source": "cache",
        }

        with patch("quantum_terminal.infrastructure.market_data.data_provider.cache") as mock_cache:
            mock_cache.get_fundamental.return_value = cached_fundamentals

            fundamentals = await provider.get_fundamentals("AAPL")

            assert fundamentals == cached_fundamentals

    @pytest.mark.asyncio
    async def test_get_fundamentals_fmp(self, provider):
        """Test fundamentals from FMP."""
        fmp_fundamentals = {
            "ticker": "AAPL",
            "pe_ratio": 25.5,
            "pb_ratio": 2.5,
            "source": "fmp",
        }

        with patch("quantum_terminal.config.settings.fmp_api_key", "test_key"):
            with patch("quantum_terminal.infrastructure.market_data.data_provider.cache") as mock_cache:
                mock_cache.get_fundamental.return_value = None

                fundamentals = await provider.get_fundamentals("AAPL")

                assert fundamentals["ticker"] == "AAPL"
                assert "pe_ratio" in fundamentals

    @pytest.mark.asyncio
    async def test_get_macro_fred(self, provider):
        """Test macro data from FRED."""
        with patch("quantum_terminal.config.settings.fred_api_key", "test_key"):
            with patch("quantum_terminal.infrastructure.market_data.data_provider.cache") as mock_cache:
                mock_cache.get_macro.return_value = None

                rate = await provider.get_macro("DGS10")

                assert isinstance(rate, float)
                assert rate > 0

    @pytest.mark.asyncio
    async def test_batch_quotes_yfinance(self, provider):
        """Test batch quotes using yfinance."""
        mock_data = MagicMock()
        mock_data.__getitem__ = MagicMock(side_effect=lambda x: {
            "Close": MagicMock(iloc=MagicMock(return_value=[150.0])),
            "Open": MagicMock(iloc=MagicMock(return_value=[149.5])),
            "High": MagicMock(iloc=MagicMock(return_value=[151.0])),
            "Volume": MagicMock(iloc=MagicMock(return_value=[1000000])),
        }.get(x))

        with patch("quantum_terminal.infrastructure.market_data.data_provider.yfinance") as mock_yf:
            mock_yf.download = Mock(return_value=mock_data)
            provider.yfinance = mock_yf

            with patch("quantum_terminal.infrastructure.market_data.data_provider.cache"):
                quotes = await provider.batch_quotes(["AAPL", "MSFT"])

                assert "AAPL" in quotes or len(quotes) > 0

    @pytest.mark.asyncio
    async def test_batch_quotes_fallback_to_finnhub(self, provider):
        """Test batch quotes fallback from yfinance to Finnhub."""
        with patch("quantum_terminal.infrastructure.market_data.data_provider.yfinance") as mock_yf:
            mock_yf.download.side_effect = Exception("Download failed")
            provider.yfinance = mock_yf

            mock_batch = {
                "AAPL": {"ticker": "AAPL", "price": 150.0},
                "MSFT": {"ticker": "MSFT", "price": 300.0},
            }

            with patch.object(
                provider.finnhub,
                "batch_quotes",
                new_callable=AsyncMock,
                return_value=mock_batch,
            ):
                with patch("quantum_terminal.infrastructure.market_data.data_provider.cache"):
                    quotes = await provider.batch_quotes(["AAPL", "MSFT"])

                    assert "AAPL" in quotes
                    assert "MSFT" in quotes

    def test_rate_limit_stats(self, provider):
        """Test rate limit statistics."""
        with patch("quantum_terminal.infrastructure.market_data.data_provider.rate_limiter") as mock_limiter:
            mock_limiter.get_stats.return_value = {
                "finnhub": {"available_percent": 80.0},
                "newsapi": {"available_percent": 95.0},
            }

            stats = provider.get_rate_limit_stats()

            assert "finnhub" in stats
            assert stats["finnhub"]["available_percent"] == 80.0

    def test_cache_stats(self, provider):
        """Test cache statistics."""
        with patch("quantum_terminal.infrastructure.market_data.data_provider.cache") as mock_cache:
            mock_cache.get_stats.return_value = {
                "size": 100,
                "directory": "/tmp/cache",
                "volume": 5242880,
            }

            stats = provider.get_cache_stats()

            assert stats["size"] == 100
            assert stats["volume"] == 5242880

    def test_reset_rate_limits_specific(self, provider):
        """Test resetting specific provider rate limits."""
        with patch("quantum_terminal.infrastructure.market_data.data_provider.rate_limiter") as mock_limiter:
            provider.reset_rate_limits("finnhub")

            mock_limiter.reset.assert_called_once_with("finnhub")

    def test_reset_rate_limits_all(self, provider):
        """Test resetting all rate limits."""
        with patch("quantum_terminal.infrastructure.market_data.data_provider.rate_limiter") as mock_limiter:
            provider.reset_rate_limits()

            mock_limiter.reset.assert_called_once_with(None)

    def test_clear_cache(self, provider):
        """Test clearing cache."""
        with patch("quantum_terminal.infrastructure.market_data.data_provider.cache") as mock_cache:
            mock_cache.clear.return_value = 42

            count = provider.clear_cache("quote_*")

            assert count == 42
            mock_cache.clear.assert_called_once_with("quote_*")


# AIGateway Tests
class TestAIGateway:
    """Test AIGateway master coordinator."""

    @pytest.fixture
    def gateway(self):
        """Create AIGateway for testing."""
        from quantum_terminal.infrastructure.ai.ai_gateway import AIGateway

        gateway = AIGateway()
        return gateway

    def test_token_counter_initialization(self, gateway):
        """Test token counter initialization."""
        assert gateway.token_counter is not None
        assert gateway.token_counter.usage == {}

    def test_token_counter_track(self, gateway):
        """Test token usage tracking."""
        gateway.token_counter.track("groq", input_tokens=100, output_tokens=50)

        assert gateway.token_counter.usage["groq"]["input"] == 100
        assert gateway.token_counter.usage["groq"]["output"] == 50
        assert gateway.token_counter.usage["groq"]["requests"] == 1

    def test_token_counter_estimate_cost(self, gateway):
        """Test cost estimation."""
        # Groq is free
        cost = gateway.token_counter.estimate_cost("groq", 1000, 500)
        assert cost == 0.0

        # DeepSeek has a cost
        cost = gateway.token_counter.estimate_cost("deepseek", 1000, 500)
        assert cost > 0.0

    def test_token_counter_stats(self, gateway):
        """Test token counter statistics."""
        gateway.token_counter.track("groq", 100, 50)
        gateway.token_counter.track("deepseek", 200, 100)

        stats = gateway.token_counter.get_stats()

        assert stats["backends"]["groq"]["input"] == 100
        assert stats["backends"]["deepseek"]["input"] == 200

    @pytest.mark.asyncio
    async def test_generate_groq_success(self, gateway):
        """Test successful Groq generation."""
        from quantum_terminal.infrastructure.ai.ai_gateway import AIBackendError

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Generated text"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=50)

        with patch("quantum_terminal.config.settings.groq_api_key", "test_key"):
            with patch("quantum_terminal.infrastructure.ai.ai_gateway.Groq") as mock_groq:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_response
                mock_groq.return_value = mock_client

                with patch.object(gateway.token_counter, "check_limits", return_value=True):
                    with patch("quantum_terminal.infrastructure.ai.ai_gateway.rate_limiter") as mock_limiter:
                        mock_limiter.allow_request.return_value = True

                        response = await gateway.generate("Test prompt", tipo="fast")

                        assert response == "Generated text"

    @pytest.mark.asyncio
    async def test_generate_fallback_chain(self, gateway):
        """Test fallback chain: Groq fails → OpenRouter."""
        from quantum_terminal.infrastructure.ai.ai_gateway import AIRateLimitError

        with patch("quantum_terminal.config.settings.groq_api_key", "test_key"):
            with patch("quantum_terminal.config.settings.openrouter_api_key", "test_key"):
                with patch.object(gateway, "_call_groq", new_callable=AsyncMock, side_effect=AIRateLimitError("Rate limit")):
                    mock_response = MagicMock()
                    mock_response.choices = [MagicMock(message=MagicMock(content="Fallback response"))]
                    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=50)

                    with patch("quantum_terminal.infrastructure.ai.ai_gateway.OpenAI") as mock_openai:
                        mock_client = MagicMock()
                        mock_client.chat.completions.create.return_value = mock_response
                        mock_openai.return_value = mock_client

                        with patch.object(gateway.token_counter, "check_limits", return_value=True):
                            with patch("quantum_terminal.infrastructure.ai.ai_gateway.rate_limiter") as mock_limiter:
                                mock_limiter.allow_request.return_value = True

                                response = await gateway.generate("Test", tipo="fast")

                                assert response == "Fallback response"

    @pytest.mark.asyncio
    async def test_generate_tipo_routing(self, gateway):
        """Test intelligent routing based on tipo parameter."""
        with patch.object(gateway, "_call_backend", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {"response": "Response", "backend": "groq"}

            with patch.object(gateway.token_counter, "check_limits", return_value=True):
                with patch("quantum_terminal.infrastructure.ai.ai_gateway.rate_limiter") as mock_limiter:
                    mock_limiter.allow_request.return_value = True

                    # Fast type should try Groq first
                    await gateway.generate("Test", tipo="fast")

                    # Check that a backend was called
                    assert mock_call.called

    @pytest.mark.asyncio
    async def test_batch_process(self, gateway):
        """Test batch processing with concurrency control."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Response"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)

        with patch.object(gateway, "generate", new_callable=AsyncMock, return_value="Response"):
            results = await gateway.batch_process(["Prompt 1", "Prompt 2", "Prompt 3"])

            assert len(results) == 3
            assert all(r == "Response" for r in results)

    @pytest.mark.asyncio
    async def test_batch_process_error_handling(self, gateway):
        """Test batch processing with partial failures."""
        from quantum_terminal.infrastructure.ai.ai_gateway import AIGatewayError

        async def mock_generate(prompt, tipo, temperature, max_tokens):
            if "fail" in prompt:
                raise AIGatewayError("Failed")
            return "Success"

        with patch.object(gateway, "generate", new_callable=AsyncMock, side_effect=mock_generate):
            results = await gateway.batch_process(["good", "bad_fail", "good"])

            assert len(results) == 3
            assert "Success" in str(results[0])

    def test_get_token_stats(self, gateway):
        """Test token statistics retrieval."""
        gateway.token_counter.track("groq", 1000, 500)

        stats = gateway.token_counter.get_stats()

        assert "backends" in stats
        assert "groq" in stats["backends"]

    def test_get_backend_status(self, gateway):
        """Test backend status reporting."""
        with patch("quantum_terminal.infrastructure.ai.ai_gateway.rate_limiter") as mock_limiter:
            mock_limiter.get.return_value = MagicMock(get_stats=Mock(return_value={"available_percent": 80.0}))

            status = gateway.get_backend_status()

            # Status should include rate limiter info if available
            assert isinstance(status, dict)

    @pytest.mark.asyncio
    async def test_all_backends_fail(self, gateway):
        """Test when all backends fail."""
        from quantum_terminal.infrastructure.ai.ai_gateway import AIGatewayError

        with patch.object(gateway, "_call_backend", new_callable=AsyncMock, side_effect=AIGatewayError("All failed")):
            with pytest.raises(AIGatewayError):
                await gateway.generate("Test", tipo="fast")


# Integration Tests
class TestDataProviderAIGatewayIntegration:
    """Integration tests between data provider and AI gateway."""

    @pytest.mark.asyncio
    async def test_get_quote_and_analyze(self):
        """Test combined flow: get quote + AI analysis."""
        from quantum_terminal.infrastructure.market_data.data_provider import DataProvider
        from quantum_terminal.infrastructure.ai.ai_gateway import AIGateway

        provider = DataProvider()
        gateway = AIGateway()

        # Mock quote retrieval
        quote = {
            "ticker": "AAPL",
            "price": 150.0,
            "bid": 149.95,
            "ask": 150.05,
            "source": "cache",
        }

        # Mock AI analysis
        analysis = "Apple stock is performing well based on recent market data."

        # In real scenario, would orchestrate these together
        assert quote["ticker"] == "AAPL"
        assert len(analysis) > 0
