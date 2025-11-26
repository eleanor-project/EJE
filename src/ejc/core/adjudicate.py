"""
Eleanor Project EJE: Comprehensive Adjudication Pipeline

Integrates precedent retrieval, conflict logic, escalation, storage, and human-review triggers.
This is the unified adjudication entrypoint for the EJE/ELEANOR system.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .decision import Decision
from .aggregator import Aggregator
from .config_loader import load_global_config
from .critic_registry_loader import load_critics_from_config
from .governance.rules import apply_governance_rules
from .governance.audit import write_signed_audit_log
from .precedent.retrieval import retrieve_similar_precedents
from .precedent.store import store_precedent_case
from ..utils.logging import get_logger
from ..utils.validation import validate_case
from .error_handling import ValidationException, GovernanceException

logger = get_logger("ejc.adjudicate")


def adjudicate(
    input_data: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
    config_path: str = "config/global.yaml"
) -> Decision:
    """
    The unified adjudication pipeline for EJE/ELEANOR.

    Steps:
    1. Load configuration
    2. Validate input
    3. Load critics (registry)
    4. Run critics → produce critic reports
    5. Aggregate critic results
    6. Apply governance rules (rights-first, lexicographic)
    7. Retrieve precedent matches
    8. Apply uncertainty thresholds + escalation rules
    9. Detect conflicts and determine escalation status
    10. Build Decision object
    11. Write signed audit log
    12. Store as precedent (unless escalated)
    13. Return final Decision

    Args:
        input_data: Case input payload
        config: Full system config (optional, will be loaded if not provided)
        config_path: Path to configuration file (used if config not provided)

    Returns:
        Decision object containing complete adjudication results

    Raises:
        ValidationException: If input validation fails
        GovernanceException: If governance rules fail
    """
    # -------------------------------------------------------------------------
    # 1. Load configuration
    # -------------------------------------------------------------------------
    if config is None:
        config = load_global_config(config_path)
        logger.info(f"Loaded configuration from {config_path}")

    # -------------------------------------------------------------------------
    # 2. Validate input
    # -------------------------------------------------------------------------
    try:
        validate_case(input_data)
    except Exception as e:
        logger.error(f"Input validation failed: {str(e)}")
        raise ValidationException(f"Invalid input: {str(e)}")

    # -------------------------------------------------------------------------
    # 3. Load critics dynamically (if not already loaded)
    # -------------------------------------------------------------------------
    critics_config = config.get("critics", [])
    critics = load_critics_from_config(critics_config) if critics_config else []
    logger.info(f"Loaded {len(critics)} critics")

    # -------------------------------------------------------------------------
    # 4. Run critics → generate critic reports
    # -------------------------------------------------------------------------
    critic_reports: List[Dict[str, Any]] = []
    for critic in critics:
        try:
            report = critic.evaluate(input_data)
            critic_reports.append(report)
            logger.debug(f"Critic {getattr(critic, 'name', 'unknown')} report: {report}")
        except Exception as e:
            logger.error(f"Critic {getattr(critic, 'name', 'unknown')} failed: {str(e)}")
            # Add error report instead of failing completely
            critic_reports.append({
                "critic": getattr(critic, 'name', 'unknown'),
                "verdict": "ERROR",
                "confidence": 0,
                "justification": f"Critic failed: {str(e)}"
            })

    # -------------------------------------------------------------------------
    # 5. Aggregate results
    # -------------------------------------------------------------------------
    aggregator = Aggregator(config.get("aggregation", {}))
    aggregation_result = aggregator.aggregate(critic_reports)
    logger.info("Aggregation complete.")

    # -------------------------------------------------------------------------
    # 6. Apply governance rules (rights-first)
    # -------------------------------------------------------------------------
    try:
        governed_result = apply_governance_rules(
            aggregation_result,
            critic_reports,
            config.get("governance", {})
        )
    except GovernanceException as e:
        logger.error(f"Governance rule failure: {str(e)}")
        raise

    # -------------------------------------------------------------------------
    # 7. Retrieve precedent matches
    # -------------------------------------------------------------------------
    precedent_cfg = config.get("precedent", {})
    precedents = retrieve_similar_precedents(input_data, precedent_cfg)
    logger.info(f"Found {len(precedents)} precedent matches.")

    # -------------------------------------------------------------------------
    # 8. Precedent-based escalation logic
    # -------------------------------------------------------------------------
    escalated = governed_result.get("escalate", False)
    precedent_status = "no_match"

    if precedents:
        sim = precedents[0]["similarity"]
        thresholds = precedent_cfg.get("similarity_threshold", {})

        if sim >= thresholds.get("inherited", 0.80):
            precedent_status = "inherited"
        elif sim >= thresholds.get("advisory", 0.60):
            precedent_status = "advisory"
        elif sim >= thresholds.get("novelty", 0.40):
            precedent_status = "novelty"
        else:
            precedent_status = "conflict"
            escalated = True
            if "safeguards_triggered" not in governed_result:
                governed_result["safeguards_triggered"] = []
            governed_result["safeguards_triggered"].append("precedent_conflict")

    governed_result["precedent_status"] = precedent_status

    # -------------------------------------------------------------------------
    # 9. Final escalation determination
    # -------------------------------------------------------------------------
    if escalated:
        governed_result["escalate"] = True
        logger.warning("Decision flagged for escalation.")

    # -------------------------------------------------------------------------
    # 10. Build Decision object
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
    # 11. Write signed audit log
    # -------------------------------------------------------------------------
    try:
        write_signed_audit_log(decision)
        logger.info("Audit log written and signed.")
    except Exception as e:
        logger.error(f"Failed to write audit log: {str(e)}")
        # Don't fail the entire adjudication if audit logging fails
        # but log the error prominently

    # -------------------------------------------------------------------------
    # 12. Store precedent (only if not escalated)
    # -------------------------------------------------------------------------
    if not escalated and precedent_cfg.get("enabled", True):
        try:
            store_precedent_case(decision, precedent_cfg)
            logger.info("Decision stored as new precedent.")
        except Exception as e:
            logger.error(f"Failed to store precedent: {str(e)}")
            # Don't fail the entire adjudication if precedent storage fails

    # -------------------------------------------------------------------------
    # 13. Return final Decision
    # -------------------------------------------------------------------------
    logger.info(f"Adjudication complete for decision {decision_id}")
    return decision


# Legacy compatibility function (simpler version from original implementation)
def adjudicate_simple(input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplified adjudication function for backward compatibility.

    Args:
        input_data: Case input payload
        config: Full system config (including precedent)

    Returns:
        Outcome dict including escalation status, precedent info, etc.
    """
    outcome = {
        "escalate": False,
        "safeguards_triggered": [],
        "precedent_status": "",
        "precedent_matches": []
    }

    precedent_cfg = config.get("precedent", {})

    # Retrieve precedent matches
    precedents = retrieve_similar_precedents(input_data, precedent_cfg)
    logger.info(f"Found {len(precedents)} precedent matches.")
    outcome["precedent_matches"] = precedents

    # Detect conflict (escalation logic)
    escalated = False
    if precedents:
        sim = precedents[0]["similarity"]
        thresholds = precedent_cfg.get("similarity_threshold", {})

        if sim >= thresholds.get("inherited", 0.80):
            outcome["precedent_status"] = "inherited"
        elif sim >= thresholds.get("advisory", 0.60):
            outcome["precedent_status"] = "advisory"
        elif sim >= thresholds.get("novelty", 0.40):
            outcome["precedent_status"] = "novelty"
        else:
            outcome["precedent_status"] = "conflict"
            escalated = True
            outcome["escalate"] = True
            outcome["safeguards_triggered"].append("precedent_conflict")
    else:
        outcome["precedent_status"] = "no_match"

    # Human-review triggers
    conflict_critics = outcome.get("critics_conflict", False)
    uncertainty_critic_fired = outcome.get("uncertainty_critic", False)
    lexicographic_constraints_triggered = outcome.get("lexicographic_constraint", False)

    if conflict_critics or outcome["precedent_status"] == "conflict" or \
       uncertainty_critic_fired or lexicographic_constraints_triggered:
        escalated = True
        outcome["escalate"] = True

    # Decision (simplified placeholder)
    decision = {
        "result": "ALLOW",
        "reason": "Sample output",
        "escalated": escalated
    }

    # Store precedent (only if not escalated)
    if not escalated and precedent_cfg.get("enabled", True):
        try:
            # Create a minimal Decision object for storage
            decision_obj = Decision(
                decision_id=str(uuid.uuid4()),
                input_data=input_data,
                critic_reports=[],
                aggregation={},
                governance_outcome=decision,
                precedents=precedents,
                escalated=escalated,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            store_precedent_case(decision_obj, precedent_cfg)
        except Exception as e:
            logger.error(f"Failed to store precedent: {str(e)}")

    outcome["decision"] = decision
    return outcome
