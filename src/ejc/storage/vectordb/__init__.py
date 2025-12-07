"""
VectorDB storage layer for precedent embeddings.

Provides abstract interface and multiple backend implementations
for storing and querying vector embeddings.
"""

from .base import VectorStore, SearchResult, EmbeddingMetadata
from .factory import init_vectordb, get_vectordb_backend, create_collection_if_not_exists
from .sync import EmbeddingSync, search_similar_precedents

__all__ = [
    "VectorStore",
    "SearchResult",
    "EmbeddingMetadata",
    "init_vectordb",
    "get_vectordb_backend",
    "create_collection_if_not_exists",
    "EmbeddingSync",
    "search_similar_precedents",
]
