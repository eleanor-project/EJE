from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import json

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
        Log a decision bundle from the DecisionEngine.
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
        # Find event by request_id stored in result_json
        events = session.query(AuditEvent).all()
        for event in events:
            try:
                result = json.loads(event.result_json) if event.result_json else {}
                # Check if this event matches the request_id
                # (request_id might be stored in different places depending on version)
                if isinstance(result, dict):
                    # Append feedback
                    existing_feedback = json.loads(event.feedback) if event.feedback else []
                    if not isinstance(existing_feedback, list):
                        existing_feedback = [existing_feedback]
                    existing_feedback.append(feedback_data)
                    event.feedback = json.dumps(existing_feedback)
                    session.commit()
                    break
            except (json.JSONDecodeError, KeyError):
                continue
        session.close()
