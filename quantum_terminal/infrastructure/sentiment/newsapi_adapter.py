"""NewsAPI adapter for financial news headlines with rate limiting and caching.

Provides real-time news headlines for stocks and companies via NewsAPI.
Implements token bucket rate limiting (100 req/day) and configurable TTL caching.

Rate Limit: 100 requests/day (free tier)
Cache TTL: 24 hours for headlines
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

from quantum_terminal.config import settings
from quantum_terminal.utils.cache import cache
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.utils.rate_limiter import rate_limiter

logger = get_logger(__name__)


class NewsAPIError(Exception):
    """Base exception for NewsAPI errors."""

    pass


class NewsAPIRateLimitError(NewsAPIError):
    """Exception raised when rate limit is exceeded."""

    pass


class NewsAPIHTTPError(NewsAPIError):
    """Exception raised for HTTP errors from NewsAPI."""

    pass


class NewsAPIConnectionError(NewsAPIError):
    """Exception raised for connection errors."""

    pass


class NewsAPIAdapter:
    """Adapter for NewsAPI financial news data.

    Provides methods for:
    - Real-time headlines (company name, ticker)
    - Custom news search (date range, keywords)
    - Sentiment-ready data (title, description, source)
    - Batch operations with rate limit management
    """

    BASE_URL = "https://newsapi.org/v2"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize NewsAPI adapter.

        Args:
            api_key: NewsAPI key. If None, reads from NEWSAPI_KEY env var.

        Raises:
            ValueError: If no API key is provided or found.
        """
        self.api_key = api_key or settings.newsapi_key
        if not self.api_key:
            raise ValueError("NEWSAPI_KEY not provided and not found in config")

        self.session: Optional[aiohttp.ClientSession] = None
        # Register rate limiter if not already done
        if rate_limiter.get("newsapi") is None:
            rate_limiter.register("newsapi", 100, 1)  # 100 req/day
        logger.info("NewsAPIAdapter initialized")

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request to NewsAPI.

        Args:
            endpoint: API endpoint (e.g., "everything", "top-headlines").
            params: Query parameters.

        Returns:
            JSON response as dictionary.

        Raises:
            NewsAPIRateLimitError: If rate limit exceeded.
            NewsAPIHTTPError: If HTTP error occurs.
            NewsAPIConnectionError: If connection fails.
        """
        # Check rate limit
        if not rate_limiter.allow_request("newsapi"):
            logger.warning("NewsAPI: daily rate limit exceeded")
            raise NewsAPIRateLimitError("NewsAPI: exceeded 100 req/day rate limit")

        if params is None:
            params = {}
        params["apiKey"] = self.api_key

        url = f"{self.BASE_URL}/{endpoint}"

        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 429:
                    raise NewsAPIRateLimitError(f"NewsAPI rate limit: {response.reason}")
                elif response.status == 401:
                    raise NewsAPIError("NewsAPI: Invalid API key")
                elif response.status >= 400:
                    raise NewsAPIHTTPError(f"NewsAPI HTTP {response.status}: {response.reason}")

                data = await response.json()

                # Check for API error response
                if data.get("status") == "error":
                    error_msg = data.get("message", "Unknown error")
                    raise NewsAPIError(f"NewsAPI error: {error_msg}")

                logger.debug(f"NewsAPI GET {endpoint}: {response.status}")
                return data

        except aiohttp.ClientError as e:
            raise NewsAPIConnectionError(f"NewsAPI connection error: {str(e)}") from e

    async def get_headlines(
        self,
        ticker: str,
        company_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get latest headlines for a stock or company.

        Args:
            ticker: Stock ticker (e.g., "AAPL").
            company_name: Optional full company name for better search.
            limit: Maximum number of headlines to return (1-100, default 10).

        Returns:
            List of headline dictionaries:
            [
                {
                    "source": str,
                    "author": str,
                    "title": str,
                    "description": str,
                    "url": str,
                    "publishedAt": str (ISO 8601),
                    "sentiment_ready": True  # Data ready for sentiment analysis
                }
            ]

        Raises:
            NewsAPIRateLimitError: If rate limit exceeded.
            NewsAPIHTTPError: If API error occurs.

        Examples:
            >>> async with NewsAPIAdapter() as adapter:
            ...     headlines = await adapter.get_headlines("AAPL", "Apple Inc", limit=20)
            ...     for article in headlines:
            ...         print(article["title"])
        """
        # Use company name if available, fallback to ticker
        query = company_name or ticker
        cache_key = f"newsapi_headlines_{ticker}"

        # Try cache first (24 hour TTL)
        cached = cache.get_macro(cache_key)
        if cached:
            logger.debug(f"Headlines cache HIT: {ticker}")
            return cached[:limit]

        limit = min(limit, 100)  # API max

        try:
            data = await self._get(
                "everything",
                {
                    "q": query,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": limit,
                },
            )

            articles = data.get("articles", [])

            # Transform data
            headlines = []
            for article in articles:
                headline = {
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "author": article.get("author", "Unknown"),
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "url": article.get("url", ""),
                    "image": article.get("urlToImage", ""),
                    "publishedAt": article.get("publishedAt", ""),
                    "content": article.get("content", ""),
                    "sentiment_ready": True,
                }
                headlines.append(headline)

            # Cache for 24 hours
            cache.set_with_ttl(cache_key, headlines, ttl_minutes=24 * 60)
            logger.debug(f"Headlines cache SET: {ticker} ({len(headlines)} articles)")

            return headlines

        except NewsAPIError:
            raise
        except Exception as e:
            logger.error(f"Error getting headlines for {ticker}: {e}")
            raise NewsAPIError(f"Failed to get headlines for {ticker}") from e

    async def search(
        self,
        query: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search for news articles with date range.

        Args:
            query: Search query (e.g., "stock market crash").
            from_date: Start date (YYYY-MM-DD).
            to_date: End date (YYYY-MM-DD).
            limit: Maximum results (1-100, default 20).

        Returns:
            List of article dictionaries matching search query.

        Raises:
            NewsAPIHTTPError: If API error occurs.

        Examples:
            >>> async with NewsAPIAdapter() as adapter:
            ...     articles = await adapter.search(
            ...         "Fed rate hike",
            ...         from_date="2026-01-01",
            ...         to_date="2026-04-25"
            ...     )
        """
        cache_key = f"newsapi_search_{query}_{from_date}_{to_date}"

        # Try cache
        cached = cache.get_macro(cache_key)
        if cached:
            logger.debug(f"Search cache HIT: {query}")
            return cached[:limit]

        limit = min(limit, 100)

        params = {
            "q": query,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": limit,
        }

        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        try:
            data = await self._get("everything", params)
            articles = data.get("articles", [])

            # Transform
            results = []
            for article in articles:
                results.append(
                    {
                        "source": article.get("source", {}).get("name", "Unknown"),
                        "author": article.get("author", "Unknown"),
                        "title": article.get("title", ""),
                        "description": article.get("description", ""),
                        "url": article.get("url", ""),
                        "publishedAt": article.get("publishedAt", ""),
                        "sentiment_ready": True,
                    }
                )

            # Cache for 24 hours
            cache.set_with_ttl(cache_key, results, ttl_minutes=24 * 60)

            return results

        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            raise NewsAPIError(f"Failed to search for '{query}'") from e

    async def batch_headlines(self, tickers: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Get headlines for multiple tickers concurrently.

        Args:
            tickers: List of stock tickers.

        Returns:
            Dictionary mapping ticker to headlines list. Includes exceptions for failed requests.

        Examples:
            >>> async with NewsAPIAdapter() as adapter:
            ...     all_headlines = await adapter.batch_headlines(["AAPL", "MSFT", "GOOGL"])
        """
        logger.info(f"Fetching headlines for {len(tickers)} tickers")

        tasks = [self.get_headlines(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        headlines = {}
        for ticker, result in zip(tickers, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to get headlines for {ticker}: {result}")
                headlines[ticker] = {"error": str(result)}
            else:
                headlines[ticker] = result

        logger.info(f"Batch headlines completed: {len(tickers)} tickers")
        return headlines

    async def get_daily_sentiment_volume(
        self,
        ticker: str,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Get aggregated news volume and sentiment readiness for X days.

        Args:
            ticker: Stock ticker.
            days: Number of days to look back (1-30).

        Returns:
            Dictionary with volume and dates:
            {
                "ticker": str,
                "total_articles": int,
                "date_distribution": {date: count, ...},
                "latest_date": str,
                "oldest_date": str
            }
        """
        days = min(max(days, 1), 30)
        to_date = datetime.now().date()
        from_date = to_date - timedelta(days=days)

        cache_key = f"newsapi_volume_{ticker}_{days}d"

        # Try cache
        cached = cache.get_macro(cache_key)
        if cached:
            return cached

        try:
            headlines = await self.get_headlines(
                ticker,
                limit=100,
            )

            # Count by date
            date_distribution = {}
            for article in headlines:
                pub_date = article.get("publishedAt", "").split("T")[0]
                if pub_date:
                    date_distribution[pub_date] = date_distribution.get(pub_date, 0) + 1

            result = {
                "ticker": ticker,
                "total_articles": len(headlines),
                "date_distribution": date_distribution,
                "latest_date": max(date_distribution.keys()) if date_distribution else None,
                "oldest_date": min(date_distribution.keys()) if date_distribution else None,
            }

            # Cache for 24 hours
            cache.set_with_ttl(cache_key, result, ttl_minutes=24 * 60)

            return result

        except Exception as e:
            logger.error(f"Error getting sentiment volume for {ticker}: {e}")
            raise NewsAPIError(f"Failed to get sentiment volume for {ticker}") from e


# Global adapter instance
_newsapi_adapter: Optional[NewsAPIAdapter] = None


async def get_headlines(
    ticker: str,
    company_name: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get headlines using global adapter.

    Args:
        ticker: Stock ticker.
        company_name: Optional full company name.
        limit: Maximum results.

    Returns:
        List of headlines.
    """
    global _newsapi_adapter
    if _newsapi_adapter is None:
        _newsapi_adapter = NewsAPIAdapter()

    return await _newsapi_adapter.get_headlines(ticker, company_name, limit)


async def search(
    query: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Search news using global adapter.

    Args:
        query: Search query.
        from_date: Start date.
        to_date: End date.
        limit: Maximum results.

    Returns:
        List of articles.
    """
    global _newsapi_adapter
    if _newsapi_adapter is None:
        _newsapi_adapter = NewsAPIAdapter()

    return await _newsapi_adapter.search(query, from_date, to_date, limit)
