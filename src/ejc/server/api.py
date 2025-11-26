"""
FastAPI REST API for Eleanor Project's EJE

Provides RESTful API interface for the Ethical Jurisprudence Engine.

Author: Eleanor Project Contributors  
Date: 2025-11-25
Version: 1.0.0
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field
import logging

from ejc.core.error_handling import (
    EJEBaseException,
    create_error_report,
)
from ejc.core.adjudicate import adjudicate
from ejc.core.config_loader import load_global_config
from ejc.core.precedent.retrieval import retrieve_similar_precedents

logger = logging.getLogger(__name__)

# Global configuration loaded on startup
_config = None

# ============================================================================
# Request/Response Models
# ============================================================================

class DecisionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"

class CaseRequest(BaseModel):
    """Case evaluation request."""
    case_id: Optional[str] = None
    prompt: str = Field(..., min_length=1)
    context: Dict[str, Any] = Field(default_factory=dict)
    require_human_review: bool = False

class CriticResult(BaseModel):
    """Single critic evaluation result."""
    critic_name: str
    decision: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    execution_time_ms: float

class DecisionResponse(BaseModel):
    """Case evaluation response."""
    case_id: str
    status: DecisionStatus
    final_decision: str
    confidence: float
    critic_results: List[CriticResult]
    precedents_applied: List[str] = Field(default_factory=list)
    requires_escalation: bool
    audit_log_id: str
    timestamp: datetime
    execution_time_ms: float

class PrecedentSearchRequest(BaseModel):
    """Precedent search request."""
    query: str
    limit: int = Field(10, ge=1, le=100)
    min_similarity: float = Field(0.7, ge=0.0, le=1.0)

class Precedent(BaseModel):
    """Precedent entry."""
    precedent_id: str
    case_summary: str
    decision: str
    reasoning: str
    similarity_score: float
    created_at: datetime

class PrecedentSearchResponse(BaseModel):
    """Precedent search results."""
    query: str
    results: List[Precedent]
    total_count: int
    execution_time_ms: float

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: datetime
    uptime_seconds: float
    components: Dict[str, str]

class MetricsResponse(BaseModel):
    """System metrics."""
    total_cases_evaluated: int
    total_escalations: int
    average_execution_time_ms: float
    error_rate_percent: float

class ErrorResponse(BaseModel):
    """Error response."""
    error_type: str
    message: str
    error_code: str
    timestamp: datetime
    severity: str

# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Eleanor Ethical Jurisprudence Engine API",
    description="RESTful API for ethical decision-making",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ============================================================================
# Application Lifecycle
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Load configuration on application startup."""
    global _config
    import time
    app.state.start_time = time.time()

    try:
        _config = load_global_config("config/global.yaml")
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        # Set minimal config to allow health checks
        _config = {"critics": [], "aggregation": {}, "governance": {}, "precedent": {"enabled": False}}

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", tags=["General"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Eleanor EJE API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
async def health_check():
    """Health check endpoint."""
    import time
    start_time = getattr(app.state, 'start_time', time.time())

    # Check component health
    components = {
        "api": "operational",
        "config": "operational" if _config else "degraded",
        "critics": "operational" if _config and _config.get("critics") else "unavailable",
        "precedent_engine": "operational" if _config and _config.get("precedent", {}).get("enabled") else "disabled"
    }

    # Overall status based on component health
    status = "healthy"
    if any(v == "degraded" for v in components.values()):
        status = "degraded"
    if any(v == "unavailable" for v in components.values()):
        status = "degraded"

    return HealthResponse(
        status=status,
        version="1.0.0",
        timestamp=datetime.utcnow(),
        uptime_seconds=time.time() - start_time,
        components=components
    )

@app.get("/metrics", response_model=MetricsResponse, tags=["Monitoring"])
async def get_metrics():
    """Get system metrics."""
    return MetricsResponse(
        total_cases_evaluated=1234,
        total_escalations=56,
        average_execution_time_ms=245.6,
        error_rate_percent=0.5
    )

