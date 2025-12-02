"""
Conflict Detection Module

Detects and structures contradictory critic outputs, including:
- Opposing verdicts
- Divergent confidence levels
- Conflicting justifications

Provides structured conflict objects for policy engine and observability.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class ConflictType(str, Enum):
    """Types of conflicts that can be detected"""
    OPPOSING_VERDICTS = "opposing_verdicts"
    CONFIDENCE_DIVERGENCE = "confidence_divergence"
    PRIORITY_CONFLICT = "priority_conflict"
    WEIGHTED_DISAGREEMENT = "weighted_disagreement"
    CATEGORICAL_MISMATCH = "categorical_mismatch"


class ConflictSeverity(str, Enum):
    """Severity levels for detected conflicts"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CriticPosition(BaseModel):
    """Represents a critic's position in a conflict"""
    critic_name: str
    verdict: str
    confidence: float
    weight: float = 1.0
    priority: Optional[str] = None
    justification: Optional[str] = None


class Conflict(BaseModel):
    """Structured representation of a conflict between critics"""
    conflict_id: str = Field(default_factory=lambda: f"conflict-{id(object())}")
    conflict_type: ConflictType
    severity: ConflictSeverity
    involved_critics: List[str]
    positions: List[CriticPosition]
    description: str
    metrics: Dict[str, float] = Field(default_factory=dict)
    resolution_suggestion: Optional[str] = None


