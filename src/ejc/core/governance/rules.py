# src/ejc/core/governance/rules.py

from typing import Dict, Any, List
from ..error_handling import GovernanceException
from ...utils.logging import get_logger

logger = get_logger("ejc.governance.rules")


class RightsViolation(GovernanceException):
    """Raised when a critical right is violated."""
    pass


def apply_governance_rules(
    aggregated: Dict[str, Any],
    critic_reports: List[Dict[str, Any]],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Applies the lexicographic governance hierarchy:
    1. Hard rights constraints (non-negotiable)
    2. Safety constraints
    3. Non-discrimination
    4. Fairness balance
    5. Transparency + proportionality (advisory)
    6. Uncertainty → escalation
    7. Precedent conflicts → escalation

    Args:
        aggregated: Aggregated results from all critics
        critic_reports: Individual critic reports
        config: Governance configuration including rights hierarchy

    Returns:
        A modified governance outcome dict

    Raises:
        RightsViolation: If a critical right is violated
        GovernanceException: If configuration is invalid
    """
    rights_cfg = config.get("rights_hierarchy")
    if not rights_cfg:
        raise GovernanceException("Missing rights hierarchy configuration.")

    outcome = aggregated.copy()
    outcome["safeguards_triggered"] = []
    outcome["escalate"] = False

    # ----------------------------------------------------------------------
    # 1. Hard rights violations (dignity, autonomy, non_discrimination)
    # ----------------------------------------------------------------------
    for right, rule in rights_cfg.items():
        if rule.get("required") and _violates_right(critic_reports, right):
            logger.error(f"Critical rights violation: {right}")
            raise RightsViolation(
                f"Decision prohibited due to violation of '{right}'."
            )

    # ----------------------------------------------------------------------
    # 2. Safety guard
    # ----------------------------------------------------------------------
    if _violates_right(critic_reports, "safety"):
        outcome["escalate"] = True
        outcome["safeguards_triggered"].append("safety")
        logger.warning("Safety safeguard triggered → escalation required.")

    # ----------------------------------------------------------------------
    # 3. Fairness balancing (moderate severity)
    # ----------------------------------------------------------------------
    if _violates_right(critic_reports, "fairness"):
        outcome["safeguards_triggered"].append("fairness")
        logger.info("Fairness concerns detected → soft penalty applied.")
        outcome["fairness_penalty"] = True

    # ----------------------------------------------------------------------
    # 4. Transparency + Proportionality (advisory)
    # ----------------------------------------------------------------------
    for advisory_right in ["transparency", "proportionality"]:
        if _violates_right(critic_reports, advisory_right):
            outcome["safeguards_triggered"].append(advisory_right)
            logger.info(f"Advisory safeguard triggered: {advisory_right}")

    # ----------------------------------------------------------------------
    # 5. Uncertainty threshold (critical from ELEANOR v4.5.1)
    # ----------------------------------------------------------------------
    if _critic_uncertainty_high(critic_reports):
        logger.warning("High uncertainty detected → escalation.")
        outcome["escalate"] = True
        outcome["safeguards_triggered"].append("uncertainty")

    # ----------------------------------------------------------------------
    # 6. Precedent disagreements
    # ----------------------------------------------------------------------
    if _precedent_conflicts(critic_reports):
        logger.warning("Precedent conflict → escalation.")
        outcome["escalate"] = True
        outcome["safeguards_triggered"].append("precedent_conflict")

    return outcome


# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------

def _violates_right(critic_reports: List[Dict[str, Any]], right_name: str) -> bool:
    """
    Returns True if any critic report flags a violation of the given right.

    Args:
        critic_reports: List of critic reports
        right_name: Name of the right to check

    Returns:
        True if violation detected, False otherwise
    """
    for report in critic_reports:
        if report.get("right") == right_name and report.get("violation", False):
            return True
    return False


def _critic_uncertainty_high(critic_reports: List[Dict[str, Any]]) -> bool:
    """
    Determines if the uncertainty critic indicates low confidence.
    Implements ELEANOR v4.5.1 guidance (forced sampling + multiple triggers).

    Args:
        critic_reports: List of critic reports

    Returns:
        True if high uncertainty detected, False otherwise
    """
    for r in critic_reports:
        if r.get("critic") == "uncertainty" and r.get("confidence_score", 1.0) < 0.4:
            return True
    return False


def _precedent_conflicts(critic_reports: List[Dict[str, Any]]) -> bool:
    """
    Detects if precedent critic indicates a deviation from established decisions.

    Args:
        critic_reports: List of critic reports

    Returns:
        True if precedent conflict detected, False otherwise
    """
    for r in critic_reports:
        if r.get("critic") == "precedent" and r.get("conflict", False):
            return True
    return False
