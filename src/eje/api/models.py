"""Pydantic schemas for the Moral Ops Center FastAPI layer."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


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


class CriticReport(BaseModel):
    """Normalized critic output included in responses."""
    
    model_config = ConfigDict(strict=True)

    critic: str = Field(..., min_length=1)
    verdict: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    justification: str = Field(..., min_length=1)
    execution_time_ms: float = Field(0.0, ge=0.0)


class EvidenceBundle(BaseModel):
    """Evidence bundle containing critic reports and justifications."""
    
    model_config = ConfigDict(strict=True)
    
    critic_reports: List[CriticReport] = Field(default_factory=list, description="Individual critic evaluations")
    aggregation_method: str = Field(..., description="Method used to aggregate critic outputs")
    total_critics: int = Field(..., ge=0, description="Total number of critics evaluated")
    successful_critics: int = Field(..., ge=0, description="Number of critics that completed successfully")
    failed_critics: int = Field(0, ge=0, description="Number of critics that failed")


class PrecedentBundle(BaseModel):
    """Bundle of precedents used in the decision."""
    
    model_config = ConfigDict(strict=True)
    
    precedent_ids: List[str] = Field(default_factory=list, description="IDs of precedents consulted")
    count: int = Field(0, ge=0, description="Number of precedents used")
    relevance_scores: Optional[List[float]] = Field(None, description="Relevance scores for each precedent")


class DecisionOutput(BaseModel):
    """Complete decision output from the adjudication pipeline."""
    
    model_config = ConfigDict(strict=True)

    case_id: str = Field(..., description="Unique identifier for this decision")
    verdict: str = Field(..., min_length=1, description="Final verdict")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level of the decision")
    escalated: bool = Field(..., description="Whether this case was escalated for human review")
    timestamp: datetime = Field(..., description="When the decision was made")
    evidence: EvidenceBundle = Field(..., description="Evidence supporting the decision")
    precedents: PrecedentBundle = Field(..., description="Precedents consulted")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional decision metadata")


class CaseResult(BaseModel):
    """Aggregated decision payload returned to callers (legacy)."""
    
    model_config = ConfigDict(strict=True)

    case_id: str = Field(..., min_length=1)
    verdict: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    escalated: bool
    precedents: List[str] = Field(default_factory=list)
    timestamp: datetime
    critic_reports: List[CriticReport] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    """Wrapper response for /evaluate and /decision."""
    
    model_config = ConfigDict(strict=True)

    result: CaseResult


class DecisionResponse(BaseModel):
    """Response for /decision endpoint with full DecisionOutput."""
    
    model_config = ConfigDict(strict=True)
    
    decision: DecisionOutput


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

    precedents: List[PrecedentRecord]
    count: int = Field(..., ge=0)


class CriticInfo(BaseModel):
    """Information about a configured critic."""
    
    model_config = ConfigDict(strict=True)

    name: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    enabled: bool = True
    weight: Optional[float] = Field(None, ge=0.0)


class CriticsResponse(BaseModel):
    """Response model for GET /critics."""
    
    model_config = ConfigDict(strict=True)

    critics: List[CriticInfo]
    count: int = Field(..., ge=0)


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


class EscalationResponse(BaseModel):
    """Acknowledgement for escalations."""
    
    model_config = ConfigDict(strict=True)

    case_id: str
    recorded: bool
    reason: str
    timestamp: datetime


class HealthCheck(BaseModel):
    """Complete health check response with component status."""
    
    model_config = ConfigDict(strict=True)

    status: str = Field(..., pattern="^(ok|degraded|error)$", description="Overall system status")
    components: Dict[str, str] = Field(..., description="Status of individual components")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="Time of health check")
    error_rate: float = Field(0.0, ge=0.0, le=1.0, description="Recent error rate")
    uptime_seconds: Optional[float] = Field(None, ge=0.0, description="System uptime in seconds")


class HealthResponse(BaseModel):
    """Service health report (legacy alias for HealthCheck)."""
    
    model_config = ConfigDict(strict=True)

    status: str = Field(..., pattern="^(ok|degraded|error)$")
    components: Dict[str, str]
    version: str
    timestamp: datetime
    error_rate: float = Field(0.0, ge=0.0, le=1.0)


class ValidationErrorDetail(BaseModel):
    """Detailed validation error response."""
    
    model_config = ConfigDict(strict=True)
    
    field: str
    message: str
    type: str


class ValidationErrorResponse(BaseModel):
    """Response for validation errors."""
    
    model_config = ConfigDict(strict=True)
    
    detail: str = "Validation error"
    errors: List[ValidationErrorDetail]
