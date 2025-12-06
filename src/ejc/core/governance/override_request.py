"""
Override Request Model - Task 7.1

Defines Pydantic models for human override requests in the governance system.

Provides structured, validated data models for:
- Override requests with reviewer information
- Proposed override outcomes
- Justification and reasoning
- Metadata and audit trail

All models include comprehensive schema validation using Pydantic.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator
import uuid


class OverrideOutcome(str, Enum):
    """
    Proposed override outcomes.

    Valid values for what the reviewer wants to change the decision to.
    """
    ALLOW = "ALLOW"
    DENY = "DENY"
    REVIEW = "REVIEW"
    ESCALATE = "ESCALATE"


class OverrideReason(str, Enum):
    """
    Categorized reasons for override requests.

    Helps classify and analyze override patterns.
    """
    TECHNICAL_ERROR = "technical_error"
    MISSING_CONTEXT = "missing_context"
    POLICY_EXCEPTION = "policy_exception"
    RISK_ASSESSMENT = "risk_assessment"
    ETHICAL_CONCERN = "ethical_concern"
    PRECEDENT_BASED = "precedent_based"
    STAKEHOLDER_INPUT = "stakeholder_input"
    EMERGENCY = "emergency"
    OTHER = "other"


class ReviewerRole(str, Enum):
    """
    Roles of reviewers who can submit override requests.

    Defines authorization levels for oversight.
    """
    SENIOR_REVIEWER = "senior_reviewer"
    ETHICS_OFFICER = "ethics_officer"
    LEGAL_COUNSEL = "legal_counsel"
    TECHNICAL_LEAD = "technical_lead"
    GOVERNANCE_BOARD = "governance_board"
    AUDITOR = "auditor"
    SYSTEM_ADMINISTRATOR = "system_administrator"


class OverrideRequest(BaseModel):
    """
    Override request model for human reviewers.

    Task 7.1 Requirements:
    - Reviewer ID: Identifies the reviewer making the request
    - Justification: Human-readable explanation for the override
    - Proposed override outcome: The decision the reviewer wants

    Additional fields for completeness and auditability:
    - Request metadata (ID, timestamp, etc.)
    - Decision reference (what decision is being overridden)
    - Categorized reason
    - Reviewer role and credentials
    """

    # Core Task 7.1 Fields
    reviewer_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique identifier of the reviewer submitting the override request"
    )

    justification: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Human-readable explanation for why the override is needed"
    )

    proposed_outcome: OverrideOutcome = Field(
        ...,
        description="The decision outcome the reviewer is proposing"
    )

    # Request Metadata
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this override request"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the override request was created"
    )

    # Decision Reference
    decision_id: str = Field(
        ...,
        min_length=1,
        description="ID of the decision being overridden"
    )

    original_outcome: Optional[str] = Field(
        None,
        pattern="^(ALLOW|DENY|REVIEW|ESCALATE)$",
        description="The original decision outcome before override"
    )

    # Categorization
    reason_category: OverrideReason = Field(
        default=OverrideReason.OTHER,
        description="Categorized reason for the override"
    )

    # Reviewer Information
    reviewer_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Human-readable name of the reviewer"
    )

    reviewer_role: ReviewerRole = Field(
        ...,
        description="Role/authority level of the reviewer"
    )

    reviewer_email: Optional[str] = Field(
        None,
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        description="Email address of the reviewer for audit trail"
    )

    # Additional Context
    additional_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context or metadata for the override"
    )

    supporting_documents: List[str] = Field(
        default_factory=list,
        description="References to supporting documents (URLs, file paths, etc.)"
    )

    stakeholder_input: Optional[str] = Field(
        None,
        max_length=5000,
        description="Input from stakeholders that influenced this override"
    )

    # Urgency and Priority
    is_urgent: bool = Field(
        default=False,
        description="Whether this override request is urgent/emergency"
    )

    priority: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Priority level (0=normal, 10=critical)"
    )

    # Expiration
    expires_at: Optional[datetime] = Field(
        None,
        description="Optional expiration time for this override request"
    )

    @field_validator('justification')
    @classmethod
    def validate_justification_content(cls, v: str) -> str:
        """
        Validate that justification contains meaningful content.

        Ensures the justification is not just whitespace or placeholder text.
        """
        stripped = v.strip()
        if not stripped:
            raise ValueError("Justification cannot be empty or whitespace only")

        # Check for placeholder text
        placeholder_phrases = [
            "todo",
            "tbd",
            "to be determined",
            "fill this out",
            "placeholder"
        ]
        lower_just = stripped.lower()
        if any(phrase in lower_just for phrase in placeholder_phrases) and len(stripped) < 50:
            raise ValueError("Justification appears to be placeholder text. Please provide a real explanation.")

        return stripped

    @model_validator(mode='after')
    def validate_expiration(self) -> 'OverrideRequest':
        """
        Validate that expiration time is in the future if set.
        """
        if self.expires_at is not None:
            if self.expires_at <= self.timestamp:
                raise ValueError("Expiration time must be in the future")

        return self

    @model_validator(mode='after')
    def validate_outcome_change(self) -> 'OverrideRequest':
        """
        Validate that proposed outcome is different from original if original is provided.
        """
        if self.original_outcome is not None:
            if self.proposed_outcome.value == self.original_outcome:
                raise ValueError(
                    f"Proposed outcome ({self.proposed_outcome.value}) must be different "
                    f"from original outcome ({self.original_outcome})"
                )

        return self

    def is_expired(self) -> bool:
        """Check if this override request has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at

    def is_emergency(self) -> bool:
        """Check if this is an emergency override."""
        return self.is_urgent or self.reason_category == OverrideReason.EMERGENCY

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            'request_id': self.request_id,
            'reviewer_id': self.reviewer_id,
            'reviewer_name': self.reviewer_name,
            'reviewer_role': self.reviewer_role.value,
            'reviewer_email': self.reviewer_email,
            'decision_id': self.decision_id,
            'original_outcome': self.original_outcome,
            'proposed_outcome': self.proposed_outcome.value,
            'justification': self.justification,
            'reason_category': self.reason_category.value,
            'timestamp': self.timestamp.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_urgent': self.is_urgent,
            'priority': self.priority,
            'additional_context': self.additional_context,
            'supporting_documents': self.supporting_documents,
            'stakeholder_input': self.stakeholder_input
        }

    def get_summary(self) -> str:
        """
        Get a human-readable summary of this override request.

        Returns:
            One-line summary string
        """
        return (
            f"Override request {self.request_id[:8]} by {self.reviewer_name or self.reviewer_id} "
            f"({self.reviewer_role.value}): {self.original_outcome or '?'} → {self.proposed_outcome.value} "
            f"for decision {self.decision_id[:8]} - {self.reason_category.value}"
        )

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "reviewer_id": "reviewer_12345",
                "reviewer_name": "Dr. Jane Smith",
                "reviewer_role": "ethics_officer",
                "reviewer_email": "jane.smith@organization.org",
                "decision_id": "decision_67890",
                "original_outcome": "DENY",
                "proposed_outcome": "ALLOW",
                "justification": "After careful ethical review and stakeholder consultation, "
                               "the original denial was based on incomplete context. The specific "
                               "use case falls under our exception policy for educational purposes.",
                "reason_category": "policy_exception",
                "is_urgent": False,
                "priority": 5
            }
        }


class OverrideRequestBatch(BaseModel):
    """
    Batch of override requests for bulk processing.

    Useful for processing multiple related override requests together.
    """
    batch_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this batch"
    )

    requests: List[OverrideRequest] = Field(
        ...,
        min_length=1,
        description="List of override requests in this batch"
    )

    batch_submitted_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the batch was submitted"
    )

    batch_submitted_by: str = Field(
        ...,
        description="Who submitted this batch"
    )

    def get_request_count(self) -> int:
        """Get the number of requests in this batch."""
        return len(self.requests)

    def get_urgent_count(self) -> int:
        """Get the number of urgent requests in this batch."""
        return sum(1 for req in self.requests if req.is_urgent)


# Export all models
__all__ = [
    'OverrideRequest',
    'OverrideOutcome',
    'OverrideReason',
    'ReviewerRole',
    'OverrideRequestBatch'
]
