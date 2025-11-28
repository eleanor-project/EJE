"""
Templated feedback forms for human reviewers.

Provides structured feedback collection with validation, optional fields,
and integration with ground truth system for calibration.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Type of feedback being provided."""

    VERDICT_CORRECTION = "verdict_correction"  # Correcting critic verdict
    REASONING_ENHANCEMENT = "reasoning_enhancement"  # Adding context
    PRINCIPLE_CLARIFICATION = "principle_clarification"  # Clarifying application
    NEW_PRECEDENT = "new_precedent"  # Establishing new precedent
    EDGE_CASE = "edge_case"  # Identifying edge case


class VerdictOption(Enum):
    """Standardized verdict options."""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    CONDITIONAL = "conditional"  # Allowed with conditions
    DEFER = "defer"  # Defer to higher authority


@dataclass
class FeedbackQuestion:
    """Single question in feedback form."""

    question_id: str
    question_text: str
    question_type: str  # "multiple_choice", "text", "rating", "boolean"
    required: bool = True
    options: Optional[List[str]] = None  # For multiple choice
    help_text: Optional[str] = None


@dataclass
class FeedbackResponse:
    """Response to a feedback question."""

    question_id: str
    response: Any
    confidence: Optional[float] = None  # Optional confidence rating


@dataclass
class ReviewFeedback:
    """
    Complete feedback from human reviewer.

    Includes verdict, confidence, reasoning, and optional structured responses.
    """

    bundle_id: str
    reviewer_id: str
    verdict: VerdictOption
    confidence: float  # 0.0 to 1.0
    reasoning: str
    feedback_type: FeedbackType
    responses: List[FeedbackResponse] = field(default_factory=list)
    conditions: Optional[str] = None  # For conditional verdicts
    principles_applied: List[str] = field(default_factory=list)
    override_critics: bool = False  # Whether this overrides critic consensus
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeedbackFormBuilder:
    """
    Builds templated feedback forms for different review scenarios.

    Generates context-aware questions based on:
    - Dissent analysis (high dissent = more detailed questions)
    - Input context (privacy-sensitive = additional privacy questions)
    - Precedent similarity (similar cases = ask about consistency)
    """

    def __init__(self):
        """Initialize feedback form builder."""
        self.base_questions = self._create_base_questions()

    def _create_base_questions(self) -> List[FeedbackQuestion]:
        """Create base questions for all feedback forms."""
        return [
            FeedbackQuestion(
                question_id="verdict",
                question_text="What is your verdict for this case?",
                question_type="multiple_choice",
                required=True,
                options=["allowed", "blocked", "conditional", "defer"],
                help_text="Select the most appropriate verdict based on applicable principles"
            ),
            FeedbackQuestion(
                question_id="confidence",
                question_text="How confident are you in this verdict?",
                question_type="rating",
                required=True,
                help_text="Rate from 0.0 (not confident) to 1.0 (very confident)"
            ),
            FeedbackQuestion(
                question_id="reasoning",
                question_text="Please explain your reasoning",
                question_type="text",
                required=True,
                help_text="Describe why this verdict is appropriate, referencing specific principles"
            ),
            FeedbackQuestion(
                question_id="principles_applied",
                question_text="Which principles did you apply?",
                question_type="multiple_choice",
                required=False,
                options=[
                    "Privacy Protection",
                    "User Autonomy",
                    "Harm Prevention",
                    "Transparency",
                    "Fairness",
                    "Accountability",
                    "Legal Compliance",
                    "Beneficence",
                    "Other"
                ],
                help_text="Select all that apply"
            )
        ]

    def build_form(
        self,
        bundle_id: str,
        dissent_analysis: Optional[Any] = None,
        input_context: Optional[Dict] = None,
        similar_precedents: Optional[List] = None
    ) -> List[FeedbackQuestion]:
        """
        Build feedback form tailored to the case.

        Args:
            bundle_id: Escalation bundle ID
            dissent_analysis: Optional dissent analysis
            input_context: Optional input context
            similar_precedents: Optional similar precedents

        Returns:
            List of feedback questions
        """
        questions = self.base_questions.copy()

        # Add dissent-specific questions
        if dissent_analysis and dissent_analysis.dissent_index > 0.5:
            questions.append(FeedbackQuestion(
                question_id="critic_disagreement",
                question_text="Why do you think the critics disagreed on this case?",
                question_type="text",
                required=False,
                help_text="Understanding disagreement helps improve critic calibration"
            ))

            if dissent_analysis.conflicting_principles:
                questions.append(FeedbackQuestion(
                    question_id="principle_priority",
                    question_text="Which principle should take priority in this case?",
                    question_type="multiple_choice",
                    required=False,
                    options=dissent_analysis.conflicting_principles,
                    help_text="Help establish precedent for principle prioritization"
                ))

        # Add context-specific questions
        if input_context:
            if input_context.get("privacy_sensitive"):
                questions.append(FeedbackQuestion(
                    question_id="privacy_assessment",
                    question_text="How severe is the privacy risk in this case?",
                    question_type="multiple_choice",
                    required=False,
                    options=["minimal", "low", "moderate", "high", "critical"],
                    help_text="Assess privacy impact for precedent classification"
                ))

            if input_context.get("safety_critical"):
                questions.append(FeedbackQuestion(
                    question_id="safety_assessment",
                    question_text="What safety risks are present?",
                    question_type="text",
                    required=False,
                    help_text="Describe potential safety concerns"
                ))

            if input_context.get("jurisdiction"):
                questions.append(FeedbackQuestion(
                    question_id="jurisdiction_compliance",
                    question_text=f"Does this verdict comply with {input_context['jurisdiction']} regulations?",
                    question_type="boolean",
                    required=False,
                    help_text="Verify regulatory compliance"
                ))

        # Add precedent-specific questions
        if similar_precedents and len(similar_precedents) > 0:
            questions.append(FeedbackQuestion(
                question_id="precedent_consistency",
                question_text="Is your verdict consistent with similar precedents?",
                question_type="boolean",
                required=False,
                help_text="Ensure consistency in precedent application"
            ))

            questions.append(FeedbackQuestion(
                question_id="precedent_differences",
                question_text="If inconsistent, what makes this case different?",
                question_type="text",
                required=False,
                help_text="Explain how this case differs from similar precedents"
            ))

        # Add conditional verdict questions
        questions.append(FeedbackQuestion(
            question_id="conditions",
            question_text="If conditional, what conditions must be met?",
            question_type="text",
            required=False,
            help_text="Specify conditions for approval (only for conditional verdicts)"
        ))

        # Add new precedent question
        questions.append(FeedbackQuestion(
            question_id="new_precedent",
            question_text="Should this case establish a new precedent?",
            question_type="boolean",
            required=False,
            help_text="Mark if this case represents a novel situation requiring precedent"
        ))

        return questions

    def validate_feedback(
        self,
        feedback: ReviewFeedback,
        form_questions: List[FeedbackQuestion]
    ) -> tuple[bool, List[str]]:
        """
        Validate feedback against form requirements.

        Args:
            feedback: Review feedback to validate
            form_questions: Questions from the form

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check required questions answered
        # Note: verdict, confidence, reasoning are validated separately as direct fields
        response_ids = {r.question_id for r in feedback.responses}
        core_fields = {"verdict", "confidence", "reasoning", "principles_applied", "conditions"}

        for question in form_questions:
            if question.required and question.question_id not in core_fields:
                if question.question_id not in response_ids:
                    errors.append(f"Required question '{question.question_id}' not answered")

        # Validate verdict
        if feedback.verdict not in VerdictOption:
            errors.append(f"Invalid verdict: {feedback.verdict}")

        # Validate confidence
        if not (0.0 <= feedback.confidence <= 1.0):
            errors.append(f"Confidence must be between 0.0 and 1.0, got {feedback.confidence}")

        # Validate reasoning
        if not feedback.reasoning or len(feedback.reasoning.strip()) < 10:
            errors.append("Reasoning must be at least 10 characters")

        # Validate conditional verdict
        if feedback.verdict == VerdictOption.CONDITIONAL:
            if not feedback.conditions:
                errors.append("Conditional verdict requires conditions to be specified")

        # Validate response types
        for response in feedback.responses:
            question = next(
                (q for q in form_questions if q.question_id == response.question_id),
                None
            )
            if question:
                if question.question_type == "rating":
                    if not isinstance(response.response, (int, float)):
                        errors.append(
                            f"Question '{question.question_id}' expects numeric rating"
                        )
                elif question.question_type == "boolean":
                    if not isinstance(response.response, bool):
                        errors.append(
                            f"Question '{question.question_id}' expects boolean response"
                        )

        is_valid = len(errors) == 0
        return is_valid, errors

    def create_feedback_from_responses(
        self,
        bundle_id: str,
        reviewer_id: str,
        responses: Dict[str, Any],
        feedback_type: FeedbackType = FeedbackType.VERDICT_CORRECTION
    ) -> ReviewFeedback:
        """
        Create ReviewFeedback object from response dictionary.

        Args:
            bundle_id: Escalation bundle ID
            reviewer_id: Reviewer identifier
            responses: Dict mapping question_id to response
            feedback_type: Type of feedback

        Returns:
            ReviewFeedback object

        Raises:
            ValueError: If required fields missing
        """
        # Extract required fields
        verdict_str = responses.get("verdict")
        if not verdict_str:
            raise ValueError("Verdict is required")

        try:
            verdict = VerdictOption(verdict_str)
        except ValueError:
            raise ValueError(f"Invalid verdict: {verdict_str}")

        confidence = responses.get("confidence")
        if confidence is None:
            raise ValueError("Confidence is required")

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid confidence: {confidence}")

        reasoning = responses.get("reasoning", "")
        if not reasoning:
            raise ValueError("Reasoning is required")

        # Extract optional fields
        conditions = responses.get("conditions")
        principles = responses.get("principles_applied", [])
        if isinstance(principles, str):
            principles = [p.strip() for p in principles.split(",")]

        # Build feedback responses
        feedback_responses = []
        for question_id, response in responses.items():
            if question_id not in ["verdict", "confidence", "reasoning", "conditions", "principles_applied"]:
                feedback_responses.append(FeedbackResponse(
                    question_id=question_id,
                    response=response
                ))

        return ReviewFeedback(
            bundle_id=bundle_id,
            reviewer_id=reviewer_id,
            verdict=verdict,
            confidence=confidence,
            reasoning=reasoning,
            feedback_type=feedback_type,
            responses=feedback_responses,
            conditions=conditions,
            principles_applied=principles,
            metadata={
                "total_questions": len(responses),
                "generated_at": datetime.utcnow().isoformat()
            }
        )


class FeedbackAggregator:
    """
    Aggregates feedback from multiple reviewers.

    Handles consensus building, conflict resolution, and precedent creation.
    """

    def aggregate_reviews(
        self,
        feedbacks: List[ReviewFeedback]
    ) -> Dict[str, Any]:
        """
        Aggregate multiple reviews into consensus.

        Args:
            feedbacks: List of review feedbacks

        Returns:
            Aggregated result with consensus verdict and confidence
        """
        if not feedbacks:
            return {
                "consensus_verdict": None,
                "consensus_confidence": 0.0,
                "agreement_level": "none",
                "reviews": []
            }

        # Count verdicts
        verdict_counts: Dict[str, int] = {}
        total_confidence = 0.0

        for feedback in feedbacks:
            verdict_str = feedback.verdict.value
            verdict_counts[verdict_str] = verdict_counts.get(verdict_str, 0) + 1
            total_confidence += feedback.confidence

        # Find consensus
        sorted_verdicts = sorted(
            verdict_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        consensus_verdict = sorted_verdicts[0][0]
        consensus_count = sorted_verdicts[0][1]
        agreement_ratio = consensus_count / len(feedbacks)

        # Classify agreement
        if agreement_ratio == 1.0:
            agreement_level = "unanimous"
        elif agreement_ratio >= 0.75:
            agreement_level = "strong_consensus"
        elif agreement_ratio >= 0.5:
            agreement_level = "majority"
        else:
            agreement_level = "split"

        # Average confidence
        avg_confidence = total_confidence / len(feedbacks)

        return {
            "consensus_verdict": consensus_verdict,
            "consensus_confidence": avg_confidence,
            "agreement_level": agreement_level,
            "vote_distribution": verdict_counts,
            "num_reviewers": len(feedbacks),
            "reviews": [
                {
                    "reviewer_id": f.reviewer_id,
                    "verdict": f.verdict.value,
                    "confidence": f.confidence,
                    "reasoning": f.reasoning
                }
                for f in feedbacks
            ]
        }
