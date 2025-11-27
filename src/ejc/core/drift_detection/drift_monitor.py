"""
Main drift monitoring system integrating all drift detection components.

Provides unified interface for:
- Constitutional drift detection
- Precedent consistency checking
- Ethical consensus tracking
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
from sqlalchemy import create_engine, Column, String, Float, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from .constitutional_drift import ConstitutionalDriftDetector, DriftAlert
from .precedent_consistency import PrecedentConsistencyChecker
from .consensus_tracker import ConsensusTracker
from ...utils.logging import get_logger

Base = declarative_base()
logger = get_logger("ejc.drift_monitor")


class DriftAlertEntry(Base):
    """Database model for drift alerts."""

    __tablename__ = "drift_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    metrics = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    acknowledged = Column(Integer, default=0)  # 0=no, 1=yes
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String, nullable=True)


class DriftMonitor:
    """
    Main drift monitoring system.

    Integrates:
    - Constitutional drift detection
    - Precedent consistency checking
    - Ethical consensus tracking

    Provides unified API for drift monitoring and alerting.
    """

    def __init__(
        self,
        db_uri: Optional[str] = None,
        drift_threshold: float = 0.02,
        similarity_threshold: float = 0.85,
        consensus_threshold: float = 0.8
    ):
        """
        Initialize drift monitor.

        Args:
            db_uri: Database URI for storing alerts
            drift_threshold: Threshold for constitutional drift
            similarity_threshold: Threshold for precedent similarity
            consensus_threshold: Threshold for consensus
        """
        self.db_uri = db_uri or os.getenv(
            "EJC_DRIFT_DB_URI",
            "sqlite:///eleanor_data/drift_monitoring.db"
        )
        self.engine = create_engine(self.db_uri)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        # Initialize detectors
        self.constitutional_detector = ConstitutionalDriftDetector(drift_threshold)
        self.consistency_checker = PrecedentConsistencyChecker(
            similarity_threshold=similarity_threshold
        )
        self.consensus_tracker = ConsensusTracker(consensus_threshold=consensus_threshold)

    def analyze_drift(
        self,
        decisions: List[Dict],
        store_alerts: bool = True
    ) -> Dict:
        """
        Perform comprehensive drift analysis on decisions.

        Args:
            decisions: List of decision dicts
            store_alerts: Whether to store alerts in database

        Returns:
            Comprehensive drift analysis report
        """
        logger.info(f"Analyzing drift across {len(decisions)} decisions")

        # Run all detectors
        constitutional_report = self.constitutional_detector.generate_rights_protection_report(decisions)
        consistency_report = self.consistency_checker.generate_consistency_report(decisions)
        consensus_report = self.consensus_tracker.generate_consensus_report(decisions)

        # Extract alerts
        all_alerts = []

        # Constitutional drift alerts
        for alert_dict in constitutional_report.get("drift_alerts", []):
            alert = DriftAlert(
                alert_type="constitutional_drift",
                severity=alert_dict["severity"],
                title=alert_dict["title"],
                description=alert_dict["description"],
                detected_at=datetime.utcnow().isoformat(),
                metrics=alert_dict["metrics"],
                recommendations=alert_dict["recommendations"],
            )
            all_alerts.append(alert)

        # Precedent consistency alerts
        for inconsistency in consistency_report.get("inconsistencies", []):
            if inconsistency["inconsistency_score"] > 0.8:
                alert = DriftAlert(
                    alert_type="precedent_inconsistency",
                    severity="high" if inconsistency["inconsistency_score"] > 0.9 else "medium",
                    title=f"Precedent inconsistency detected",
                    description=inconsistency["explanation"],
                    detected_at=datetime.utcnow().isoformat(),
                    metrics={
                        "case_1": inconsistency["case_1_id"],
                        "case_2": inconsistency["case_2_id"],
                        "similarity": inconsistency["similarity"],
                        "verdicts": inconsistency["verdicts"],
                    },
                    recommendations=["Review both cases for policy clarification"],
                )
                all_alerts.append(alert)

        # Consensus shift alerts
        for shift in consensus_report.get("shifts_detected", []):
            if shift["magnitude"] > 0.15:
                alert = DriftAlert(
                    alert_type="consensus_shift",
                    severity="medium",
                    title=f"Consensus shift: {shift['type']}",
                    description=shift["description"],
                    detected_at=datetime.utcnow().isoformat(),
                    metrics={"magnitude": shift["magnitude"]},
                    recommendations=["Review critic configurations"],
                )
                all_alerts.append(alert)

        # Store alerts if requested
        if store_alerts:
            for alert in all_alerts:
                self.store_alert(alert)

        # Calculate overall health
        health_score = self._calculate_health_score(
            constitutional_report,
            consistency_report,
            consensus_report
        )

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health_score": health_score,
            "status": self._determine_status(health_score),
            "constitutional_drift": constitutional_report,
            "precedent_consistency": consistency_report,
            "ethical_consensus": consensus_report,
            "alerts": [
                {
                    "type": a.alert_type,
                    "severity": a.severity,
                    "title": a.title,
                    "description": a.description,
                }
                for a in sorted(all_alerts, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}[x.severity])
            ],
            "summary": self._generate_summary(all_alerts, health_score),
        }

    def store_alert(self, alert: DriftAlert) -> int:
        """
        Store drift alert in database.

        Args:
            alert: DriftAlert to store

        Returns:
            Alert ID
        """
        session: Session = self.Session()
        try:
            entry = DriftAlertEntry(
                alert_type=alert.alert_type,
                severity=alert.severity,
                title=alert.title,
                description=alert.description,
                detected_at=datetime.fromisoformat(alert.detected_at),
                metrics=alert.metrics,
                recommendations=alert.recommendations,
            )
            session.add(entry)
            session.commit()
            alert_id = entry.id
            logger.info(f"Stored {alert.severity} alert: {alert.title}")
            return alert_id
        finally:
            session.close()

    def get_alerts(
        self,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Retrieve stored alerts.

        Args:
            severity: Filter by severity
            alert_type: Filter by alert type
            acknowledged: Filter by acknowledgment status
            start_date: Filter by date
            limit: Maximum results

        Returns:
            List of alert dicts
        """
        session: Session = self.Session()
        try:
            query = session.query(DriftAlertEntry)

            if severity:
                query = query.filter(DriftAlertEntry.severity == severity)
            if alert_type:
                query = query.filter(DriftAlertEntry.alert_type == alert_type)
            if acknowledged is not None:
                query = query.filter(DriftAlertEntry.acknowledged == (1 if acknowledged else 0))
            if start_date:
                query = query.filter(DriftAlertEntry.detected_at >= start_date)

            query = query.order_by(DriftAlertEntry.detected_at.desc())
            query = query.limit(limit)

            entries = query.all()

            return [
                {
                    "id": e.id,
                    "alert_type": e.alert_type,
                    "severity": e.severity,
                    "title": e.title,
                    "description": e.description,
                    "detected_at": e.detected_at.isoformat(),
                    "metrics": e.metrics,
                    "recommendations": e.recommendations,
                    "acknowledged": bool(e.acknowledged),
                }
                for e in entries
            ]
        finally:
            session.close()

    def acknowledge_alert(
        self,
        alert_id: int,
        acknowledged_by: str
    ) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: ID of alert to acknowledge
            acknowledged_by: User acknowledging the alert

        Returns:
            Success status
        """
        session: Session = self.Session()
        try:
            entry = session.query(DriftAlertEntry).filter(
                DriftAlertEntry.id == alert_id
            ).first()

            if not entry:
                return False

            entry.acknowledged = 1
            entry.acknowledged_at = datetime.utcnow()
            entry.acknowledged_by = acknowledged_by
            session.commit()
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return True
        finally:
            session.close()

    def _calculate_health_score(
        self,
        constitutional_report: Dict,
        consistency_report: Dict,
        consensus_report: Dict
    ) -> float:
        """
        Calculate overall system health score (0-100).

        Args:
            constitutional_report: Rights protection report
            consistency_report: Precedent consistency report
            consensus_report: Consensus report

        Returns:
            Health score (0-100)
        """
        # Constitutional health (40% weight)
        const_status = constitutional_report.get("status", "drifting")
        const_score = 100 if const_status == "healthy" else 60

        # Precedent consistency (30% weight)
        inconsistencies = consistency_report.get("summary", {}).get("inconsistencies_found", 0)
        total_decisions = consistency_report.get("summary", {}).get("total_decisions_analyzed", 1)
        inconsistency_rate = inconsistencies / total_decisions if total_decisions > 0 else 0
        consistency_score = max(0, 100 - (inconsistency_rate * 500))  # Penalize inconsistencies

        # Consensus health (30% weight)
        consensus_metrics = consensus_report.get("metrics", {})
        consensus_rate = consensus_metrics.get("consensus_rate", 0.5)
        consensus_score = consensus_rate * 100

        # Weighted average
        health_score = (
            const_score * 0.4 +
            consistency_score * 0.3 +
            consensus_score * 0.3
        )

        return round(health_score, 1)

    def _determine_status(self, health_score: float) -> str:
        """Determine system status from health score."""
        if health_score >= 90:
            return "excellent"
        elif health_score >= 75:
            return "good"
        elif health_score >= 60:
            return "concerning"
        else:
            return "critical"

    def _generate_summary(
        self,
        alerts: List[DriftAlert],
        health_score: float
    ) -> Dict:
        """Generate executive summary."""
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        high_alerts = [a for a in alerts if a.severity == "high"]

        summary_text = f"System health: {health_score:.0f}/100"

        if critical_alerts:
            summary_text += f" | {len(critical_alerts)} critical alerts"
        if high_alerts:
            summary_text += f" | {len(high_alerts)} high-priority alerts"

        return {
            "health_score": health_score,
            "total_alerts": len(alerts),
            "critical_alerts": len(critical_alerts),
            "high_alerts": len(high_alerts),
            "summary_text": summary_text,
        }
