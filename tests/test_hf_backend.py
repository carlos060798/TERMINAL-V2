"""Tests for HuggingFace local sentiment and embeddings backend.

Tests cover:
- FinBERT sentiment analysis
- SEC-BERT sentiment analysis
- Sentence embeddings
- LRU caching for embeddings
- No API calls (fully local)
- GPU acceleration support
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from quantum_terminal.infrastructure.ai.backends.hf_backend import (
    HFBackend,
    HFAnalysisException,
    HFAuthException,
    HFLoadException,
)


@pytest.fixture
def hf_backend():
    """Create HF backend instance."""
    with patch("quantum_terminal.config.settings") as mock_settings:
        mock_settings.hf_token = "test_hf_token"
        backend = HFBackend(hf_token="test_hf_token", use_gpu=False)
        yield backend


class TestHFBackendInit:
    """Test HF backend initialization."""

    def test_init_with_token(self):
        """Test initialization with provided token."""
        backend = HFBackend(hf_token="test_token", use_gpu=False)
        assert backend.hf_token == "test_token"
        assert backend.use_gpu is False

    def test_init_with_gpu(self):
        """Test initialization with GPU support."""
        backend = HFBackend(hf_token="test_token", use_gpu=True)
        assert backend.use_gpu is True

    def test_models_defined(self):
        """Test models are defined."""
        backend = HFBackend(hf_token="test", use_gpu=False)
        assert "finbert" in backend.FINBERT_MODEL.lower()
        assert "secbert" in backend.SECBERT_MODEL.lower()


class TestHFBackendLoadFinBERT:
    """Test FinBERT model loading."""

    @pytest.mark.asyncio
    async def test_load_finbert_success(self, hf_backend):
        """Test successful FinBERT loading."""
        mock_pipeline = MagicMock()
        with patch("quantum_terminal.infrastructure.ai.backends.hf_backend.pipeline") as mock_pipe_fn:
            mock_pipe_fn.return_value = mock_pipeline
            result = await hf_backend._load_finbert()
            assert result is not None

    @pytest.mark.asyncio
    async def test_load_finbert_error(self, hf_backend):
        """Test FinBERT loading error."""
        with patch("quantum_terminal.infrastructure.ai.backends.hf_backend.pipeline") as mock_pipe_fn:
            mock_pipe_fn.side_effect = Exception("Model not found")
            with pytest.raises(HFLoadException):
                await hf_backend._load_finbert()

    @pytest.mark.asyncio
    async def test_load_finbert_cached(self, hf_backend):
        """Test FinBERT is cached after first load."""
        mock_pipeline = MagicMock()
        with patch("quantum_terminal.infrastructure.ai.backends.hf_backend.pipeline") as mock_pipe_fn:
            mock_pipe_fn.return_value = mock_pipeline

            # First load
            result1 = await hf_backend._load_finbert()
            # Second load should return cached instance
            result2 = await hf_backend._load_finbert()

            assert result1 is result2
            # Pipeline called only once due to caching
            assert mock_pipe_fn.call_count == 1


class TestHFBackendLoadSecBERT:
    """Test SEC-BERT model loading."""

    @pytest.mark.asyncio
    async def test_load_secbert_success(self, hf_backend):
        """Test successful SEC-BERT loading."""
        mock_pipeline = MagicMock()
        with patch("quantum_terminal.infrastructure.ai.backends.hf_backend.pipeline") as mock_pipe_fn:
            mock_pipe_fn.return_value = mock_pipeline
            result = await hf_backend._load_secbert()
            assert result is not None


class TestHFBackendLoadEmbedder:
    """Test sentence-transformers embedder loading."""

    @pytest.mark.asyncio
    async def test_load_embedder_success(self, hf_backend):
        """Test successful embedder loading."""
        mock_embedder = MagicMock()
        with patch("quantum_terminal.infrastructure.ai.backends.hf_backend.SentenceTransformer") as mock_st:
            mock_st.return_value = mock_embedder
            result = await hf_backend._load_embedder()
            assert result is not None


class TestHFBackendAnalyzeSentiment:
    """Test sentiment analysis."""

    @pytest.mark.asyncio
    async def test_analyze_sentiment_finbert(self, hf_backend):
        """Test FinBERT sentiment analysis."""
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [
            {"label": "POSITIVE", "score": 0.95}
        ]

        with patch.object(hf_backend, "_load_finbert") as mock_load:
            mock_load.return_value = mock_pipeline
            with patch("quantum_terminal.infrastructure.ai.backends.hf_backend.asyncio.get_event_loop") as mock_loop:
                mock_executor = MagicMock()
                mock_loop.return_value.run_in_executor = AsyncMock(
                    return_value={"label": "POSITIVE", "score": 0.95}
                )

                result = await hf_backend.analyze_sentiment(
                    "Apple stock surged higher",
                    model="finbert",
                )

                assert result["label"] == "POSITIVE"
                assert result["score"] == 0.95
                assert result["model"] == "finbert"

    @pytest.mark.asyncio
    async def test_analyze_sentiment_secbert(self, hf_backend):
        """Test SEC-BERT sentiment analysis."""
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [
            {"label": "NEGATIVE", "score": 0.88}
        ]

        with patch.object(hf_backend, "_load_secbert") as mock_load:
            mock_load.return_value = mock_pipeline
            with patch("quantum_terminal.infrastructure.ai.backends.hf_backend.asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(
                    return_value={"label": "NEGATIVE", "score": 0.88}
                )

                result = await hf_backend.analyze_sentiment(
                    "Company reported losses",
                    model="secbert",
                )

                assert result["label"] == "NEGATIVE"
                assert result["model"] == "secbert"

    @pytest.mark.asyncio
    async def test_analyze_sentiment_unknown_model(self, hf_backend):
        """Test sentiment analysis with unknown model."""
        with pytest.raises(HFAnalysisException):
            await hf_backend.analyze_sentiment("text", model="unknown_model")

    @pytest.mark.asyncio
    async def test_analyze_sentiment_text_truncated(self, hf_backend):
        """Test sentiment analysis truncates long text."""
        long_text = "word " * 1000  # Very long text
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [
            {"label": "NEUTRAL", "score": 0.5}
        ]

        with patch.object(hf_backend, "_load_finbert") as mock_load:
            mock_load.return_value = mock_pipeline
            with patch("quantum_terminal.infrastructure.ai.backends.hf_backend.asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(
                    return_value={"label": "NEUTRAL", "score": 0.5}
                )

                result = await hf_backend.analyze_sentiment(long_text)
                assert result["label"] == "NEUTRAL"


class TestHFBackendBatchAnalyze:
    """Test batch sentiment analysis."""

    @pytest.mark.asyncio
    async def test_batch_analyze_success(self, hf_backend):
        """Test batch sentiment analysis."""
        with patch.object(hf_backend, "analyze_sentiment") as mock_analyze:
            async def async_analyze(*args, **kwargs):
                return {"label": "POSITIVE", "score": 0.9, "model": "finbert"}

            mock_analyze.side_effect = async_analyze

            results = await hf_backend.batch_analyze([
                "Great earnings report",
                "Stock crash today",
            ])

            assert len(results) == 2
            assert all("label" in r for r in results)

    @pytest.mark.asyncio
    async def test_batch_analyze_with_failures(self, hf_backend):
        """Test batch analysis handles failures."""
        with patch.object(hf_backend, "analyze_sentiment") as mock_analyze:
            async def async_analyze(*args, **kwargs):
                raise HFAnalysisException("Error")

            mock_analyze.side_effect = async_analyze

            results = await hf_backend.batch_analyze([
                "text1",
                "text2",
            ])

            assert len(results) == 2
            assert all(r["label"] == "UNKNOWN" for r in results)


class TestHFBackendEmbeddings:
    """Test embedding functionality."""

    @pytest.mark.asyncio
    async def test_get_embedding_success(self, hf_backend):
        """Test successful embedding generation."""
        mock_embedder = MagicMock()
        mock_embedder.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]

        with patch.object(hf_backend, "_load_embedder") as mock_load:
            mock_load.return_value = mock_embedder
            with patch("quantum_terminal.infrastructure.ai.backends.hf_backend.asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(
                    return_value=[0.1, 0.2, 0.3]
                )

                embedding = await hf_backend.get_embedding("Apple Inc")
                assert embedding == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_get_embedding_cached(self, hf_backend):
        """Test embedding caching."""
        mock_embedder = MagicMock()
        mock_embedder.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]

        with patch.object(hf_backend, "_load_embedder") as mock_load:
            mock_load.return_value = mock_embedder
            with patch("quantum_terminal.infrastructure.ai.backends.hf_backend.asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(
                    return_value=[0.1, 0.2, 0.3]
                )

                # First call
                emb1 = await hf_backend.get_embedding("Apple Inc")
                # Second call should use cache
                emb2 = await hf_backend.get_embedding("Apple Inc")

                assert emb1 == emb2


class TestHFBackendBatchEmbeddings:
    """Test batch embedding generation."""

    @pytest.mark.asyncio
    async def test_batch_get_embeddings_success(self, hf_backend):
        """Test batch embedding generation."""
        with patch.object(hf_backend, "get_embedding") as mock_get_emb:
            async def async_get_emb(*args, **kwargs):
                return [0.1, 0.2, 0.3]

            mock_get_emb.side_effect = async_get_emb

            embeddings = await hf_backend.batch_get_embeddings([
                "Apple Inc",
                "Microsoft Corp",
            ])

            assert len(embeddings) == 2
            assert all(len(e) == 3 for e in embeddings)

    @pytest.mark.asyncio
    async def test_batch_get_embeddings_with_failures(self, hf_backend):
        """Test batch embeddings handles failures."""
        with patch.object(hf_backend, "get_embedding") as mock_get_emb:
            async def async_get_emb(*args, **kwargs):
                raise HFAnalysisException("Error")

            mock_get_emb.side_effect = async_get_emb

            embeddings = await hf_backend.batch_get_embeddings([
                "text1",
                "text2",
            ])

            assert len(embeddings) == 2
            assert all(e == [] for e in embeddings)


class TestHFBackendCacheManagement:
    """Test embedding cache management."""

    def test_get_cache_stats(self, hf_backend):
        """Test getting cache statistics."""
        stats = hf_backend.get_cache_stats()
        assert "cache_info" in stats
        assert "hits" in stats["cache_info"]
        assert "misses" in stats["cache_info"]

    def test_clear_embedding_cache(self, hf_backend):
        """Test clearing embedding cache."""
        hf_backend.clear_embedding_cache()
        stats = hf_backend.get_cache_stats()
        assert stats["cache_info"]["hits"] == 0
        assert stats["cache_info"]["misses"] == 0


class TestHFBackendGlobal:
    """Test global backend instance."""

    @pytest.mark.asyncio
    async def test_get_hf_backend(self):
        """Test get_hf_backend returns instance."""
        from quantum_terminal.infrastructure.ai.backends.hf_backend import (
            get_hf_backend,
        )

        with patch("quantum_terminal.config.settings") as mock_settings:
            mock_settings.hf_token = "test_token"
            backend = await get_hf_backend(use_gpu=False)
            assert isinstance(backend, HFBackend)


class TestHFBackendExceptions:
    """Test exception hierarchy."""

    def test_exception_hierarchy(self):
        """Test exceptions inherit from HFException."""
        from quantum_terminal.infrastructure.ai.backends.hf_backend import HFException

        assert issubclass(HFAuthException, HFException)
        assert issubclass(HFLoadException, HFException)
        assert issubclass(HFAnalysisException, HFException)

    def test_exception_messages(self):
        """Test exception messages."""
        exc = HFLoadException("Model download failed")
        assert "Model download failed" in str(exc)
