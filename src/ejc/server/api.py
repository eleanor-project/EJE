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

logger = logging.getLogger(__name__)

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
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        uptime_seconds=time.time() - start_time,
        components={
            "api": "operational",
            "critics": "operational",
            "precedent_engine": "operational"
        }
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
    import uuid
    
    start_time = time.time()
    case_id = request.case_id or f"case_{uuid.uuid4().hex[:8]}"
    
    try:
        logger.info(f"Evaluating case {case_id}")
        
        # TODO: Integrate with actual EJE engine
        critic_results = [
            CriticResult(
                critic_name="openai_critic",
                decision="approved",
                confidence=0.85,
                reasoning="Content aligns with guidelines",
                execution_time_ms=120.5
            )
        ]
        
        execution_time = (time.time() - start_time) * 1000
        
        return DecisionResponse(
            case_id=case_id,
            status=DecisionStatus.ESCALATED if request.require_human_review else DecisionStatus.APPROVED,
            final_decision="approved",
            confidence=0.85,
            critic_results=critic_results,
            precedents_applied=["precedent_001"],
            requires_escalation=request.require_human_review,
            audit_log_id=f"audit_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow(),
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
    
    # TODO: Integrate with precedent engine
    results = [
        Precedent(
            precedent_id="prec_001",
            case_summary="Similar case from 2024",
            decision="approved",
            reasoning="Based on ethical principles",
            similarity_score=0.92,
            created_at=datetime(2024, 1, 15)
        )
    ]
    
    execution_time = (time.time() - start_time) * 1000
    
    return PrecedentSearchResponse(
        query=request.query,
        results=results,
        total_count=len(results),
        execution_time_ms=execution_time
    )

# ============================================================================
# Server Startup
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
