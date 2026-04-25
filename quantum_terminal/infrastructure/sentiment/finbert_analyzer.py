"""FinBERT local sentiment analyzer for financial text.

Provides sentiment analysis using FinBERT, a BERT model fine-tuned on financial data.
Supports individual and batch analysis with caching.

Uses: transformers library with Hugging Face FinBERT model
Cache TTL: 1 hour for analyzed text
"""

import asyncio
import hashlib
from typing import Any, Dict, List, Optional, Tuple

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
except ImportError:
    pipeline = None
    AutoTokenizer = None
    AutoModelForSequenceClassification = None

from quantum_terminal.config import settings
from quantum_terminal.utils.cache import cache
from quantum_terminal.utils.logger import get_logger

logger = get_logger(__name__)


class FinBERTError(Exception):
    """Base exception for FinBERT errors."""

    pass


class FinBERTModelError(FinBERTError):
    """Exception raised when model fails to load."""

    pass


class FinBERTAnalysisError(FinBERTError):
    """Exception raised when analysis fails."""

    pass


class FinBERTAnalyzer:
    """Analyzer using FinBERT for financial sentiment analysis.

    Provides methods for:
    - Single text sentiment analysis
    - Batch sentiment analysis with concurrent processing
    - Confidence scores and label mapping
    - Results caching with TTL
    - Token count estimation
    """

    MODEL_NAME = "ProsusAI/finbert"

    def __init__(self, device: str = "cpu"):
        """Initialize FinBERT analyzer.

        Args:
            device: Device to run model on ("cpu" or "cuda").

        Raises:
            FinBERTModelError: If model fails to load.
        """
        if pipeline is None:
            raise ValueError("transformers library not installed. Install with: pip install transformers torch")

        self.device = device
        self.model = None
        self.tokenizer = None

        try:
            logger.info(f"Loading FinBERT model from {self.MODEL_NAME}...")

            self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.MODEL_NAME)

            # Create pipeline
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if device == "cuda" else -1,
                framework="pt",
            )

            logger.info(f"FinBERT model loaded on {device}")

        except Exception as e:
            raise FinBERTModelError(f"Failed to load FinBERT model: {str(e)}") from e

    def _text_hash(self, text: str) -> str:
        """Generate cache key hash from text."""
        return hashlib.md5(text.encode()).hexdigest()

    def _map_labels(self, raw_label: str) -> str:
        """Map FinBERT label to sentiment."""
        label_map = {
            "positive": "positive",
            "negative": "negative",
            "neutral": "neutral",
        }
        return label_map.get(raw_label.lower(), "neutral")

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of a single text.

        Args:
            text: Text to analyze (financial news, tweets, etc.).

        Returns:
            Dictionary with sentiment analysis:
            {
                "text": str (truncated if long),
                "sentiment": str ("positive", "negative", "neutral"),
                "confidence": float (0-1),
                "scores": {
                    "positive": float,
                    "negative": float,
                    "neutral": float
                },
                "tokens": int (approximate token count)
            }

        Raises:
            FinBERTAnalysisError: If analysis fails.

        Examples:
            >>> analyzer = FinBERTAnalyzer()
            >>> result = analyzer.analyze_sentiment("Apple stock reached new highs today")
            >>> print(f"Sentiment: {result['sentiment']} ({result['confidence']:.2%})")
        """
        if not text or not text.strip():
            raise FinBERTAnalysisError("Empty text provided")

        # Truncate for caching
        text_display = text[:100] + "..." if len(text) > 100 else text
        cache_key = f"finbert_sentiment_{self._text_hash(text)}"

        # Try cache (1 hour TTL)
        cached = cache.get_fundamental(cache_key)
        if cached:
            logger.debug(f"FinBERT cache HIT")
            return cached

        try:
            # Tokenize to estimate token count
            tokens = self.tokenizer.encode(text)
            token_count = len(tokens)

            # Truncate to model max length (512 for BERT)
            if token_count > 512:
                text_truncated = text[: int(len(text) * (512 / token_count))]
                logger.warning(f"Text truncated from {token_count} to ~512 tokens")
            else:
                text_truncated = text

            # Analyze
            raw_results = self.sentiment_pipeline(text_truncated, truncation=True)

            # First result is the prediction
            prediction = raw_results[0] if raw_results else {"label": "NEUTRAL", "score": 0.0}

            sentiment = self._map_labels(prediction.get("label", "neutral"))
            confidence = float(prediction.get("score", 0.0))

            # Build scores dictionary
            # FinBERT provides: positive, negative, neutral scores
            scores = {
                "positive": 0.0,
                "negative": 0.0,
                "neutral": 0.0,
            }

            # Map confidence to detected sentiment
            scores[sentiment] = confidence
            # Distribute remaining probability
            remaining = 1.0 - confidence
            other_sentiments = [s for s in scores.keys() if s != sentiment]
            if other_sentiments:
                per_other = remaining / len(other_sentiments)
                for s in other_sentiments:
                    scores[s] = per_other

            result = {
                "text": text_display,
                "sentiment": sentiment,
                "confidence": confidence,
                "scores": scores,
                "tokens": token_count,
            }

            # Cache for 1 hour
            cache.set_with_ttl(cache_key, result, ttl_minutes=60)
            logger.debug(f"FinBERT cache SET: {sentiment} ({confidence:.2%})")

            return result

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            raise FinBERTAnalysisError(f"Failed to analyze sentiment: {str(e)}") from e

    def analyze_batch(
        self,
        texts: List[str],
        max_workers: int = 4,
    ) -> List[Dict[str, Any]]:
        """Analyze sentiment for multiple texts.

        Args:
            texts: List of texts to analyze.
            max_workers: Number of concurrent workers (limited by GPU memory).

        Returns:
            List of sentiment analysis results.

        Examples:
            >>> analyzer = FinBERTAnalyzer()
            >>> headlines = [
            ...     "Stock market surges on positive earnings",
            ...     "Company faces accounting scandal"
            ... ]
            >>> results = analyzer.analyze_batch(headlines)
            >>> for text, result in zip(headlines, results):
            ...     print(f"{result['sentiment']}: {text}")
        """
        logger.info(f"Analyzing sentiment for {len(texts)} texts with {max_workers} workers")

        results = []
        errors = []

        for i, text in enumerate(texts):
            try:
                result = self.analyze_sentiment(text)
                results.append(result)
                logger.debug(f"Analyzed [{i+1}/{len(texts)}]: {result['sentiment']}")

            except FinBERTAnalysisError as e:
                logger.warning(f"Error analyzing text {i}: {e}")
                errors.append({"index": i, "error": str(e), "text": text[:50]})
                results.append({"error": str(e), "sentiment": "unknown"})

        if errors:
            logger.warning(f"Batch analysis completed with {len(errors)} errors")

        return results

    def batch_headlines(self, headlines: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Analyze sentiment for financial headlines.

        Args:
            headlines: List of headline dicts with 'title' and 'description' keys.

        Returns:
            List of headlines with sentiment analysis added.

        Examples:
            >>> analyzer = FinBERTAnalyzer()
            >>> headlines = [
            ...     {"title": "Apple rises", "description": "Stock up 5%"},
            ...     {"title": "Market crash", "description": "Indices fall sharply"}
            ... ]
            >>> with_sentiment = analyzer.batch_headlines(headlines)
        """
        logger.info(f"Analyzing {len(headlines)} headlines")

        results = []
        for headline in headlines:
            try:
                # Combine title and description
                text = f"{headline.get('title', '')} {headline.get('description', '')}"
                sentiment_result = self.analyze_sentiment(text)

                # Add sentiment to headline
                headline_with_sentiment = {
                    **headline,
                    "sentiment": sentiment_result["sentiment"],
                    "confidence": sentiment_result["confidence"],
                    "sentiment_scores": sentiment_result["scores"],
                }
                results.append(headline_with_sentiment)

            except Exception as e:
                logger.warning(f"Error analyzing headline: {e}")
                results.append({**headline, "error": str(e)})

        logger.info(f"Analyzed {len(results)} headlines")
        return results

    def get_aggregated_sentiment(self, texts: List[str]) -> Dict[str, Any]:
        """Get aggregated sentiment across multiple texts.

        Args:
            texts: List of texts to analyze.

        Returns:
            Dictionary with aggregated metrics:
            {
                "total_texts": int,
                "positive_count": int,
                "negative_count": int,
                "neutral_count": int,
                "avg_confidence": float,
                "dominant_sentiment": str,
                "positive_ratio": float (0-1)
            }

        Examples:
            >>> analyzer = FinBERTAnalyzer()
            >>> articles = ["Good earnings report", "Stock decline", "Neutral market"]
            >>> agg = analyzer.get_aggregated_sentiment(articles)
            >>> print(f"Dominant: {agg['dominant_sentiment']}, Positive ratio: {agg['positive_ratio']:.1%}")
        """
        logger.info(f"Aggregating sentiment for {len(texts)} texts")

        results = self.analyze_batch(texts)

        sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
        confidence_scores = []

        for result in results:
            if "error" not in result:
                sentiment = result.get("sentiment", "neutral")
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
                confidence_scores.append(result.get("confidence", 0.0))

        total = len([r for r in results if "error" not in r])

        if total == 0:
            return {
                "total_texts": len(texts),
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "avg_confidence": 0.0,
                "dominant_sentiment": "unknown",
                "positive_ratio": 0.0,
            }

        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        dominant = max(sentiment_counts, key=sentiment_counts.get)

        return {
            "total_texts": len(texts),
            "positive_count": sentiment_counts.get("positive", 0),
            "negative_count": sentiment_counts.get("negative", 0),
            "neutral_count": sentiment_counts.get("neutral", 0),
            "avg_confidence": avg_confidence,
            "dominant_sentiment": dominant,
            "positive_ratio": sentiment_counts.get("positive", 0) / total if total > 0 else 0.0,
        }

    def estimate_cost(self, tokens: int, provider: str = "hf") -> float:
        """Estimate cost of sentiment analysis (local model is free).

        Args:
            tokens: Number of tokens to analyze.
            provider: Provider name (default "hf" for Hugging Face local).

        Returns:
            Estimated cost in USD (0 for local model).
        """
        # Local FinBERT is free
        return 0.0


