"""FastAPI endpoints for evaluation, escalation, and health checks."""
from __future__ import annotations

import copy
import json
import time
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from ejc.core.adjudicate import adjudicate
from ejc.core.config_loader import load_global_config
from ejc.core.error_handling import EJEBaseException, create_error_report

from eje.api import models
from eje.config.settings import Settings
from eje.db import escalation_log
from eje.learning.context_model import DissentAwareContextModel

router = APIRouter()


# Dependencies -----------------------------------------------------------------

def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_config(request: Request) -> Dict[str, Any]:
    return request.app.state.config


def get_context_model(request: Request) -> DissentAwareContextModel:
    return request.app.state.context_model


def get_engine(request: Request):
    return request.app.state.engine


# Routes -----------------------------------------------------------------------
# Note: All routes are protected by authentication via app.py dependencies

@router.post("/decision", response_model=models.DecisionResponse)
async def decision(
    request_body: models.EvaluationRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    config: Dict[str, Any] = Depends(get_config),
    context_model: DissentAwareContextModel = Depends(get_context_model),
    engine=Depends(get_engine),
):
    """Run the adjudication pipeline and return complete DecisionOutput.
    
    🔒 **Authentication Required**: Bearer token via Authorization header
    
    This endpoint performs full ethical evaluation using the configured
    critics, aggregates their outputs, consults precedents, and returns
    a comprehensive decision with all supporting evidence.
    
    Args:
        request_body: Evaluation request with prompt and context
        request: FastAPI request object
        settings: Application settings
        config: Critic configuration
        context_model: Learning model for weight suggestions
        engine: Database engine
        
    Returns:
        DecisionResponse with complete DecisionOutput
        
    Raises:
        HTTPException: For validation or processing errors
    """

    input_data = {
        "text": request_body.prompt,
        "prompt": request_body.prompt,
        "context": request_body.context,
        "require_human_review": request_body.require_human_review,
    }

    adjudication_config = copy.deepcopy(config)
    if settings.dynamic_weights:
        suggested_weights = context_model.suggest_weights()
        if suggested_weights:
            adjudication_config.setdefault("aggregation", {})["critic_weights"] = suggested_weights

    try:
        decision_result = adjudicate(input_data=input_data, config=adjudication_config)
    except EJEBaseException as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=create_error_report(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - catch-all safety
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    # Extract critic reports
    critic_reports: List[Dict[str, Any]] = list(decision_result.critic_reports)
    
    # Update learning model
    context_model.record_outcome(
        decision_result.governance_outcome.get("verdict", "ERROR"),
        critic_reports
    )
    
    # Calculate error statistics
    error_stats = decision_result.aggregation.get("errors", {}) if isinstance(decision_result.aggregation, dict) else {}
    error_count = error_stats.get("count", 0) if isinstance(error_stats, dict) else 0
    total_reports = len(critic_reports)
    successful_count = total_reports - error_count

    # Update global error tracking
    stats = request.app.state.error_stats
    stats["errors"] += int(error_count)
    stats["total"] += total_reports
    stats["last_error_rate"] = error_stats.get("rate", 0.0) if isinstance(error_stats, dict) else 0.0

    # Build structured response models
    case_id = request_body.case_id or decision_result.decision_id
    verdict = decision_result.governance_outcome.get("verdict", "UNKNOWN")
    confidence = decision_result.governance_outcome.get("confidence", 0.0)
    escalated = decision_result.escalated or (confidence <= settings.escalation_threshold)
    
    # Build EvidenceBundle
    evidence = models.EvidenceBundle(
        critic_reports=[models.CriticReport(**report) for report in critic_reports],
        aggregation_method=adjudication_config.get("aggregation", {}).get("method", "weighted_vote"),
        total_critics=total_reports,
        successful_critics=successful_count,
        failed_critics=error_count,
        error_rate=stats["last_error_rate"],
    )
    
    # Build PrecedentBundle
    precedent_ids = [p.get("id", f"precedent_{idx}") for idx, p in enumerate(decision_result.precedents)]
    precedents = models.PrecedentBundle(
        precedent_ids=precedent_ids,
        count=len(precedent_ids),
        relevance_scores=None,  # Could be populated from precedent system in future
    )
    
    # Build DecisionOutput
    decision_output = models.DecisionOutput(
        case_id=case_id,
        verdict=verdict,
        confidence=confidence,
        escalated=escalated,
        timestamp=datetime.fromisoformat(decision_result.timestamp.replace("Z", "+00:00")),
        evidence=evidence,
        precedents=precedents,
        metadata={
            "dynamic_weights_used": settings.dynamic_weights,
            "escalation_threshold": settings.escalation_threshold,
            "require_human_review": request_body.require_human_review,
        },
    )

    # Persist decision to database
    try:
        escalation_log.log_precedent(
            engine,
            case_id=case_id,
            prompt=request_body.prompt,
            verdict=verdict,
            confidence=confidence,
            escalated=escalated,
            precedents=precedent_ids,
            critic_reports=critic_reports,
        )
    except Exception:
        # Persistence is non-blocking; surface errors to logs only
        request.app.logger.exception("Failed to persist precedent record")

    return models.DecisionResponse(decision=decision_output)


# Backward compatibility alias
@router.post("/evaluate", response_model=models.EvaluationResponse, include_in_schema=False)
async def evaluate(
    request_body: models.EvaluationRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    config: Dict[str, Any] = Depends(get_config),
    context_model: DissentAwareContextModel = Depends(get_context_model),
    engine=Depends(get_engine),
):
    """Legacy endpoint - provides backward compatibility.
    
    🔒 **Authentication Required**: Bearer token via Authorization header
    
    Returns data in the old CaseResult format. New integrations should
    use the /decision endpoint for full DecisionOutput.
    """
    # Get full decision
    decision_response = await decision(request_body, request, settings, config, context_model, engine)
    decision_output = decision_response.decision
    
    # Convert to legacy format
    case_result = models.CaseResult(
        case_id=decision_output.case_id,
        verdict=decision_output.verdict,
        confidence=decision_output.confidence,
        escalated=decision_output.escalated,
        precedents=decision_output.precedents.precedent_ids,
        timestamp=decision_output.timestamp,
        critic_reports=decision_output.evidence.critic_reports,
    )
    
    return models.EvaluationResponse(result=case_result)


@router.get("/precedents", response_model=models.PrecedentsResponse)
async def get_precedents(
    request: Request,
    limit: int = Query(default=10, ge=1, le=100, description="Number of precedents to retrieve"),
    engine=Depends(get_engine),
):
    """Retrieve recent precedent records from the database.
    
    🔒 **Authentication Required**: Bearer token via Authorization header
    
    Returns historical decisions with full critic reports and metadata.
    Useful for precedent analysis and system auditing.
    
    Args:
        request: FastAPI request object
        limit: Number of records to return (1-100)
        engine: Database engine
        
    Returns:
        PrecedentsResponse with list of PrecedentRecord objects
        
    Raises:
        HTTPException: If database query fails
    """
    
    try:
        records = escalation_log.fetch_recent(engine, limit=limit)
        
        precedent_list = []
        for record in records:
            # Parse JSON fields safely
            try:
                precedents = json.loads(record.precedents or "[]")
            except json.JSONDecodeError:
                request.app.logger.warning(f"Failed to parse precedents for case {record.case_id}")
                precedents = []
            
            try:
                critic_reports = json.loads(record.critic_reports or "[]")
            except json.JSONDecodeError:
                request.app.logger.warning(f"Failed to parse critic reports for case {record.case_id}")
                critic_reports = []
            
            # Build validated models
            try:
                precedent_list.append(
                    models.PrecedentRecord(
                        case_id=record.case_id,
                        prompt=record.prompt,
                        verdict=record.verdict,
                        confidence=record.confidence,
                        escalated=record.escalated,
                        precedents=precedents,
                        critic_reports=[models.CriticReport(**report) for report in critic_reports],
                        created_at=record.created_at,
                    )
                )
            except Exception as e:
                request.app.logger.error(f"Failed to build precedent record for case {record.case_id}: {e}")
                continue
        
        return models.PrecedentsResponse(
            precedents=precedent_list,
            count=len(precedent_list),
        )
    except Exception as exc:
        request.app.logger.exception("Failed to retrieve precedents")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to retrieve precedents: {exc}",
        ) from exc


