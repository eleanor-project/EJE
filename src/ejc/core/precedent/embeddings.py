# src/ejc/core/precedent/embeddings.py

import numpy as np
from typing import Any
from sentence_transformers import SentenceTransformer

_model_cache = {}


def load_model(model_name: str) -> SentenceTransformer:
    """
    Load and cache a sentence transformer model.

    Args:
        model_name: Name of the sentence-transformers model to load

    Returns:
        Loaded SentenceTransformer model
    """
    if model_name not in _model_cache:
        _model_cache[model_name] = SentenceTransformer(model_name)
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
