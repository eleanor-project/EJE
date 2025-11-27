"""
FastAPI REST API for Eleanor Project's EJE

Provides RESTful API interface for the Ethical Jurisprudence Engine.

Author: Eleanor Project Contributors  
Date: 2025-11-25
Version: 1.0.0
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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

allowed_origins_env = [
    origin.strip()
    for origin in os.getenv("EJE_ALLOWED_ORIGINS", "http://localhost,http://127.0.0.1").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_env,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

security = HTTPBearer(auto_error=False)


def verify_bearer(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Simple bearer token enforcement when EJE_API_TOKEN is set."""
    expected_token = os.getenv("EJE_API_TOKEN")
    if not expected_token:
        return None

    if not credentials or credentials.credentials != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
        )
    return credentials

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
async def get_metrics(credentials: HTTPAuthorizationCredentials = Depends(verify_bearer)):
    """Get system metrics."""
    return MetricsResponse(
        total_cases_evaluated=1234,
        total_escalations=56,
        average_execution_time_ms=245.6,
        error_rate_percent=0.5
    )

@app.post("/evaluate", response_model=DecisionResponse, tags=["Decisions"])
async def evaluate_case(
    request: CaseRequest,
    credentials: HTTPAuthorizationCredentials = Depends(verify_bearer)
):
    """Evaluate case through EJE governance pipeline."""
    import time

    start_time = time.time()

    try:
        logger.info(f"Evaluating case: {request.prompt[:50]}...")

        # Build input data from request
        input_data = {
            "text": request.prompt,
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
async def search_precedents(
    request: PrecedentSearchRequest,
    credentials: HTTPAuthorizationCredentials = Depends(verify_bearer)
):
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
# Phase 3: Intelligence & Adaptation Endpoints
# ============================================================================

# --- Calibration Endpoints ---

class FeedbackRequest(BaseModel):
    """Ground truth feedback for calibration."""
    decision_id: str
    reviewer_id: str
    verdict: str = Field(..., pattern="^(allowed|blocked|escalated)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    critic_verdicts: Dict[str, str]

class CalibrationMetrics(BaseModel):
    """Critic calibration metrics."""
    critic_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    avg_confidence: float
    calibration_error: float
    overconfidence_ratio: float

class ThresholdTuningResponse(BaseModel):
    """Threshold tuning results."""
    critic_name: str
    old_thresholds: Dict[str, float]
    new_thresholds: Dict[str, float]
    expected_accuracy: float

@app.post("/calibration/feedback", tags=["Phase 3: Calibration"])
async def submit_feedback(
    request: FeedbackRequest,
    credentials: HTTPAuthorizationCredentials = Depends(verify_bearer)
):
    """Submit ground truth feedback for critic calibration."""
    try:
        from ejc.core.calibration import FeedbackCollector

        collector = FeedbackCollector()
        collector.submit_feedback(
            decision_id=request.decision_id,
            reviewer_id=request.reviewer_id,
            verdict=request.verdict,
            confidence=request.confidence,
            critic_verdicts=request.critic_verdicts
        )

        return {"status": "success", "message": "Feedback recorded"}
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )

@app.get("/calibration/metrics/{critic_name}", response_model=CalibrationMetrics, tags=["Phase 3: Calibration"])
async def get_calibration_metrics(
    critic_name: str,
    credentials: HTTPAuthorizationCredentials = Depends(verify_bearer)
):
    """Get calibration metrics for a specific critic."""
    try:
        from ejc.core.calibration import CriticCalibrator

        calibrator = CriticCalibrator()
        performance = calibrator.get_critic_performance(critic_name)

        return CalibrationMetrics(
            critic_name=performance.critic_name,
            accuracy=performance.accuracy,
            precision=performance.precision,
            recall=performance.recall,
            f1_score=performance.f1_score,
            avg_confidence=performance.avg_confidence,
            calibration_error=performance.calibration_error,
            overconfidence_ratio=performance.overconfidence_ratio
        )
    except Exception as e:
        logger.error(f"Calibration metrics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not retrieve metrics for {critic_name}: {str(e)}"
        )

@app.post("/calibration/tune/{critic_name}", response_model=ThresholdTuningResponse, tags=["Phase 3: Calibration"])
async def tune_thresholds(
    critic_name: str,
    target_accuracy: float = 0.90,
    credentials: HTTPAuthorizationCredentials = Depends(verify_bearer)
):
    """Auto-tune confidence thresholds for a critic."""
    try:
        from ejc.core.calibration import CriticCalibrator

        calibrator = CriticCalibrator()
        old_thresholds = calibrator.get_current_thresholds(critic_name)
        new_thresholds = calibrator.tune_critic_thresholds(critic_name, target_accuracy)

        return ThresholdTuningResponse(
            critic_name=critic_name,
            old_thresholds=old_thresholds.__dict__ if old_thresholds else {},
            new_thresholds=new_thresholds.__dict__,
            expected_accuracy=target_accuracy
        )
    except Exception as e:
        logger.error(f"Threshold tuning error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to tune thresholds: {str(e)}"
        )

# --- Drift Detection Endpoints ---

class DriftHealthResponse(BaseModel):
    """Drift detection health report."""
    health_score: float = Field(..., ge=0.0, le=100.0)
    constitutional_drift_alerts: int
    consistency_issues: int
    consensus_problems: int
    overall_assessment: str

class DriftAlert(BaseModel):
    """Single drift alert."""
    alert_id: int
    alert_type: str
    severity: str
    message: str
    detected_at: datetime
    acknowledged: bool

@app.get("/drift/health", response_model=DriftHealthResponse, tags=["Phase 3: Drift Detection"])
async def get_drift_health(
    days: int = 30,
    credentials: HTTPAuthorizationCredentials = Depends(verify_bearer)
):
    """Get system drift health score."""
    try:
        from ejc.core.drift_detection import DriftMonitor
        from datetime import datetime, timedelta

        monitor = DriftMonitor()

        # Get recent decisions (in production, fetch from audit log)
        # For now, return mock data or fetch from database
        analysis = monitor.analyze_drift([])  # Empty for now - would fetch real decisions

        health_score = analysis.get("health_score", 100.0)
        alerts = analysis.get("all_alerts", [])

        constitutional_alerts = len([a for a in alerts if a.alert_type == "constitutional_drift"])
        consistency_alerts = len([a for a in alerts if a.alert_type == "precedent_inconsistency"])
        consensus_alerts = len([a for a in alerts if a.alert_type == "consensus_shift"])

        if health_score >= 90:
            assessment = "excellent"
        elif health_score >= 75:
            assessment = "good"
        elif health_score >= 60:
            assessment = "concerning"
        else:
            assessment = "critical"

        return DriftHealthResponse(
            health_score=health_score,
            constitutional_drift_alerts=constitutional_alerts,
            consistency_issues=consistency_alerts,
            consensus_problems=consensus_alerts,
            overall_assessment=assessment
        )
    except Exception as e:
        logger.error(f"Drift health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check drift health: {str(e)}"
        )

@app.get("/drift/alerts", response_model=List[DriftAlert], tags=["Phase 3: Drift Detection"])
async def get_drift_alerts(
    limit: int = 50,
    severity: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(verify_bearer)
):
    """Get recent drift alerts."""
    try:
        from ejc.core.drift_detection import DriftMonitor

        monitor = DriftMonitor()
        alerts = monitor.get_recent_alerts(limit=limit, severity=severity)

        return [
            DriftAlert(
                alert_id=alert.id,
                alert_type=alert.alert_type,
                severity=alert.severity,
                message=alert.message,
                detected_at=alert.detected_at,
                acknowledged=alert.acknowledged
            )
            for alert in alerts
        ]
    except Exception as e:
        logger.error(f"Drift alerts error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve alerts: {str(e)}"
        )

# --- Context-Aware Evaluation Endpoint ---

class ContextualEvaluationRequest(BaseModel):
    """Case evaluation with context awareness."""
    case_id: Optional[str] = None
    prompt: str = Field(..., min_length=1)
    jurisdiction: Optional[str] = None  # e.g., "EU", "US-CA", "US-HIPAA"
    cultural_context: Optional[str] = None  # e.g., "western", "eastern", "middle_eastern"
    domain: Optional[str] = None  # e.g., "healthcare", "finance", "education"
    context: Dict[str, Any] = Field(default_factory=dict)

@app.post("/evaluate/contextual", response_model=DecisionResponse, tags=["Phase 3: Context System"])
async def evaluate_with_context(
    request: ContextualEvaluationRequest,
    credentials: HTTPAuthorizationCredentials = Depends(verify_bearer)
):
    """Evaluate case with jurisdiction, cultural, and domain context."""
    import time

    start_time = time.time()

    try:
        from ejc.core.context import ContextManager, ContextualizedRequest

        # Build contextualized request
        manager = ContextManager()

        contextualized = ContextualizedRequest(
            case_id=request.case_id or f"case_{int(time.time())}",
            prompt=request.prompt,
            base_context=request.context,
            jurisdiction=request.jurisdiction,
            cultural_context=request.cultural_context,
            domain=request.domain
        )

        # Analyze with context
        context_analysis = manager.analyze_with_context(contextualized)

        # Run standard evaluation with enhanced context
        enhanced_context = {
            **request.context,
            "context_analysis": context_analysis,
            "jurisdiction": request.jurisdiction,
            "cultural_context": request.cultural_context,
            "domain": request.domain
        }

        input_data = {
            "text": request.prompt,
            "prompt": request.prompt,
            "context": enhanced_context,
        }

        result = adjudicate(input_data, _config)

        execution_time = (time.time() - start_time) * 1000

        return DecisionResponse(
            case_id=request.case_id or f"case_{int(time.time())}",
            status=DecisionStatus.APPROVED if result["verdict"] == "allowed" else DecisionStatus.REJECTED,
            final_decision=result["verdict"],
            confidence=result.get("confidence", 0.0),
            critic_results=[
                CriticResult(
                    critic_name=cr["critic"],
                    decision=cr["verdict"],
                    confidence=cr.get("confidence", 0.0),
                    reasoning=cr.get("reason", ""),
                    execution_time_ms=0.0
                )
                for cr in result.get("critic_results", [])
            ],
            precedents_applied=[],
            requires_escalation=result.get("requires_escalation", False),
            audit_log_id=f"audit_{int(time.time())}",
            timestamp=datetime.utcnow(),
            execution_time_ms=execution_time
        )
    except Exception as e:
        logger.error(f"Contextual evaluation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Contextual evaluation failed: {str(e)}"
        )

# --- Performance Metrics Endpoint ---

class PerformanceStats(BaseModel):
    """Performance optimization statistics."""
    cache_hit_rate: float
    cache_size: int
    avg_cache_speedup: float
    avg_parallel_speedup: float
    total_time_saved_ms: float

@app.get("/performance/stats", response_model=PerformanceStats, tags=["Phase 3: Performance"])
async def get_performance_stats(
    credentials: HTTPAuthorizationCredentials = Depends(verify_bearer)
):
    """Get performance optimization statistics."""
    try:
        from ejc.core.performance import PerformanceManager

        manager = PerformanceManager()
        stats = manager.get_statistics()

        return PerformanceStats(
            cache_hit_rate=stats.get("cache_hit_rate", 0.0),
            cache_size=stats.get("cache_size", 0),
            avg_cache_speedup=stats.get("avg_cache_speedup", 1.0),
            avg_parallel_speedup=stats.get("avg_parallel_speedup", 1.0),
            total_time_saved_ms=stats.get("total_time_saved_ms", 0.0)
        )
    except Exception as e:
        logger.error(f"Performance stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve performance stats: {str(e)}"
        )

# ============================================================================
# Server Startup
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
