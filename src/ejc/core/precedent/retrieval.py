# src/ejc/core/precedent/retrieval.py

import json
import os
import numpy as np
from typing import Dict, Any, List

from .embeddings import embed_text
from .vector_manager import VectorPrecedentManager
from ...utils.logging import get_logger

logger = get_logger("ejc.precedent.retrieval")

# Global vector manager instance (initialized on first use)
_vector_manager = None


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


def _get_vector_manager(config: Dict[str, Any]) -> VectorPrecedentManager:
    """
    Get or create the global VectorPrecedentManager instance.

    Args:
        config: Precedent configuration

    Returns:
        VectorPrecedentManager instance
    """
    global _vector_manager

    if _vector_manager is None:
        logger.info("Initializing VectorPrecedentManager")
        _vector_manager = VectorPrecedentManager(config)

    return _vector_manager


def retrieve_similar_precedents(
    input_data: Dict[str, Any],
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Retrieves similar precedent cases based on embedding similarity.

    Supports two backends:
    - "vector": Uses Qdrant vector database (production-grade)
    - "file": Uses legacy JSONL file storage (fallback)

    Args:
        input_data: Input case data
        config: Precedent configuration including backend, store path, and embedding model

    Returns:
        List of precedents sorted by similarity (highest first)
    """
    if not config.get("enabled", True):
        logger.info("Precedent retrieval disabled in config")
        return []

    # Determine backend (default to "file" for backwards compatibility)
    backend = config.get("backend", "file")

    if backend == "vector":
        # Use VectorPrecedentManager (Qdrant)
        logger.debug("Using vector backend for precedent retrieval")
        return _retrieve_with_vector_db(input_data, config)
    else:
        # Use legacy file-based retrieval
        logger.debug("Using file backend for precedent retrieval")
        return _retrieve_with_file_storage(input_data, config)


def _retrieve_with_vector_db(
    input_data: Dict[str, Any],
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Retrieve precedents using Qdrant vector database.

    Args:
        input_data: Input case data
        config: Precedent configuration

    Returns:
        List of precedents sorted by similarity
    """
    try:
        manager = _get_vector_manager(config)

        # Get search parameters
        limit = config.get("limit", 10)
        min_similarity = config.get("min_similarity", 0.0)

        # Search for similar precedents
        precedents = manager.search_similar(
            query_data=input_data,
            limit=limit,
            min_similarity=min_similarity
        )

        logger.info(f"Retrieved {len(precedents)} precedents from vector DB")
        return precedents

    except Exception as e:
        logger.error(f"Vector DB retrieval failed: {str(e)}, falling back to file storage")
        # Fallback to file storage
        return _retrieve_with_file_storage(input_data, config)


def _retrieve_with_file_storage(
    input_data: Dict[str, Any],
    config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Retrieve precedents using legacy file storage (JSONL).

    Args:
        input_data: Input case data
        config: Precedent configuration

    Returns:
        List of precedents sorted by similarity
    """
    store_path = config.get("store", {}).get("path", "data/precedents/")
    precedents = load_precedents(store_path)

    if not precedents:
        logger.info("No precedents found in file storage")
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

    logger.info(f"Retrieved {len(scored)} precedents from file storage")

    return scored
