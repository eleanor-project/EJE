"""
Ground truth feedback collection for critic calibration.

Captures human review outcomes to establish ground truth for critic performance measurement.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, Column, String, Float, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os

Base = declarative_base()


class GroundTruthEntry(Base):
    """Database model for ground truth feedback."""

    __tablename__ = "ground_truth_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(String, nullable=False, index=True)
    reviewer_id = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Ground truth verdict from human reviewer
    verdict = Column(String, nullable=False)  # ALLOW, DENY, REVIEW
    confidence = Column(Float, nullable=False)  # 0.0-1.0

    # Justification for the ground truth
    justification = Column(String, nullable=True)

    # Original decision data for comparison
    critic_verdicts = Column(JSON, nullable=False)  # {critic_name: verdict}
    input_context = Column(JSON, nullable=True)

    # Metadata
    review_duration_seconds = Column(Float, nullable=True)
    flags = Column(JSON, nullable=True)  # Any special flags or notes


@dataclass
class GroundTruth:
    """Ground truth verdict from human reviewer."""

    decision_id: str
    verdict: str  # ALLOW, DENY, REVIEW
    confidence: float  # 0.0 to 1.0
    reviewer_id: str
    justification: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    critic_verdicts: Dict[str, str] = field(default_factory=dict)
    input_context: Optional[Dict[str, Any]] = None
    review_duration_seconds: Optional[float] = None
    flags: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "decision_id": self.decision_id,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "reviewer_id": self.reviewer_id,
            "justification": self.justification,
            "timestamp": self.timestamp,
            "critic_verdicts": self.critic_verdicts,
            "input_context": self.input_context,
            "review_duration_seconds": self.review_duration_seconds,
            "flags": self.flags,
        }


class FeedbackCollector:
    """
    Collects and stores ground truth feedback from human reviewers.

    This provides the training signal for calibrating critic performance.
    """

    def __init__(self, db_uri: Optional[str] = None):
        """
        Initialize feedback collector.

        Args:
            db_uri: SQLAlchemy database URI (defaults to env var or SQLite)
        """
        self.db_uri = db_uri or os.getenv(
            "EJC_CALIBRATION_DB_URI",
            "sqlite:///eleanor_data/calibration.db"
        )
        self.engine = create_engine(self.db_uri)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def submit_feedback(self, ground_truth: GroundTruth) -> str:
        """
        Submit ground truth feedback for a decision.

        Args:
            ground_truth: Ground truth verdict and metadata

        Returns:
            ID of the stored feedback entry

        Raises:
            ValueError: If feedback data is invalid
        """
        # Validate
        if ground_truth.verdict not in ["ALLOW", "DENY", "REVIEW"]:
            raise ValueError(f"Invalid verdict: {ground_truth.verdict}")
        if not (0.0 <= ground_truth.confidence <= 1.0):
            raise ValueError(f"Confidence must be 0-1: {ground_truth.confidence}")

        session: Session = self.Session()
        try:
            entry = GroundTruthEntry(
                decision_id=ground_truth.decision_id,
                reviewer_id=ground_truth.reviewer_id,
                timestamp=datetime.fromisoformat(ground_truth.timestamp),
                verdict=ground_truth.verdict,
                confidence=ground_truth.confidence,
                justification=ground_truth.justification,
                critic_verdicts=ground_truth.critic_verdicts,
                input_context=ground_truth.input_context,
                review_duration_seconds=ground_truth.review_duration_seconds,
                flags=ground_truth.flags,
            )
            session.add(entry)
            session.commit()
            entry_id = entry.id
            return str(entry_id)
        finally:
            session.close()

    def get_feedback(
        self,
        decision_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[GroundTruth]:
        """
        Retrieve ground truth feedback entries.

        Args:
            decision_id: Filter by specific decision ID
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of entries to return

        Returns:
            List of ground truth entries
        """
        session: Session = self.Session()
        try:
            query = session.query(GroundTruthEntry)

            if decision_id:
                query = query.filter(GroundTruthEntry.decision_id == decision_id)
            if start_date:
                query = query.filter(GroundTruthEntry.timestamp >= start_date)
            if end_date:
                query = query.filter(GroundTruthEntry.timestamp <= end_date)

            query = query.order_by(GroundTruthEntry.timestamp.desc())
            query = query.limit(limit)

            entries = query.all()

            return [
                GroundTruth(
                    decision_id=e.decision_id,
                    verdict=e.verdict,
                    confidence=e.confidence,
                    reviewer_id=e.reviewer_id,
                    justification=e.justification,
                    timestamp=e.timestamp.isoformat(),
                    critic_verdicts=e.critic_verdicts or {},
                    input_context=e.input_context,
                    review_duration_seconds=e.review_duration_seconds,
                    flags=e.flags,
                )
                for e in entries
            ]
        finally:
            session.close()

    def get_feedback_count(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Get count of feedback entries in date range.

        Args:
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            Number of feedback entries
        """
        session: Session = self.Session()
        try:
            query = session.query(GroundTruthEntry)
            if start_date:
                query = query.filter(GroundTruthEntry.timestamp >= start_date)
            if end_date:
                query = query.filter(GroundTruthEntry.timestamp <= end_date)
            return query.count()
        finally:
            session.close()
