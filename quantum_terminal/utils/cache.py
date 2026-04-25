"""Cache management with TTL support using diskcache.

Provides a wrapper around diskcache with type-specific TTL configurations:
- Quotes: 1 minute
- Fundamentals: 1 hour
- Macro data: 24 hours
- Company info: 7 days

Implements expiration strategy and logging for cache operations.
"""

from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

import diskcache

from quantum_terminal.config import settings
from quantum_terminal.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CacheConfig:
    """Cache configuration with TTL mappings by data type."""

    # TTL in minutes
    QUOTES_TTL: int = 1
    FUNDAMENTALS_TTL: int = 60
    MACRO_TTL: int = 24 * 60
    COMPANY_INFO_TTL: int = 7 * 24 * 60


class CacheManager:
    """Manager for disk-based caching with TTL support.

    Wraps diskcache.Cache with type-aware TTL configurations and
    structured logging.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize cache manager.

        Args:
            cache_dir: Directory for cache storage. Defaults to settings.cache_dir.

        Raises:
            OSError: If cache directory cannot be created.
        """
        self.cache_dir = cache_dir or settings.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        try:
            self.cache = diskcache.Cache(str(self.cache_dir))
            logger.info(f"Cache initialized at {self.cache_dir}")
        except Exception as e:
            logger.error(f"Failed to initialize cache: {e}")
            raise

    def get_with_ttl(
        self,
        key: str,
        func: Optional[Callable[..., T]] = None,
        ttl_minutes: int = 60,
        *args,
        **kwargs,
    ) -> T:
        """Get value from cache or compute and cache it.

        Args:
            key: Cache key.
            func: Function to call if cache miss. If None, returns cached value or None.
            ttl_minutes: Time-to-live in minutes.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Cached or computed value.

        Examples:
            >>> cache = CacheManager()
            >>> result = cache.get_with_ttl("aapl_quote", fetch_quote, 1, ticker="AAPL")
        """
        try:
            # Check if key exists and not expired
            if key in self.cache:
                cached_value, expiry = self.cache[key]
                if datetime.now() < expiry:
                    logger.debug(f"Cache HIT: {key}")
                    return cached_value
                else:
                    # Expired
                    logger.debug(f"Cache EXPIRED: {key}")
                    del self.cache[key]
            else:
                logger.debug(f"Cache MISS: {key}")

            # If no function provided, return None
            if func is None:
                return None

            # Compute value
            logger.debug(f"Computing value for {key}")
            value = func(*args, **kwargs)

            # Cache with TTL
            expiry = datetime.now() + timedelta(minutes=ttl_minutes)
            self.cache[key] = (value, expiry)
            logger.debug(f"Cache SET: {key} (TTL: {ttl_minutes}m)")

            return value

        except Exception as e:
            logger.error(f"Cache error for key {key}: {e}")
            if func is not None:
                logger.info(f"Falling back to function execution for {key}")
                return func(*args, **kwargs)
            raise

    def set_with_ttl(
        self, key: str, value: Any, ttl_minutes: int = 60
    ) -> None:
        """Set value in cache with TTL.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl_minutes: Time-to-live in minutes.

        Raises:
            Exception: If cache write fails.
        """
        try:
            expiry = datetime.now() + timedelta(minutes=ttl_minutes)
            self.cache[key] = (value, expiry)
            logger.debug(f"Cache SET: {key} (TTL: {ttl_minutes}m)")
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            raise

    def get_quote(self, key: str, func: Optional[Callable] = None, *args, **kwargs) -> Any:
        """Get quote from cache with 1-minute TTL.

        Args:
            key: Cache key.
            func: Function to call if cache miss.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Cached or computed quote.
        """
        return self.get_with_ttl(key, func, CacheConfig.QUOTES_TTL, *args, **kwargs)

    def get_fundamental(
        self, key: str, func: Optional[Callable] = None, *args, **kwargs
    ) -> Any:
        """Get fundamental from cache with 1-hour TTL.

        Args:
            key: Cache key.
            func: Function to call if cache miss.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Cached or computed fundamental.
        """
        return self.get_with_ttl(key, func, CacheConfig.FUNDAMENTALS_TTL, *args, **kwargs)

    def get_macro(self, key: str, func: Optional[Callable] = None, *args, **kwargs) -> Any:
        """Get macro data from cache with 24-hour TTL.

        Args:
            key: Cache key.
            func: Function to call if cache miss.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Cached or computed macro data.
        """
        return self.get_with_ttl(key, func, CacheConfig.MACRO_TTL, *args, **kwargs)

    def get_company_info(self, key: str, func: Optional[Callable] = None, *args, **kwargs) -> Any:
        """Get company info from cache with 7-day TTL.

        Args:
            key: Cache key.
            func: Function to call if cache miss.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            Cached or computed company info.
        """
        return self.get_with_ttl(key, func, CacheConfig.COMPANY_INFO_TTL, *args, **kwargs)

    def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries.

        Args:
            pattern: Optional key pattern to match (e.g., "aapl_*"). If None, clears all.

        Returns:
            Number of entries cleared.

        Raises:
            Exception: If clear operation fails.
        """
        try:
            count = 0

            if pattern is None:
                # Clear all
                count = len(self.cache)
                self.cache.clear()
                logger.info(f"Cache cleared: {count} entries removed")
            else:
                # Clear matching pattern
                keys_to_delete = [k for k in self.cache.keys() if pattern in str(k)]
                for key in keys_to_delete:
                    del self.cache[key]
                count = len(keys_to_delete)
                logger.info(f"Cache cleared: {count} entries matching '{pattern}' removed")

            return count

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats.
        """
        try:
            return {
                "size": len(self.cache),
                "directory": str(self.cache_dir),
                "volume": sum(
                    (self.cache_dir / f).stat().st_size
                    for f in self.cache_dir.glob("**/*")
                    if f.is_file()
                ),
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}

    def close(self) -> None:
        """Close cache connection."""
        try:
            self.cache.close()
            logger.info("Cache closed")
        except Exception as e:
            logger.error(f"Error closing cache: {e}")


# Global cache instance
cache = CacheManager()


def cache_result(ttl_minutes: int = 60, cache_key: Optional[str] = None):
    """Decorator to cache function results with TTL.

    Args:
        ttl_minutes: Time-to-live in minutes.
        cache_key: Optional custom cache key (uses function name if None).

    Returns:
        Decorated function.

    Examples:
        >>> @cache_result(ttl_minutes=1)
        ... def get_quote(ticker: str):
        ...     return fetch_quote(ticker)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            key = cache_key or f"{func.__name__}:{args}:{kwargs}"
            return cache.get_with_ttl(key, lambda: func(*args, **kwargs), ttl_minutes)

        return wrapper

    return decorator
