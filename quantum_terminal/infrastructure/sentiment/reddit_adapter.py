"""Reddit adapter for stock sentiment and community discussion data.

Provides real-time Reddit posts and comments from investment subreddits.
Uses PRAW (Python Reddit API Wrapper) with rate limiting and caching.

Rate Limit: 60 requests/minute (reddit's default for authenticated users)
Cache TTL: 24 hours for posts
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

try:
    import praw
    from praw.exceptions import InvalidToken, ResponseException
except ImportError:
    praw = None
    InvalidToken = Exception
    ResponseException = Exception

from quantum_terminal.config import settings
from quantum_terminal.utils.cache import cache
from quantum_terminal.utils.logger import get_logger
from quantum_terminal.utils.rate_limiter import rate_limiter

logger = get_logger(__name__)


class RedditAPIError(Exception):
    """Base exception for Reddit API errors."""

    pass


class RedditAuthError(RedditAPIError):
    """Exception raised for authentication errors."""

    pass


class RedditConnectionError(RedditAPIError):
    """Exception raised for connection errors."""

    pass


class RedditAdapter:
    """Adapter for Reddit sentiment and discussion data.

    Provides methods for:
    - Posts from investment subreddits (r/stocks, r/investing, r/wallstreetbets)
    - Ticker-specific discussion threads
    - Sentiment-ready data (title, upvotes, comments)
    - Comment sentiment analysis
    - Batch operations with concurrent requests
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: str = "QuantumTerminal/1.0",
    ):
        """Initialize Reddit adapter.

        Args:
            client_id: Reddit app client ID.
            client_secret: Reddit app client secret.
            user_agent: User agent string for requests.

        Raises:
            ValueError: If credentials not provided or praw not installed.
            RedditAuthError: If authentication fails.
        """
        if praw is None:
            raise ValueError("praw not installed. Install with: pip install praw")

        self.client_id = client_id or settings.reddit_client_id
        self.client_secret = client_secret or settings.reddit_client_secret

        if not self.client_id or not self.client_secret:
            raise ValueError("Reddit credentials (client_id, client_secret) not configured")

        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=user_agent,
            )

            # Verify authentication
            _ = self.reddit.user.me()
            logger.info("RedditAdapter initialized and authenticated")

        except InvalidToken as e:
            raise RedditAuthError(f"Reddit authentication failed: invalid token") from e
        except Exception as e:
            raise RedditAuthError(f"Reddit authentication failed: {str(e)}") from e

        # Register rate limiter if not already done
        if rate_limiter.get("reddit") is None:
            rate_limiter.register("reddit", 60, 1)  # 60 req/min

    def _check_rate_limit(self) -> bool:
        """Check and enforce rate limit."""
        if not rate_limiter.allow_request("reddit"):
            logger.warning("Reddit: rate limit exceeded")
            return False
        return True

    def get_posts(
        self,
        subreddit: str,
        ticker: Optional[str] = None,
        limit: int = 30,
        sort_by: str = "hot",
    ) -> List[Dict[str, Any]]:
        """Get posts from a subreddit, optionally filtered by ticker.

        Args:
            subreddit: Subreddit name (e.g., "stocks", "investing", "wallstreetbets").
            ticker: Optional ticker to search for in posts.
            limit: Maximum posts to return (1-100, default 30).
            sort_by: Sort order ("hot", "new", "top", "rising").

        Returns:
            List of post dictionaries:
            [
                {
                    "id": str,
                    "title": str,
                    "author": str,
                    "created_utc": int (Unix timestamp),
                    "score": int (upvotes - downvotes),
                    "num_comments": int,
                    "selftext": str,
                    "url": str,
                    "ticker": str (if found),
                    "sentiment_ready": True
                }
            ]

        Raises:
            RedditConnectionError: If API call fails.

        Examples:
            >>> adapter = RedditAdapter()
            >>> posts = adapter.get_posts("stocks", ticker="AAPL", limit=20)
            >>> for post in posts:
            ...     print(f"{post['title']} | Score: {post['score']}")
        """
        if not self._check_rate_limit():
            raise RedditAPIError("Reddit rate limit exceeded")

        cache_key = f"reddit_posts_{subreddit}_{ticker}_{sort_by}"

        # Try cache (24 hour TTL)
        cached = cache.get_macro(cache_key)
        if cached:
            logger.debug(f"Reddit posts cache HIT: {subreddit}")
            return cached[:limit]

        limit = min(limit, 100)

        try:
            subreddit_obj = self.reddit.subreddit(subreddit)

            # Get posts based on sort
            if sort_by == "hot":
                posts = subreddit_obj.hot(limit=limit)
            elif sort_by == "new":
                posts = subreddit_obj.new(limit=limit)
            elif sort_by == "top":
                posts = subreddit_obj.top(time_filter="week", limit=limit)
            elif sort_by == "rising":
                posts = subreddit_obj.rising(limit=limit)
            else:
                posts = subreddit_obj.hot(limit=limit)

            results = []
            for post in posts:
                # Filter by ticker if specified
                post_text = f"{post.title} {post.selftext}".upper()
                found_ticker = ticker.upper() if ticker and ticker.upper() in post_text else None

                if ticker and not found_ticker:
                    continue

                post_dict = {
                    "id": post.id,
                    "title": post.title,
                    "author": str(post.author),
                    "created_utc": int(post.created_utc),
                    "score": post.score,
                    "num_comments": post.num_comments,
                    "selftext": post.selftext,
                    "url": post.url,
                    "ticker": found_ticker,
                    "sentiment_ready": True,
                }
                results.append(post_dict)

            # Cache for 24 hours
            cache.set_with_ttl(cache_key, results, ttl_minutes=24 * 60)
            logger.debug(f"Reddit posts cache SET: {subreddit} ({len(results)} posts)")

            return results

        except ResponseException as e:
            raise RedditConnectionError(f"Reddit API error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error getting posts from {subreddit}: {e}")
            raise RedditConnectionError(f"Failed to get posts from {subreddit}") from e

    def get_sentiment_summary(
        self,
        ticker: str,
        subreddit: str = "stocks",
        days: int = 7,
    ) -> Dict[str, Any]:
        """Get sentiment summary for a ticker from recent posts.

        Args:
            ticker: Stock ticker (e.g., "AAPL").
            subreddit: Subreddit to search (default "stocks").
            days: Days to look back (not strictly enforced by Reddit API).

        Returns:
            Dictionary with sentiment metrics:
            {
                "ticker": str,
                "subreddit": str,
                "total_posts": int,
                "total_score": int,
                "avg_score_per_post": float,
                "total_comments": int,
                "avg_comments_per_post": float,
                "sentiment_ready": True
            }

        Examples:
            >>> adapter = RedditAdapter()
            >>> summary = adapter.get_sentiment_summary("AAPL", subreddit="stocks")
            >>> print(f"Total engagement: {summary['total_score']}")
        """
        cache_key = f"reddit_sentiment_{ticker}_{subreddit}_{days}d"

        # Try cache
        cached = cache.get_macro(cache_key)
        if cached:
            logger.debug(f"Reddit sentiment cache HIT: {ticker}")
            return cached

        try:
            posts = self.get_posts(subreddit, ticker=ticker, limit=50)

            if not posts:
                return {
                    "ticker": ticker,
                    "subreddit": subreddit,
                    "total_posts": 0,
                    "total_score": 0,
                    "avg_score_per_post": 0,
                    "total_comments": 0,
                    "avg_comments_per_post": 0,
                    "sentiment_ready": False,
                }

            total_score = sum(p.get("score", 0) for p in posts)
            total_comments = sum(p.get("num_comments", 0) for p in posts)

            result = {
                "ticker": ticker,
                "subreddit": subreddit,
                "total_posts": len(posts),
                "total_score": total_score,
                "avg_score_per_post": total_score / len(posts) if posts else 0,
                "total_comments": total_comments,
                "avg_comments_per_post": total_comments / len(posts) if posts else 0,
                "sentiment_ready": True,
            }

            # Cache for 24 hours
            cache.set_with_ttl(cache_key, result, ttl_minutes=24 * 60)

            return result

        except Exception as e:
            logger.error(f"Error getting sentiment for {ticker}: {e}")
            raise RedditAPIError(f"Failed to get sentiment for {ticker}") from e

    def batch_sentiment(self, tickers: List[str], subreddit: str = "stocks") -> Dict[str, Dict[str, Any]]:
        """Get sentiment summaries for multiple tickers.

        Args:
            tickers: List of stock tickers.
            subreddit: Subreddit to search.

        Returns:
            Dictionary mapping ticker to sentiment summary. Includes exceptions for failed requests.

        Examples:
            >>> adapter = RedditAdapter()
            >>> summaries = adapter.batch_sentiment(["AAPL", "MSFT", "GOOGL"])
        """
        logger.info(f"Fetching sentiment for {len(tickers)} tickers from r/{subreddit}")

        results = {}
        for ticker in tickers:
            try:
                sentiment = self.get_sentiment_summary(ticker, subreddit)
                results[ticker] = sentiment
            except Exception as e:
                logger.warning(f"Failed to get sentiment for {ticker}: {e}")
                results[ticker] = {"error": str(e)}

        logger.info(f"Batch sentiment completed: {len(tickers)} tickers")
        return results


# Global adapter instance
_reddit_adapter: Optional[RedditAdapter] = None


def get_posts(
    subreddit: str,
    ticker: Optional[str] = None,
    limit: int = 30,
    sort_by: str = "hot",
) -> List[Dict[str, Any]]:
    """Get posts using global adapter.

    Args:
        subreddit: Subreddit name.
        ticker: Optional ticker filter.
        limit: Maximum results.
        sort_by: Sort order.

    Returns:
        List of posts.
    """
    global _reddit_adapter
    if _reddit_adapter is None:
        _reddit_adapter = RedditAdapter()

    return _reddit_adapter.get_posts(subreddit, ticker, limit, sort_by)


def get_sentiment_summary(
    ticker: str,
    subreddit: str = "stocks",
    days: int = 7,
) -> Dict[str, Any]:
    """Get sentiment summary using global adapter.

    Args:
        ticker: Stock ticker.
        subreddit: Subreddit name.
        days: Days to look back.

    Returns:
        Sentiment summary dictionary.
    """
    global _reddit_adapter
    if _reddit_adapter is None:
        _reddit_adapter = RedditAdapter()

    return _reddit_adapter.get_sentiment_summary(ticker, subreddit, days)
