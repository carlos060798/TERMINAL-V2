"""Tests for DeepSeek reasoning LLM backend.

Tests cover:
- Reasoning mode with thinking budget
- Extended thinking responses
- Error handling
- Batch processing
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from quantum_terminal.infrastructure.ai.backends.deepseek_backend import (
    DeepSeekBackend,
    DeepSeekAuthException,
    DeepSeekGenerationException,
    DeepSeekRateLimitException,
)
from quantum_terminal.utils.rate_limiter import rate_limiter


@pytest.fixture
def deepseek_backend():
    """Create DeepSeek backend instance."""
    with patch("quantum_terminal.config.settings") as mock_settings:
        mock_settings.deepseek_api_key = "test_deepseek_key"
        backend = DeepSeekBackend(api_key="test_deepseek_key")
        yield backend


class TestDeepSeekBackendInit:
    """Test DeepSeek backend initialization."""

    def test_init_with_api_key(self):
        """Test initialization with provided API key."""
        backend = DeepSeekBackend(api_key="test_key")
        assert backend.api_key == "test_key"

    def test_init_without_api_key_raises(self):
        """Test initialization without API key raises exception."""
        with patch("quantum_terminal.config.settings") as mock_settings:
            mock_settings.deepseek_api_key = None
            with pytest.raises(DeepSeekAuthException):
                DeepSeekBackend()

    def test_model_defined(self):
        """Test model is defined."""
        backend = DeepSeekBackend(api_key="test")
        assert backend.MODEL == "deepseek-reasoner"

    def test_base_url_defined(self):
        """Test API base URL is defined."""
        backend = DeepSeekBackend(api_key="test")
        assert backend.BASE_URL == "https://api.deepseek.com/chat/completions"


class TestDeepSeekBackendRateLimit:
    """Test rate limiting."""

    def test_rate_limiter_registered(self):
        """Test DeepSeek rate limiter is registered."""
        limiter = rate_limiter.get("deepseek")
        assert limiter is not None

    @pytest.mark.asyncio
    async def test_rate_limit_exception(self, deepseek_backend):
        """Test rate limit exception is raised."""
        with patch.object(rate_limiter, "allow_request", return_value=False):
            with pytest.raises(DeepSeekRateLimitException):
                await deepseek_backend.generate("test prompt")


class TestDeepSeekBackendGenerate:
    """Test generate method with extended thinking."""

    @pytest.mark.asyncio
    async def test_generate_success(self, deepseek_backend):
        """Test successful text generation with thinking."""
        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "thinking": "Step 1: Analyze fundamentals...",
                        "content": "AAPL appears undervalued based on..."
                    }
                }
            ]
        }

        with patch.object(deepseek_backend, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_session.post.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )
            mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await deepseek_backend.generate(
                    "Evaluate AAPL valuation",
                    thinking_budget=5000,
                )

                assert result["thinking"] == "Step 1: Analyze fundamentals..."
                assert "undervalued" in result["content"]

    @pytest.mark.asyncio
    async def test_generate_with_thinking_budget(self, deepseek_backend):
        """Test generate with custom thinking budget."""
        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "thinking": "Deep analysis...",
                        "content": "Conclusion..."
                    }
                }
            ]
        }

        with patch.object(deepseek_backend, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_session.post.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )
            mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                result = await deepseek_backend.generate(
                    "prompt",
                    thinking_budget=10000,
                    max_tokens=3000,
                )

                assert "thinking" in result
                assert "content" in result

    @pytest.mark.asyncio
    async def test_generate_auth_error_401(self, deepseek_backend):
        """Test generate handles 401 auth error."""
        with patch.object(deepseek_backend, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_session.post.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )
            mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                with pytest.raises(DeepSeekAuthException):
                    await deepseek_backend.generate("prompt")

    @pytest.mark.asyncio
    async def test_generate_timeout(self, deepseek_backend):
        """Test generate handles timeout."""
        with patch.object(deepseek_backend, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_session.post = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                with pytest.raises(DeepSeekGenerationException):
                    await deepseek_backend.generate("prompt")


class TestDeepSeekBackendBatchGenerate:
    """Test batch_generate method."""

    @pytest.mark.asyncio
    async def test_batch_generate_success(self, deepseek_backend):
        """Test batch generation."""
        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "thinking": "Analysis...",
                        "content": "Result"
                    }
                }
            ]
        }

        with patch.object(deepseek_backend, "generate") as mock_gen:
            async def async_gen(*args, **kwargs):
                return {
                    "thinking": "Analysis...",
                    "content": "Result"
                }

            mock_gen.side_effect = async_gen

            with patch.object(rate_limiter, "allow_request", return_value=True):
                results = await deepseek_backend.batch_generate([
                    "Analyze AAPL",
                    "Analyze MSFT",
                ])

                assert len(results) == 2
                assert all("thinking" in r for r in results)
                assert all("content" in r for r in results)

    @pytest.mark.asyncio
    async def test_batch_generate_with_failures(self, deepseek_backend):
        """Test batch generation handles failures."""
        with patch.object(deepseek_backend, "generate") as mock_gen:
            async def async_gen(*args, **kwargs):
                raise DeepSeekGenerationException("Error")

            mock_gen.side_effect = async_gen

            with patch.object(rate_limiter, "allow_request", return_value=True):
                results = await deepseek_backend.batch_generate([
                    "prompt1",
                    "prompt2",
                ])

                assert len(results) == 2
                assert all(r["content"] == "" for r in results)


class TestDeepSeekBackendClose:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close(self, deepseek_backend):
        """Test closing backend."""
        deepseek_backend.session = AsyncMock()
        await deepseek_backend.close()
        deepseek_backend.session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_session(self, deepseek_backend):
        """Test closing with no session."""
        deepseek_backend.session = None
        await deepseek_backend.close()
        # Should not raise


class TestDeepSeekBackendContextManager:
    """Test context manager."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self, deepseek_backend):
        """Test async context manager."""
        async with deepseek_backend as backend:
            assert backend is not None


class TestDeepSeekBackendGlobal:
    """Test global backend instance."""

    @pytest.mark.asyncio
    async def test_get_deepseek_backend(self):
        """Test get_deepseek_backend returns instance."""
        from quantum_terminal.infrastructure.ai.backends.deepseek_backend import (
            get_deepseek_backend,
        )

        with patch("quantum_terminal.config.settings") as mock_settings:
            mock_settings.deepseek_api_key = "test_key"
            backend = await get_deepseek_backend()
            assert isinstance(backend, DeepSeekBackend)


class TestDeepSeekBackendExceptions:
    """Test exception hierarchy."""

    def test_exception_hierarchy(self):
        """Test exceptions inherit from DeepSeekException."""
        from quantum_terminal.infrastructure.ai.backends.deepseek_backend import (
            DeepSeekException,
        )

        assert issubclass(DeepSeekAuthException, DeepSeekException)
        assert issubclass(DeepSeekRateLimitException, DeepSeekException)
        assert issubclass(DeepSeekGenerationException, DeepSeekException)

    def test_exception_messages(self):
        """Test exception messages."""
        exc = DeepSeekAuthException("Invalid key")
        assert "Invalid key" in str(exc)
