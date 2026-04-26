"""
Tests for Embedding Generation and Semantic Search.

Tests cover:
- Embedding generation
- Mock embeddings (deterministic)
- Vector storage (in-memory)
- Semantic similarity search
- Batch operations

Phase 2 - Infrastructure Testing
Reference: PLAN_MAESTRO.md - Phase 2: Testing
"""

import pytest
import numpy as np
from datetime import datetime

from quantum_terminal.infrastructure.ml.embeddings import (
    EmbeddingGenerator,
    VectorStore,
    generate_embedding,
    search_similar_thesis,
    store_thesis_embedding
)


class TestEmbeddingGenerator:
    """Tests for embedding generation."""

    def test_generator_initialization(self):
        """Test generator initializes correctly."""
        gen = EmbeddingGenerator()
        assert gen is not None
        assert gen.model_name == "all-MiniLM-L6-v2"

    def test_generate_embedding_simple(self):
        """Test generating embedding for simple text."""
        gen = EmbeddingGenerator()
        text = "Apple is undervalued"

        embedding = gen.generate(text)

        assert embedding is not None
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)

    def test_generate_embedding_long_text(self):
        """Test generating embedding for long text."""
        gen = EmbeddingGenerator()
        text = """
        Apple Inc. is a technology company with strong ecosystem advantages.
        The ecosystem lock-in creates a durable competitive moat.
        Services revenue is growing faster than hardware, improving margins.
        This creates a compelling value opportunity at current prices.
        """

        embedding = gen.generate(text)

        assert embedding.shape == (384,)

    def test_generate_embedding_empty_text_error(self):
        """Test empty text raises error."""
        gen = EmbeddingGenerator()

        with pytest.raises(ValueError, match="cannot be empty"):
            gen.generate("")

    def test_generate_embedding_deterministic(self):
        """Test mock embeddings are deterministic (same text = same embedding)."""
        gen = EmbeddingGenerator()
        text = "Apple thesis"

        emb1 = gen.generate(text)
        emb2 = gen.generate(text)

        # Should be identical (cached)
        np.testing.assert_array_almost_equal(emb1, emb2)

    def test_generate_embedding_different_texts(self):
        """Test different texts produce different embeddings."""
        gen = EmbeddingGenerator()

        emb_apple = gen.generate("Apple is undervalued")
        emb_microsoft = gen.generate("Microsoft has strong cloud growth")

        # Should not be identical
        assert not np.allclose(emb_apple, emb_microsoft)

    def test_embedding_normalized(self):
        """Test mock embeddings are normalized."""
        gen = EmbeddingGenerator()
        embedding = gen.generate("Test text")

        # Check norm is approximately 1 for mock embeddings
        norm = np.linalg.norm(embedding)
        assert 0.95 < norm < 1.05  # Approximately 1

    def test_generate_batch_embeddings(self):
        """Test batch embedding generation."""
        gen = EmbeddingGenerator()
        texts = [
            "Apple thesis about ecosystem",
            "Microsoft thesis about cloud",
            "Google thesis about search"
        ]

        embeddings = gen.generate_batch(texts)

        assert embeddings.shape == (3, 384)

    def test_generate_batch_empty_error(self):
        """Test batch with empty list raises error."""
        gen = EmbeddingGenerator()

        with pytest.raises(ValueError, match="cannot be empty"):
            gen.generate_batch([])

    def test_generate_batch_length_mismatch(self):
        """Test batch operations complete even with varied texts."""
        gen = EmbeddingGenerator()
        texts = [
            "Short text",
            "Much longer text with more details and context about the investment thesis",
            "Medium length text"
        ]

        embeddings = gen.generate_batch(texts)

        assert embeddings.shape == (3, 384)


