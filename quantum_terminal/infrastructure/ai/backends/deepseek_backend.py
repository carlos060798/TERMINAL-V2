"""DeepSeek backend for reasoning-focused LLM inference.

Uses DeepSeek R1 model via API with:
- Async/await support
- Extended thinking (reasoning) mode
- Token bucket rate limiting
- Specific exception handling

Model: DeepSeek R1
Best for: Deep analysis, multi-step reasoning, complex thesis evaluation
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

# Register DeepSeek rate limiter
rate_limiter.register("deepseek", 60, 1)


class DeepSeekException(Exception):
    """Base exception for DeepSeek backend errors."""
    pass


class DeepSeekAuthException(DeepSeekException):
    """Raised when DeepSeek API key is missing or invalid."""
    pass


class DeepSeekRateLimitException(DeepSeekException):
    """Raised when DeepSeek API rate limit is exceeded."""
    pass


class DeepSeekGenerationException(DeepSeekException):
    """Raised when text generation fails."""
    pass


class DeepSeekBackend:
    """Async backend for DeepSeek API.

    Provides reasoning-focused text generation with extended thinking.

    Examples:
        >>> backend = DeepSeekBackend()
        >>> result = await backend.generate(
        ...     "Evaluate if AAPL is undervalued",
        ...     thinking_budget=10000,
        ... )
        >>> print(result["content"])
    """

    MODEL = "deepseek-reasoner"
    BASE_URL = "https://api.deepseek.com/chat/completions"
    TIMEOUT = 120

    def __init__(self, api_key: Optional[str] = None):
        """Initialize DeepSeek backend.

        Args:
            api_key: DeepSeek API key. Defaults to settings.deepseek_api_key.

        Raises:
            DeepSeekAuthException: If API key not configured.
        """
        self.api_key = api_key or settings.deepseek_api_key
        if not self.api_key:
            raise DeepSeekAuthException("DEEPSEEK_API_KEY not configured in .env")

        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"DeepSeekBackend initialized (model: {self.MODEL})")

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
        thinking_budget: int = 5000,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Generate text with reasoning using DeepSeek API.

        Args:
            prompt: Text prompt.
            thinking_budget: Tokens for extended thinking (5000-10000 for deep reasoning).
            max_tokens: Maximum tokens in output response.

        Returns:
            Dictionary with "thinking" and "content" keys.

        Raises:
            DeepSeekRateLimitException: If rate limited.
            DeepSeekGenerationException: If generation fails.

        Examples:
            >>> result = await backend.generate(
            ...     "Is Tesla overvalued at current P/E?",
            ...     thinking_budget=8000,
            ... )
            >>> print(f"Thinking: {result['thinking'][:500]}...")
            >>> print(f"Response: {result['content']}")
        """
        # Check rate limit
        if not rate_limiter.allow_request("deepseek"):
            raise DeepSeekRateLimitException("DeepSeek rate limit exceeded")

        session = await self._ensure_session()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "thinking": {
                "type": "enabled",
                "budget_tokens": thinking_budget,
            },
            "max_tokens": max_tokens,
        }

        try:
            logger.debug(f"Generating with DeepSeek (thinking_budget={thinking_budget})")

            async with session.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.TIMEOUT),
            ) as response:
                if response.status == 401:
                    raise DeepSeekAuthException("Invalid API key")
                elif response.status == 429:
                    raise DeepSeekRateLimitException("Rate limit exceeded")
                elif response.status >= 400:
                    raise DeepSeekGenerationException(f"HTTP {response.status}")

                data = await response.json()

                # Extract thinking and content
                thinking = ""
                content = ""

                for item in data.get("choices", []):
                    msg = item.get("message", {})
                    if "thinking" in msg:
                        thinking = msg["thinking"]
                    if "content" in msg:
                        content = msg["content"]

                logger.debug(f"Generation complete (thinking: {len(thinking)} chars)")
                return {
                    "thinking": thinking,
                    "content": content,
                }

        except asyncio.TimeoutError:
            raise DeepSeekGenerationException("Request timeout")
        except DeepSeekException:
            raise
        except Exception as e:
            logger.error(f"DeepSeek generation failed: {e}")
            raise DeepSeekGenerationException(f"Generation failed: {str(e)}")

    async def batch_generate(
        self,
        prompts: list[str],
        thinking_budget: int = 5000,
        max_tokens: int = 2048,
    ) -> list[dict[str, Any]]:
        """Generate text for multiple prompts sequentially.

        Args:
            prompts: List of prompts.
            thinking_budget: Tokens for thinking.
            max_tokens: Max tokens per response.

        Returns:
            List of results with thinking and content.

        Examples:
            >>> results = await backend.batch_generate([
            ...     "Analyze AAPL valuation",
            ...     "Analyze MSFT valuation",
            ... ])
        """
        results = []

        for prompt in prompts:
            try:
                result = await self.generate(prompt, thinking_budget, max_tokens)
                results.append(result)
            except DeepSeekException as e:
                logger.warning(f"Batch generation failed: {e}")
                results.append({"thinking": "", "content": ""})

        return results

    async def close(self) -> None:
        """Close session."""
        if self.session:
            await self.session.close()
            logger.info("DeepSeekBackend closed")


# Global backend instance
_deepseek_backend: Optional[DeepSeekBackend] = None


async def get_deepseek_backend() -> DeepSeekBackend:
    """Get or create global DeepSeek backend.

    Returns:
        DeepSeekBackend instance.

    Raises:
        DeepSeekAuthException: If API key not configured.
    """
    global _deepseek_backend
    if _deepseek_backend is None:
        _deepseek_backend = DeepSeekBackend()
    return _deepseek_backend
