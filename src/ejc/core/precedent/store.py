# src/ejc/core/precedent/store.py

import json
import os
import re
from typing import Any, Dict

from .embeddings import embed_text
from ...utils.logging import get_logger
from ..error_handling import ConfigurationException, PrecedentException

logger = get_logger("ejc.precedent.store")


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

    Args:
        decision: Decision object to store
        config: Precedent configuration including store path and embedding model

    Raises:
        ConfigurationException: If configuration is missing required keys
        PrecedentException: If storage operation fails
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