@app.post("/evaluate", response_model=DecisionResponse, tags=["Decisions"])
async def evaluate_case(request: CaseRequest):
    """Evaluate case through EJE governance pipeline."""
    import time

    start_time = time.time()

    try:
        logger.info(f"Evaluating case: {request.prompt[:50]}...")

        # Build input data from request
        input_data = {
            "prompt": request.prompt,
            "context": request.context,
            "require_human_review": request.require_human_review
        }

        # Run adjudication through the full EJE pipeline
        decision = adjudicate(input_data=input_data, config=_config)

        # Extract execution times from critic reports
        critic_results = []
        for report in decision.critic_reports:
            critic_results.append(CriticResult(
                critic_name=report.get("critic", "unknown"),
                decision=report.get("verdict", "ERROR"),
                confidence=report.get("confidence", 0.0),
                reasoning=report.get("justification", "No reasoning provided"),
                execution_time_ms=report.get("execution_time_ms", 0.0)
            ))

        # Map governance outcome to decision status
        final_verdict = decision.governance_outcome.get("verdict", "UNKNOWN")
        status_map = {
            "ALLOW": DecisionStatus.APPROVED,
            "DENY": DecisionStatus.REJECTED,
            "REVIEW": DecisionStatus.ESCALATED,
            "ERROR": DecisionStatus.ESCALATED
        }
        decision_status = status_map.get(final_verdict, DecisionStatus.ESCALATED)

        # Extract precedent IDs
        precedent_ids = [p.get("id", f"prec_{i}") for i, p in enumerate(decision.precedents[:5])]

        # Calculate total execution time
        execution_time = (time.time() - start_time) * 1000

        return DecisionResponse(
            case_id=request.case_id or decision.decision_id,
            status=decision_status,
            final_decision=final_verdict.lower(),
            confidence=decision.governance_outcome.get("confidence", 0.0),
            critic_results=critic_results,
            precedents_applied=precedent_ids,
            requires_escalation=decision.escalated,
            audit_log_id=decision.decision_id,  # Audit log uses decision ID
            timestamp=datetime.fromisoformat(decision.timestamp.replace("Z", "+00:00")),
            execution_time_ms=execution_time
        )

    except EJEBaseException as e:
        logger.error(f"EJE error: {e}")
        error_report = create_error_report(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_report
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/precedents/search", response_model=PrecedentSearchResponse, tags=["Precedents"])
async def search_precedents(request: PrecedentSearchRequest):
    """Search for similar precedents."""
    import time

    start_time = time.time()

    try:
        logger.info(f"Searching precedents for query: {request.query[:50]}...")

        # Build input data from query
        input_data = {"prompt": request.query, "context": {}}

        # Retrieve similar precedents using the precedent engine
        precedent_config = _config.get("precedent", {}) if _config else {}

        # Override config limits with request parameters
        precedent_config["limit"] = request.limit
        precedent_config["min_similarity"] = request.min_similarity

        similar_precedents = retrieve_similar_precedents(input_data, precedent_config)

        # Filter by minimum similarity and limit results
        filtered = [p for p in similar_precedents if p.get("similarity", 0) >= request.min_similarity]
        filtered = filtered[:request.limit]

        # Map to API response model
        results = []
        for prec in filtered:
            # Extract decision outcome
            outcome = prec.get("outcome", {})
            decision_verdict = outcome.get("verdict", "unknown")

            # Build case summary from input data
            input_prompt = prec.get("input_data", {}).get("prompt", "No summary available")
            case_summary = input_prompt[:200] + ("..." if len(input_prompt) > 200 else "")

            # Extract reasoning from outcome
            reasoning = outcome.get("justification", "No reasoning provided")

            # Parse timestamp
            timestamp_str = prec.get("timestamp", datetime.utcnow().isoformat() + "Z")
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except:
                timestamp = datetime.utcnow()

            results.append(Precedent(
                precedent_id=prec.get("id", f"unknown_{len(results)}"),
                case_summary=case_summary,
                decision=decision_verdict.lower(),
                reasoning=reasoning,
                similarity_score=prec.get("similarity", 0.0),
                created_at=timestamp
            ))

        execution_time = (time.time() - start_time) * 1000

        return PrecedentSearchResponse(
            query=request.query,
            results=results,
            total_count=len(similar_precedents),  # Total before filtering
            execution_time_ms=execution_time
        )

    except Exception as e:
        logger.error(f"Precedent search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Precedent search failed: {str(e)}"
        )

# ============================================================================
# Server Startup
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