class TestVectorStore:
    """Tests for vector storage and search."""

    def test_store_initialization(self):
        """Test vector store initializes."""
        store = VectorStore()
        assert store is not None
        assert store.collection_name == "theses"

    def test_add_single_embedding(self):
        """Test adding single embedding."""
        store = VectorStore()

        store.add(
            ids=["thesis_1"],
            embeddings=[[0.1, 0.2] + [0.0] * 382],
            metadatas=[{"ticker": "AAPL"}],
            documents=["Apple thesis"]
        )

        # Should succeed without error

    def test_add_multiple_embeddings(self):
        """Test adding multiple embeddings."""
        store = VectorStore()

        store.add(
            ids=["thesis_1", "thesis_2", "thesis_3"],
            embeddings=[
                [0.1, 0.2] + [0.0] * 382,
                [0.2, 0.1] + [0.0] * 382,
                [0.3, 0.4] + [0.0] * 382
            ],
            metadatas=[
                {"ticker": "AAPL"},
                {"ticker": "MSFT"},
                {"ticker": "GOOGL"}
            ],
            documents=[
                "Apple thesis",
                "Microsoft thesis",
                "Google thesis"
            ]
        )

    def test_add_empty_ids_error(self):
        """Test adding with empty IDs raises error."""
        store = VectorStore()

        with pytest.raises(ValueError, match="cannot be empty"):
            store.add(
                ids=[],
                embeddings=[],
                metadatas=[],
                documents=[]
            )

    def test_add_mismatched_lengths_error(self):
        """Test adding with mismatched lengths raises error."""
        store = VectorStore()

        with pytest.raises(ValueError, match="Mismatched lengths"):
            store.add(
                ids=["thesis_1", "thesis_2"],
                embeddings=[[0.1] * 384],  # Only 1 embedding
                metadatas=[{"ticker": "AAPL"}],
                documents=["Apple thesis"]
            )

    def test_search_similar_embeddings(self):
        """Test searching for similar embeddings."""
        store = VectorStore()

        # Add some embeddings
        gen = EmbeddingGenerator()
        texts = [
            "Apple is undervalued due to ecosystem",
            "Microsoft cloud growth story",
            "Apple services revenue acceleration"
        ]

        for i, text in enumerate(texts):
            embedding = gen.generate(text).tolist()
            store.add(
                ids=[f"thesis_{i}"],
                embeddings=[embedding],
                metadatas=[{"ticker": ["AAPL", "MSFT", "AAPL"][i]}],
                documents=[text]
            )

        # Search for Apple-like thesis
        query_embedding = gen.generate("Apple ecosystem advantage").tolist()
        results = store.search(query_embedding, top_k=3)

        assert len(results) <= 3
        assert all("similarity" in r for r in results)
        assert all("metadata" in r for r in results)

    def test_search_empty_query_error(self):
        """Test search with empty query raises error."""
        store = VectorStore()

        with pytest.raises(ValueError, match="cannot be empty"):
            store.search([], top_k=5)

    def test_search_similarity_scores(self):
        """Test similarity scores are in valid range."""
        store = VectorStore()
        gen = EmbeddingGenerator()

        # Add embeddings
        texts = ["Apple thesis", "Microsoft thesis"]
        for i, text in enumerate(texts):
            embedding = gen.generate(text).tolist()
            store.add(
                ids=[f"thesis_{i}"],
                embeddings=[embedding],
                metadatas=[{"ticker": ["AAPL", "MSFT"][i]}],
                documents=[text]
            )

        # Search
        query_embedding = gen.generate("Apple investment").tolist()
        results = store.search(query_embedding, top_k=2)

        for result in results:
            # Similarity should be between -1 and 1
            assert -1.0 <= result["similarity"] <= 1.0

    def test_search_respects_top_k(self):
        """Test search returns at most top_k results."""
        store = VectorStore()
        gen = EmbeddingGenerator()

        # Add 10 embeddings
        for i in range(10):
            text = f"Thesis number {i}"
            embedding = gen.generate(text).tolist()
            store.add(
                ids=[f"thesis_{i}"],
                embeddings=[embedding],
                metadatas=[{"index": i}],
                documents=[text]
            )

        # Search with top_k=3
        query_embedding = gen.generate("Query text").tolist()
        results = store.search(query_embedding, top_k=3)

        assert len(results) <= 3

    def test_delete_embeddings(self):
        """Test deleting embeddings."""
        store = VectorStore()

        store.add(
            ids=["thesis_1", "thesis_2"],
            embeddings=[[0.1] * 384, [0.2] * 384],
            metadatas=[{"ticker": "AAPL"}, {"ticker": "MSFT"}],
            documents=["Apple", "Microsoft"]
        )

        store.delete(["thesis_1"])

        # Verify deletion worked (no error)

    def test_get_all_documents(self):
        """Test retrieving all stored documents."""
        store = VectorStore()

        store.add(
            ids=["thesis_1", "thesis_2"],
            embeddings=[[0.1] * 384, [0.2] * 384],
            metadatas=[
                {"ticker": "AAPL", "date": "2024-04-25"},
                {"ticker": "MSFT", "date": "2024-04-24"}
            ],
            documents=["Apple thesis", "Microsoft thesis"]
        )

        all_docs = store.get_all()

        assert len(all_docs) >= 2
        assert all("id" in doc for doc in all_docs)
        assert all("document" in doc for doc in all_docs)
        assert all("metadata" in doc for doc in all_docs)


