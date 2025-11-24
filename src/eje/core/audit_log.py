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
    def append_feedback(self, event_id, feedback):
        session = self.Session()
        event = session.query(AuditEvent).filter_by(id=event_id).first()
        event.feedback = feedback
        session.commit()
        session.close()