@router.get("/critics", response_model=models.CriticsResponse)
async def get_critics(
    request: Request,
    config: Dict[str, Any] = Depends(get_config),
):
    """List all configured critics with their settings.
    
    🔒 **Authentication Required**: Bearer token via Authorization header
    
    Returns information about each critic including type, enabled status,
    and weight. Useful for understanding system configuration and debugging.
    
    Args:
        request: FastAPI request object
        config: Critic configuration
        
    Returns:
        CriticsResponse with list of CriticInfo objects
        
    Raises:
        HTTPException: If config parsing fails
    """
    
    try:
        critics_config = config.get("critics", [])
        
        critic_list = []
        for critic_cfg in critics_config:
            if isinstance(critic_cfg, dict):
                try:
                    critic_list.append(
                        models.CriticInfo(
                            name=critic_cfg.get("name", "unknown"),
                            type=critic_cfg.get("type", "unknown"),
                            enabled=critic_cfg.get("enabled", True),
                            weight=critic_cfg.get("weight"),
                            description=critic_cfg.get("description"),
                        )
                    )
                except Exception as e:
                    request.app.logger.warning(f"Failed to parse critic config: {e}")
                    continue
        
        return models.CriticsResponse(
            critics=critic_list,
            count=len(critic_list),
        )
    except Exception as exc:
        request.app.logger.exception("Failed to retrieve critics")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to retrieve critics: {exc}",
        ) from exc


