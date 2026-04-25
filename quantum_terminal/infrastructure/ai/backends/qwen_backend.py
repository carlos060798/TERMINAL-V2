"""Qwen backend for bulk text processing.

Uses Qwen2.5-72B model via API with:
- Async/await support
- Batch processing
- Token bucket rate limiting
- Cost-effective for large-scale analysis

Model: Qwen2.5-72B
Best for: Bulk analysis, portfolio screening, batch thesis generation
"""

import asyncio
from typing import Any, Optional

try:
    import aiohttp
except ImportError:
    raise ImportError("aiohttp package required: pip install aiohttp")

from quantum_terminal.config import settings
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.utils.rate_limiter import rate_limiter

logger = get_logger(__name__)

# Register Qwen rate limiter
rate_limiter.register("qwen", 100, 1)


class QwenException(Exception):
    """Base exception for Qwen backend errors."""
    pass


class QwenAuthException(QwenException):
    """Raised when Qwen API key is missing or invalid."""
    pass


class QwenRateLimitException(QwenException):
    """Raised when Qwen API rate limit is exceeded."""
    pass


class QwenGenerationException(QwenException):
    """Raised when text generation fails."""
    pass


class QwenBackend:
    """Async backend for Qwen API.

    Provides bulk text generation with batch support.

    Examples:
        >>> backend = QwenBackend()
        >>> result = await backend.generate("Analyze AAPL")
        >>> results = await backend.batch_generate(["Analyze AAPL", "Analyze MSFT"])
    """

    MODEL = "qwen2.5-72b"
    BASE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    TIMEOUT = 60

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Qwen backend.

        Args:
            api_key: Qwen API key. Defaults to settings.qwen_api_key.

        Raises:
            QwenAuthException: If API key not configured.
        """
        self.api_key = api_key or settings.qwen_api_key
        if not self.api_key:
            raise QwenAuthException("QWEN_API_KEY not configured in .env")

        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"QwenBackend initialized (model: {self.MODEL})")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure session exists."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using Qwen API.

        Args:
            prompt: Text prompt.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.

        Returns:
            Generated text.

        Raises:
            QwenRateLimitException: If rate limited.
            QwenGenerationException: If generation fails.

        Examples:
            >>> response = await backend.generate(
            ...     "Analyze AAPL fundamentals",
            ...     max_tokens=1000,
            ... )
            >>> print(response)
        """
        # Check rate limit
        if not rate_limiter.allow_request("qwen"):
            raise QwenRateLimitException("Qwen rate limit exceeded")

        session = await self._ensure_session()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.MODEL,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ]
            },
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        }

        try:
            logger.debug(f"Generating with Qwen (temp={temperature})")

            async with session.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.TIMEOUT),
            ) as response:
                if response.status == 401:
                    raise QwenAuthException("Invalid API key")
                elif response.status == 429:
                    raise QwenRateLimitException("Rate limit exceeded")
                elif response.status >= 400:
                    raise QwenGenerationException(f"HTTP {response.status}")

                data = await response.json()

                # Extract text from response
                if "output" in data and "text" in data["output"]:
                    text = data["output"]["text"]
                    logger.debug(f"Generation complete ({len(text)} chars)")
                    return text
                else:
                    raise QwenGenerationException("No text in response")

        except asyncio.TimeoutError:
            raise QwenGenerationException("Request timeout")
        except QwenException:
            raise
        except Exception as e:
            logger.error(f"Qwen generation failed: {e}")
            raise QwenGenerationException(f"Generation failed: {str(e)}")

    async def batch_generate(
        self,
        prompts: list[str],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> list[str]:
        """Generate text for multiple prompts in batch.

        Args:
            prompts: List of prompts.
            max_tokens: Max tokens per response.
            temperature: Sampling temperature.

        Returns:
            List of generated texts.

        Examples:
            >>> results = await backend.batch_generate([
            ...     "Analyze AAPL",
            ...     "Analyze MSFT",
            ...     "Analyze GOOGL",
            ... ])
            >>> for i, result in enumerate(results):
            ...     print(f"Result {i}: {result[:100]}...")
        """
        results = []

        for prompt in prompts:
            try:
                text = await self.generate(prompt, max_tokens, temperature)
                results.append(text)
            except QwenException as e:
                logger.warning(f"Batch generation failed: {e}")
                results.append("")

        return results

    async def stream_generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> None:
        """Stream text generation (if supported by Qwen API).

        Note: Implementation depends on Qwen API streaming support.

        Args:
            prompt: Text prompt.
            max_tokens: Max tokens.
            temperature: Sampling temperature.
        """
        logger.warning("Qwen streaming not yet implemented")

    async def close(self) -> None:
        """Close session."""
        if self.session:
            await self.session.close()
            logger.info("QwenBackend closed")


# Global backend instance
_qwen_backend: Optional[QwenBackend] = None


async def get_qwen_backend() -> QwenBackend:
    """Get or create global Qwen backend.

    Returns:
        QwenBackend instance.

    Raises:
        QwenAuthException: If API key not configured.
    """
    global _qwen_backend
    if _qwen_backend is None:
        _qwen_backend = QwenBackend()
    return _qwen_backend
