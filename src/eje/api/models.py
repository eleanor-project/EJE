"""Pydantic schemas for the Moral Ops Center FastAPI layer."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# REQUEST MODELS (Task 10.2: Strict Validation)
# ============================================================================

class EvaluationRequest(BaseModel):
    """Incoming request to evaluate a prompt with optional context."""
    
    model_config = ConfigDict(strict=True, extra="forbid")

    prompt: str = Field(..., min_length=1, max_length=50000, description="The prompt text to evaluate")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for evaluation")
    case_id: Optional[str] = Field(None, max_length=255, description="Optional case identifier")
    require_human_review: bool = Field(False, description="Whether to require human review")
    
    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Ensure prompt is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Prompt cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, v: Optional[str]) -> Optional[str]:
        """Ensure case_id is valid if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError("Case ID cannot be empty or whitespace only")
            return v.strip()
        return v


class EscalationRequest(BaseModel):
    """Manual escalation body."""
    
    model_config = ConfigDict(strict=True, extra="forbid")

    case_id: str = Field(..., min_length=1, max_length=255, description="Case identifier")
    reason: str = Field(..., min_length=1, max_length=5000, description="Reason for escalation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator("case_id", "reason")
    @classmethod
    def validate_not_whitespace(cls, v: str) -> str:
        """Ensure string fields are not just whitespace."""
        if not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()


# ============================================================================
# CORE RESPONSE MODELS (Task 10.3: DecisionOutput, EvidenceBundle, etc.)
# ============================================================================

class CriticReport(BaseModel):
    """Normalized critic output included in responses."""
    
    model_config = ConfigDict(strict=True)

    critic: str = Field(..., min_length=1, description="Name of the critic")
    verdict: str = Field(..., min_length=1, description="Critic's verdict")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    justification: str = Field(..., min_length=1, description="Reasoning for the verdict")
    execution_time_ms: float = Field(0.0, ge=0.0, description="Execution time in milliseconds")


class EvidenceBundle(BaseModel):
    """Evidence bundle containing critic reports and aggregation metadata."""
    
    model_config = ConfigDict(strict=True)
    
    critic_reports: List[CriticReport] = Field(..., description="Individual critic evaluations")
    aggregation_method: str = Field(..., description="Method used to aggregate critic outputs")
    total_critics: int = Field(..., ge=0, description="Total number of critics evaluated")
    successful_critics: int = Field(..., ge=0, description="Number of critics that completed successfully")
    failed_critics: int = Field(0, ge=0, description="Number of critics that failed")
    error_rate: float = Field(0.0, ge=0.0, le=1.0, description="Rate of critic failures")


class PrecedentBundle(BaseModel):
    """Bundle of precedents consulted during decision-making."""
    
    model_config = ConfigDict(strict=True)
    
    precedent_ids: List[str] = Field(..., description="IDs of precedents consulted")
    count: int = Field(..., ge=0, description="Number of precedents used")
    relevance_scores: Optional[List[float]] = Field(None, description="Relevance scores for each precedent")


class DecisionOutput(BaseModel):
    """Complete decision output from the adjudication pipeline (Task 10.3)."""
    
    model_config = ConfigDict(strict=True)

    case_id: str = Field(..., min_length=1, description="Unique identifier for this decision")
    verdict: str = Field(..., min_length=1, description="Final verdict")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level of the decision")
    escalated: bool = Field(..., description="Whether this case was escalated for human review")
    timestamp: datetime = Field(..., description="When the decision was made")
    evidence: EvidenceBundle = Field(..., description="Evidence supporting the decision")
    precedents: PrecedentBundle = Field(..., description="Precedents consulted")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional decision metadata")


class DecisionResponse(BaseModel):
    """Response wrapper for /decision endpoint."""
    
    model_config = ConfigDict(strict=True)
    
    decision: DecisionOutput = Field(..., description="Complete decision output")


# ============================================================================
# LEGACY/COMPATIBILITY MODELS
# ============================================================================

class CaseResult(BaseModel):
    """Aggregated decision payload (legacy format for backward compatibility)."""
    
    model_config = ConfigDict(strict=True)

    case_id: str = Field(..., min_length=1)
    verdict: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    escalated: bool
    precedents: List[str] = Field(default_factory=list)
    timestamp: datetime
    critic_reports: List[CriticReport] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    """Wrapper response for /evaluate endpoint (legacy)."""
    
    model_config = ConfigDict(strict=True)

    result: CaseResult


# ============================================================================
# PRECEDENT MODELS (Task 10.1: GET /precedents)
# ============================================================================

class PrecedentRecord(BaseModel):
    """Single precedent record from the database."""
    
    model_config = ConfigDict(strict=True)

    case_id: str
    prompt: str
    verdict: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    escalated: bool
    precedents: List[str] = Field(default_factory=list)
    critic_reports: List[CriticReport] = Field(default_factory=list)
    created_at: datetime


class PrecedentsResponse(BaseModel):
    """Response model for GET /precedents."""
    
    model_config = ConfigDict(strict=True)

    precedents: List[PrecedentRecord] = Field(..., description="List of precedent records")
    count: int = Field(..., ge=0, description="Number of precedents returned")


# ============================================================================
# CRITIC MODELS (Task 10.1: GET /critics)
# ============================================================================

class CriticInfo(BaseModel):
    """Information about a configured critic."""
    
    model_config = ConfigDict(strict=True)

    name: str = Field(..., min_length=1, description="Critic name")
    type: str = Field(..., min_length=1, description="Critic type")
    enabled: bool = Field(True, description="Whether the critic is enabled")
    weight: Optional[float] = Field(None, ge=0.0, description="Critic weight in aggregation")
    description: Optional[str] = Field(None, description="Critic description")


class CriticsResponse(BaseModel):
    """Response model for GET /critics."""
    
    model_config = ConfigDict(strict=True)

    critics: List[CriticInfo] = Field(..., description="List of configured critics")
    count: int = Field(..., ge=0, description="Number of critics")


# ============================================================================
# ESCALATION MODELS
# ============================================================================

class EscalationResponse(BaseModel):
    """Acknowledgement for escalations."""
    
    model_config = ConfigDict(strict=True)

    case_id: str
    recorded: bool
    reason: str
    timestamp: datetime


# ============================================================================
# HEALTH CHECK MODELS (Task 10.3: HealthCheck)
# ============================================================================

class HealthCheck(BaseModel):
    """Complete health check response with component status (Task 10.3)."""
    
    model_config = ConfigDict(strict=True)

    status: str = Field(..., pattern="^(ok|degraded|error)$", description="Overall system status")
    components: Dict[str, str] = Field(..., description="Status of individual components")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="Time of health check")
    error_rate: float = Field(0.0, ge=0.0, le=1.0, description="Recent error rate")
    uptime_seconds: Optional[float] = Field(None, ge=0.0, description="System uptime in seconds")


class HealthResponse(BaseModel):
    """Service health report (alias for HealthCheck)."""
    
    model_config = ConfigDict(strict=True)

    status: str = Field(..., pattern="^(ok|degraded|error)$")
    components: Dict[str, str]
    version: str
    timestamp: datetime
    error_rate: float = Field(0.0, ge=0.0, le=1.0)


# ============================================================================
# VALIDATION ERROR MODELS (Task 10.2)
# ============================================================================

class ValidationErrorDetail(BaseModel):
    """Detailed validation error."""
    
    model_config = ConfigDict(strict=True)
    
    field: str = Field(..., description="Field path that failed validation")
    message: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(BaseModel):
    """Response for validation errors."""
    
    model_config = ConfigDict(strict=True)
    
    detail: str = Field("Validation error", description="Error summary")
    errors: List[ValidationErrorDetail] = Field(..., description="List of validation errors")
