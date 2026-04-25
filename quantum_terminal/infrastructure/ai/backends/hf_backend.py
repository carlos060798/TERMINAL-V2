"""Hugging Face backend for local sentiment analysis and embeddings.

Uses local FinBERT and sentence-transformers models with:
- In-memory LRU caching for embeddings
- Batch processing
- No API calls (fully local)
- GPU acceleration support

Models:
- FinBERT: Financial sentiment analysis
- SEC-BERT: SEC filing analysis
- sentence-transformers: Semantic embeddings

Best for: Local, offline sentiment analysis, embeddings, no latency
"""

import asyncio
from functools import lru_cache
from typing import Any, Optional

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
    from sentence_transformers import SentenceTransformer
except ImportError:
    raise ImportError(
        "transformers and sentence-transformers required: "
        "pip install transformers sentence-transformers torch"
    )

from quantum_terminal.config import settings
from quantum_terminal.utils.logger import get_logger

logger = get_logger(__name__)


class HFException(Exception):
    """Base exception for HuggingFace backend errors."""
    pass


class HFAuthException(HFException):
    """Raised when HF token is missing or invalid."""
    pass


class HFLoadException(HFException):
    """Raised when model fails to load."""
    pass


class HFAnalysisException(HFException):
    """Raised when analysis fails."""
    pass


