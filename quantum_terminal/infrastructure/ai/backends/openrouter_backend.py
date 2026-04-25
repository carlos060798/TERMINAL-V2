"""OpenRouter backend for universal LLM fallback.

Uses OpenRouter API to access multiple models with:
- Async/await support
- Model selection (fallback chain)
- Token bucket rate limiting
- Cost tracking

Best for: Fallback when primary backends fail, model flexibility
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

# Register OpenRouter rate limiter
rate_limiter.register("openrouter", 100, 1)


class OpenRouterException(Exception):
    """Base exception for OpenRouter backend errors."""
    pass


class OpenRouterAuthException(OpenRouterException):
    """Raised when OpenRouter API key is missing or invalid."""
    pass


class OpenRouterRateLimitException(OpenRouterException):
    """Raised when OpenRouter API rate limit is exceeded."""
    pass


class OpenRouterGenerationException(OpenRouterException):
    """Raised when text generation fails."""
    pass


class OpenRouterBackend:
    """Async backend for OpenRouter API.

    Provides fallback access to multiple LLM models.

    Examples:
        >>> backend = OpenRouterBackend()
        >>> result = await backend.generate(
        ...     "Analyze AAPL",
        ...     model="meta-llama/llama-2-70b",
        ... )
    """

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    TIMEOUT = 60

    # Available models (fallback chain)
    MODELS = {
        "meta-llama/llama-2-70b": "Llama 2 70B",
        "anthropic/claude-3-sonnet": "Claude 3 Sonnet",
        "openai/gpt-4-turbo": "GPT-4 Turbo",
        "mistralai/mistral-large": "Mistral Large",
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenRouter backend.

        Args:
            api_key: OpenRouter API key. Defaults to settings.openrouter_api_key.

        Raises:
            OpenRouterAuthException: If API key not configured.
        """
        self.api_key = api_key or settings.openrouter_api_key
        if not self.api_key:
            raise OpenRouterAuthException("OPENROUTER_API_KEY not configured in .env")

        self.session: Optional[aiohttp.ClientSession] = None
        logger.info("OpenRouterBackend initialized")

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
        model: str = "meta-llama/llama-2-70b",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using OpenRouter API.

        Args:
            prompt: Text prompt.
            model: Model to use (from MODELS or custom).
            max_tokens: Maximum tokens in response.
            temperature: Sampling temperature.

        Returns:
            Generated text.

        Raises:
            OpenRouterRateLimitException: If rate limited.
            OpenRouterGenerationException: If generation fails.

        Examples:
            >>> response = await backend.generate(
            ...     "Analyze AAPL valuation",
            ...     model="meta-llama/llama-2-70b",
            ... )
        """
        # Check rate limit
        if not rate_limiter.allow_request("openrouter"):
            raise OpenRouterRateLimitException("OpenRouter rate limit exceeded")

        session = await self._ensure_session()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            logger.debug(f"Generating with OpenRouter (model={model})")

            async with session.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.TIMEOUT),
            ) as response:
                if response.status == 401:
                    raise OpenRouterAuthException("Invalid API key")
                elif response.status == 429:
                    raise OpenRouterRateLimitException("Rate limit exceeded")
                elif response.status >= 400:
                    raise OpenRouterGenerationException(f"HTTP {response.status}")

                data = await response.json()

                # Extract text from response
                if "choices" in data and data["choices"]:
                    text = data["choices"][0]["message"]["content"]
                    logger.debug(f"Generation complete ({len(text)} chars)")
                    return text
                else:
                    raise OpenRouterGenerationException("No choices in response")

        except asyncio.TimeoutError:
            raise OpenRouterGenerationException("Request timeout")
        except OpenRouterException:
            raise
        except Exception as e:
            logger.error(f"OpenRouter generation failed: {e}")
            raise OpenRouterGenerationException(f"Generation failed: {str(e)}")

    async def batch_generate(
        self,
        prompts: list[str],
        model: str = "meta-llama/llama-2-70b",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> list[str]:
        """Generate text for multiple prompts.

        Args:
            prompts: List of prompts.
            model: Model to use.
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
                text = await self.generate(prompt, model, max_tokens, temperature)
                results.append(text)
            except OpenRouterException as e:
                logger.warning(f"Batch generation failed: {e}")
                results.append("")

        return results

    async def list_models(self) -> dict[str, str]:
        """List available models.

        Returns:
            Dictionary mapping model IDs to names.
        """
        return self.MODELS.copy()

    async def close(self) -> None:
        """Close session."""
        if self.session:
            await self.session.close()
            logger.info("OpenRouterBackend closed")


# Global backend instance
_openrouter_backend: Optional[OpenRouterBackend] = None


async def get_openrouter_backend() -> OpenRouterBackend:
    """Get or create global OpenRouter backend.

    Returns:
        OpenRouterBackend instance.

    Raises:
        OpenRouterAuthException: If API key not configured.
    """
    global _openrouter_backend
    if _openrouter_backend is None:
        _openrouter_backend = OpenRouterBackend()
    return _openrouter_backend
