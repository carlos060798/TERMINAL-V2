"""
Machine Learning Infrastructure Module.

Provides embeddings, vector search (RAG), and ML model integrations.

Modules:
- embeddings: Semantic embeddings and vector search using sentence-transformers + ChromaDB
- lightgbm_scorer: Thesis scoring model (LightGBM trained on historical data)
- prophet_forecasting: Price forecasting using Facebook Prophet
- lstm_signals: LSTM-based signal generation

Phase 2 - Infrastructure Layer
Reference: PLAN_MAESTRO.md - Phase 2: ML Adapters
"""

from quantum_terminal.infrastructure.ml.embeddings import (
    generate_embedding,
    search_similar_thesis,
    store_thesis_embedding,
    EmbeddingGenerator,
    VectorStore
)

__all__ = [
    "generate_embedding",
    "search_similar_thesis",
    "store_thesis_embedding",
    "EmbeddingGenerator",
    "VectorStore"
]
