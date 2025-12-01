from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import json
from typing import Any, Dict, List, Optional

Base = declarative_base()

class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    prompt = Column(Text)
    verdict = Column(String(50))
    result_json = Column(Text)
    details_json = Column(Text)
    feedback = Column(Text, nullable=True)

def get_engine(db_uri):
    return create_engine(db_uri)

class AuditLogger:
    def __init__(self, db_uri):
        self.engine = get_engine(db_uri)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def log_event(self, prompt, agg, details):
        session = self.Session()
        event = AuditEvent(
            timestamp=datetime.datetime.utcnow(),
            prompt=prompt,
            verdict=agg['overall_verdict'],
            result_json=json.dumps(agg),
            details_json=json.dumps(details),
            feedback=None
        )
        session.add(event)
        session.commit()
        session.close()

    def log_decision(self, bundle):
        """
        Log a decision bundle from the EthicalReasoningEngine.
        Wrapper around log_event that extracts the appropriate fields.
        """
        self.log_event(
            prompt=json.dumps(bundle['input']),
            agg=bundle['final_decision'],
            details=bundle['critic_outputs']
        )

    def append_feedback(self, event_id, feedback):
        session = self.Session()
        event = session.query(AuditEvent).filter_by(id=event_id).first()
        if event:
            event.feedback = feedback
            session.commit()
        session.close()

    def log_feedback(self, request_id: str, feedback_data: dict):
        """
        Log feedback for a specific request ID.

        Args:
            request_id: The request ID from the decision bundle
            feedback_data: Dictionary containing feedback information
        """
        session = self.Session()
        try:
            events = session.query(AuditEvent).all()
            for event in events:
                try:
                    result = json.loads(event.result_json) if event.result_json else {}
                    if self._event_matches_request(result, request_id):
                        self._append_feedback_to_event(event, feedback_data)
                        session.commit()
                        return

                    details = json.loads(event.details_json) if event.details_json else {}
                    if self._event_matches_request(details, request_id):
                        self._append_feedback_to_event(event, feedback_data)
                        session.commit()
                        return
                except json.JSONDecodeError:
                    continue
        finally:
            session.close()

    def get_feedback(self, request_id: Optional[str]) -> List[Dict[str, Any]]:
        """Retrieve feedback entries for a request ID from the audit log."""
        session = self.Session()
        feedback_entries: List[Dict[str, Any]] = []
        try:
            events = session.query(AuditEvent).all()
            for event in events:
                try:
                    result = json.loads(event.result_json) if event.result_json else {}
                    if request_id is not None and not self._event_matches_request(result, request_id):
                        details = json.loads(event.details_json) if event.details_json else {}
                        if not self._event_matches_request(details, request_id):
                            continue

                    if event.feedback:
                        stored_feedback = json.loads(event.feedback)
                        if isinstance(stored_feedback, list):
                            feedback_entries.extend(stored_feedback)
                        else:
                            feedback_entries.append(stored_feedback)
                except json.JSONDecodeError:
                    continue
            return feedback_entries
        finally:
            session.close()

    @staticmethod
    def _event_matches_request(event_payload: Any, request_id: str) -> bool:
        """Determine whether an audit event payload references the request ID."""
        if not isinstance(event_payload, dict):
            return False

        candidate_keys = ("request_id", "decision_id", "id")
        if any(event_payload.get(key) == request_id for key in candidate_keys):
            return True

        for nested_key in ("final_decision", "decision", "bundle"):
            nested = event_payload.get(nested_key)
            if isinstance(nested, dict) and any(
                nested.get(key) == request_id for key in candidate_keys
            ):
                return True

        return False

    @staticmethod
    def _append_feedback_to_event(event: AuditEvent, feedback_data: Dict[str, Any]) -> None:
        existing_feedback = json.loads(event.feedback) if event.feedback else []
        if not isinstance(existing_feedback, list):
            existing_feedback = [existing_feedback]
        existing_feedback.append(feedback_data)
        event.feedback = json.dumps(existing_feedback)