# Global analyzer instance
_finbert_analyzer: Optional[FinBERTAnalyzer] = None


def get_analyzer(device: str = "cpu") -> FinBERTAnalyzer:
    """Get or create global FinBERT analyzer.

    Args:
        device: Device to run on ("cpu" or "cuda").

    Returns:
        FinBERTAnalyzer instance.
    """
    global _finbert_analyzer
    if _finbert_analyzer is None:
        _finbert_analyzer = FinBERTAnalyzer(device=device)
    return _finbert_analyzer


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """Analyze sentiment using global analyzer.

    Args:
        text: Text to analyze.

    Returns:
        Sentiment analysis result.
    """
    analyzer = get_analyzer()
    return analyzer.analyze_sentiment(text)


def analyze_batch(texts: List[str]) -> List[Dict[str, Any]]:
    """Analyze batch of texts using global analyzer.

    Args:
        texts: List of texts to analyze.

    Returns:
        List of sentiment results.
    """
    analyzer = get_analyzer()
    return analyzer.analyze_batch(texts)


def batch_headlines(headlines: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Analyze headlines using global analyzer.

    Args:
        headlines: List of headline dictionaries.

    Returns:
        Headlines with sentiment scores.
    """
    analyzer = get_analyzer()
    return analyzer.batch_headlines(headlines)
