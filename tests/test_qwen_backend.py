"""Tests for Qwen bulk processing LLM backend.

Tests cover:
- Batch text generation
- Bulk processing capabilities
- Cost-effective analysis
- Error handling
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from quantum_terminal.infrastructure.ai.backends.qwen_backend import (
    QwenBackend,
    QwenAuthException,
    QwenGenerationException,
    QwenRateLimitException,
)
from quantum_terminal.utils.rate_limiter import rate_limiter


@pytest.fixture
def qwen_backend():
    """Create Qwen backend instance."""
    with patch("quantum_terminal.config.settings") as mock_settings:
        mock_settings.qwen_api_key = "test_qwen_key"
        backend = QwenBackend(api_key="test_qwen_key")
        yield backend


class TestQwenBackendInit:
    """Test Qwen backend initialization."""

    def test_init_with_api_key(self):
        """Test initialization with provided API key."""
        backend = QwenBackend(api_key="test_key")
        assert backend.api_key == "test_key"

    def test_init_without_api_key_raises(self):
        """Test initialization without API key raises exception."""
        with patch("quantum_terminal.config.settings") as mock_settings:
            mock_settings.qwen_api_key = None
            with pytest.raises(QwenAuthException):
                QwenBackend()

    def test_model_defined(self):
        """Test model is defined."""
        backend = QwenBackend(api_key="test")
        assert backend.MODEL == "qwen2.5-72b"

    def test_base_url_defined(self):
        """Test API base URL is defined."""
        backend = QwenBackend(api_key="test")
        assert "dashscope.aliyuncs.com" in backend.BASE_URL


class TestQwenBackendRateLimit:
    """Test rate limiting."""

    def test_rate_limiter_registered(self):
        """Test Qwen rate limiter is registered."""
        limiter = rate_limiter.get("qwen")
        assert limiter is not None

    @pytest.mark.asyncio
    async def test_rate_limit_exception(self, qwen_backend):
        """Test rate limit exception is raised."""
        with patch.object(rate_limiter, "allow_request", return_value=False):
            with pytest.raises(QwenRateLimitException):
                await qwen_backend.generate("test prompt")


class TestQwenBackendGenerate:
    """Test generate method."""

    @pytest.mark.asyncio
    async def test_generate_success(self, qwen_backend):
        """Test successful text generation."""
        mock_response_data = {
            "output": {
                "text": "AAPL is trading at a discount to intrinsic value"
            }
        }

        with patch.object(qwen_backend, "_ensure_session") as mock_session_fn:
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
                result = await qwen_backend.generate("Analyze AAPL")
                assert result == "AAPL is trading at a discount to intrinsic value"

    @pytest.mark.asyncio
    async def test_generate_with_parameters(self, qwen_backend):
        """Test generate with custom parameters."""
        mock_response_data = {
            "output": {"text": "Result"}
        }

        with patch.object(qwen_backend, "_ensure_session") as mock_session_fn:
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
                result = await qwen_backend.generate(
                    "prompt",
                    max_tokens=1000,
                    temperature=0.5,
                )
                assert result == "Result"

    @pytest.mark.asyncio
    async def test_generate_auth_error_401(self, qwen_backend):
        """Test generate handles 401 auth error."""
        with patch.object(qwen_backend, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_session.post.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )
            mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                with pytest.raises(QwenAuthException):
                    await qwen_backend.generate("prompt")

    @pytest.mark.asyncio
    async def test_generate_rate_limit_429(self, qwen_backend):
        """Test generate handles 429 rate limit."""
        with patch.object(qwen_backend, "_ensure_session") as mock_session_fn:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_session.post.return_value.__aenter__ = AsyncMock(
                return_value=mock_response
            )
            mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_fn.return_value = mock_session

            with patch.object(rate_limiter, "allow_request", return_value=True):
                with pytest.raises(QwenGenerationException):
                    await qwen_backend.generate("prompt")

    @pytest.mark.asyncio
    async def test_generate_no_response_text(self, qwen_backend):
        """Test generate handles missing response text."""
        mock_response_data = {"output": {}}

        with patch.object(qwen_backend, "_ensure_session") as mock_session_fn:
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
                with pytest.raises(QwenGenerationException):
                    await qwen_backend.generate("prompt")


class TestQwenBackendBatchGenerate:
    """Test batch_generate method."""

    @pytest.mark.asyncio
    async def test_batch_generate_success(self, qwen_backend):
        """Test batch generation."""
        mock_response_data = {
            "output": {"text": "Response"}
        }

        with patch.object(qwen_backend, "_ensure_session") as mock_session_fn:
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
                results = await qwen_backend.batch_generate([
                    "Analyze AAPL",
                    "Analyze MSFT",
                    "Analyze GOOGL",
                ])

                assert len(results) == 3
                assert all(r == "Response" for r in results)

    @pytest.mark.asyncio
    async def test_batch_generate_with_failures(self, qwen_backend):
        """Test batch generation handles failures."""
        with patch.object(qwen_backend, "generate") as mock_gen:
            async def async_gen(*args, **kwargs):
                raise QwenGenerationException("Error")

            mock_gen.side_effect = async_gen

            with patch.object(rate_limiter, "allow_request", return_value=True):
                results = await qwen_backend.batch_generate([
                    "prompt1",
                    "prompt2",
                ])

                assert len(results) == 2
                assert all(r == "" for r in results)


class TestQwenBackendStreamGenerate:
    """Test stream_generate method."""

    @pytest.mark.asyncio
    async def test_stream_generate_warning(self, qwen_backend):
        """Test stream_generate logs warning (not implemented)."""
        await qwen_backend.stream_generate("prompt")
        # Should complete without error but log warning


class TestQwenBackendClose:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close(self, qwen_backend):
        """Test closing backend."""
        qwen_backend.session = AsyncMock()
        await qwen_backend.close()
        qwen_backend.session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_session(self, qwen_backend):
        """Test closing with no session."""
        qwen_backend.session = None
        await qwen_backend.close()
        # Should not raise


class TestQwenBackendContextManager:
    """Test context manager."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self, qwen_backend):
        """Test async context manager."""
        async with qwen_backend as backend:
            assert backend is not None


class TestQwenBackendGlobal:
    """Test global backend instance."""

    @pytest.mark.asyncio
    async def test_get_qwen_backend(self):
        """Test get_qwen_backend returns instance."""
        from quantum_terminal.infrastructure.ai.backends.qwen_backend import (
            get_qwen_backend,
        )

        with patch("quantum_terminal.config.settings") as mock_settings:
            mock_settings.qwen_api_key = "test_key"
            backend = await get_qwen_backend()
            assert isinstance(backend, QwenBackend)


class TestQwenBackendExceptions:
    """Test exception hierarchy."""

    def test_exception_hierarchy(self):
        """Test exceptions inherit from QwenException."""
        from quantum_terminal.infrastructure.ai.backends.qwen_backend import (
            QwenException,
        )

        assert issubclass(QwenAuthException, QwenException)
        assert issubclass(QwenRateLimitException, QwenException)
        assert issubclass(QwenGenerationException, QwenException)

    def test_exception_messages(self):
        """Test exception messages."""
        exc = QwenAuthException("API key missing")
        assert "API key missing" in str(exc)
