"""Precedent management module for EJE."""

from .embeddings import embed_text, load_model
from .retrieval import retrieve_similar_precedents, load_precedents, cosine_similarity
from .store import store_precedent_case

__all__ = [
    'embed_text',
    'load_model',
    'retrieve_similar_precedents',
    'load_precedents',
    'cosine_similarity',
    'store_precedent_case'
]
