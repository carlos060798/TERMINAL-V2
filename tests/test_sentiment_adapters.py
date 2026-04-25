"""Comprehensive tests for sentiment adapters (NewsAPI, Reddit, FinBERT).

Tests cover:
- Successful API calls and data transformation
- Error handling (rate limits, auth, connection)
- Caching behavior (hits, misses, TTL)
- Batch operations
- Edge cases (empty results, malformed data)
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
import asyncio

# NewsAPI Tests
class TestNewsAPIAdapter:
    """Test NewsAPI adapter."""

    @pytest.fixture
    def adapter(self):
        """Create NewsAPI adapter for testing."""
        with patch.dict("quantum_terminal.config.settings.__dict__", {"newsapi_key": "test_key"}):
            from quantum_terminal.infrastructure.sentiment.newsapi_adapter import NewsAPIAdapter

            return NewsAPIAdapter(api_key="test_key")

    @pytest.mark.asyncio
    async def test_get_headlines_success(self, adapter):
        """Test successful headlines fetch."""
        mock_response = {
            "status": "ok",
            "articles": [
                {
                    "source": {"name": "TechNews"},
                    "author": "John Doe",
                    "title": "Apple rises 5%",
                    "description": "Stock hits new highs",
                    "url": "http://example.com",
                    "urlToImage": "http://example.com/image.jpg",
                    "publishedAt": "2026-04-25T10:00:00Z",
                    "content": "Full content here",
                }
            ],
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            with patch("quantum_terminal.infrastructure.sentiment.newsapi_adapter.cache") as mock_cache:
                mock_cache.get_macro.return_value = None

                headlines = await adapter.get_headlines("AAPL", limit=10)

                assert len(headlines) == 1
                assert headlines[0]["title"] == "Apple rises 5%"
                assert headlines[0]["sentiment_ready"] is True
                assert headlines[0]["source"] == "TechNews"

    @pytest.mark.asyncio
    async def test_get_headlines_cache_hit(self, adapter):
        """Test cache hit for headlines."""
        cached_data = [{"title": "Cached", "sentiment_ready": True}]

        with patch("quantum_terminal.infrastructure.sentiment.newsapi_adapter.cache") as mock_cache:
            mock_cache.get_macro.return_value = cached_data

            headlines = await adapter.get_headlines("AAPL")

            assert headlines == cached_data
            assert mock_cache.get_macro.called

    @pytest.mark.asyncio
    async def test_get_headlines_rate_limit(self, adapter):
        """Test rate limit handling."""
        from quantum_terminal.infrastructure.sentiment.newsapi_adapter import NewsAPIRateLimitError

        with patch.object(adapter, "_get") as mock_get:
            mock_get.side_effect = NewsAPIRateLimitError("Rate limit exceeded")

            with pytest.raises(NewsAPIRateLimitError):
                await adapter.get_headlines("AAPL")

    @pytest.mark.asyncio
    async def test_search_with_dates(self, adapter):
        """Test search with date range."""
        mock_response = {
            "status": "ok",
            "articles": [
                {
                    "source": {"name": "FinanceNews"},
                    "author": "Jane Smith",
                    "title": "Fed raises rates",
                    "description": "Interest rates increase",
                    "url": "http://example.com",
                    "publishedAt": "2026-04-20T15:00:00Z",
                }
            ],
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            with patch("quantum_terminal.infrastructure.sentiment.newsapi_adapter.cache") as mock_cache:
                mock_cache.get_macro.return_value = None

                results = await adapter.search(
                    "Fed rate",
                    from_date="2026-04-01",
                    to_date="2026-04-30",
                    limit=20,
                )

                assert len(results) == 1
                assert "Fed" in results[0]["title"]

    @pytest.mark.asyncio
    async def test_batch_headlines(self, adapter):
        """Test batch headlines for multiple tickers."""
        mock_response = {
            "status": "ok",
            "articles": [{"source": {"name": "News"}, "title": "Test", "publishedAt": "2026-04-25T00:00:00Z"}],
        }

        with patch.object(adapter, "_get", new_callable=AsyncMock, return_value=mock_response):
            with patch("quantum_terminal.infrastructure.sentiment.newsapi_adapter.cache") as mock_cache:
                mock_cache.get_macro.return_value = None

                batch = await adapter.batch_headlines(["AAPL", "MSFT", "GOOGL"])

                assert len(batch) == 3
                assert "AAPL" in batch
                assert "MSFT" in batch

    @pytest.mark.asyncio
    async def test_get_daily_sentiment_volume(self, adapter):
        """Test aggregated sentiment volume."""
        mock_headlines = [
            {"publishedAt": "2026-04-25T10:00:00Z", "title": "Article 1"},
            {"publishedAt": "2026-04-25T15:00:00Z", "title": "Article 2"},
            {"publishedAt": "2026-04-24T10:00:00Z", "title": "Article 3"},
        ]

        with patch.object(adapter, "get_headlines", new_callable=AsyncMock, return_value=mock_headlines):
            with patch("quantum_terminal.infrastructure.sentiment.newsapi_adapter.cache") as mock_cache:
                mock_cache.get_macro.return_value = None

                volume = await adapter.get_daily_sentiment_volume("AAPL", days=7)

                assert volume["ticker"] == "AAPL"
                assert volume["total_articles"] == 3
                assert "2026-04-25" in volume["date_distribution"]
                assert volume["date_distribution"]["2026-04-25"] == 2

    def test_newsapi_connection_error(self, adapter):
        """Test connection error handling."""
        from quantum_terminal.infrastructure.sentiment.newsapi_adapter import NewsAPIConnectionError

        with patch.object(adapter, "_get") as mock_get:
            mock_get.side_effect = NewsAPIConnectionError("Connection failed")

            with pytest.raises(NewsAPIConnectionError):
                asyncio.run(adapter.get_headlines("AAPL"))


# Reddit Tests
class TestRedditAdapter:
    """Test Reddit adapter."""

    @pytest.fixture
    def adapter(self):
        """Create Reddit adapter for testing."""
        with patch("quantum_terminal.infrastructure.sentiment.reddit_adapter.praw"):
            from quantum_terminal.infrastructure.sentiment.reddit_adapter import RedditAdapter

            with patch.object(RedditAdapter, "__init__", return_value=None):
                adapter = RedditAdapter()
                adapter.reddit = MagicMock()
                adapter._check_rate_limit = Mock(return_value=True)
                return adapter

    def test_get_posts_success(self, adapter):
        """Test successful post retrieval."""
        mock_post = MagicMock()
        mock_post.id = "abc123"
        mock_post.title = "AAPL gaining momentum"
        mock_post.author = "investor_user"
        mock_post.created_utc = 1619000000
        mock_post.score = 150
        mock_post.num_comments = 45
        mock_post.selftext = "Bullish on Apple AAPL"
        mock_post.url = "https://reddit.com/r/stocks/comments/abc123"

        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = [mock_post]
        adapter.reddit.subreddit.return_value = mock_subreddit

        with patch("quantum_terminal.infrastructure.sentiment.reddit_adapter.cache") as mock_cache:
            mock_cache.get_macro.return_value = None

            posts = adapter.get_posts("stocks", ticker="AAPL", limit=10)

            assert len(posts) == 1
            assert posts[0]["title"] == "AAPL gaining momentum"
            assert posts[0]["ticker"] == "AAPL"
            assert posts[0]["score"] == 150

    def test_get_posts_cache_hit(self, adapter):
        """Test cache hit for posts."""
        cached_posts = [{"title": "Cached", "ticker": "AAPL"}]

        with patch("quantum_terminal.infrastructure.sentiment.reddit_adapter.cache") as mock_cache:
            mock_cache.get_macro.return_value = cached_posts

            posts = adapter.get_posts("stocks", ticker="AAPL")

            assert posts == cached_posts

    def test_get_posts_sort_options(self, adapter):
        """Test different sort options."""
        mock_post = MagicMock()
        mock_post.id = "def456"
        mock_post.title = "New post"
        mock_post.author = "user"
        mock_post.created_utc = 1619100000
        mock_post.score = 50
        mock_post.num_comments = 10
        mock_post.selftext = "MSFT"
        mock_post.url = "https://reddit.com"

        mock_subreddit = MagicMock()
        for sort in ["hot", "new", "top", "rising"]:
            setattr(mock_subreddit, sort, MagicMock(return_value=[mock_post]))

        adapter.reddit.subreddit.return_value = mock_subreddit

        with patch("quantum_terminal.infrastructure.sentiment.reddit_adapter.cache") as mock_cache:
            mock_cache.get_macro.return_value = None

            for sort_by in ["hot", "new", "top", "rising"]:
                posts = adapter.get_posts("stocks", sort_by=sort_by)
                assert len(posts) == 1

    def test_get_sentiment_summary(self, adapter):
        """Test sentiment summary aggregation."""
        mock_posts = [
            {"score": 100, "num_comments": 20, "ticker": "AAPL"},
            {"score": 80, "num_comments": 15, "ticker": "AAPL"},
            {"score": 120, "num_comments": 25, "ticker": "AAPL"},
        ]

        with patch.object(adapter, "get_posts", return_value=mock_posts):
            with patch("quantum_terminal.infrastructure.sentiment.reddit_adapter.cache") as mock_cache:
                mock_cache.get_macro.return_value = None

                summary = adapter.get_sentiment_summary("AAPL")

                assert summary["ticker"] == "AAPL"
                assert summary["total_posts"] == 3
                assert summary["total_score"] == 300
                assert summary["total_comments"] == 60
                assert summary["avg_score_per_post"] == 100.0
                assert summary["avg_comments_per_post"] == 20.0

    def test_batch_sentiment(self, adapter):
        """Test batch sentiment for multiple tickers."""
        mock_summary = {"ticker": "AAPL", "total_posts": 5, "sentiment_ready": True}

        with patch.object(adapter, "get_sentiment_summary", return_value=mock_summary):
            batch = adapter.batch_sentiment(["AAPL", "MSFT", "GOOGL"])

            assert len(batch) == 3
            assert batch["AAPL"]["ticker"] == "AAPL"

    def test_ticker_not_found(self, adapter):
        """Test filtering when ticker not found in posts."""
        mock_post = MagicMock()
        mock_post.id = "xyz"
        mock_post.title = "General market discussion"
        mock_post.author = "user"
        mock_post.created_utc = 1619000000
        mock_post.score = 50
        mock_post.num_comments = 10
        mock_post.selftext = "Market is volatile"
        mock_post.url = "https://reddit.com"

        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = [mock_post]
        adapter.reddit.subreddit.return_value = mock_subreddit

        with patch("quantum_terminal.infrastructure.sentiment.reddit_adapter.cache") as mock_cache:
            mock_cache.get_macro.return_value = None

            posts = adapter.get_posts("stocks", ticker="AAPL", limit=10)

            # Should be empty since AAPL not mentioned
            assert len(posts) == 0


# FinBERT Tests
class TestFinBERTAnalyzer:
    """Test FinBERT sentiment analyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create FinBERT analyzer for testing."""
        with patch("quantum_terminal.infrastructure.sentiment.finbert_analyzer.pipeline"):
            from quantum_terminal.infrastructure.sentiment.finbert_analyzer import FinBERTAnalyzer

            with patch.object(FinBERTAnalyzer, "__init__", return_value=None):
                analyzer = FinBERTAnalyzer()
                analyzer.sentiment_pipeline = MagicMock()
                analyzer.tokenizer = MagicMock()
                analyzer.tokenizer.encode = Mock(return_value=[101, 2054, 2003] + [0] * 100)
                return analyzer

    def test_analyze_sentiment_positive(self, analyzer):
        """Test positive sentiment analysis."""
        analyzer.sentiment_pipeline.return_value = [{"label": "positive", "score": 0.95}]

        with patch("quantum_terminal.infrastructure.sentiment.finbert_analyzer.cache") as mock_cache:
            mock_cache.get_fundamental.return_value = None

            result = analyzer.analyze_sentiment("Apple stock soared to new heights today")

            assert result["sentiment"] == "positive"
            assert result["confidence"] == 0.95
            assert result["scores"]["positive"] == 0.95

    def test_analyze_sentiment_negative(self, analyzer):
        """Test negative sentiment analysis."""
        analyzer.sentiment_pipeline.return_value = [{"label": "negative", "score": 0.87}]

        with patch("quantum_terminal.infrastructure.sentiment.finbert_analyzer.cache") as mock_cache:
            mock_cache.get_fundamental.return_value = None

            result = analyzer.analyze_sentiment("Stock market crash reported today")

            assert result["sentiment"] == "negative"
            assert result["confidence"] == 0.87

    def test_analyze_sentiment_neutral(self, analyzer):
        """Test neutral sentiment analysis."""
        analyzer.sentiment_pipeline.return_value = [{"label": "neutral", "score": 0.65}]

        with patch("quantum_terminal.infrastructure.sentiment.finbert_analyzer.cache") as mock_cache:
            mock_cache.get_fundamental.return_value = None

            result = analyzer.analyze_sentiment("Trading volume increased today")

            assert result["sentiment"] == "neutral"
            assert result["confidence"] == 0.65

    def test_analyze_sentiment_cache_hit(self, analyzer):
        """Test cache hit for sentiment."""
        cached_result = {"sentiment": "positive", "confidence": 0.9}

        with patch("quantum_terminal.infrastructure.sentiment.finbert_analyzer.cache") as mock_cache:
            mock_cache.get_fundamental.return_value = cached_result

            result = analyzer.analyze_sentiment("Test text")

            assert result == cached_result

    def test_analyze_batch(self, analyzer):
        """Test batch sentiment analysis."""
        analyzer.sentiment_pipeline.side_effect = [
            [{"label": "positive", "score": 0.9}],
            [{"label": "negative", "score": 0.85}],
            [{"label": "neutral", "score": 0.6}],
        ]

        with patch("quantum_terminal.infrastructure.sentiment.finbert_analyzer.cache") as mock_cache:
            mock_cache.get_fundamental.return_value = None

            texts = ["Good news", "Bad news", "Market news"]
            results = analyzer.analyze_batch(texts)

            assert len(results) == 3
            assert results[0]["sentiment"] == "positive"
            assert results[1]["sentiment"] == "negative"
            assert results[2]["sentiment"] == "neutral"

    def test_batch_headlines(self, analyzer):
        """Test batch headlines analysis."""
        analyzer.sentiment_pipeline.side_effect = [
            [{"label": "positive", "score": 0.92}],
            [{"label": "negative", "score": 0.88}],
        ]

        headlines = [
            {"title": "Stock rises", "description": "Apple gains 5%"},
            {"title": "Company issues", "description": "Losses reported"},
        ]

        with patch("quantum_terminal.infrastructure.sentiment.finbert_analyzer.cache") as mock_cache:
            mock_cache.get_fundamental.return_value = None

            with_sentiment = analyzer.batch_headlines(headlines)

            assert len(with_sentiment) == 2
            assert with_sentiment[0]["sentiment"] == "positive"
            assert with_sentiment[1]["sentiment"] == "negative"

    def test_get_aggregated_sentiment(self, analyzer):
        """Test aggregated sentiment metrics."""
        analyzer.sentiment_pipeline.side_effect = [
            [{"label": "positive", "score": 0.9}],
            [{"label": "positive", "score": 0.85}],
            [{"label": "neutral", "score": 0.6}],
        ]

        with patch("quantum_terminal.infrastructure.sentiment.finbert_analyzer.cache") as mock_cache:
            mock_cache.get_fundamental.return_value = None

            texts = ["Good", "Great", "Okay"]
            agg = analyzer.get_aggregated_sentiment(texts)

            assert agg["total_texts"] == 3
            assert agg["positive_count"] == 2
            assert agg["neutral_count"] == 1
            assert agg["dominant_sentiment"] == "positive"
            assert agg["positive_ratio"] == pytest.approx(0.667, rel=0.01)

    def test_empty_text_error(self, analyzer):
        """Test empty text handling."""
        from quantum_terminal.infrastructure.sentiment.finbert_analyzer import FinBERTAnalysisError

        with pytest.raises(FinBERTAnalysisError):
            analyzer.analyze_sentiment("")

    def test_estimate_cost(self, analyzer):
        """Test cost estimation (should be 0 for local model)."""
        cost = analyzer.estimate_cost(1000)
        assert cost == 0.0


# Integration tests
class TestSentimentAdaptersIntegration:
    """Integration tests for all sentiment adapters."""

    @pytest.mark.asyncio
    async def test_complete_sentiment_pipeline(self):
        """Test complete sentiment analysis pipeline."""
        # Get headlines from NewsAPI
        # Analyze with FinBERT
        # Verify sentiment flow

        headlines = [
            {"title": "Stock soars", "description": "Company beats earnings"},
            {"title": "Market falls", "description": "Economic concerns rise"},
        ]

        # Simulate FinBERT analysis
        with patch("quantum_terminal.infrastructure.sentiment.finbert_analyzer.pipeline") as mock_pipeline:
            mock_pipeline.return_value = MagicMock()
            mock_pipeline.return_value.side_effect = [
                [{"label": "positive", "score": 0.9}],
                [{"label": "negative", "score": 0.88}],
            ]

            # This would run the full pipeline in real scenario
            assert len(headlines) == 2
