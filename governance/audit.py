# governance/audit.py
"""Audit logging wrapper for governance decisions."""

import os
from typing import Any
from src.ejc.core.signed_audit_log import SignedAuditLogger
from src.ejc.utils.logging import get_logger

logger = get_logger("governance.audit")

# Global audit logger instance
_audit_logger = None


def get_audit_logger() -> SignedAuditLogger:
    """Get or create the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        db_uri = os.getenv("EJC_DB_URI", "sqlite:///eleanor_data/audit.db")
        _audit_logger = SignedAuditLogger(db_uri=db_uri)
    return _audit_logger


def write_signed_audit_log(decision: Any) -> None:
    """
    Write a signed audit log entry for a decision.

    Args:
        decision: Decision object to log
    """
    try:
        audit_logger = get_audit_logger()

        # Convert Decision object to dict format expected by audit logger
        decision_bundle = decision.to_dict()

        # Ensure required fields exist
        if "request_id" not in decision_bundle:
            decision_bundle["request_id"] = decision.decision_id
        if "timestamp" not in decision_bundle or not decision_bundle["timestamp"]:
            from datetime import datetime
            decision_bundle["timestamp"] = datetime.utcnow().isoformat()

        # Log the decision
        audit_logger.log_decision(decision_bundle)
        logger.info(f"Audit log written for decision {decision.decision_id}")

    except Exception as e:
        logger.error(f"Failed to write audit log: {str(e)}")
        raise
