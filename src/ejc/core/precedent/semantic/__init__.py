"""
Semantic Precedent Search System

Provides vector embedding-based precedent retrieval for semantic similarity
matching beyond exact hash-based lookup.

Components:
- VectorPrecedentStore: Vector database for embeddings
- HybridSearch: Combined hash + semantic search
- PrivacyBundling: K-anonymity and differential privacy
- SimilarPrecedent: Result container with similarity scores
"""

from .vector_store import VectorPrecedentStore, SimilarPrecedent
from .hybrid_search import HybridPrecedentSearch
from .privacy import PrivacyPreservingPrecedents, AnonymousBundle

__all__ = [
    "VectorPrecedentStore",
    "SimilarPrecedent",
    "HybridPrecedentSearch",
    "PrivacyPreservingPrecedents",
    "AnonymousBundle",
]
