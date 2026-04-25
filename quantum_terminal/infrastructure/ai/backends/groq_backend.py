"""Groq backend for fast LLM inference.

Uses Llama 3.3 70B model via Groq API with:
- Async/await support
- Token bucket rate limiting (30 req/min)
- Streaming support
- Specific exception handling

Model: Llama 3.3 70B
Rate limit: 30 requests/minute
Best for: Fast analysis, thesis generation, quick queries
"""

import asyncio
from typing import Any, AsyncGenerator, Optional

try:
    from groq import AsyncGroq, RateLimitError as GroqRateLimitError
except ImportError:
    raise ImportError("groq package required: pip install groq")

from quantum_terminal.config import settings
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.utils.rate_limiter import rate_limiter

logger = get_logger(__name__)

# Register Groq rate limiter (30 req/min)
rate_limiter.register("groq", 30, 1)


class GroqException(Exception):
    """Base exception for Groq backend errors."""
    pass


class GroqRateLimitExceeded(GroqException):
    """Raised when Groq API rate limit is exceeded."""
    pass


class GroqAuthException(GroqException):
    """Raised when Groq API key is missing or invalid."""
    pass


class GroqGenerationException(GroqException):
    """Raised when text generation fails."""
    pass


class GroqBackend:
    """Async backend for Groq API.

    Provides methods for text generation with rate limiting and streaming.

    Examples:
        >>> backend = GroqBackend()
        >>> result = await backend.generate("Analyze AAPL valuation")
        >>> async for chunk in backend.stream("Generate thesis for TSLA"):
        ...     print(chunk, end="")
    """

    MODEL = "llama-3.3-70b-versatile"
    TIMEOUT = 60

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Groq backend.

        Args:
            api_key: Groq API key. Defaults to settings.groq_api_key.

        Raises:
            GroqAuthException: If API key not configured.
        """
        self.api_key = api_key or settings.groq_api_key
        if not self.api_key:
            raise GroqAuthException("GROQ_API_KEY not configured in .env")

        self.client = AsyncGroq(api_key=self.api_key)
        logger.info(f"GroqBackend initialized (model: {self.MODEL})")

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using Groq API.

        Args:
            prompt: Text prompt.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature (0-2).

        Returns:
            Generated text.

        Raises:
            GroqRateLimitExceeded: If rate limited.
            GroqGenerationException: If generation fails.

        Examples:
            >>> response = await backend.generate(
            ...     "Analyze AAPL fundamentals",
            ...     max_tokens=1000,
            ...     temperature=0.5,
            ... )
            >>> print(response)
        """
        # Check rate limit
        if not rate_limiter.allow_request("groq"):
            raise GroqRateLimitExceeded("Groq rate limit (30 req/min)")

        try:
            logger.debug(f"Generating with Groq (temp={temperature})")

            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            text = response.choices[0].message.content
            logger.debug(f"Generation complete ({len(text)} chars)")
            return text

        except GroqRateLimitError as e:
            raise GroqRateLimitExceeded(f"Groq rate limited: {str(e)}")
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            raise GroqGenerationException(f"Generation failed: {str(e)}")

    async def stream(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Stream text generation from Groq API.

        Args:
            prompt: Text prompt.
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.

        Yields:
            Text chunks as they arrive.

        Raises:
            GroqRateLimitExceeded: If rate limited.
            GroqGenerationException: If streaming fails.

        Examples:
            >>> async for chunk in backend.stream("Write investment thesis"):
            ...     print(chunk, end="", flush=True)
        """
        # Check rate limit
        if not rate_limiter.allow_request("groq"):
            raise GroqRateLimitExceeded("Groq rate limit (30 req/min)")

        try:
            logger.debug("Starting Groq stream")

            stream = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            logger.debug("Stream complete")

        except GroqRateLimitError as e:
            raise GroqRateLimitExceeded(f"Rate limited: {str(e)}")
        except Exception as e:
            logger.error(f"Groq stream failed: {e}")
            raise GroqGenerationException(f"Streaming failed: {str(e)}")

    async def batch_generate(
        self,
        prompts: list[str],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> list[str]:
        """Generate text for multiple prompts sequentially.

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
            ... ])
        """
        results = []

        for prompt in prompts:
            try:
                text = await self.generate(prompt, max_tokens, temperature)
                results.append(text)
            except GroqException as e:
                logger.warning(f"Batch generation failed for prompt: {e}")
                results.append("")

        return results

    async def close(self) -> None:
        """Close Groq client."""
        try:
            await self.client.close()
            logger.info("GroqBackend closed")
        except Exception as e:
            logger.error(f"Error closing Groq client: {e}")


# Global backend instance
_groq_backend: Optional[GroqBackend] = None


async def get_groq_backend() -> GroqBackend:
    """Get or create global Groq backend.

    Returns:
        GroqBackend instance.

    Raises:
        GroqAuthException: If API key not configured.
    """
    global _groq_backend
    if _groq_backend is None:
        _groq_backend = GroqBackend()
    return _groq_backend
