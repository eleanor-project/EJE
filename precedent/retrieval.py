# precedent/retrieval.py

import json
import os
import numpy as np
from typing import Dict, Any, List, Optional

from precedent.embeddings import embed_text
from utils.logging import logger


def load_precedents(store_path: str) -> List[Dict[str, Any]]:
    precedents = []
    if not os.path.exists(store_path):
        return precedents

    for filename in os.listdir(store_path):
        if filename.endswith(".jsonl"):
            with open(os.path.join(store_path, filename), "r") as f:
                for line in f:
                    precedents.append(json.loads(line))
    return precedents


def cosine_similarity(vec_a, vec_b) -> float:
    if np.linalg.norm(vec_a) == 0 or np.linalg.norm(vec_b) == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b)))


def retrieve_similar_precedents(
    input_data: Dict[str, Any],
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Retrieves similar precedent cases based on embedding similarity.
    Returns list of precedents sorted by similarity.
    """

    if not config.get("enabled", True):
        return []

    store_path = config["store"]["path"]
    precedents = load_precedents(store_path)
    if not precedents:
        return []

    query_text = json.dumps(input_data, sort_keys=True)
    query_vec = embed_text(query_text, config["embedding_model"])

    scored = []
    for prec in precedents:
        prec_vec = np.array(prec.get("embedding"))
        score = cosine_similarity(query_vec, prec_vec)
        prec["similarity"] = score
        scored.append(prec)

    # Highest similarity first
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored
