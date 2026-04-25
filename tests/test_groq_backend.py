"""Tests for Groq LLM backend.

Tests cover:
- Rate limiting (30 req/min)
- Text generation
- Streaming support
- Batch processing
- Error handling
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from quantum_terminal.infrastructure.ai.backends.groq_backend import (
    GroqBackend,
    GroqAuthException,
    GroqGenerationException,
    GroqRateLimitExceeded,
)
from quantum_terminal.utils.rate_limiter import rate_limiter


@pytest.fixture
def groq_backend():
    """Create Groq backend instance."""
    with patch("quantum_terminal.config.settings") as mock_settings:
        mock_settings.groq_api_key = "test_groq_key"
        with patch("quantum_terminal.infrastructure.ai.backends.groq_backend.AsyncGroq"):
            backend = GroqBackend(api_key="test_groq_key")
            yield backend


class TestGroqBackendInit:
    """Test Groq backend initialization."""

    def test_init_with_api_key(self):
        """Test initialization with provided API key."""
        with patch("quantum_terminal.infrastructure.ai.backends.groq_backend.AsyncGroq"):
            backend = GroqBackend(api_key="test_key")
            assert backend.api_key == "test_key"

    def test_init_without_api_key_raises(self):
        """Test initialization without API key raises exception."""
        with patch("quantum_terminal.config.settings") as mock_settings:
            mock_settings.groq_api_key = None
            with pytest.raises(GroqAuthException):
                GroqBackend()

    def test_model_defined(self):
        """Test model is defined."""
        with patch("quantum_terminal.infrastructure.ai.backends.groq_backend.AsyncGroq"):
            backend = GroqBackend(api_key="test")
            assert backend.MODEL == "llama-3.3-70b-versatile"

    def test_timeout_defined(self):
        """Test timeout is defined."""
        with patch("quantum_terminal.infrastructure.ai.backends.groq_backend.AsyncGroq"):
            backend = GroqBackend(api_key="test")
            assert backend.TIMEOUT == 60


class TestGroqBackendRateLimit:
    """Test rate limiting."""

    def test_rate_limiter_registered(self):
        """Test Groq rate limiter is registered."""
        limiter = rate_limiter.get("groq")
        assert limiter is not None

    @pytest.mark.asyncio
    async def test_rate_limit_exception(self, groq_backend):
        """Test rate limit exception is raised."""
        with patch.object(rate_limiter, "allow_request", return_value=False):
            with pytest.raises(GroqRateLimitExceeded):
                await groq_backend.generate("test prompt")


class TestGroqBackendGenerate:
    """Test generate method."""

    @pytest.mark.asyncio
    async def test_generate_success(self, groq_backend):
        """Test successful text generation."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Generated text response"))
        ]

        groq_backend.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        with patch.object(rate_limiter, "allow_request", return_value=True):
            result = await groq_backend.generate("Analyze AAPL")
            assert result == "Generated text response"

    @pytest.mark.asyncio
    async def test_generate_with_parameters(self, groq_backend):
        """Test generate with custom parameters."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Result"))
        ]

        groq_backend.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        with patch.object(rate_limiter, "allow_request", return_value=True):
            result = await groq_backend.generate(
                "prompt",
                max_tokens=1000,
                temperature=0.5,
            )
            assert result == "Result"
            groq_backend.client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_api_error(self, groq_backend):
        """Test generate handles API errors."""
        groq_backend.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API error")
        )

        with patch.object(rate_limiter, "allow_request", return_value=True):
            with pytest.raises(GroqGenerationException):
                await groq_backend.generate("prompt")


class TestGroqBackendStream:
    """Test stream method."""

    @pytest.mark.asyncio
    async def test_stream_success(self, groq_backend):
        """Test successful streaming."""
        async def mock_stream():
            yield MagicMock(choices=[MagicMock(delta=MagicMock(content="chunk1 "))])
            yield MagicMock(choices=[MagicMock(delta=MagicMock(content="chunk2 "))])
            yield MagicMock(choices=[MagicMock(delta=MagicMock(content="chunk3"))])

        groq_backend.client.chat.completions.create = AsyncMock(
            return_value=mock_stream()
        )

        with patch.object(rate_limiter, "allow_request", return_value=True):
            chunks = []
            async for chunk in groq_backend.stream("prompt"):
                chunks.append(chunk)

            assert len(chunks) == 3
            assert "".join(chunks) == "chunk1 chunk2 chunk3"

    @pytest.mark.asyncio
    async def test_stream_api_error(self, groq_backend):
        """Test stream handles API errors."""
        groq_backend.client.chat.completions.create = AsyncMock(
            side_effect=Exception("Stream error")
        )

        with patch.object(rate_limiter, "allow_request", return_value=True):
            with pytest.raises(GroqGenerationException):
                async for _ in groq_backend.stream("prompt"):
                    pass


class TestGroqBackendBatchGenerate:
    """Test batch_generate method."""

    @pytest.mark.asyncio
    async def test_batch_generate_success(self, groq_backend):
        """Test batch generation."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Response"))
        ]

        groq_backend.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        with patch.object(rate_limiter, "allow_request", return_value=True):
            results = await groq_backend.batch_generate([
                "Analyze AAPL",
                "Analyze MSFT",
                "Analyze GOOGL",
            ])

            assert len(results) == 3
            assert all(r == "Response" for r in results)

    @pytest.mark.asyncio
    async def test_batch_generate_with_failures(self, groq_backend):
        """Test batch generation handles failures."""
        groq_backend.client.chat.completions.create = AsyncMock(
            side_effect=Exception("Error")
        )

        with patch.object(rate_limiter, "allow_request", return_value=True):
            results = await groq_backend.batch_generate([
                "prompt1",
                "prompt2",
            ])

            assert len(results) == 2
            assert all(r == "" for r in results)


class TestGroqBackendClose:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close(self, groq_backend):
        """Test closing backend."""
        groq_backend.client.close = AsyncMock()
        await groq_backend.close()
        groq_backend.client.close.assert_called_once()


class TestGroqBackendGlobal:
    """Test global backend instance."""

    @pytest.mark.asyncio
    async def test_get_groq_backend(self):
        """Test get_groq_backend returns instance."""
        from quantum_terminal.infrastructure.ai.backends.groq_backend import (
            get_groq_backend,
        )

        with patch("quantum_terminal.config.settings") as mock_settings:
            mock_settings.groq_api_key = "test_key"
            with patch("quantum_terminal.infrastructure.ai.backends.groq_backend.AsyncGroq"):
                backend = await get_groq_backend()
                assert isinstance(backend, GroqBackend)


class TestGroqBackendExceptions:
    """Test exception hierarchy."""

    def test_exception_hierarchy(self):
        """Test exceptions inherit from GroqException."""
        from quantum_terminal.infrastructure.ai.backends.groq_backend import GroqException

        assert issubclass(GroqRateLimitExceeded, GroqException)
        assert issubclass(GroqAuthException, GroqException)
        assert issubclass(GroqGenerationException, GroqException)

    def test_exception_messages(self):
        """Test exception messages."""
        exc = GroqAuthException("Missing API key")
        assert "Missing API key" in str(exc)
