# src/ejc/core/precedent/store.py

import json
import os
import re
from typing import Any, Dict

from .embeddings import embed_text
from .vector_manager import VectorPrecedentManager
from ...utils.logging import get_logger
from ..error_handling import ConfigurationException, PrecedentException

logger = get_logger("ejc.precedent.store")

# Global vector manager instance
_vector_manager = None


def _get_vector_manager(config: Dict[str, Any]) -> VectorPrecedentManager:
    """Get or create the global VectorPrecedentManager instance."""
    global _vector_manager

    if _vector_manager is None:
        logger.info("Initializing VectorPrecedentManager for storage")
        _vector_manager = VectorPrecedentManager(config)

    return _vector_manager


def sanitize_id(decision_id: str) -> str:
    """
    Sanitize decision ID to prevent path traversal attacks.

    Args:
        decision_id: Raw decision ID

    Returns:
        Sanitized decision ID safe for use in filenames
    """
    return re.sub(r'[^a-zA-Z0-9_-]', '', decision_id)


def store_precedent_case(decision: Any, config: Dict[str, Any]) -> None:
    """
    Stores the final decision as a precedent case.

    Supports two backends:
    - "vector": Uses Qdrant vector database (production-grade)
    - "file": Uses legacy JSONL file storage (fallback)

    Args:
        decision: Decision object to store
        config: Precedent configuration including backend, store path, and embedding model

    Raises:
        ConfigurationException: If configuration is missing required keys
        PrecedentException: If storage operation fails
    """
    # Determine backend (default to "file" for backwards compatibility)
    backend = config.get("backend", "file")

    if backend == "vector":
        # Use VectorPrecedentManager (Qdrant)
        logger.debug("Using vector backend for precedent storage")
        _store_with_vector_db(decision, config)
    else:
        # Use legacy file-based storage
        logger.debug("Using file backend for precedent storage")
        _store_with_file_storage(decision, config)


def _store_with_vector_db(decision: Any, config: Dict[str, Any]) -> None:
    """
    Store precedent using Qdrant vector database.

    Args:
        decision: Decision object to store
        config: Precedent configuration

    Raises:
        PrecedentException: If storage fails
    """
    try:
        manager = _get_vector_manager(config)

        # Store precedent in vector DB
        point_id = manager.store_precedent(
            decision_id=decision.decision_id,
            input_data=decision.input_data,
            outcome=decision.governance_outcome,
            timestamp=decision.timestamp
        )

        logger.info(f"Stored precedent {decision.decision_id} in vector DB (point: {point_id})")

    except Exception as e:
        logger.error(f"Vector DB storage failed: {str(e)}, falling back to file storage")
        # Fallback to file storage
        _store_with_file_storage(decision, config)


def _store_with_file_storage(decision: Any, config: Dict[str, Any]) -> None:
    """
    Store precedent using legacy file storage (JSONL).

    Args:
        decision: Decision object to store
        config: Precedent configuration

    Raises:
        ConfigurationException: If configuration is invalid
        PrecedentException: If storage fails
    """
    try:
        # Validate configuration
        if "store" not in config or "path" not in config["store"]:
            raise ConfigurationException("Missing precedent store path in config")

        if "embedding_model" not in config:
            raise ConfigurationException("Missing embedding_model in precedent config")

        path = config["store"]["path"]
        os.makedirs(path, exist_ok=True)

        # Sanitize decision ID to prevent path traversal
        safe_id = sanitize_id(decision.decision_id)

        # Build precedent structure
        prec = {
            "id": decision.decision_id,
            "input_data": decision.input_data,
            "outcome": decision.governance_outcome,
            "timestamp": decision.timestamp,
            "embedding": embed_text(
                json.dumps(decision.input_data, sort_keys=True),
                config["embedding_model"]
            ).tolist(),
        }

        filename = os.path.join(path, f"{safe_id}.jsonl")

        # Write to file
        with open(filename, "a") as f:
            f.write(json.dumps(prec) + "\n")

        logger.info(f"Stored precedent case {decision.decision_id} to {filename}")

    except (KeyError, AttributeError) as e:
        raise ConfigurationException(f"Invalid precedent configuration or decision object: {str(e)}")
    except IOError as e:
        raise PrecedentException(f"Failed to store precedent: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error storing precedent: {str(e)}")
        raise PrecedentException(f"Precedent storage failed: {str(e)}")
