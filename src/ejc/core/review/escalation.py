"""
Enhanced escalation bundles for human review.

Provides rich context bundles with dissent analysis, similar precedents,
and explanation summaries to help human reviewers make informed decisions.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class CriticVote:
    """Individual critic's vote in a decision."""

    critic_name: str
    verdict: str  # "allowed", "blocked", "review"
    confidence: float
    reasoning: str
    critical_factors: List[str] = field(default_factory=list)


@dataclass
class DissentAnalysis:
    """Analysis of disagreement among critics."""

    dissent_index: float  # 0.0 (unanimous) to 1.0 (maximum disagreement)
    majority_verdict: str
    minority_verdicts: List[str]
    split_ratio: str  # e.g., "3:2:1" for 3 allowed, 2 blocked, 1 review
    disagreement_type: str  # "unanimous", "strong_majority", "split", "deadlock"
    conflicting_principles: List[str] = field(default_factory=list)
    reasoning_divergence: float = 0.0  # 0.0 (identical) to 1.0 (completely disjoint)
    summary: Optional[str] = None


@dataclass
class SimilarCase:
    """Similar precedent for context."""

    precedent_id: str
    similarity_score: float
    verdict: str
    context: str
    resolution_notes: Optional[str] = None


@dataclass
class EscalationBundle:
    """
    Rich bundle for human review with comprehensive context.

    Includes:
    - Original case details
    - All critic votes with reasoning
    - Dissent analysis
    - Similar precedents
    - Explanation summary
    - Review metadata
    """

    bundle_id: str
    case_id: str
    input_data: Dict[str, Any]
    critic_votes: List[CriticVote]
    dissent_analysis: DissentAnalysis
    similar_precedents: List[SimilarCase]
    explanation_summary: str
    priority: str  # "critical", "high", "medium", "low"
    escalated_at: datetime = field(default_factory=datetime.utcnow)
    review_deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    rights_impact: List[Dict[str, Any]] = field(default_factory=list)


