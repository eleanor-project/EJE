"""
Ethical consensus tracker - monitors changes in critic agreement patterns.

Tracks shifts in how critics agree/disagree, which may indicate:
1. Evolving ethical standards
2. Critic drift
3. Emerging edge cases
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
import statistics


@dataclass
class ConsensusMetrics:
    """Metrics for critic consensus in a time period."""

    period_start: datetime
    period_end: datetime
    total_decisions: int
    unanimous_decisions: int  # All critics agree
    majority_decisions: int  # >50% agree
    split_decisions: int  # 50/50 split
    avg_dissent_index: float  # Average disagreement (0=consensus, 1=total disagreement)
    most_contentious_critics: List[Tuple[str, str]]  # Pairs that disagree most


@dataclass
class ConsensusShift:
    """Detected shift in consensus patterns."""

    shift_type: str  # "increasing_dissent", "decreasing_dissent", "polarization"
    magnitude: float  # Size of the shift
    baseline_consensus: float
    current_consensus: float
    affected_critics: List[str]
    description: str
    examples: List[str]  # Decision IDs showing the shift


class ConsensusTracker:
    """
    Tracks ethical consensus among critics over time.

    Monitors how much critics agree, and detects shifts that may indicate:
    - Emerging ethical complexities
    - Critic recalibration needs
    - System-wide drift
    """

    def __init__(
        self,
        consensus_threshold: float = 0.8,
        shift_threshold: float = 0.15
    ):
        """
        Initialize consensus tracker.

        Args:
            consensus_threshold: Minimum agreement rate for "consensus"
            shift_threshold: Minimum change to flag as shift
        """
        self.consensus_threshold = consensus_threshold
        self.shift_threshold = shift_threshold

    def calculate_consensus_metrics(
        self,
        decisions: List[Dict],
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> ConsensusMetrics:
        """
        Calculate consensus metrics for a time period.

        Args:
            decisions: List of decision dicts
            period_start: Start of period (optional)
            period_end: End of period (optional)

        Returns:
            ConsensusMetrics for the period
        """
        if not decisions:
            return ConsensusMetrics(
                period_start=period_start or datetime.utcnow(),
                period_end=period_end or datetime.utcnow(),
                total_decisions=0,
                unanimous_decisions=0,
                majority_decisions=0,
                split_decisions=0,
                avg_dissent_index=0.0,
                most_contentious_critics=[],
            )

        # Extract timestamps if not provided
        if not period_start or not period_end:
            timestamps = [self._parse_timestamp(d.get("timestamp", "")) for d in decisions]
            period_start = min(timestamps)
            period_end = max(timestamps)

        # Analyze each decision
        unanimous = 0
        majority = 0
        split = 0
        dissent_indices = []
        critic_disagreements = defaultdict(int)

        for decision in decisions:
            critic_reports = decision.get("critic_reports", [])

            if not critic_reports:
                continue

            # Extract verdicts
            verdicts = [r.get("verdict", "REVIEW") for r in critic_reports]
            critic_names = [r.get("critic", "unknown") for r in critic_reports]

            # Count verdict distribution
            verdict_counts = Counter(verdicts)
            most_common = verdict_counts.most_common(1)[0][1] if verdict_counts else 0
            total = len(verdicts)

            if total == 0:
                continue

            # Classify consensus level
            agreement_rate = most_common / total

            if agreement_rate == 1.0:
                unanimous += 1
            elif agreement_rate > 0.5:
                majority += 1
            elif agreement_rate == 0.5:
                split += 1

            # Calculate dissent index (0=consensus, 1=total disagreement)
            dissent = 1.0 - agreement_rate
            dissent_indices.append(dissent)

            # Track which critics disagree
            for i, verdict1 in enumerate(verdicts):
                for j in range(i + 1, len(verdicts)):
                    verdict2 = verdicts[j]
                    if verdict1 != verdict2:
                        pair = tuple(sorted([critic_names[i], critic_names[j]]))
                        critic_disagreements[pair] += 1

        avg_dissent = statistics.mean(dissent_indices) if dissent_indices else 0.0

        # Most contentious critic pairs
        most_contentious = sorted(
            critic_disagreements.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return ConsensusMetrics(
            period_start=period_start,
            period_end=period_end,
            total_decisions=len(decisions),
            unanimous_decisions=unanimous,
            majority_decisions=majority,
            split_decisions=split,
            avg_dissent_index=avg_dissent,
            most_contentious_critics=most_contentious,
        )

    def detect_consensus_shifts(
        self,
        decisions: List[Dict],
        baseline_period_days: int = 30,
        current_period_days: int = 7
    ) -> List[ConsensusShift]:
        """
        Detect shifts in consensus patterns over time.

        Args:
            decisions: List of decision dicts
            baseline_period_days: Days for baseline
            current_period_days: Days for current period

        Returns:
            List of detected consensus shifts
        """
        now = datetime.utcnow()
        baseline_start = now - timedelta(days=baseline_period_days)
        current_start = now - timedelta(days=current_period_days)

        # Split decisions by period
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

        baseline_metrics = self.calculate_consensus_metrics(baseline_decisions)
        current_metrics = self.calculate_consensus_metrics(current_decisions)

        shifts = []

        # Check for overall consensus shift
        baseline_consensus = 1.0 - baseline_metrics.avg_dissent_index
        current_consensus = 1.0 - current_metrics.avg_dissent_index
        consensus_change = current_consensus - baseline_consensus

        if abs(consensus_change) >= self.shift_threshold:
            shift = self._create_consensus_shift(
                baseline_metrics, current_metrics, consensus_change
            )
            shifts.append(shift)

        # Check for critic-specific shifts
        critic_shifts = self._detect_critic_pair_shifts(
            baseline_metrics, current_metrics
        )
        shifts.extend(critic_shifts)

        return shifts

    def _create_consensus_shift(
        self,
        baseline: ConsensusMetrics,
        current: ConsensusMetrics,
        change: float
    ) -> ConsensusShift:
        """Create consensus shift report."""
        baseline_consensus = 1.0 - baseline.avg_dissent_index
        current_consensus = 1.0 - current.avg_dissent_index

        if change > 0:
            shift_type = "decreasing_dissent"
            description = (
                f"Ethical consensus improving: "
                f"Critics agreeing more ({baseline_consensus:.0%} → {current_consensus:.0%})"
            )
        else:
            shift_type = "increasing_dissent"
            description = (
                f"Ethical consensus declining: "
                f"Critics disagreeing more ({baseline_consensus:.0%} → {current_consensus:.0%})"
            )

        return ConsensusShift(
            shift_type=shift_type,
            magnitude=abs(change),
            baseline_consensus=baseline_consensus,
            current_consensus=current_consensus,
            affected_critics=[],  # Could be enhanced
            description=description,
            examples=[],
        )

    def _detect_critic_pair_shifts(
        self,
        baseline: ConsensusMetrics,
        current: ConsensusMetrics
    ) -> List[ConsensusShift]:
        """Detect shifts in specific critic pair agreement."""
        shifts = []

        # Check if previously-agreeing critics now disagree
        baseline_pairs = set(p[0] for p in baseline.most_contentious_critics)
        current_pairs = set(p[0] for p in current.most_contentious_critics)

        new_contentious = current_pairs - baseline_pairs

        if new_contentious and len(new_contentious) >= 2:
            critics = list(new_contentious)[0]  # First pair
            shift = ConsensusShift(
                shift_type="polarization",
                magnitude=0.5,
                baseline_consensus=0.9,
                current_consensus=0.6,
                affected_critics=list(critics),
                description=f"New disagreement pattern: {critics[0]} vs {critics[1]}",
                examples=[],
            )
            shifts.append(shift)

        return shifts

    def generate_consensus_report(
        self,
        decisions: List[Dict]
    ) -> Dict:
        """
        Generate comprehensive consensus report.

        Args:
            decisions: List of decision dicts

        Returns:
            Report dict with consensus metrics
        """
        # Current metrics
        current_metrics = self.calculate_consensus_metrics(decisions)

        # Detect shifts
        shifts = self.detect_consensus_shifts(decisions)

        # Calculate health
        consensus_rate = 1.0 - current_metrics.avg_dissent_index
        status = "healthy" if consensus_rate >= self.consensus_threshold else "concerning"

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "metrics": {
                "total_decisions": current_metrics.total_decisions,
                "unanimous_decisions": current_metrics.unanimous_decisions,
                "majority_decisions": current_metrics.majority_decisions,
                "split_decisions": current_metrics.split_decisions,
                "consensus_rate": consensus_rate,
                "avg_dissent_index": current_metrics.avg_dissent_index,
            },
            "most_contentious_critics": [
                {"critics": list(pair), "disagreements": count}
                for pair, count in current_metrics.most_contentious_critics
            ],
            "shifts_detected": [
                {
                    "type": shift.shift_type,
                    "magnitude": shift.magnitude,
                    "description": shift.description,
                    "affected_critics": shift.affected_critics,
                }
                for shift in shifts
            ],
            "recommendations": self._generate_recommendations(current_metrics, shifts),
        }

    def _generate_recommendations(
        self,
        metrics: ConsensusMetrics,
        shifts: List[ConsensusShift]
    ) -> List[str]:
        """Generate recommendations based on consensus analysis."""
        recommendations = []

        consensus_rate = 1.0 - metrics.avg_dissent_index

        if consensus_rate < 0.6:
            recommendations.append(
                "⚠️ Low consensus rate - consider reviewing critic configurations"
            )

        if metrics.split_decisions / metrics.total_decisions > 0.2:
            recommendations.append(
                "🔀 High rate of split decisions - may need additional tie-breaking logic"
            )

        increasing_dissent_shifts = [s for s in shifts if s.shift_type == "increasing_dissent"]
        if increasing_dissent_shifts:
            recommendations.append(
                f"📉 Consensus declining - {len(increasing_dissent_shifts)} shifts detected"
            )

        if metrics.most_contentious_critics:
            pair, count = metrics.most_contentious_critics[0]
            recommendations.append(
                f"🔍 Review disagreements between {pair[0]} and {pair[1]} ({count} times)"
            )

        if not recommendations:
            recommendations.append("✅ Consensus patterns healthy")

        return recommendations

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime."""
        if not timestamp_str:
            return datetime.utcnow()

        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except Exception:
            return datetime.utcnow()
