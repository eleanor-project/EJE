# src/ejc/core/precedent/embeddings.py

import hashlib
import os
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

_model_cache = {}


def _hashing_encoder(dimension: int = 384):
    """Create a deterministic hashing-based encoder for offline use."""

    class _HashingModel:
        def __init__(self, text_dim: int = 256, context_dim: int = 128):
            self.text_vectorizer = HashingVectorizer(
                n_features=text_dim,
                alternate_sign=False,
                norm=None,
                ngram_range=(1, 1),
                lowercase=True,
            )
            self.context_vectorizer = HashingVectorizer(
                n_features=context_dim,
                alternate_sign=False,
                norm=None,
                ngram_range=(1, 1),
                lowercase=True,
            )

        def encode(self, texts, convert_to_numpy=True):
            if isinstance(texts, str):
                texts = [texts]

            embeddings = []
            for text in texts:
                if text is None:
                    text = ""

                text_part = text
                context_part = ""
                if "CONTEXT:" in text:
                    text_part, context_part = text.split("CONTEXT:", 1)
                elif "context" in text:
                    context_part = text

                text_vec = self.text_vectorizer.transform([text_part]).toarray()[0]
                context_vec = self.context_vectorizer.transform([context_part]).toarray()[0] * 3

                combined = np.concatenate([text_vec, context_vec])
                norm = np.linalg.norm(combined)
                embeddings.append(combined / norm if norm else combined)

            return np.array(embeddings)

    return _HashingModel()


def load_model(model_name: str) -> Any:
    """
    Load and cache an embedding model with an offline-friendly default.

    Args:
        model_name: Name of the sentence-transformers model to load

    Returns:
        Loaded embedding model implementing ``encode``
    """
    if model_name not in _model_cache:
        model: Any = _hashing_encoder()

        if os.environ.get("EJC_ENABLE_SENTENCE_TRANSFORMER") == "1":
            try:
                from sentence_transformers import SentenceTransformer

                model = SentenceTransformer(model_name, local_files_only=True)
            except Exception:
                # Keep hashing encoder fallback
                model = _hashing_encoder()

        _model_cache[model_name] = model

    return _model_cache[model_name]


def embed_text(text: str, model_name: str) -> np.ndarray:
    """
    Generate embedding vector for text.

    Args:
        text: Text to embed
        model_name: Name of the sentence-transformers model to use

    Returns:
        numpy array containing the embedding vector
    """
    model = load_model(model_name)
    vec = model.encode([text], convert_to_numpy=True)
    return vec[0]