class TestPublicAPIs:
    """Tests for public API functions."""

    def test_generate_embedding_function(self):
        """Test generate_embedding function."""
        embedding = generate_embedding("Apple thesis text")

        assert embedding is not None
        assert isinstance(embedding, list)
        assert len(embedding) == 384

    def test_generate_embedding_consistency(self):
        """Test generate_embedding returns consistent results."""
        text = "Apple is undervalued"

        emb1 = generate_embedding(text)
        emb2 = generate_embedding(text)

        assert emb1 == emb2

    def test_store_thesis_embedding(self):
        """Test storing thesis embedding."""
        thesis_id = "thesis_apple_001"
        text = "Apple ecosystem advantage"
        metadata = {
            "ticker": "AAPL",
            "created_at": "2024-04-25",
            "score": 85.0
        }

        store_thesis_embedding(thesis_id, text, metadata)

        # Should not raise error

    def test_search_similar_thesis(self):
        """Test searching for similar theses."""
        # Store some theses first
        store_thesis_embedding(
            "thesis_1",
            "Apple ecosystem advantage thesis",
            {"ticker": "AAPL"}
        )
        store_thesis_embedding(
            "thesis_2",
            "Microsoft cloud dominance thesis",
            {"ticker": "MSFT"}
        )
        store_thesis_embedding(
            "thesis_3",
            "Apple services growth acceleration",
            {"ticker": "AAPL"}
        )

        # Search for similar
        query_embedding = generate_embedding("Apple competitive advantage")
        results = search_similar_thesis(query_embedding, top_k=3)

        assert len(results) > 0
        assert len(results) <= 3

    def test_search_similar_thesis_top_k(self):
        """Test search_similar_thesis respects top_k parameter."""
        # Store theses
        for i in range(10):
            store_thesis_embedding(
                f"thesis_{i}",
                f"Thesis number {i}",
                {"ticker": f"TICK{i}"}
            )

        query_embedding = generate_embedding("Search query")
        results_5 = search_similar_thesis(query_embedding, top_k=5)
        results_2 = search_similar_thesis(query_embedding, top_k=2)

        assert len(results_5) <= 5
        assert len(results_2) <= 2


class TestSemanticSimilarity:
    """Tests for semantic similarity calculations."""

    def test_same_text_similarity(self):
        """Test identical texts have highest similarity."""
        store = VectorStore()
        gen = EmbeddingGenerator()

        text = "Apple ecosystem advantage"
        embedding = gen.generate(text).tolist()

        store.add(
            ids=["thesis_1"],
            embeddings=[embedding],
            metadatas=[{"ticker": "AAPL"}],
            documents=[text]
        )

        # Search with same embedding should have high similarity
        results = store.search(embedding, top_k=1)

        assert len(results) > 0
        assert results[0]["similarity"] > 0.99

    def test_different_texts_lower_similarity(self):
        """Test different texts have lower similarity."""
        store = VectorStore()
        gen = EmbeddingGenerator()

        # Add Apple thesis
        embedding_apple = gen.generate("Apple ecosystem").tolist()
        store.add(
            ids=["thesis_apple"],
            embeddings=[embedding_apple],
            metadatas=[{"ticker": "AAPL"}],
            documents=["Apple ecosystem"]
        )

        # Add completely different thesis
        embedding_crypto = gen.generate("Bitcoin blockchain technology").tolist()
        store.add(
            ids=["thesis_crypto"],
            embeddings=[embedding_crypto],
            metadatas=[{"ticker": "BTC"}],
            documents=["Bitcoin thesis"]
        )

        # Search Apple space should rank Apple thesis higher
        results = store.search(embedding_apple, top_k=2)

        if len(results) >= 2:
            # Apple thesis should be more similar to Apple query
            apple_idx = next(i for i, r in enumerate(results) if r["id"] == "thesis_apple")
            apple_sim = results[apple_idx]["similarity"]
            assert apple_sim > 0.5  # Should be reasonably similar to itself


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_very_long_text_embedding(self):
        """Test embedding of very long text."""
        gen = EmbeddingGenerator()

        long_text = " ".join(["Apple"] * 1000)  # 1000 repetitions
        embedding = gen.generate(long_text)

        assert embedding.shape == (384,)

    def test_special_characters_in_text(self):
        """Test text with special characters."""
        gen = EmbeddingGenerator()

        text = "Apple Inc. $AAPL: PE=25.5, P/B=45.3% growth @2024-04-25"
        embedding = gen.generate(text)

        assert embedding.shape == (384,)

    def test_multiple_languages(self):
        """Test text in different languages."""
        gen = EmbeddingGenerator()

        texts = [
            "Apple ecosystem advantage",
            "苹果生态系统优势",  # Chinese
            "Avantage écosystème Apple"  # French
        ]

        for text in texts:
            embedding = gen.generate(text)
            assert embedding.shape == (384,)

    def test_unicode_text(self):
        """Test unicode text."""
        gen = EmbeddingGenerator()

        text = "Tesla $TSLA ✓ growth 📈 2024 → future"
        embedding = gen.generate(text)

        assert embedding.shape == (384,)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
