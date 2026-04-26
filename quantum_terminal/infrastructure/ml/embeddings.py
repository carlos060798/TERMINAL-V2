"""
Embedding Generation and Semantic Search for Investment Theses.

Uses sentence-transformers for generating semantic embeddings and ChromaDB
for vector storage and similarity search.

Features:
- Generate embeddings from thesis text
- Store embeddings in ChromaDB
- Semantic search across thesis corpus
- Batch embedding generation

Phase 2 - Infrastructure Layer Implementation
Reference: PLAN_MAESTRO.md - Phase 2: ML Adapters
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np

from quantum_terminal.utils.logger import get_logger
from quantum_terminal.utils.cache import cache

logger = get_logger(__name__)

# TODO: Replace with actual sentence-transformers imports when available
# from sentence_transformers import SentenceTransformer
# import chromadb


class EmbeddingGenerator:
    """Generate semantic embeddings for thesis text."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding generator.

        Args:
            model_name: HuggingFace model identifier
        """
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        """Load sentence-transformer model."""
        try:
            # TODO: Uncomment when sentence-transformers is available
            # from sentence_transformers import SentenceTransformer
            # self.model = SentenceTransformer(self.model_name)
            # logger.info(f"Loaded embedding model: {self.model_name}")

            logger.warning(
                "sentence-transformers not available, using mock embeddings. "
                "Install: pip install sentence-transformers"
            )
        except ImportError:
            logger.warning(
                "sentence-transformers import failed, using mock embeddings"
            )

    def generate(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.

        Args:
            text: Input text

        Returns:
            Embedding vector (384-dimensional)

        Examples:
            >>> generator = EmbeddingGenerator()
            >>> embedding = generator.generate("Apple thesis text")
            >>> print(embedding.shape)
            (384,)
        """
        if not text or len(text.strip()) == 0:
            raise ValueError("Text cannot be empty")

        try:
            # Check cache first
            cache_key = f"embedding_{hash(text)}"
            cached = cache.get(cache_key)
            if cached is not None:
                return np.array(cached)

            if self.model is not None:
                # Real embedding
                embedding = self.model.encode(text, convert_to_numpy=True)
            else:
                # Mock embedding (384-dimensional)
                embedding = self._generate_mock_embedding(text)

            # Cache result
            cache.set(cache_key, embedding.tolist(), ttl_minutes=1440)  # 24h

            logger.debug(f"Generated embedding for text ({len(text)} chars)")
            return embedding

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}", exc_info=True)
            raise

    def generate_batch(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts

        Returns:
            Array of embeddings (N x 384)

        Examples:
            >>> generator = EmbeddingGenerator()
            >>> embeddings = generator.generate_batch([
            ...     "Apple thesis",
            ...     "Microsoft thesis"
            ... ])
            >>> print(embeddings.shape)
            (2, 384)
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        try:
            if self.model is not None:
                embeddings = self.model.encode(texts, convert_to_numpy=True)
            else:
                embeddings = np.array([
                    self._generate_mock_embedding(text) for text in texts
                ])

            logger.debug(f"Generated {len(texts)} embeddings")
            return embeddings

        except Exception as e:
            logger.error(f"Batch embedding failed: {e}", exc_info=True)
            raise

    @staticmethod
    def _generate_mock_embedding(text: str, dim: int = 384) -> np.ndarray:
        """
        Generate deterministic mock embedding from text.

        Args:
            text: Input text
            dim: Embedding dimension

        Returns:
            Mock embedding vector
        """
        # Use text hash for deterministic but varied embeddings
        hash_val = hash(text)
        np.random.seed(abs(hash_val) % (2**31))
        embedding = np.random.randn(dim).astype(np.float32)
        # Normalize
        embedding = embedding / np.linalg.norm(embedding)
        return embedding


class VectorStore:
    """Store and retrieve embeddings using ChromaDB."""

    def __init__(self, collection_name: str = "theses"):
        """
        Initialize vector store.

        Args:
            collection_name: ChromaDB collection name
        """
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._load_chromadb()

    def _load_chromadb(self) -> None:
        """Load ChromaDB client."""
        try:
            # TODO: Uncomment when chromadb is available
            # import chromadb
            # self.client = chromadb.Client()
            # self.collection = self.client.get_or_create_collection(
            #     name=self.collection_name,
            #     metadata={"hnsw:space": "cosine"}
            # )
            # logger.info(f"Loaded ChromaDB collection: {self.collection_name}")

            logger.warning(
                "ChromaDB not available, using in-memory storage. "
                "Install: pip install chromadb"
            )
            self.in_memory_store: Dict[str, Dict] = {}

        except ImportError:
            logger.warning("ChromaDB import failed, using in-memory storage")
            self.in_memory_store = {}

    def add(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict],
        documents: List[str]
    ) -> None:
        """
        Add embeddings to store.

        Args:
            ids: Document IDs
            embeddings: Embedding vectors
            metadatas: Metadata for each document
            documents: Original text documents

        Examples:
            >>> store = VectorStore()
            >>> store.add(
            ...     ids=["thesis_1"],
            ...     embeddings=[[0.1, 0.2, ...]],
            ...     metadatas=[{"ticker": "AAPL"}],
            ...     documents=["Apple thesis"]
            ... )
        """
        if not ids or not embeddings or not documents:
            raise ValueError("IDs, embeddings, and documents cannot be empty")

        if len(ids) != len(embeddings) or len(ids) != len(documents):
            raise ValueError("Mismatched lengths of ids, embeddings, documents")

        try:
            if self.collection is not None:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents
                )
            else:
                # In-memory storage
                for idx, doc_id in enumerate(ids):
                    self.in_memory_store[doc_id] = {
                        "embedding": embeddings[idx],
                        "metadata": metadatas[idx] if idx < len(metadatas) else {},
                        "document": documents[idx]
                    }

            logger.debug(f"Added {len(ids)} embeddings to store")

        except Exception as e:
            logger.error(f"Failed to add embeddings: {e}", exc_info=True)
            raise

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict]:
        """
        Search for similar embeddings.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return

        Returns:
            List of similar documents with scores

        Examples:
            >>> store = VectorStore()
            >>> results = store.search([0.1, 0.2, ...], top_k=5)
            >>> for result in results:
            ...     print(result["ticker"], result["similarity"])
        """
        if not query_embedding:
            raise ValueError("Query embedding cannot be empty")

        try:
            if self.collection is not None:
                # ChromaDB search
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    include=["embeddings", "metadatas", "documents", "distances"]
                )

                # Format results
                similar = []
                for i in range(len(results["ids"][0])):
                    similar.append({
                        "id": results["ids"][0][i],
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "similarity": 1 - results["distances"][0][i]  # Convert distance to similarity
                    })

                return similar

            else:
                # In-memory search using cosine similarity
                similar = []

                for doc_id, doc_data in self.in_memory_store.items():
                    stored_embedding = np.array(doc_data["embedding"])
                    query_vec = np.array(query_embedding)

                    # Normalize
                    stored_embedding = stored_embedding / np.linalg.norm(stored_embedding)
                    query_vec = query_vec / np.linalg.norm(query_vec)

                    # Cosine similarity
                    similarity = float(np.dot(stored_embedding, query_vec))

                    similar.append({
                        "id": doc_id,
                        "document": doc_data["document"],
                        "metadata": doc_data["metadata"],
                        "similarity": similarity
                    })

                # Sort by similarity and return top_k
                similar.sort(key=lambda x: x["similarity"], reverse=True)
                return similar[:top_k]

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            raise

    def delete(self, ids: List[str]) -> None:
        """
        Delete embeddings by ID.

        Args:
            ids: Document IDs to delete
        """
        try:
            if self.collection is not None:
                self.collection.delete(ids=ids)
            else:
                for doc_id in ids:
                    self.in_memory_store.pop(doc_id, None)

            logger.debug(f"Deleted {len(ids)} embeddings")

        except Exception as e:
            logger.error(f"Delete failed: {e}", exc_info=True)
            raise

    def get_all(self) -> List[Dict]:
        """
        Get all stored documents.

        Returns:
            List of all documents with metadata
        """
        try:
            if self.collection is not None:
                # Get all from ChromaDB
                all_docs = self.collection.get()
                results = []
                for i in range(len(all_docs["ids"])):
                    results.append({
                        "id": all_docs["ids"][i],
                        "document": all_docs["documents"][i],
                        "metadata": all_docs["metadatas"][i]
                    })
                return results
            else:
                return [
                    {
                        "id": doc_id,
                        "document": doc_data["document"],
                        "metadata": doc_data["metadata"]
                    }
                    for doc_id, doc_data in self.in_memory_store.items()
                ]

        except Exception as e:
            logger.error(f"Get all failed: {e}", exc_info=True)
            raise


