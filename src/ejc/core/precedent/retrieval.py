# src/ejc/core/precedent/retrieval.py

import json
import os
import numpy as np
from typing import Dict, Any, List

from .embeddings import embed_text
from ...utils.logging import get_logger

logger = get_logger("ejc.precedent.retrieval")


def load_precedents(store_path: str) -> List[Dict[str, Any]]:
    """
    Load all precedent cases from the store directory.

    Args:
        store_path: Path to precedent storage directory

    Returns:
        List of precedent dictionaries
    """
    precedents = []
    if not os.path.exists(store_path):
        logger.warning(f"Precedent store path does not exist: {store_path}")
        return precedents

    for filename in os.listdir(store_path):
        if filename.endswith(".jsonl"):
            filepath = os.path.join(store_path, filename)
            try:
                with open(filepath, "r") as f:
                    for line in f:
                        precedents.append(json.loads(line))
            except Exception as e:
                logger.error(f"Failed to load precedent from {filename}: {str(e)}")

    return precedents


def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        vec_a: First vector
        vec_b: Second vector

    Returns:
        Cosine similarity score (0.0 to 1.0)
    """
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def retrieve_similar_precedents(
    input_data: Dict[str, Any],
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Retrieves similar precedent cases based on embedding similarity.

    Args:
        input_data: Input case data
        config: Precedent configuration including store path and embedding model

    Returns:
        List of precedents sorted by similarity (highest first)
    """
    if not config.get("enabled", True):
        logger.info("Precedent retrieval disabled in config")
        return []

    store_path = config["store"]["path"]
    precedents = load_precedents(store_path)

    if not precedents:
        logger.info("No precedents found in store")
        return []

    # Generate query embedding
    query_text = json.dumps(input_data, sort_keys=True)
    query_vec = embed_text(query_text, config["embedding_model"])

    # Score all precedents
    scored = []
    for prec in precedents:
        try:
            prec_vec = np.array(prec.get("embedding"))
            score = cosine_similarity(query_vec, prec_vec)
            prec["similarity"] = score
            scored.append(prec)
        except Exception as e:
            logger.error(f"Failed to score precedent {prec.get('id')}: {str(e)}")

    # Sort by similarity (highest first)
    scored.sort(key=lambda x: x["similarity"], reverse=True)

    logger.info(f"Retrieved {len(scored)} precedents, top similarity: {scored[0]['similarity'] if scored else 'N/A'}")

    return scored