class EscalationBundleBuilder:
    """
    Builds rich escalation bundles for human review.

    Analyzes critic disagreement, finds similar precedents, and generates
    comprehensive context to help reviewers make informed decisions.
    """

    def __init__(
        self,
        precedent_search: Optional[Any] = None,  # Hybrid search instance
        explainer: Optional[Any] = None  # Explanation generator
    ):
        """
        Initialize escalation bundle builder.

        Args:
            precedent_search: Optional search instance for finding similar cases
            explainer: Optional explainer for generating summaries
        """
        self.precedent_search = precedent_search
        self.explainer = explainer

    def build_bundle(
        self,
        case_id: str,
        input_data: Dict,
        critic_results: List[Dict],
        priority: Optional[str] = None
    ) -> EscalationBundle:
        """
        Build comprehensive escalation bundle.

        Args:
            case_id: Unique case identifier
            input_data: Input data with prompt and context
            critic_results: List of critic result dictionaries
            priority: Optional priority override

        Returns:
            EscalationBundle with rich context
        """
        # Convert critic results to votes
        critic_votes = self._extract_votes(critic_results)

        # Analyze dissent, including reasoning divergence and conflicts
        dissent_analysis = self._analyze_dissent(critic_votes)

        # Assess rights and risk impact to guide human review focus
        rights_impact = self._assess_rights_impact(input_data, critic_votes)

        # Find similar precedents
        similar_precedents = self._find_similar_precedents(input_data)

        # Generate explanation summary
        explanation_summary = self._generate_explanation(
            input_data,
            critic_votes,
            dissent_analysis
        )

        # Determine priority if not provided
        if priority is None:
            priority = self._determine_priority(dissent_analysis, input_data, rights_impact)

        # Generate bundle ID
        bundle_id = self._generate_bundle_id(case_id)

        return EscalationBundle(
            bundle_id=bundle_id,
            case_id=case_id,
            input_data=input_data,
            critic_votes=critic_votes,
            dissent_analysis=dissent_analysis,
            similar_precedents=similar_precedents,
            explanation_summary=explanation_summary,
            priority=priority,
            metadata={
                "num_critics": len(critic_votes),
                "num_similar_precedents": len(similar_precedents),
                "generated_at": datetime.utcnow().isoformat(),
                "review_checklist": self._build_review_checklist(dissent_analysis, rights_impact),
            },
            rights_impact=rights_impact,
        )

    def _extract_votes(self, critic_results: List[Dict]) -> List[CriticVote]:
        """Extract critic votes from result dictionaries."""
        votes = []

        for result in critic_results:
            vote = CriticVote(
                critic_name=result.get("critic_name", "unknown"),
                verdict=result.get("verdict", "review"),
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("reasoning", "No reasoning provided"),
                critical_factors=result.get("critical_factors", [])
            )
            votes.append(vote)

        return votes

    def _analyze_dissent(self, votes: List[CriticVote]) -> DissentAnalysis:
        """
        Analyze disagreement among critics.

        Args:
            votes: List of critic votes

        Returns:
            DissentAnalysis with dissent metrics
        """
        if not votes:
            return DissentAnalysis(
                dissent_index=0.0,
                majority_verdict="review",
                minority_verdicts=[],
                split_ratio="0:0:0",
                disagreement_type="unanimous"
            )

        # Count verdicts
        verdict_counts: Dict[str, int] = {}
        for vote in votes:
            verdict = vote.verdict
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        # Find majority and minority
        sorted_verdicts = sorted(
            verdict_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        majority_verdict = sorted_verdicts[0][0]
        majority_count = sorted_verdicts[0][1]
        minority_verdicts = [v for v, _ in sorted_verdicts[1:]]

        # Calculate dissent index
        dissent_index = self._calculate_dissent_index(verdict_counts, len(votes))

        # Determine disagreement type
        disagreement_type = self._classify_disagreement(
            verdict_counts,
            len(votes)
        )

        # Build split ratio
        split_ratio = ":".join(str(count) for _, count in sorted_verdicts)

        reasoning_divergence = self._calculate_reasoning_divergence(votes)
        conflicting_principles = self._identify_conflicts(votes)
        summary = self._summarize_dissent(
            majority_verdict=majority_verdict,
            verdict_counts=verdict_counts,
            reasoning_divergence=reasoning_divergence,
        )

        return DissentAnalysis(
            dissent_index=dissent_index,
            majority_verdict=majority_verdict,
            minority_verdicts=minority_verdicts,
            split_ratio=split_ratio,
            disagreement_type=disagreement_type,
            conflicting_principles=conflicting_principles,
            reasoning_divergence=reasoning_divergence,
            summary=summary,
        )

    def _calculate_dissent_index(
        self,
        verdict_counts: Dict[str, int],
        total_votes: int
    ) -> float:
        """
        Calculate dissent index (0.0 = unanimous, 1.0 = maximum disagreement).

        Uses normalized entropy:
        - Unanimous: entropy = 0
        - Maximum disagreement (equal split): entropy = log(n)
        - Normalized: dissent_index = entropy / log(n)

        Args:
            verdict_counts: Dict mapping verdict to count
            total_votes: Total number of votes

        Returns:
            Dissent index between 0.0 and 1.0
        """
        if total_votes <= 1 or len(verdict_counts) == 1:
            return 0.0

        # Calculate entropy
        import math
        entropy = 0.0
        for count in verdict_counts.values():
            if count > 0:
                p = count / total_votes
                entropy -= p * math.log2(p)

        # Normalize by maximum entropy
        max_entropy = math.log2(min(total_votes, 3))  # Max 3 verdict types

        if max_entropy == 0:
            return 0.0

        dissent_index = entropy / max_entropy

        return min(1.0, max(0.0, dissent_index))

    def _classify_disagreement(
        self,
        verdict_counts: Dict[str, int],
        total_votes: int
    ) -> str:
        """
        Classify type of disagreement.

        Args:
            verdict_counts: Dict mapping verdict to count
            total_votes: Total number of votes

        Returns:
            Disagreement classification
        """
        if len(verdict_counts) == 1:
            return "unanimous"

        sorted_counts = sorted(verdict_counts.values(), reverse=True)
        majority_count = sorted_counts[0]
        majority_ratio = majority_count / total_votes

        if majority_ratio >= 0.8:
            return "strong_majority"
        elif majority_ratio >= 0.6:
            return "majority"
        elif len(verdict_counts) >= 3 and sorted_counts[0] == sorted_counts[1]:
            return "deadlock"
        else:
            return "split"

    def _identify_conflicts(self, votes: List[CriticVote]) -> List[str]:
        """
        Identify conflicting principles from critic reasoning.

        Args:
            votes: List of critic votes

        Returns:
            List of conflicting principle names
        """
        # Extract all critical factors
        all_factors = set()
        for vote in votes:
            all_factors.update(vote.critical_factors)

        # For now, return factors that appear in both allowed and blocked votes
        allowed_factors = set()
        blocked_factors = set()

        for vote in votes:
            if vote.verdict == "allowed":
                allowed_factors.update(vote.critical_factors)
            elif vote.verdict == "blocked":
                blocked_factors.update(vote.critical_factors)

        # Conflicting factors appear in both verdicts
        conflicts = allowed_factors.intersection(blocked_factors)

        return sorted(list(conflicts))

    def _calculate_reasoning_divergence(self, votes: List[CriticVote]) -> float:
        """Approximate divergence in critic reasoning using Jaccard distance."""
        if len(votes) <= 1:
            return 0.0

        if len({v.verdict for v in votes}) == 1:
            return 0.0

        token_sets = [set(v.reasoning.lower().split()) for v in votes]
        distances: List[float] = []

        for i, tokens_a in enumerate(token_sets):
            for tokens_b in token_sets[i + 1 :]:
                if not tokens_a and not tokens_b:
                    distances.append(0.0)
                    continue
                intersection = len(tokens_a.intersection(tokens_b))
                union = len(tokens_a.union(tokens_b)) or 1
                distances.append(1.0 - (intersection / union))

        if not distances:
            return 0.0

        divergence = sum(distances) / len(distances)
        return max(0.0, min(divergence, 1.0))

    def _summarize_dissent(
        self,
        majority_verdict: str,
        verdict_counts: Dict[str, int],
        reasoning_divergence: float,
    ) -> str:
        """Human readable dissent summary for dashboards and reviewers."""
        counts = ", ".join(f"{v}:{c}" for v, c in verdict_counts.items())
        divergence_label = "aligned" if reasoning_divergence < 0.25 else "divergent"
        return (
            f"Majority verdict {majority_verdict} with distribution {counts}; "
            f"critic reasoning appears {divergence_label}"
        )

    def _assess_rights_impact(
        self, input_data: Dict[str, Any], votes: List[CriticVote]
    ) -> List[Dict[str, Any]]:
        """Derive rights impact flags from critic factors and context."""
        rights_map = {
            "privacy": "Privacy and Data Protection",
            "autonomy": "Autonomy and Agency",
            "safety": "Safety and Bodily Integrity",
            "fairness": "Fairness and Non-discrimination",
            "transparency": "Transparency and Accountability",
            "legal_compliance": "Legal and Regulatory Compliance",
        }

        impacts: Dict[str, Dict[str, Any]] = {}
        safety_critical = input_data.get("context", {}).get("safety_critical", False)

        for vote in votes:
            severity = "high" if vote.verdict == "blocked" else "medium"
            if safety_critical:
                severity = "critical"

            for factor in vote.critical_factors:
                normalized = factor.lower().replace(" ", "_")
                right_name = rights_map.get(normalized)
                if not right_name:
                    continue

                impact = impacts.setdefault(
                    right_name,
                    {
                        "right": right_name,
                        "severity": severity,
                        "sources": set(),
                        "notes": set(),
                    },
                )
                impact["severity"] = max(impact["severity"], severity, key=self._severity_rank)
                impact["sources"].add(vote.critic_name)
                impact["notes"].add(vote.reasoning[:200])

        results = []
        for impact in impacts.values():
            results.append(
                {
                    "right": impact["right"],
                    "severity": impact["severity"],
                    "sources": sorted(impact["sources"]),
                    "notes": sorted(impact["notes"]),
                }
            )
        return sorted(results, key=lambda i: self._severity_rank(i["severity"]), reverse=True)

    def _build_review_checklist(
        self, dissent: DissentAnalysis, rights_impact: List[Dict[str, Any]]
    ) -> List[str]:
        """Provide a short checklist reviewers can follow during triage."""
        checklist = ["Confirm majority reasoning and dissent rationale"]

        if dissent.reasoning_divergence >= 0.5:
            checklist.append("Capture why critic justifications differ materially")
        if rights_impact:
            top_right = rights_impact[0]
            checklist.append(
                f"Validate mitigation for {top_right['right']} (severity: {top_right['severity']})"
            )
        if dissent.conflicting_principles:
            checklist.append(
                "Document how conflicting principles were prioritized: "
                + ", ".join(sorted(dissent.conflicting_principles))
            )

        return checklist

    @staticmethod
    def _severity_rank(severity: str) -> int:
        order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        return order.get(severity, 1)

    def _find_similar_precedents(
        self,
        input_data: Dict,
        top_k: int = 5
    ) -> List[SimilarCase]:
        """
        Find similar precedents for context.

        Args:
            input_data: Input data with prompt and context
            top_k: Number of similar cases to return

        Returns:
            List of similar cases
        """
        if not self.precedent_search:
            return []

        try:
            # Search for similar precedents
            results = self.precedent_search.search(
                input_data,
                top_k=top_k,
                min_similarity=0.7
            )

            # Convert to SimilarCase format
            similar_cases = []
            for result in results:
                precedent = result.precedent
                case = SimilarCase(
                    precedent_id=result.precedent_id,
                    similarity_score=result.similarity_score,
                    verdict=precedent.get("outcome", {}).get("verdict", "unknown"),
                    context=precedent.get("input_data", {}).get("prompt", ""),
                    resolution_notes=precedent.get("outcome", {}).get("justification")
                )
                similar_cases.append(case)

            return similar_cases
        except Exception as e:
            logger.error(f"Failed to find similar precedents: {e}")
            return []

    def _generate_explanation(
        self,
        input_data: Dict,
        votes: List[CriticVote],
        dissent: DissentAnalysis
    ) -> str:
        """
        Generate explanation summary for the bundle.

        Args:
            input_data: Input data
            votes: Critic votes
            dissent: Dissent analysis

        Returns:
            Summary explanation string
        """
        if self.explainer:
            try:
                # Use explainer if available
                return self.explainer.generate_summary(input_data, votes, dissent)
            except Exception as e:
                logger.error(f"Explainer failed: {e}")

        # Fallback: Generate simple summary
        prompt = input_data.get("prompt", "")[:100]
        summary_parts = [
            f"Case requires human review due to {dissent.disagreement_type} among critics.",
            f"Vote split: {dissent.split_ratio} ({dissent.majority_verdict} majority).",
            f"Dissent index: {dissent.dissent_index:.2f}.",
        ]

        if dissent.conflicting_principles:
            conflicts_str = ", ".join(dissent.conflicting_principles[:3])
            summary_parts.append(f"Conflicting principles: {conflicts_str}.")

        summary_parts.append(f"Prompt: {prompt}...")

        return " ".join(summary_parts)

    def _determine_priority(
        self,
        dissent: DissentAnalysis,
        input_data: Dict,
        rights_impact: List[Dict[str, Any]],
    ) -> str:
        """
        Determine review priority based on dissent and context.

        Args:
            dissent: Dissent analysis
            input_data: Input data

        Returns:
            Priority level: "critical", "high", "medium", "low"
        """
        # Critical: high dissent + high-stakes context
        context = input_data.get("context", {})
        is_high_stakes = (
            context.get("privacy_sensitive", False) or
            context.get("safety_critical", False) or
            context.get("legal_risk", False)
        )

        has_critical_rights = any(
            impact.get("severity") == "critical" for impact in rights_impact
        )

        if (dissent.dissent_index >= 0.8 and is_high_stakes) or has_critical_rights:
            return "critical"
        elif dissent.dissent_index >= 0.7 or is_high_stakes:
            return "high"
        elif dissent.dissent_index >= 0.4:
            return "medium"
        else:
            return "low"

    def _generate_bundle_id(self, case_id: str) -> str:
        """Generate unique bundle ID from case ID."""
        timestamp = datetime.utcnow().isoformat()
        combined = f"{case_id}:{timestamp}"
        hash_digest = hashlib.sha256(combined.encode()).hexdigest()
        return f"bundle_{hash_digest[:16]}"