@router.post("/escalate", response_model=models.EscalationResponse)
async def escalate(
    payload: models.EscalationRequest,
    request: Request,
    engine=Depends(get_engine),
):
    """Record manual escalations for offline follow-up.
    
    🔒 **Authentication Required**: Bearer token via Authorization header
    
    Allows humans to flag cases that require additional review or
    intervention beyond the automated decision process.
    
    Args:
        payload: Escalation request with case ID and reason
        request: FastAPI request object
        engine: Database engine
        
    Returns:
        EscalationResponse confirming the escalation was recorded
        
    Raises:
        HTTPException: If database write fails
    """

    try:
        escalation_log.log_escalation(
            engine,
            case_id=payload.case_id,
            reason=payload.reason,
            metadata=payload.metadata,
        )
    except Exception as exc:
        request.app.logger.exception(f"Failed to log escalation for case {payload.case_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to record escalation: {exc}",
        ) from exc

    return models.EscalationResponse(
        case_id=payload.case_id,
        recorded=True,
        reason=payload.reason,
        timestamp=datetime.utcnow(),
    )


@router.get("/health", response_model=models.HealthCheck)
async def health(request: Request):
    """Return comprehensive health check with component status.
    
    ℹ️ **Note**: This endpoint may be exempted from authentication for
    load balancer health checks. Configure via middleware if needed.
    
    Checks configuration, database, and tracks error rates and uptime.
    Used by monitoring systems and load balancers.
    
    Args:
        request: FastAPI request object
        
    Returns:
        HealthCheck with system status and metrics
    """

    config_loaded = bool(request.app.state.config)
    db_ready = bool(request.app.state.engine)
    error_stats = request.app.state.error_stats
    total = error_stats.get("total", 0)
    aggregated_error_rate = (error_stats.get("errors", 0) / total) if total else 0.0
    
    # Calculate uptime
    uptime_seconds = time.time() - request.app.state.start_time
    
    # Determine overall status
    if config_loaded and db_ready:
        if aggregated_error_rate > 0.5:
            overall_status = "degraded"
        else:
            overall_status = "ok"
    else:
        overall_status = "error"
    
    return models.HealthCheck(
        status=overall_status,
        components={
            "config": "loaded" if config_loaded else "missing",
            "database": "ready" if db_ready else "unavailable",
            "learning_model": "ready" if hasattr(request.app.state, "context_model") else "unavailable",
            "authentication": "enabled" if request.app.state.settings.require_api_token else "disabled",
        },
        version=request.app.state.version,
        timestamp=datetime.utcnow(),
        error_rate=aggregated_error_rate,
        uptime_seconds=uptime_seconds,
    )


def load_config(path: str) -> Dict[str, Any]:
    """Helper to load shared configuration for the app factory.
    
    Args:
        path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """

    return load_global_config(path)
