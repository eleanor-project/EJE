"""
Constitutional drift detection - monitors changes in rights protection over time.

Tracks whether the system maintains consistent protection of constitutional rights
(dignity, autonomy, non-discrimination) or if standards are degrading.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import statistics


@dataclass
class RightsViolationRate:
    """Violation rate for a specific right."""

    right_name: str
    period_start: datetime
    period_end: datetime
    total_decisions: int
    violations_detected: int
    violations_blocked: int
    violation_rate: float  # violations_detected / total_decisions
    blocking_rate: float   # violations_blocked / violations_detected

    @property
    def is_drifting(self) -> bool:
        """Check if violation rate indicates drift."""
        # If violation rate is increasing or blocking rate is decreasing
        return self.violation_rate > 0.05 or self.blocking_rate < 0.95


@dataclass
class DriftAlert:
    """Alert about detected constitutional drift."""

    alert_type: str  # "constitutional_drift", "precedent_inconsistency", etc.
    severity: str  # "low", "medium", "high", "critical"
    title: str
    description: str
    detected_at: str
    metrics: Dict
    recommendations: List[str]


class ConstitutionalDriftDetector:
    """
    Detects constitutional drift by monitoring rights violation patterns.

    Constitutional drift occurs when:
    1. Violation rates increase over time
    2. Blocking rates decrease (violations not being caught)
    3. Specific rights become less protected
    """

    # Core constitutional rights from RBJA
    CORE_RIGHTS = ["dignity", "autonomy", "non-discrimination"]

    def __init__(self, drift_threshold: float = 0.02):
        """
        Initialize drift detector.

        Args:
            drift_threshold: Threshold for detecting significant drift
        """
        self.drift_threshold = drift_threshold

    def analyze_rights_protection(
        self,
        decisions: List[Dict],
        baseline_period_days: int = 30,
        current_period_days: int = 7
    ) -> Dict[str, RightsViolationRate]:
        """
        Analyze rights protection across time periods.

        Args:
            decisions: List of decision dicts with critic reports
            baseline_period_days: Days for baseline calculation
            current_period_days: Days for current period

        Returns:
            Dict of right_name -> RightsViolationRate
        """
        now = datetime.utcnow()
        baseline_start = now - timedelta(days=baseline_period_days)
        current_start = now - timedelta(days=current_period_days)

        # Separate decisions by period
        baseline_decisions = [
            d for d in decisions
            if baseline_start <= self._parse_timestamp(d.get("timestamp", "")) < current_start
        ]
        current_decisions = [
            d for d in decisions
            if current_start <= self._parse_timestamp(d.get("timestamp", ""))
        ]

        # Calculate violation rates for each right
        rights_analysis = {}

        for right in self.CORE_RIGHTS:
            baseline_rate = self._calculate_violation_rate(baseline_decisions, right)
            current_rate = self._calculate_violation_rate(current_decisions, right)

            # Store current period analysis
            rights_analysis[right] = current_rate

        return rights_analysis

    def detect_drift(
        self,
        decisions: List[Dict],
        baseline_period_days: int = 30,
        current_period_days: int = 7
    ) -> List[DriftAlert]:
        """
        Detect constitutional drift by comparing time periods.

        Args:
            decisions: List of decision dicts
            baseline_period_days: Days for baseline
            current_period_days: Days for current period

        Returns:
            List of drift alerts
        """
        now = datetime.utcnow()
        baseline_start = now - timedelta(days=baseline_period_days)
        current_start = now - timedelta(days=current_period_days)

        # Separate by period
        baseline_decisions = [
            d for d in decisions
            if baseline_start <= self._parse_timestamp(d.get("timestamp", "")) < current_start
        ]
        current_decisions = [
            d for d in decisions
            if current_start <= self._parse_timestamp(d.get("timestamp", ""))
        ]

        if not baseline_decisions or not current_decisions:
            return []

        alerts = []

        for right in self.CORE_RIGHTS:
            baseline_rate = self._calculate_violation_rate(baseline_decisions, right)
            current_rate = self._calculate_violation_rate(current_decisions, right)

            # Check for drift
            drift = current_rate.violation_rate - baseline_rate.violation_rate

            if abs(drift) > self.drift_threshold:
                alert = self._create_drift_alert(
                    right, baseline_rate, current_rate, drift
                )
                alerts.append(alert)

        return alerts

    def _calculate_violation_rate(
        self,
        decisions: List[Dict],
        right: str
    ) -> RightsViolationRate:
        """Calculate violation rate for a specific right."""
        if not decisions:
            return RightsViolationRate(
                right_name=right,
                period_start=datetime.utcnow(),
                period_end=datetime.utcnow(),
                total_decisions=0,
                violations_detected=0,
                violations_blocked=0,
                violation_rate=0.0,
                blocking_rate=0.0,
            )

        timestamps = [self._parse_timestamp(d.get("timestamp", "")) for d in decisions]
        period_start = min(timestamps)
        period_end = max(timestamps)

        violations_detected = 0
        violations_blocked = 0

        for decision in decisions:
            # Check critic reports for rights violations
            critic_reports = decision.get("critic_reports", [])

            for report in critic_reports:
                if report.get("critic") == "rights_critic":
                    # Check if this right was violated
                    if report.get("right") == right and report.get("violation"):
                        violations_detected += 1

                        # Check if it was blocked
                        governance_outcome = decision.get("governance_outcome", {})
                        if governance_outcome.get("verdict") in ["DENY", "REVIEW"]:
                            violations_blocked += 1

        total = len(decisions)
        violation_rate = violations_detected / total if total > 0 else 0.0
        blocking_rate = violations_blocked / violations_detected if violations_detected > 0 else 1.0

        return RightsViolationRate(
            right_name=right,
            period_start=period_start,
            period_end=period_end,
            total_decisions=total,
            violations_detected=violations_detected,
            violations_blocked=violations_blocked,
            violation_rate=violation_rate,
            blocking_rate=blocking_rate,
        )

    def _create_drift_alert(
        self,
        right: str,
        baseline: RightsViolationRate,
        current: RightsViolationRate,
        drift: float
    ) -> DriftAlert:
        """Create drift alert from violation rate comparison."""
        severity = "low"
        if abs(drift) > 0.05:
            severity = "medium"
        if abs(drift) > 0.10:
            severity = "high"
        if abs(drift) > 0.20:
            severity = "critical"

        if drift > 0:
            title = f"⚠️ {right.title()} protection degrading"
            description = (
                f"Violation rate for {right} increased from "
                f"{baseline.violation_rate:.1%} to {current.violation_rate:.1%}"
            )
        else:
            title = f"✅ {right.title()} protection improving"
            description = (
                f"Violation rate for {right} decreased from "
                f"{baseline.violation_rate:.1%} to {current.violation_rate:.1%}"
            )

        recommendations = []
        if drift > 0:
            recommendations.append(f"Review recent decisions involving {right}")
            recommendations.append("Check if critics are calibrated correctly")
            if current.blocking_rate < 0.95:
                recommendations.append("Violations are not being blocked effectively")

        return DriftAlert(
            alert_type="constitutional_drift",
            severity=severity,
            title=title,
            description=description,
            detected_at=datetime.utcnow().isoformat(),
            metrics={
                "right": right,
                "baseline_violation_rate": baseline.violation_rate,
                "current_violation_rate": current.violation_rate,
                "drift": drift,
                "baseline_period": f"{baseline.period_start.date()} to {baseline.period_end.date()}",
                "current_period": f"{current.period_start.date()} to {current.period_end.date()}",
            },
            recommendations=recommendations,
        )

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime."""
        if not timestamp_str:
            return datetime.utcnow()

        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except Exception:
            return datetime.utcnow()

    def generate_rights_protection_report(
        self,
        decisions: List[Dict]
    ) -> Dict:
        """
        Generate comprehensive rights protection report.

        Args:
            decisions: List of decision dicts

        Returns:
            Report dict with metrics and alerts
        """
        # Analyze current state
        current_analysis = self.analyze_rights_protection(decisions)

        # Detect drift
        drift_alerts = self.detect_drift(decisions)

        # Calculate overall metrics
        total_decisions = len(decisions)
        total_violations = sum(r.violations_detected for r in current_analysis.values())
        total_blocked = sum(r.violations_blocked for r in current_analysis.values())

        overall_violation_rate = total_violations / total_decisions if total_decisions > 0 else 0.0
        overall_blocking_rate = total_blocked / total_violations if total_violations > 0 else 1.0

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_metrics": {
                "total_decisions": total_decisions,
                "total_violations": total_violations,
                "total_blocked": total_blocked,
                "violation_rate": overall_violation_rate,
                "blocking_rate": overall_blocking_rate,
            },
            "rights_analysis": {
                right: {
                    "violation_rate": rate.violation_rate,
                    "blocking_rate": rate.blocking_rate,
                    "violations_detected": rate.violations_detected,
                    "violations_blocked": rate.violations_blocked,
                    "is_drifting": rate.is_drifting,
                }
                for right, rate in current_analysis.items()
            },
            "drift_alerts": [
                {
                    "severity": alert.severity,
                    "title": alert.title,
                    "description": alert.description,
                    "metrics": alert.metrics,
                    "recommendations": alert.recommendations,
                }
                for alert in drift_alerts
            ],
            "status": "healthy" if not any(r.is_drifting for r in current_analysis.values()) else "drifting",
        }
