"""SQLite-backed precedent + escalation logging utilities."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, MetaData, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

metadata = MetaData()
Base = declarative_base(metadata=metadata)

logger = logging.getLogger(__name__)
_failed_writes: List[Dict[str, Any]] = []


class PrecedentRecord(Base):
    __tablename__ = "precedents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, index=True)
    prompt = Column(Text)
    verdict = Column(String, index=True)
    confidence = Column(Float)
    escalated = Column(Boolean, default=False)
    precedents = Column(Text)
    critic_reports = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class EscalationRecord(Base):
    __tablename__ = "escalations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String, index=True)
    reason = Column(Text)
    metadata_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


def get_engine(db_path: str):
    """Create a SQLite engine for the ops center database."""

    return create_engine(f"sqlite:///{db_path}", future=True)


def init_db(engine) -> None:
    """Create tables if they do not exist."""

    Base.metadata.create_all(engine)


def _serialize_precedents(prec_list: Iterable[str]) -> str:
    return json.dumps(list(prec_list))


def _serialize_reports(reports: Iterable[Dict[str, Any]]) -> str:
    return json.dumps(list(reports))


def _persist_with_retry(write_fn, payload: Dict[str, Any], kind: str, max_attempts: int = 3, base_delay: float = 0.1) -> bool:
    """Persist records with simple exponential backoff; enqueue on failure."""

    for attempt in range(1, max_attempts + 1):
        try:
            write_fn()
            return True
        except Exception as exc:  # pragma: no cover - defensive logging path
            if attempt == max_attempts:
                logger.exception("Failed to persist %s after %s attempts", kind, max_attempts)
                _failed_writes.append({
                    "kind": kind,
                    "payload": payload,
                    "error": str(exc),
                    "attempted_at": datetime.utcnow().isoformat(),
                })
                return False
            time.sleep(base_delay * (2 ** (attempt - 1)))


def flush_failed_writes(engine) -> None:
    """Attempt to flush any queued failed writes."""

    pending = list(_failed_writes)
    _failed_writes.clear()
    for item in pending:
        payload = item.get("payload", {})
        kind = item.get("kind", "unknown")
        if kind == "precedent":
            log_precedent(engine, **payload)
        elif kind == "escalation":
            log_escalation(engine, **payload)


def log_precedent(
    engine,
    *,
    case_id: str,
    prompt: str,
    verdict: str,
    confidence: float,
    escalated: bool,
    precedents: Iterable[str],
    critic_reports: Iterable[Dict[str, Any]],
) -> None:
    """Persist a case result along with critic context."""

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    payload = {
        "case_id": case_id,
        "prompt": prompt,
        "verdict": verdict,
        "confidence": confidence,
        "escalated": escalated,
        "precedents": _serialize_precedents(precedents),
        "critic_reports": _serialize_reports(critic_reports),
    }

    def _write():
        record = PrecedentRecord(**payload)
        with Session.begin() as session:
            session.add(record)

    _persist_with_retry(_write, payload={"case_id": case_id, "prompt": prompt, "verdict": verdict}, kind="precedent")


def log_escalation(
    engine,
    *,
    case_id: str,
    reason: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist a manual escalation to allow follow-up in the dashboard."""

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    payload = {
        "case_id": case_id,
        "reason": reason,
        "metadata_json": json.dumps(metadata or {}),
    }

    def _write():
        record = EscalationRecord(**payload)
        with Session.begin() as session:
            session.add(record)

    _persist_with_retry(_write, payload={"case_id": case_id, "reason": reason}, kind="escalation")


def fetch_recent(engine, limit: int = 10) -> List[PrecedentRecord]:
    """Return recent precedent decisions for dashboard views."""

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        return (
            session.query(PrecedentRecord)
            .order_by(PrecedentRecord.created_at.desc())
            .limit(limit)
            .all()
        )


def get_top_dissent(engine, limit: int = 10) -> List[Dict[str, Any]]:
    """Summarize critics that most often disagree with the final verdict."""

    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        rows = (
            session.query(PrecedentRecord.verdict, PrecedentRecord.critic_reports)
            .order_by(PrecedentRecord.created_at.desc())
            .limit(limit)
            .all()
        )

    dissent_counts: Dict[str, int] = {}
    for verdict, reports_json in rows:
        try:
            reports = json.loads(reports_json or "[]")
        except json.JSONDecodeError:
            reports = []
        for report in reports:
            critic = report.get("critic", "unknown")
            if report.get("verdict") and report.get("verdict") != verdict:
                dissent_counts[critic] = dissent_counts.get(critic, 0) + 1

    ranked = sorted(
        (
            {"critic": critic, "dissent_count": count}
            for critic, count in dissent_counts.items()
        ),
        key=lambda item: item["dissent_count"],
        reverse=True,
    )
    return ranked[:limit]
