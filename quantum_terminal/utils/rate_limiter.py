"""Token bucket rate limiter for API request throttling.

Implements the token bucket algorithm for distributed rate limiting.
Supports per-API configuration with logging of limit breaches.
"""

import time
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional

from quantum_terminal.utils.logger import get_logger

logger = get_logger(__name__)


class TokenBucket:
    """Token bucket rate limiter.

    Implements the token bucket algorithm where:
    - Tokens are added at a fixed rate
    - Each request consumes one token
    - Request is allowed only if tokens > 0
    """

    def __init__(
        self,
        rate: int,
        per_minutes: int = 1,
        name: str = "default",
    ):
        """Initialize token bucket.

        Args:
            rate: Number of tokens (requests) allowed.
            per_minutes: Time window in minutes for rate.
            name: Identifier for this bucket (e.g., "finnhub").

        Examples:
            >>> bucket = TokenBucket(60, 1, "finnhub")  # 60 req/min
            >>> if bucket.allow_request():
            ...     make_api_call()
        """
        self.rate = rate
        self.per_minutes = per_minutes
        self.name = name

        # Token calculation
        self.capacity = float(rate)
        self.tokens = self.capacity
        self.refill_rate = rate / (per_minutes * 60)  # tokens per second

        # Timing
        self.last_refill = time.time()

        # Thread safety
        self.lock = Lock()

        logger.info(
            f"TokenBucket initialized: {name} "
            f"(capacity={self.capacity}, refill_rate={self.refill_rate:.4f} tokens/sec)"
        )

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def allow_request(self, tokens_required: float = 1.0) -> bool:
        """Check if request is allowed under rate limit.

        Args:
            tokens_required: Number of tokens this request requires (default: 1).

        Returns:
            True if request is allowed, False if rate limited.

        Examples:
            >>> if bucket.allow_request():
            ...     api.call()
            ... else:
            ...     logger.warning("Rate limited")
        """
        with self.lock:
            self._refill()

            if self.tokens >= tokens_required:
                self.tokens -= tokens_required
                logger.debug(
                    f"Request allowed [{self.name}]: "
                    f"tokens={self.tokens:.2f}/{self.capacity}"
                )
                return True
            else:
                logger.warning(
                    f"Rate limit exceeded [{self.name}]: "
                    f"need={tokens_required}, available={self.tokens:.2f}/{self.capacity}"
                )
                return False

    def wait_if_needed(self, tokens_required: float = 1.0) -> float:
        """Wait until request is allowed.

        Args:
            tokens_required: Number of tokens this request requires.

        Returns:
            Time waited in seconds.

        Examples:
            >>> elapsed = bucket.wait_if_needed()
            >>> logger.info(f"Waited {elapsed:.2f}s for rate limit")
        """
        start = time.time()

        with self.lock:
            while True:
                self._refill()

                if self.tokens >= tokens_required:
                    self.tokens -= tokens_required
                    elapsed = time.time() - start
                    if elapsed > 0.1:
                        logger.info(
                            f"Rate limit wait [{self.name}]: "
                            f"waited={elapsed:.2f}s for {tokens_required} tokens"
                        )
                    return elapsed

                # Calculate wait time
                tokens_needed = tokens_required - self.tokens
                wait_time = tokens_needed / self.refill_rate
                time.sleep(min(wait_time, 0.1))  # Sleep in small increments

    def get_stats(self) -> dict[str, float | int]:
        """Get current bucket statistics.

        Returns:
            Dictionary with bucket state.
        """
        with self.lock:
            self._refill()
            return {
                "name": self.name,
                "tokens": float(f"{self.tokens:.2f}"),
                "capacity": self.capacity,
                "refill_rate": float(f"{self.refill_rate:.4f}"),
                "available_percent": float(f"{(self.tokens/self.capacity)*100:.1f}"),
            }

    def reset(self) -> None:
        """Reset bucket to full capacity."""
        with self.lock:
            self.tokens = self.capacity
            self.last_refill = time.time()
            logger.info(f"TokenBucket reset [{self.name}]")


class RateLimiterManager:
    """Manages multiple API rate limiters.

    Provides centralized configuration and management of rate limiters
    for different APIs.
    """

    def __init__(self):
        """Initialize rate limiter manager."""
        self.limiters: dict[str, TokenBucket] = {}
        logger.info("RateLimiterManager initialized")

    def register(
        self,
        name: str,
        rate: int,
        per_minutes: int = 1,
    ) -> TokenBucket:
        """Register a new rate limiter.

        Args:
            name: API name identifier.
            rate: Number of requests allowed per time window.
            per_minutes: Time window in minutes.

        Returns:
            Created TokenBucket instance.

        Raises:
            ValueError: If limiter already exists.

        Examples:
            >>> manager = RateLimiterManager()
            >>> finnhub = manager.register("finnhub", 60, 1)
        """
        if name in self.limiters:
            raise ValueError(f"Limiter '{name}' already registered")

        bucket = TokenBucket(rate, per_minutes, name)
        self.limiters[name] = bucket
        return bucket

    def get(self, name: str) -> Optional[TokenBucket]:
        """Get rate limiter by name.

        Args:
            name: API name identifier.

        Returns:
            TokenBucket or None if not found.
        """
        return self.limiters.get(name)

    def allow_request(self, name: str, tokens: float = 1.0) -> bool:
        """Check if request is allowed for given API.

        Args:
            name: API name identifier.
            tokens: Number of tokens required.

        Returns:
            True if allowed, False if rate limited.

        Raises:
            ValueError: If limiter not found.
        """
        bucket = self.get(name)
        if bucket is None:
            raise ValueError(f"Rate limiter '{name}' not found")
        return bucket.allow_request(tokens)

    def wait_if_needed(self, name: str, tokens: float = 1.0) -> float:
        """Wait until request is allowed for given API.

        Args:
            name: API name identifier.
            tokens: Number of tokens required.

        Returns:
            Time waited in seconds.

        Raises:
            ValueError: If limiter not found.
        """
        bucket = self.get(name)
        if bucket is None:
            raise ValueError(f"Rate limiter '{name}' not found")
        return bucket.wait_if_needed(tokens)

    def get_stats(self) -> dict[str, dict]:
        """Get statistics for all limiters.

        Returns:
            Dictionary mapping limiter names to their stats.
        """
        return {name: bucket.get_stats() for name, bucket in self.limiters.items()}

    def reset(self, name: Optional[str] = None) -> None:
        """Reset limiter(s) to full capacity.

        Args:
            name: Specific limiter to reset. If None, resets all.
        """
        if name:
            bucket = self.get(name)
            if bucket:
                bucket.reset()
        else:
            for bucket in self.limiters.values():
                bucket.reset()


# Global rate limiter manager
rate_limiter = RateLimiterManager()

# Register default API limiters
rate_limiter.register("finnhub", 60, 1)  # 60 requests/minute
rate_limiter.register("alpha_vantage", 5, 1)  # 5 requests/minute (free tier)
rate_limiter.register("fmp", 250, 1)  # 250 requests/minute
rate_limiter.register("fred", 100, 1)  # 100 requests/minute (estimated)
rate_limiter.register("newsapi", 100, 1)  # 100 requests/minute (free tier)
