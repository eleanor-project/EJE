"""FastAPI endpoints for evaluation, escalation, and health checks."""
from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request, status

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

@router.post("/evaluate", response_model=models.EvaluationResponse)
async def evaluate(
    request_body: models.EvaluationRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    config: Dict[str, Any] = Depends(get_config),
    context_model: DissentAwareContextModel = Depends(get_context_model),
    engine=Depends(get_engine),
):
    """Run the adjudication pipeline and persist the outcome."""

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
        decision = adjudicate(input_data=input_data, config=adjudication_config)
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

    critic_reports: List[Dict[str, Any]] = list(decision.critic_reports)
    context_model.record_outcome(decision.governance_outcome.get("verdict", "ERROR"), critic_reports)

    case_result = models.CaseResult(
        case_id=request_body.case_id or decision.decision_id,
        verdict=decision.governance_outcome.get("verdict", "UNKNOWN"),
        confidence=decision.governance_outcome.get("confidence", 0.0),
        escalated=decision.escalated or decision.governance_outcome.get("confidence", 0.0)
        <= settings.escalation_threshold,
        precedents=[p.get("id", f"precedent_{idx}") for idx, p in enumerate(decision.precedents)],
        timestamp=datetime.fromisoformat(decision.timestamp.replace("Z", "+00:00")),
        critic_reports=[models.CriticReport(**report) for report in critic_reports],
    )

    try:
        escalation_log.log_precedent(
            engine,
            case_id=case_result.case_id,
            prompt=request_body.prompt,
            verdict=case_result.verdict,
            confidence=case_result.confidence,
            escalated=case_result.escalated,
            precedents=case_result.precedents,
            critic_reports=critic_reports,
        )
    except Exception:
        # Persistence is non-blocking; surface errors to logs only
        request.app.logger.exception("Failed to persist precedent record")

    return models.EvaluationResponse(result=case_result)


@router.post("/escalate", response_model=models.EscalationResponse)
async def escalate(
    payload: models.EscalationRequest,
    request: Request,
    engine=Depends(get_engine),
):
    """Record manual escalations for offline follow-up."""

    try:
        escalation_log.log_escalation(
            engine,
            case_id=payload.case_id,
            reason=payload.reason,
            metadata=payload.metadata,
        )
    except Exception as exc:
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


@router.get("/health", response_model=models.HealthResponse)
async def health(request: Request):
    """Return a coarse health snapshot used by dashboards and probes."""

    config_loaded = bool(request.app.state.config)
    db_ready = bool(request.app.state.engine)
    return models.HealthResponse(
        status="ok" if config_loaded and db_ready else "degraded",
        components={
            "config": "loaded" if config_loaded else "missing",
            "database": "ready" if db_ready else "unavailable",
        },
        version=request.app.state.version,
        timestamp=datetime.utcnow(),
    )


def load_config(path: str) -> Dict[str, Any]:
    """Helper to load shared configuration for the app factory."""

    return load_global_config(path)
