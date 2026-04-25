"""Sentiment analysis adapters and analyzers.

Provides multiple sentiment data sources:
- NewsAPI: Real-time financial news headlines
- Reddit: Community sentiment from investment subreddits
- FinBERT: Local sentiment analysis using fine-tuned BERT model
"""

from quantum_terminal.infrastructure.sentiment.newsapi_adapter import (
    NewsAPIAdapter,
    NewsAPIError,
    NewsAPIRateLimitError,
    get_headlines,
    search,
)
from quantum_terminal.infrastructure.sentiment.reddit_adapter import (
    RedditAdapter,
    RedditAPIError,
    RedditAuthError,
    get_posts,
    get_sentiment_summary,
)
from quantum_terminal.infrastructure.sentiment.finbert_analyzer import (
    FinBERTAnalyzer,
    FinBERTError,
    FinBERTModelError,
    FinBERTAnalysisError,
    analyze_sentiment,
    analyze_batch,
    batch_headlines,
)

__all__ = [
    # NewsAPI
    "NewsAPIAdapter",
    "NewsAPIError",
    "NewsAPIRateLimitError",
    "get_headlines",
    "search",
    # Reddit
    "RedditAdapter",
    "RedditAPIError",
    "RedditAuthError",
    "get_posts",
    "get_sentiment_summary",
    # FinBERT
    "FinBERTAnalyzer",
    "FinBERTError",
    "FinBERTModelError",
    "FinBERTAnalysisError",
    "analyze_sentiment",
    "analyze_batch",
    "batch_headlines",
]
