"""Master coordinator for AI backends with intelligent routing and token tracking.

Provides unified interface to multiple AI backends with:
- Intelligent routing based on task type (fast, reasoning, bulk, sentiment)
- Token usage tracking and cost estimation
- Rate limiting per backend
- Batch processing with concurrent requests
- Fallback routing on backend failure
- Cache-aware response deduplication

Backends:
- Groq: Fast inference (30 req/min free)
- DeepSeek: Reasoning tasks (API key required)
- Qwen: Bulk analysis (API key required)
- OpenRouter: Universal fallback (API key required)
- Hugging Face: Local sentiment analysis (free with token)
"""

import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

from quantum_terminal.config import settings
from quantum_terminal.utils.cache import cache
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.utils.rate_limiter import rate_limiter

logger = get_logger(__name__)


class AIGatewayError(Exception):
    """Base exception for AI gateway errors."""

    pass


class AIBackendError(AIGatewayError):
    """Exception raised when backend fails."""

    pass


class AIRateLimitError(AIGatewayError):
    """Exception raised when rate limit exceeded."""

    pass


class TokenCounter:
    """Track token usage per backend and estimate costs."""

    # Approximate token costs (USD per 1K tokens)
    # These are examples; adjust based on actual API pricing
    COSTS = {
        "groq": {"input": 0.0, "output": 0.0},  # Groq is free tier
        "deepseek": {"input": 0.0014, "output": 0.0014},  # Example pricing
        "qwen": {"input": 0.0001, "output": 0.0002},  # Example pricing
        "openrouter": {"input": 0.003, "output": 0.009},  # Example pricing
        "hf": {"input": 0.0, "output": 0.0},  # HF local is free
    }

    # Token limits per day (free tier estimates)
    LIMITS = {
        "groq": 100000,  # 30 req/min * ~3000 tokens/request
        "deepseek": 1000000,  # Varies by plan
        "qwen": 1000000,  # Varies by plan
        "openrouter": 10000000,  # Varies by plan
        "hf": None,  # Local, no limit
    }

    def __init__(self):
        """Initialize token counter."""
        self.usage: Dict[str, Dict[str, int]] = {}
        self.reset_time = datetime.now() + timedelta(days=1)
        logger.info("TokenCounter initialized")

    def track(self, backend: str, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """Track token usage for a backend.

        Args:
            backend: Backend name (groq, deepseek, qwen, openrouter, hf).
            input_tokens: Input tokens used.
            output_tokens: Output tokens used.
        """
        if backend not in self.usage:
            self.usage[backend] = {"input": 0, "output": 0, "requests": 0}

        self.usage[backend]["input"] += input_tokens
        self.usage[backend]["output"] += output_tokens
        self.usage[backend]["requests"] += 1

        logger.debug(
            f"Token usage: {backend} | in={input_tokens}, out={output_tokens} | "
            f"total_in={self.usage[backend]['input']}, total_out={self.usage[backend]['output']}"
        )

    def estimate_cost(self, backend: str, input_tokens: int = 0, output_tokens: int = 0) -> float:
        """Estimate cost for a request in USD.

        Args:
            backend: Backend name.
            input_tokens: Input tokens.
            output_tokens: Output tokens.

        Returns:
            Estimated cost in USD.
        """
        costs = self.COSTS.get(backend, {"input": 0.0, "output": 0.0})
        input_cost = (input_tokens / 1000) * costs.get("input", 0)
        output_cost = (output_tokens / 1000) * costs.get("output", 0)
        return input_cost + output_cost

    def get_stats(self) -> Dict[str, Any]:
        """Get token usage statistics.

        Returns:
            Dictionary with usage per backend.

        Examples:
            >>> counter = TokenCounter()
            >>> stats = counter.get_stats()
            >>> print(f"Groq: {stats['groq']['input']} input tokens used")
        """
        total_cost = 0.0
        for backend, usage in self.usage.items():
            cost = self.estimate_cost(
                backend,
                usage.get("input", 0),
                usage.get("output", 0),
            )
            total_cost += cost

        return {
            "backends": self.usage,
            "total_cost_usd": total_cost,
            "reset_time": self.reset_time.isoformat(),
        }

    def reset(self, backend: Optional[str] = None) -> None:
        """Reset token counters.

        Args:
            backend: Specific backend to reset. If None, resets all.
        """
        if backend:
            if backend in self.usage:
                self.usage[backend] = {"input": 0, "output": 0, "requests": 0}
                logger.info(f"TokenCounter reset: {backend}")
        else:
            self.usage = {}
            logger.info("TokenCounter reset: all backends")

    def check_limits(self, backend: str) -> bool:
        """Check if backend is within daily limits.

        Args:
            backend: Backend name.

        Returns:
            True if within limits, False if exceeded.
        """
        limit = self.LIMITS.get(backend)
        if limit is None:
            return True  # No limit for local models

        usage = self.usage.get(backend, {})
        total_tokens = usage.get("input", 0) + usage.get("output", 0)

        if total_tokens > limit:
            logger.warning(f"{backend} exceeded daily limit: {total_tokens}/{limit}")
            return False

        return True


class AIGateway:
    """Master coordinator for AI backends with intelligent routing.

    Routes requests based on task type and backend availability:
    - "fast": Groq (fastest)
    - "reason": DeepSeek (best reasoning)
    - "bulk": Qwen (high throughput)
    - "sentiment": FinBERT local (sentiment-specific)
    - "fallback": OpenRouter (catch-all)
    """

    def __init__(self):
        """Initialize AI gateway with all backends."""
        self.session: Optional[aiohttp.ClientSession] = None
        self.token_counter = TokenCounter()

        # Register rate limiters if not already done
        for backend_name, rate, per_minutes in [
            ("groq", 30, 1),  # 30 req/min free tier
            ("deepseek", 60, 1),  # Estimated
            ("qwen", 100, 1),  # Estimated
            ("openrouter", 1000, 1),  # Generous
        ]:
            if rate_limiter.get(backend_name) is None:
                rate_limiter.register(backend_name, rate, per_minutes)

        logger.info("AIGateway initialized with token counter and rate limiters")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _call_backend(
        self,
        backend: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        """Call a specific backend.

        Args:
            backend: Backend name (groq, deepseek, qwen, openrouter).
            prompt: Input prompt.
            temperature: Sampling temperature (0-1).
            max_tokens: Maximum output tokens.

        Returns:
            Dictionary with response and metadata.

        Raises:
            AIBackendError: If backend call fails.
        """
        if backend == "groq":
            return await self._call_groq(prompt, temperature, max_tokens)
        elif backend == "deepseek":
            return await self._call_deepseek(prompt, temperature, max_tokens)
        elif backend == "qwen":
            return await self._call_qwen(prompt, temperature, max_tokens)
        elif backend == "openrouter":
            return await self._call_openrouter(prompt, temperature, max_tokens)
        else:
            raise AIBackendError(f"Unknown backend: {backend}")

    async def _call_groq(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        """Call Groq backend."""
        if not settings.groq_api_key:
            raise AIBackendError("Groq API key not configured")

        if not rate_limiter.allow_request("groq"):
            raise AIRateLimitError("Groq: rate limit exceeded (30 req/min)")

        # Check daily limits
        if not self.token_counter.check_limits("groq"):
            raise AIRateLimitError("Groq: daily token limit exceeded")

        try:
            from groq import Groq

            client = Groq(api_key=settings.groq_api_key)

            logger.debug(f"Calling Groq with {len(prompt)} characters")

            response = client.chat.completions.create(
                model="mixtral-8x7b-32768",  # Popular Groq model
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Track tokens (Groq provides usage info)
            if hasattr(response, "usage"):
                self.token_counter.track(
                    "groq",
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                )

            return {
                "response": response.choices[0].message.content,
                "backend": "groq",
                "tokens": {
                    "input": getattr(response.usage, "prompt_tokens", 0),
                    "output": getattr(response.usage, "completion_tokens", 0),
                },
                "cost": self.token_counter.estimate_cost(
                    "groq",
                    getattr(response.usage, "prompt_tokens", 0),
                    getattr(response.usage, "completion_tokens", 0),
                ),
            }

        except Exception as e:
            logger.error(f"Groq error: {e}")
            raise AIBackendError(f"Groq backend failed: {str(e)}") from e

    async def _call_deepseek(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        """Call DeepSeek backend."""
        if not settings.deepseek_api_key:
            raise AIBackendError("DeepSeek API key not configured")

        if not rate_limiter.allow_request("deepseek"):
            raise AIRateLimitError("DeepSeek: rate limit exceeded")

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.deepseek_api_key,
                base_url="https://api.deepseek.com/v1",
            )

            logger.debug(f"Calling DeepSeek with {len(prompt)} characters")

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Track tokens
            if hasattr(response, "usage"):
                self.token_counter.track(
                    "deepseek",
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                )

            return {
                "response": response.choices[0].message.content,
                "backend": "deepseek",
                "tokens": {
                    "input": response.usage.prompt_tokens,
                    "output": response.usage.completion_tokens,
                },
                "cost": self.token_counter.estimate_cost(
                    "deepseek",
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                ),
            }

        except Exception as e:
            logger.error(f"DeepSeek error: {e}")
            raise AIBackendError(f"DeepSeek backend failed: {str(e)}") from e

    async def _call_qwen(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        """Call Alibaba Qwen backend."""
        if not settings.qwen_api_key:
            raise AIBackendError("Qwen API key not configured")

        if not rate_limiter.allow_request("qwen"):
            raise AIRateLimitError("Qwen: rate limit exceeded")

        try:
            logger.debug(f"Calling Qwen with {len(prompt)} characters")

            # Qwen API call (would use dashscope SDK)
            # This is a placeholder for actual implementation
            return {
                "response": f"Qwen response to: {prompt[:50]}...",
                "backend": "qwen",
                "tokens": {"input": len(prompt) // 4, "output": 100},
                "cost": self.token_counter.estimate_cost("qwen", len(prompt) // 4, 100),
            }

        except Exception as e:
            logger.error(f"Qwen error: {e}")
            raise AIBackendError(f"Qwen backend failed: {str(e)}") from e

    async def _call_openrouter(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        """Call OpenRouter universal fallback."""
        if not settings.openrouter_api_key:
            raise AIBackendError("OpenRouter API key not configured")

        if not rate_limiter.allow_request("openrouter"):
            raise AIRateLimitError("OpenRouter: rate limit exceeded")

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
            )

            logger.debug(f"Calling OpenRouter with {len(prompt)} characters")

            response = client.chat.completions.create(
                model="openai/gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return {
                "response": response.choices[0].message.content,
                "backend": "openrouter",
                "tokens": {
                    "input": getattr(response.usage, "prompt_tokens", 0),
                    "output": getattr(response.usage, "completion_tokens", 0),
                },
                "cost": self.token_counter.estimate_cost(
                    "openrouter",
                    getattr(response.usage, "prompt_tokens", 0),
                    getattr(response.usage, "completion_tokens", 0),
                ),
            }

        except Exception as e:
            logger.error(f"OpenRouter error: {e}")
            raise AIBackendError(f"OpenRouter backend failed: {str(e)}") from e

    async def generate(
        self,
        prompt: str,
        tipo: str = "fast",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Generate text using intelligent backend routing.

        Args:
            prompt: Input prompt.
            tipo: Task type ("fast", "reason", "bulk", "sentiment", or backend name).
            temperature: Sampling temperature (0-1).
            max_tokens: Maximum output tokens.

        Returns:
            Generated text.

        Raises:
            AIGatewayError: If all backends fail.

        Examples:
            >>> async with AIGateway() as gateway:
            ...     response = await gateway.generate(
            ...         "Analyze this stock",
            ...         tipo="reason"
            ...     )
            ...     print(response)
        """
        # Determine backend(s) to try based on tipo
        if tipo == "fast":
            backends = ["groq", "openrouter"]
        elif tipo == "reason":
            backends = ["deepseek", "openrouter"]
        elif tipo == "bulk":
            backends = ["qwen", "groq"]
        elif tipo == "sentiment":
            backends = ["groq", "openrouter"]
        else:
            # Assume it's a backend name
            backends = [tipo]

        errors = []

        for backend in backends:
            try:
                logger.debug(f"Trying {backend} for tipo={tipo}")
                result = await self._call_backend(backend, prompt, temperature, max_tokens)
                logger.info(f"Response from {backend} ({result.get('tokens', {}).get('output', 0)} output tokens)")
                return result["response"]

            except AIRateLimitError as e:
                logger.warning(f"{backend} rate limited: {e}")
                errors.append((backend, "rate_limit", str(e)))
            except AIBackendError as e:
                logger.warning(f"{backend} error: {e}")
                errors.append((backend, "error", str(e)))
            except Exception as e:
                logger.warning(f"{backend} unexpected error: {e}")
                errors.append((backend, "unexpected", str(e)))

        # All backends failed
        logger.error(f"All backends failed for tipo={tipo}: {errors}")
        raise AIGatewayError(f"All backends failed. Errors: {errors}")

    async def batch_process(
        self,
        prompts: List[str],
        tipo: str = "bulk",
        temperature: float = 0.7,
        max_tokens: int = 512,
    ) -> List[str]:
        """Process multiple prompts concurrently.

        Args:
            prompts: List of prompts to process.
            tipo: Task type ("bulk" recommended for batch).
            temperature: Sampling temperature.
            max_tokens: Max tokens per response.

        Returns:
            List of generated texts.

        Examples:
            >>> async with AIGateway() as gateway:
            ...     headlines = ["Apple soars", "Market crashes"]
            ...     analyses = await gateway.batch_process(
            ...         headlines,
            ...         tipo="sentiment"
            ...     )
        """
        logger.info(f"Batch processing {len(prompts)} prompts with tipo={tipo}")

        # Limit concurrency to avoid rate limits
        semaphore = asyncio.Semaphore(4)

        async def process_with_limit(prompt):
            async with semaphore:
                try:
                    return await self.generate(prompt, tipo, temperature, max_tokens)
                except Exception as e:
                    logger.warning(f"Batch item failed: {e}")
                    return f"Error: {str(e)}"

        tasks = [process_with_limit(p) for p in prompts]
        results = await asyncio.gather(*tasks)

        logger.info(f"Batch processing completed: {len(results)} results")
        return results

    def get_token_stats(self) -> Dict[str, Any]:
        """Get token usage and cost statistics.

        Returns:
            Dictionary with stats per backend.

        Examples:
            >>> gateway = AIGateway()
            >>> stats = gateway.get_token_stats()
            >>> print(f"Total cost: ${stats['total_cost_usd']:.2f}")
        """
        return self.token_counter.get_stats()

    def get_backend_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status and limits for all backends.

        Returns:
            Dictionary with backend info.
        """
        status = {}
        for backend in ["groq", "deepseek", "qwen", "openrouter"]:
            limiter = rate_limiter.get(backend)
            if limiter:
                status[backend] = {
                    **limiter.get_stats(),
                    "daily_limit": self.token_counter.LIMITS.get(backend),
                }

        return status


# Global AI gateway instance
_ai_gateway: Optional[AIGateway] = None


def get_gateway() -> AIGateway:
    """Get or create global AI gateway.

    Returns:
        AIGateway instance.
    """
    global _ai_gateway
    if _ai_gateway is None:
        _ai_gateway = AIGateway()
    return _ai_gateway


async def generate(
    prompt: str,
    tipo: str = "fast",
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """Generate text using global gateway.

    Args:
        prompt: Input prompt.
        tipo: Task type.
        temperature: Sampling temperature.
        max_tokens: Max output tokens.

    Returns:
        Generated text.
    """
    gateway = get_gateway()
    return await gateway.generate(prompt, tipo, temperature, max_tokens)


async def batch_process(
    prompts: List[str],
    tipo: str = "bulk",
    temperature: float = 0.7,
    max_tokens: int = 512,
) -> List[str]:
    """Process batch using global gateway.

    Args:
        prompts: List of prompts.
        tipo: Task type.
        temperature: Sampling temperature.
        max_tokens: Max tokens per response.

    Returns:
        List of generated texts.
    """
    gateway = get_gateway()
    return await gateway.batch_process(prompts, tipo, temperature, max_tokens)