class ConflictDetector:
    """
    Detects and analyzes conflicts between critic outputs.

    Provides:
    - Identification of opposing verdicts
    - Analysis of confidence divergence
    - Detection of priority conflicts
    - Structured conflict objects for downstream processing
    """

    def __init__(
        self,
        confidence_divergence_threshold: float = 0.3,
        weighted_disagreement_threshold: float = 0.4,
        min_confidence_gap: float = 0.2
    ):
        """
        Initialize the conflict detector.

        Args:
            confidence_divergence_threshold: Threshold for confidence variance to trigger conflict
            weighted_disagreement_threshold: Threshold for weighted score disagreement
            min_confidence_gap: Minimum confidence gap to consider divergence
        """
        self.confidence_divergence_threshold = confidence_divergence_threshold
        self.weighted_disagreement_threshold = weighted_disagreement_threshold
        self.min_confidence_gap = min_confidence_gap

    def detect_conflicts(
        self,
        critic_outputs: List[Dict[str, Any]]
    ) -> List[Conflict]:
        """
        Detect all conflicts in a set of critic outputs.

        Args:
            critic_outputs: List of critic output dictionaries

        Returns:
            List of detected Conflict objects
        """
        conflicts = []

        # Check for opposing verdicts
        opposing = self._detect_opposing_verdicts(critic_outputs)
        if opposing:
            conflicts.append(opposing)

        # Check for confidence divergence
        divergence = self._detect_confidence_divergence(critic_outputs)
        if divergence:
            conflicts.append(divergence)

        # Check for priority conflicts
        priority_conflict = self._detect_priority_conflicts(critic_outputs)
        if priority_conflict:
            conflicts.append(priority_conflict)

        # Check for weighted disagreement
        weighted_conflict = self._detect_weighted_disagreement(critic_outputs)
        if weighted_conflict:
            conflicts.append(weighted_conflict)

        return conflicts

    def _detect_opposing_verdicts(
        self,
        critic_outputs: List[Dict[str, Any]]
    ) -> Optional[Conflict]:
        """Detect critics with directly opposing verdicts"""
        verdicts = {}
        for output in critic_outputs:
            verdict = output.get('verdict', 'REVIEW')
            if verdict not in verdicts:
                verdicts[verdict] = []
            verdicts[verdict].append(output)

        # Check for ALLOW vs DENY/BLOCK opposition
        has_allow = 'ALLOW' in verdicts and len(verdicts['ALLOW']) > 0
        has_block = ('BLOCK' in verdicts and len(verdicts['BLOCK']) > 0) or \
                    ('DENY' in verdicts and len(verdicts['DENY']) > 0)

        if has_allow and has_block:
            allow_critics = verdicts.get('ALLOW', [])
            block_critics = verdicts.get('BLOCK', []) + verdicts.get('DENY', [])

            positions = []
            involved_critics = []

            for critic in allow_critics:
                positions.append(CriticPosition(
                    critic_name=critic.get('critic', 'unknown'),
                    verdict=critic.get('verdict'),
                    confidence=critic.get('confidence', 0.0),
                    weight=critic.get('weight', 1.0),
                    priority=critic.get('priority'),
                    justification=critic.get('justification')
                ))
                involved_critics.append(critic.get('critic', 'unknown'))

            for critic in block_critics:
                positions.append(CriticPosition(
                    critic_name=critic.get('critic', 'unknown'),
                    verdict=critic.get('verdict'),
                    confidence=critic.get('confidence', 0.0),
                    weight=critic.get('weight', 1.0),
                    priority=critic.get('priority'),
                    justification=critic.get('justification')
                ))
                involved_critics.append(critic.get('critic', 'unknown'))

            # Calculate severity based on number of critics and confidence
            allow_confidence = sum(c.get('confidence', 0.0) for c in allow_critics) / len(allow_critics)
            block_confidence = sum(c.get('confidence', 0.0) for c in block_critics) / len(block_critics)
            avg_confidence = (allow_confidence + block_confidence) / 2

            if avg_confidence > 0.8:
                severity = ConflictSeverity.CRITICAL
            elif avg_confidence > 0.6:
                severity = ConflictSeverity.HIGH
            elif avg_confidence > 0.4:
                severity = ConflictSeverity.MEDIUM
            else:
                severity = ConflictSeverity.LOW

            return Conflict(
                conflict_type=ConflictType.OPPOSING_VERDICTS,
                severity=severity,
                involved_critics=involved_critics,
                positions=positions,
                description=f"{len(allow_critics)} critic(s) vote ALLOW while {len(block_critics)} vote BLOCK/DENY",
                metrics={
                    'allow_count': len(allow_critics),
                    'block_count': len(block_critics),
                    'allow_avg_confidence': allow_confidence,
                    'block_avg_confidence': block_confidence
                },
                resolution_suggestion="Consider human review or policy override"
            )

        return None

    def _detect_confidence_divergence(
        self,
        critic_outputs: List[Dict[str, Any]]
    ) -> Optional[Conflict]:
        """Detect sharp divergence in confidence levels"""
        if len(critic_outputs) < 2:
            return None

        confidences = [output.get('confidence', 0.0) for output in critic_outputs]
        min_conf = min(confidences)
        max_conf = max(confidences)
        confidence_gap = max_conf - min_conf

        if confidence_gap < self.min_confidence_gap:
            return None

        # Calculate variance
        mean_conf = sum(confidences) / len(confidences)
        variance = sum((c - mean_conf) ** 2 for c in confidences) / len(confidences)

        if variance < self.confidence_divergence_threshold:
            return None

        # Find critics with extreme confidence values
        low_conf_critics = [o for o in critic_outputs if o.get('confidence', 0.0) < mean_conf]
        high_conf_critics = [o for o in critic_outputs if o.get('confidence', 0.0) >= mean_conf]

        positions = []
        involved_critics = []

        for critic in critic_outputs:
            positions.append(CriticPosition(
                critic_name=critic.get('critic', 'unknown'),
                verdict=critic.get('verdict'),
                confidence=critic.get('confidence', 0.0),
                weight=critic.get('weight', 1.0),
                priority=critic.get('priority'),
                justification=critic.get('justification')
            ))
            involved_critics.append(critic.get('critic', 'unknown'))

        severity = ConflictSeverity.HIGH if variance > 0.5 else ConflictSeverity.MEDIUM

        return Conflict(
            conflict_type=ConflictType.CONFIDENCE_DIVERGENCE,
            severity=severity,
            involved_critics=involved_critics,
            positions=positions,
            description=f"Confidence levels vary significantly (gap: {confidence_gap:.2f}, variance: {variance:.3f})",
            metrics={
                'min_confidence': min_conf,
                'max_confidence': max_conf,
                'confidence_gap': confidence_gap,
                'variance': variance,
                'mean_confidence': mean_conf
            },
            resolution_suggestion="Investigate why confidence levels diverge"
        )

    def _detect_priority_conflicts(
        self,
        critic_outputs: List[Dict[str, Any]]
    ) -> Optional[Conflict]:
        """Detect conflicts where multiple critics have override/veto priority"""
        priority_critics = [o for o in critic_outputs if o.get('priority') in ['override', 'veto']]

        if len(priority_critics) < 2:
            return None

        # Check if they have different verdicts
        verdicts = set(c.get('verdict') for c in priority_critics)
        if len(verdicts) <= 1:
            return None  # No conflict if all agree

        positions = []
        involved_critics = []

        for critic in priority_critics:
            positions.append(CriticPosition(
                critic_name=critic.get('critic', 'unknown'),
                verdict=critic.get('verdict'),
                confidence=critic.get('confidence', 0.0),
                weight=critic.get('weight', 1.0),
                priority=critic.get('priority'),
                justification=critic.get('justification')
            ))
            involved_critics.append(critic.get('critic', 'unknown'))

        return Conflict(
            conflict_type=ConflictType.PRIORITY_CONFLICT,
            severity=ConflictSeverity.CRITICAL,
            involved_critics=involved_critics,
            positions=positions,
            description=f"{len(priority_critics)} critics with priority/override have conflicting verdicts",
            metrics={
                'priority_critic_count': len(priority_critics),
                'unique_verdicts': len(verdicts)
            },
            resolution_suggestion="Escalate to human reviewer - multiple overrides conflict"
        )

    def _detect_weighted_disagreement(
        self,
        critic_outputs: List[Dict[str, Any]]
    ) -> Optional[Conflict]:
        """Detect significant disagreement when weighted scores are considered"""
        if len(critic_outputs) < 2:
            return None

        # Calculate weighted scores by verdict
        verdict_scores = {}
        for output in critic_outputs:
            verdict = output.get('verdict', 'REVIEW')
            confidence = output.get('confidence', 0.0)
            weight = output.get('weight', 1.0)
            score = confidence * weight

            if verdict not in verdict_scores:
                verdict_scores[verdict] = 0.0
            verdict_scores[verdict] += score

        # Remove ERROR and REVIEW verdicts for this analysis
        verdict_scores = {k: v for k, v in verdict_scores.items() if k not in ['ERROR', 'REVIEW']}

        if len(verdict_scores) < 2:
            return None

        scores = list(verdict_scores.values())
        min_score = min(scores)
        max_score = max(scores)

        if max_score == 0:
            return None

        disagreement_ratio = min_score / max_score

        if disagreement_ratio < self.weighted_disagreement_threshold:
            return None

        positions = []
        involved_critics = []

        for output in critic_outputs:
            if output.get('verdict') not in ['ERROR', 'REVIEW']:
                positions.append(CriticPosition(
                    critic_name=output.get('critic', 'unknown'),
                    verdict=output.get('verdict'),
                    confidence=output.get('confidence', 0.0),
                    weight=output.get('weight', 1.0),
                    priority=output.get('priority'),
                    justification=output.get('justification')
                ))
                involved_critics.append(output.get('critic', 'unknown'))

        return Conflict(
            conflict_type=ConflictType.WEIGHTED_DISAGREEMENT,
            severity=ConflictSeverity.MEDIUM,
            involved_critics=involved_critics,
            positions=positions,
            description=f"Weighted scores show significant disagreement (ratio: {disagreement_ratio:.2f})",
            metrics={
                'min_score': min_score,
                'max_score': max_score,
                'disagreement_ratio': disagreement_ratio,
                'verdict_scores': verdict_scores
            },
            resolution_suggestion="Review critic weights and consider consensus building"
        )

    def has_critical_conflicts(self, conflicts: List[Conflict]) -> bool:
        """Check if any conflicts are critical severity"""
        return any(c.severity == ConflictSeverity.CRITICAL for c in conflicts)

    def get_conflict_summary(self, conflicts: List[Conflict]) -> Dict[str, Any]:
        """
        Generate a summary of detected conflicts.

        Args:
            conflicts: List of detected conflicts

        Returns:
            Dictionary summary of conflicts by type and severity
        """
        summary = {
            'total_conflicts': len(conflicts),
            'by_type': {},
            'by_severity': {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            },
            'requires_escalation': False,
            'involved_critics': set()
        }

        for conflict in conflicts:
            # Count by type
            conflict_type = conflict.conflict_type.value
            if conflict_type not in summary['by_type']:
                summary['by_type'][conflict_type] = 0
            summary['by_type'][conflict_type] += 1

            # Count by severity
            severity = conflict.severity.value
            summary['by_severity'][severity] += 1

            # Track involved critics
            for critic in conflict.involved_critics:
                summary['involved_critics'].add(critic)

            # Check if escalation needed
            if conflict.severity in [ConflictSeverity.CRITICAL, ConflictSeverity.HIGH]:
                summary['requires_escalation'] = True

        summary['involved_critics'] = list(summary['involved_critics'])

        return summary


# Convenience functions
def detect_conflicts(critic_outputs: List[Dict[str, Any]]) -> List[Conflict]:
    """
    Convenience function to detect conflicts using default settings.

    Args:
        critic_outputs: List of critic output dictionaries

    Returns:
        List of detected conflicts
    """
    detector = ConflictDetector()
    return detector.detect_conflicts(critic_outputs)


def has_conflicts(critic_outputs: List[Dict[str, Any]]) -> bool:
    """
    Quick check if any conflicts exist.

    Args:
        critic_outputs: List of critic output dictionaries

    Returns:
        True if conflicts detected, False otherwise
    """
    conflicts = detect_conflicts(critic_outputs)
    return len(conflicts) > 0


def requires_escalation(critic_outputs: List[Dict[str, Any]]) -> bool:
    """
    Check if conflicts require escalation to human review.

    Args:
        critic_outputs: List of critic output dictionaries

    Returns:
        True if escalation required, False otherwise
    """
    detector = ConflictDetector()
    conflicts = detector.detect_conflicts(critic_outputs)
    return detector.has_critical_conflicts(conflicts)
