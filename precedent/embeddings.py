# precedent/embeddings.py

from typing import Any
from sentence_transformers import SentenceTransformer
import numpy as np

_model_cache = {}

def load_model(model_name: str):
    if model_name not in _model_cache:
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]


def embed_text(text: str, model_name: str) -> Any:
    model = load_model(model_name)
    vec = model.encode([text], convert_to_numpy=True)
    return vec[0]