class HFBackend:
    """Async backend for HuggingFace transformers (local models).

    Provides sentiment analysis and embeddings without API calls.

    Examples:
        >>> backend = HFBackend()
        >>> sentiment = await backend.analyze_sentiment("AAPL reported strong earnings")
        >>> embeddings = await backend.get_embedding("Apple Inc")
    """

    # Model identifiers
    FINBERT_MODEL = "yiyanghkust/finbert-pretrain"
    SECBERT_MODEL = "nlpaueb/sec-bert-base"
    EMBEDDER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self, hf_token: Optional[str] = None, use_gpu: bool = False):
        """Initialize HF backend with local models.

        Args:
            hf_token: Optional HuggingFace token.
            use_gpu: Whether to use GPU if available.

        Raises:
            HFLoadException: If models fail to load.
        """
        self.hf_token = hf_token or settings.hf_token
        self.use_gpu = use_gpu

        # Models (loaded lazily)
        self._finbert_pipeline = None
        self._secbert_pipeline = None
        self._embedder = None

        # Embedding cache (LRU, max 10000 items)
        self._embedding_cache = lru_cache(maxsize=10000)(self._compute_embedding)

        logger.info(
            f"HFBackend initialized (use_gpu={use_gpu}, "
            f"finbert={self.FINBERT_MODEL})"
        )

    async def _load_finbert(self) -> Any:
        """Lazy load FinBERT pipeline."""
        if self._finbert_pipeline is None:
            try:
                logger.info("Loading FinBERT model...")
                self._finbert_pipeline = pipeline(
                    "sentiment-analysis",
                    model=self.FINBERT_MODEL,
                    device=0 if self.use_gpu else -1,
                )
                logger.info("FinBERT loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load FinBERT: {e}")
                raise HFLoadException(f"FinBERT load failed: {str(e)}")

        return self._finbert_pipeline

    async def _load_secbert(self) -> Any:
        """Lazy load SEC-BERT pipeline."""
        if self._secbert_pipeline is None:
            try:
                logger.info("Loading SEC-BERT model...")
                self._secbert_pipeline = pipeline(
                    "sentiment-analysis",
                    model=self.SECBERT_MODEL,
                    device=0 if self.use_gpu else -1,
                )
                logger.info("SEC-BERT loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load SEC-BERT: {e}")
                raise HFLoadException(f"SEC-BERT load failed: {str(e)}")

        return self._secbert_pipeline

    async def _load_embedder(self) -> SentenceTransformer:
        """Lazy load sentence-transformers embedder."""
        if self._embedder is None:
            try:
                logger.info("Loading sentence-transformers model...")
                self._embedder = SentenceTransformer(
                    self.EMBEDDER_MODEL,
                    device=0 if self.use_gpu else -1,
                )
                logger.info("Embedder loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedder: {e}")
                raise HFLoadException(f"Embedder load failed: {str(e)}")

        return self._embedder

    async def analyze_sentiment(
        self,
        text: str,
        model: str = "finbert",
    ) -> dict[str, Any]:
        """Analyze sentiment of text using local FinBERT.

        Args:
            text: Text to analyze.
            model: "finbert" or "secbert".

        Returns:
            Dictionary with "label" and "score" (0-1).

        Raises:
            HFAnalysisException: If analysis fails.

        Examples:
            >>> result = await backend.analyze_sentiment(
            ...     "Apple stock is up 10% after strong earnings"
            ... )
            >>> print(f"Sentiment: {result['label']}, Score: {result['score']:.2f}")
        """
        try:
            if model == "finbert":
                pipeline = await self._load_finbert()
            elif model == "secbert":
                pipeline = await self._load_secbert()
            else:
                raise HFAnalysisException(f"Unknown model: {model}")

            # Run in thread to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: pipeline(text[:512])[0],  # Truncate for model limits
            )

            return {
                "label": result["label"],
                "score": float(result["score"]),
                "model": model,
            }

        except HFException:
            raise
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            raise HFAnalysisException(f"Analysis failed: {str(e)}")

    async def batch_analyze(
        self,
        texts: list[str],
        model: str = "finbert",
    ) -> list[dict[str, Any]]:
        """Analyze sentiment for multiple texts.

        Args:
            texts: List of texts to analyze.
            model: "finbert" or "secbert".

        Returns:
            List of sentiment results.

        Examples:
            >>> results = await backend.batch_analyze([
            ...     "Strong earnings report",
            ...     "Disappointing revenue",
            ... ])
        """
        results = []

        for text in texts:
            try:
                result = await self.analyze_sentiment(text, model)
                results.append(result)
            except HFException as e:
                logger.warning(f"Analysis failed for text: {e}")
                results.append({
                    "label": "UNKNOWN",
                    "score": 0.0,
                    "error": str(e),
                })

        return results

    def _compute_embedding(self, text: str) -> list[float]:
        """Compute embedding for text (cached).

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.
        """
        embedder = asyncio.run(self._load_embedder())
        embedding = embedder.encode(text[:512], convert_to_tensor=False)
        return embedding.tolist()

    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding for text with caching.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector (cached).

        Examples:
            >>> embedding = await backend.get_embedding("Apple Inc")
            >>> print(f"Embedding dimension: {len(embedding)}")
        """
        try:
            # Use cached computation
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                self._embedding_cache,
                text,
            )
            return embedding
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise HFAnalysisException(f"Embedding failed: {str(e)}")

    async def batch_get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.

        Examples:
            >>> embeddings = await backend.batch_get_embeddings([
            ...     "Apple Inc",
            ...     "Microsoft Corp",
            ... ])
        """
        embeddings = []

        for text in texts:
            try:
                emb = await self.get_embedding(text)
                embeddings.append(emb)
            except Exception as e:
                logger.warning(f"Embedding failed: {e}")
                embeddings.append([])

        return embeddings

    def get_cache_stats(self) -> dict[str, Any]:
        """Get embedding cache statistics.

        Returns:
            Cache hit/miss info.
        """
        return {
            "cache_info": self._embedding_cache.cache_info()._asdict(),
        }

    def clear_embedding_cache(self) -> None:
        """Clear embedding cache."""
        self._embedding_cache.cache_clear()
        logger.info("Embedding cache cleared")


# Global backend instance
_hf_backend: Optional[HFBackend] = None


async def get_hf_backend(use_gpu: bool = False) -> HFBackend:
    """Get or create global HF backend.

    Args:
        use_gpu: Whether to use GPU.

    Returns:
        HFBackend instance.

    Raises:
        HFLoadException: If models fail to load.
    """
    global _hf_backend
    if _hf_backend is None:
        _hf_backend = HFBackend(use_gpu=use_gpu)
    return _hf_backend
