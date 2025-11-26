# precedent/store.py

import json
import os
from typing import Any, Dict

from precedent.embeddings import embed_text
from utils.logging import logger


def store_precedent_case(decision: Any, config: Dict[str, Any]) -> None:
    """
    Stores the final decision as a precedent case.
    """

    path = config["store"]["path"]
    os.makedirs(path, exist_ok=True)

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

    filename = os.path.join(path, f"{decision.decision_id}.jsonl")

    with open(filename, "a") as f:
        f.write(json.dumps(prec) + "\n")

    logger.info(f"Stored precedent case {decision.decision_id}")