# ============================================================================
# Public API Functions
# ============================================================================

_embedding_generator: Optional[EmbeddingGenerator] = None
_vector_store: Optional[VectorStore] = None


def get_embedding_generator() -> EmbeddingGenerator:
    """Get or create global embedding generator."""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator


def get_vector_store() -> VectorStore:
    """Get or create global vector store."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for text.

    Args:
        text: Input text

    Returns:
        Embedding vector

    Examples:
        >>> embedding = generate_embedding("Apple thesis")
        >>> print(len(embedding))
        384
    """
    generator = get_embedding_generator()
    embedding = generator.generate(text)
    return embedding.tolist()


def search_similar_thesis(
    query_embedding: List[float],
    top_k: int = 5
) -> List[Dict]:
    """
    Search for similar theses.

    Args:
        query_embedding: Query embedding vector
        top_k: Number of results

    Returns:
        List of similar theses

    Examples:
        >>> results = search_similar_thesis(embedding, top_k=5)
        >>> for thesis in results:
        ...     print(thesis["metadata"]["ticker"])
    """
    store = get_vector_store()
    return store.search(query_embedding, top_k)


def store_thesis_embedding(
    thesis_id: str,
    text: str,
    metadata: Dict
) -> None:
    """
    Store thesis embedding.

    Args:
        thesis_id: Unique thesis ID
        text: Thesis text
        metadata: Thesis metadata (ticker, date, etc.)

    Examples:
        >>> store_thesis_embedding(
        ...     "thesis_1",
        ...     "Apple ecosystem thesis",
        ...     {"ticker": "AAPL", "date": "2024-04-25"}
        ... )
    """
    generator = get_embedding_generator()
    store = get_vector_store()

    embedding = generator.generate(text)

    store.add(
        ids=[thesis_id],
        embeddings=[embedding.tolist()],
        metadatas=[metadata],
        documents=[text]
    )

    logger.info(f"Stored thesis embedding: {thesis_id}")
