# governance/adjudicate.py

import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, List

from core.decision import Decision
from core.aggregator import Aggregator
from core.errors import ValidationError, GovernanceError
from core.validation import validate_input

from critics.registry import load_critics_from_config
from governance.rules import apply_governance_rules
from governance.audit import write_signed_audit_log

from precedent.retrieval import retrieve_similar_precedents
from precedent.store import store_precedent_case

from utils.logging import logger
from utils.config_loader import load_config


def adjudicate(
    input_data: Dict[str, Any],
    config_path: str = "config/main.yaml"
) -> Decision:
    """
    The unified adjudication pipeline for EJE/ELEANOR.
    
    Steps:
    1. Load config
    2. Validate input
    3. Load critics (registry)
    4. Run critics → produce critic reports
    5. Aggregate critic results
    6. Apply governance rules (rights-first, lexicographic)
    7. Retrieve precedent matches
    8. Apply uncertainty thresholds + escalation rules
    9. Build Decision object
    10. Write signed audit log
    11. Store as precedent (unless escalated)
    12. Return final Decision
    
    This **is** the official EJE adjudication entrypoint.
    """

    # -------------------------------------------------------------------------
    # 1. Load configuration
    # -------------------------------------------------------------------------
    config = load_config(config_path)
    logger.info("Loaded configuration.")

    # -------------------------------------------------------------------------
    # 2. Validate input
    # -------------------------------------------------------------------------
    try:
        validate_input(input_data, config.get("input_schema"))
    except ValidationError as e:
        logger.error(f"Validation failed: {str(e)}")
        raise

    # -------------------------------------------------------------------------
    # 3. Load critics dynamically
    # -------------------------------------------------------------------------
    critics = load_critics_from_config(config.get("critics"))
    logger.info(f"Loaded {len(critics)} critics: {[c.name for c in critics]}")

    # -------------------------------------------------------------------------
    # 4. Run critics → generate critic reports
    # -------------------------------------------------------------------------
    critic_reports: List[Dict[str, Any]] = []
    for critic in critics:
        try:
            report = critic.evaluate(input_data)
            critic_reports.append(report)
            logger.debug(f"Critic {critic.name} report: {report}")
        except Exception as e:
            logger.error(f"Critic {critic.name} failed: {str(e)}")
            raise GovernanceError(f"Critic failure in {critic.name}: {str(e)}")

    # -------------------------------------------------------------------------
    # 5. Aggregate results
    # -------------------------------------------------------------------------
    aggregator = Aggregator(config.get("aggregation"))
    aggregation_result = aggregator.aggregate(critic_reports)
    logger.info("Aggregation complete.")

    # -------------------------------------------------------------------------
    # 6. Apply governance rules (rights-first)
    # -------------------------------------------------------------------------
    try:
        governed_result = apply_governance_rules(
            aggregation_result,
            critic_reports,
            config.get("governance")
        )
    except GovernanceError as e:
        logger.error(f"Governance rule failure: {str(e)}")
        raise

    # -------------------------------------------------------------------------
    # 7. Retrieve precedent matches
    # -------------------------------------------------------------------------
    precedents = retrieve_similar_precedents(input_data)
    logger.info(f"Found {len(precedents)} precedent matches.")

    # -------------------------------------------------------------------------
    # 8. Escalation logic (uncertainty, conflict, novelty)
    # -------------------------------------------------------------------------
    escalated = False
    if governed_result.get("escalate", False):
        escalated = True
        logger.warning("Decision flagged for escalation.")

    # -------------------------------------------------------------------------
    # 9. Build Decision object
    # -------------------------------------------------------------------------
    decision_id = str(uuid.uuid4())
    decision = Decision(
        decision_id=decision_id,
        input_data=input_data,
        critic_reports=critic_reports,
        aggregation=aggregation_result,
        governance_outcome=governed_result,
        precedents=precedents,
        escalated=escalated,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )

    # -------------------------------------------------------------------------
    # 10. Write signed audit log
    # -------------------------------------------------------------------------
    write_signed_audit_log(decision)
    logger.info("Audit log written and signed.")

    # -------------------------------------------------------------------------
    # 11. Store precedent (only if not escalated)
    # -------------------------------------------------------------------------
    if not escalated:
        store_precedent_case(decision)
        logger.info("Decision stored as new precedent.")

    # -------------------------------------------------------------------------
    # 12. Return final Decision
    # -------------------------------------------------------------------------
    return decision
