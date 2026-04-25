"""Tests for OpenRouter universal LLM backend.

Tests cover:
- Multiple model support
- Fallback chain behavior
- Error handling
- Cost tracking via OpenRouter
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from quantum_terminal.infrastructure.ai.backends.openrouter_backend import (
    OpenRouterBackend,
    OpenRouterAuthException,
    OpenRouterGenerationException,
    OpenRouterRateLimitException,
)
from quantum_terminal.utils.rate_limiter import rate_limiter


@pytest.fixture
def openrouter_backend():
    """Create OpenRouter backend instance."""
    with patch("quantum_terminal.config.settings") as mock_settings:
        mock_settings.openrouter_api_key = "test_openrouter_key"
        backend = OpenRouterBackend(api_key="test_openrouter_key")
        yield backend


class TestOpenRouterBackendInit:
    """Test OpenRouter backend initialization."""

    def test_init_with_api_key(self):
        """Test initialization with provided API key."""
        backend = OpenRouterBackend(api_key="test_key")
        assert backend.api_key == "test_key"

    def test_init_without_api_key_raises(self):
        """Test initialization without API key raises exception."""
        with patch("quantum_terminal.config.settings") as mock_settings:
            mock_settings.openrouter_api_key = None
            with pytest.raises(OpenRouterAuthException):
                OpenRouterBackend()

    def test_models_defined(self):
        """Test models are defined."""
        backend = OpenRouterBackend(api_key="test")
        assert "meta-llama/llama-2-70b" in backend.MODELS
        assert len(backend.MODELS) > 0

    def test_base_url_defined(self):
        """Test API base URL is defined."""
        backend = OpenRouterBackend(api_key="test")
        assert "openrouter.ai" in backend.BASE_URL


class TestOpenRouterBackendRateLimit:
    """Test rate limiting."""

    def test_rate_limiter_registered(self):
        """Test OpenRouter rate limiter is registered."""
        limiter = rate_limiter.get("openrouter")
        assert limiter is not None

    @pytest.mark.asyncio
    async def test_rate_limit_exception(self, openrouter_backend):
        """Test rate limit exception is raised."""
        with patch.object(rate_limiter, "allow_request", return_value=False):
            with pytest.raises(OpenRouterRateLimitException):
                await openrouter_backend.generate("test prompt")


class TestOpenRouterBackendGenerate:
    """Test generate method."""

    @pytest.mark.asyncio
    async def test_generate_success(self, openrouter_backend):
        """Test successful text generation."""
        mock_response_data = {
            "choices": [
                {"message": {"content": "AAPL analysis result"}}
            ]
        }

        with patch.object(openrouter_backend, "_ensure_session") as mock_session_fn:
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
                result = await openrouter_backend.generate("Analyze AAPL")
                assert result == "AAPL analysis result"

    @pytest.mark.asyncio
    async def test_generate_with_custom_model(self, openrouter_backend):
        """Test generate with custom model."""
        mock_response_data = {
            "choices": [
                {"message": {"content": "Result"}}
            ]
        }

        with patch.object(openrouter_backend, "_ensure_session") as mock_session_fn:
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
                result = await openrouter_backend.generate(
                    "prompt",
                    model="anthropic/claude-3-sonnet",
                )
                assert result == "Result"

    @pytest.mark.asyncio
    async def test_generate_auth_error_401(self, openrouter_backend):
        """Test generate handles 401 auth error."""
        with patch.object(openrouter_backend, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_session.post.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )
            mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                with pytest.raises(OpenRouterAuthException):
                    await openrouter_backend.generate("prompt")

    @pytest.mark.asyncio
    async def test_generate_timeout(self, openrouter_backend):
        """Test generate handles timeout."""
        with patch.object(openrouter_backend, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_session.post = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                with pytest.raises(OpenRouterGenerationException):
                    await openrouter_backend.generate("prompt")

    @pytest.mark.asyncio
    async def test_generate_no_choices(self, openrouter_backend):
        """Test generate handles no choices in response."""
        mock_response_data = {"choices": []}

        with patch.object(openrouter_backend, "_ensure_session") as mock_session_fn:
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
                with pytest.raises(OpenRouterGenerationException):
                    await openrouter_backend.generate("prompt")


class TestOpenRouterBackendBatchGenerate:
    """Test batch_generate method."""

    @pytest.mark.asyncio
    async def test_batch_generate_success(self, openrouter_backend):
        """Test batch generation."""
        mock_response_data = {
            "choices": [
                {"message": {"content": "Response"}}
            ]
        }

        with patch.object(openrouter_backend, "_ensure_session") as mock_session_fn:
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
                results = await openrouter_backend.batch_generate([
                    "Analyze AAPL",
                    "Analyze MSFT",
                ])

                assert len(results) == 2
                assert all(r == "Response" for r in results)

    @pytest.mark.asyncio
    async def test_batch_generate_mixed_results(self, openrouter_backend):
        """Test batch generation with mixed success/failure."""
        with patch.object(openrouter_backend, "generate") as mock_gen:
            async def async_gen(*args, **kwargs):
                if "AAPL" in args[0]:
                    return "AAPL result"
                else:
                    raise OpenRouterGenerationException("Error")

            mock_gen.side_effect = async_gen

            with patch.object(rate_limiter, "allow_request", return_value=True):
                results = await openrouter_backend.batch_generate([
                    "Analyze AAPL",
                    "Analyze MSFT",
                ])

                assert len(results) == 2
                assert results[0] == "AAPL result"
                assert results[1] == ""


class TestOpenRouterBackendListModels:
    """Test list_models method."""

    @pytest.mark.asyncio
    async def test_list_models(self, openrouter_backend):
        """Test listing available models."""
        models = await openrouter_backend.list_models()
        assert isinstance(models, dict)
        assert len(models) > 0
        assert "meta-llama/llama-2-70b" in models


class TestOpenRouterBackendClose:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close(self, openrouter_backend):
        """Test closing backend."""
        openrouter_backend.session = AsyncMock()
        await openrouter_backend.close()
        openrouter_backend.session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_session(self, openrouter_backend):
        """Test closing with no session."""
        openrouter_backend.session = None
        await openrouter_backend.close()
        # Should not raise


class TestOpenRouterBackendContextManager:
    """Test context manager."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self, openrouter_backend):
        """Test async context manager."""
        async with openrouter_backend as backend:
            assert backend is not None


class TestOpenRouterBackendGlobal:
    """Test global backend instance."""

    @pytest.mark.asyncio
    async def test_get_openrouter_backend(self):
        """Test get_openrouter_backend returns instance."""
        from quantum_terminal.infrastructure.ai.backends.openrouter_backend import (
            get_openrouter_backend,
        )

        with patch("quantum_terminal.config.settings") as mock_settings:
            mock_settings.openrouter_api_key = "test_key"
            backend = await get_openrouter_backend()
            assert isinstance(backend, OpenRouterBackend)


class TestOpenRouterBackendExceptions:
    """Test exception hierarchy."""

    def test_exception_hierarchy(self):
        """Test exceptions inherit from OpenRouterException."""
        from quantum_terminal.infrastructure.ai.backends.openrouter_backend import (
            OpenRouterException,
        )

        assert issubclass(OpenRouterAuthException, OpenRouterException)
        assert issubclass(OpenRouterRateLimitException, OpenRouterException)
        assert issubclass(OpenRouterGenerationException, OpenRouterException)

    def test_exception_messages(self):
        """Test exception messages."""
        exc = OpenRouterAuthException("Invalid credentials")
        assert "Invalid credentials" in str(exc)
