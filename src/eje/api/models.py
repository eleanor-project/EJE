"""Pydantic schemas for the Moral Ops Center FastAPI layer."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvaluationRequest(BaseModel):
    """Incoming request to evaluate a prompt with optional context."""

    prompt: str = Field(..., min_length=1)
    context: Dict[str, Any] = Field(default_factory=dict)
    case_id: Optional[str] = None
    require_human_review: bool = False


class CriticReport(BaseModel):
    """Normalized critic output included in responses."""

    critic: str
    verdict: str
    confidence: float
    justification: str
    execution_time_ms: float = 0.0


class CaseResult(BaseModel):
    """Aggregated decision payload returned to callers."""

    case_id: str
    verdict: str
    confidence: float
    escalated: bool
    precedents: List[str] = Field(default_factory=list)
    timestamp: datetime
    critic_reports: List[CriticReport] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    """Wrapper response for /evaluate and /decision."""

    result: CaseResult


class PrecedentRecord(BaseModel):
    """Single precedent record from the database."""

    case_id: str
    prompt: str
    verdict: str
    confidence: float
    escalated: bool
    precedents: List[str] = Field(default_factory=list)
    critic_reports: List[CriticReport] = Field(default_factory=list)
    created_at: datetime


class PrecedentsResponse(BaseModel):
    """Response model for GET /precedents."""

    precedents: List[PrecedentRecord]
    count: int


class CriticInfo(BaseModel):
    """Information about a configured critic."""

    name: str
    type: str
    enabled: bool = True
    weight: Optional[float] = None


class CriticsResponse(BaseModel):
    """Response model for GET /critics."""

    critics: List[CriticInfo]
    count: int


class EscalationRequest(BaseModel):
    """Manual escalation body."""

    case_id: str
    reason: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EscalationResponse(BaseModel):
    """Acknowledgement for escalations."""

    case_id: str
    recorded: bool
    reason: str
    timestamp: datetime


class HealthResponse(BaseModel):
    """Service health report."""

    status: str
    components: Dict[str, str]
    version: str
    timestamp: datetime
    error_rate: float = Field(0.0, ge=0.0)
