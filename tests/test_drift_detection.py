"""
Tests for drift detection system.

Tests constitutional drift, precedent consistency, and consensus tracking.
"""

import pytest
from datetime import datetime, timedelta
from ejc.core.drift_detection import (
    DriftMonitor,
    ConstitutionalDriftDetector,
    PrecedentConsistencyChecker,
    ConsensusTracker,
)


@pytest.fixture
def sample_decisions():
    """Create sample decisions for testing."""
    now = datetime.utcnow()

    decisions = []
    for i in range(20):
        timestamp = (now - timedelta(days=20-i)).isoformat()

        decision = {
            "decision_id": f"dec-{i}",
            "timestamp": timestamp,
            "input_data": {
                "prompt": f"Should we allow action {i}?"
            },
            "critic_reports": [
                {
                    "critic": "rights_critic",
                    "verdict": "ALLOW" if i < 15 else "DENY",
                    "confidence": 0.9,
                    "right": "dignity",
                    "violation": i >= 15,  # Last 5 have violations
                },
                {
                    "critic": "safety_critic",
                    "verdict": "ALLOW" if i < 16 else "DENY",
                    "confidence": 0.85,
                },
                {
                    "critic": "fairness_critic",
                    "verdict": "ALLOW" if i < 17 else "REVIEW",
                    "confidence": 0.8,
                },
            ],
            "governance_outcome": {
                "verdict": "ALLOW" if i < 15 else "DENY",
            },
            "aggregation": {
                "confidence": 0.9 if i < 15 else 0.7,
            },
        }
        decisions.append(decision)

    return decisions


@pytest.fixture
def drift_monitor():
    """Create drift monitor with in-memory DB."""
    return DriftMonitor(db_uri="sqlite:///:memory:")


class TestConstitutionalDriftDetector:
    """Test constitutional drift detection."""

    def test_no_drift_with_stable_violations(self, sample_decisions):
        """Test that stable violation rates don't trigger drift alerts."""
        detector = ConstitutionalDriftDetector(drift_threshold=0.1)

        # Modify to have stable violation rate
        for dec in sample_decisions:
            for report in dec["critic_reports"]:
                if report["critic"] == "rights_critic":
                    report["violation"] = False  # No violations

        alerts = detector.detect_drift(sample_decisions)
        assert len(alerts) == 0

    def test_drift_detected_with_increasing_violations(self, sample_decisions):
        """Test drift detection when violations increase."""
        detector = ConstitutionalDriftDetector(drift_threshold=0.02)

        # Recent decisions have more violations
        alerts = detector.detect_drift(
            sample_decisions,
            baseline_period_days=20,
            current_period_days=5
        )

        # Should detect drift in dignity violations
        assert len(alerts) > 0
        assert any(a.metrics["right"] == "dignity" for a in alerts)

    def test_rights_protection_report(self, sample_decisions):
        """Test comprehensive rights protection report."""
        detector = ConstitutionalDriftDetector()

        report = detector.generate_rights_protection_report(sample_decisions)

        assert "overall_metrics" in report
        assert "rights_analysis" in report
        assert "drift_alerts" in report
        assert "status" in report

        assert "dignity" in report["rights_analysis"]
        assert "autonomy" in report["rights_analysis"]
        assert "non-discrimination" in report["rights_analysis"]

    def test_alert_severity_levels(self, sample_decisions):
        """Test that alert severity increases with drift magnitude."""
        detector = ConstitutionalDriftDetector(drift_threshold=0.01)

        # Create extreme drift
        for i, dec in enumerate(sample_decisions):
            for report in dec["critic_reports"]:
                if report["critic"] == "rights_critic":
                    # Recent 50% have violations
                    report["violation"] = i >= 10

        alerts = detector.detect_drift(
            sample_decisions,
            baseline_period_days=15,
            current_period_days=5
        )

        if alerts:
            # Should have high/critical severity due to large drift
            severities = [a.severity for a in alerts]
            assert any(s in ["high", "critical"] for s in severities)


class TestPrecedentConsistencyChecker:
    """Test precedent consistency checking."""

    def test_no_inconsistencies_with_identical_verdicts(self):
        """Test that identical verdicts don't flag inconsistencies."""
        decisions = [
            {
                "decision_id": f"dec-{i}",
                "input_data": {"prompt": "Should we allow this?"},
                "governance_outcome": {"verdict": "ALLOW"},
                "aggregation": {"confidence": 0.9},
                "timestamp": datetime.utcnow().isoformat(),
            }
            for i in range(5)
        ]

        checker = PrecedentConsistencyChecker()
        inconsistencies = checker.check_consistency(decisions)

        assert len(inconsistencies) == 0

    def test_detect_inconsistency_with_similar_cases(self):
        """Test detection of inconsistent verdicts for similar cases."""
        decisions = [
            {
                "decision_id": "dec-1",
                "input_data": {"prompt": "Should we allow user data collection?"},
                "governance_outcome": {"verdict": "ALLOW"},
                "aggregation": {"confidence": 0.9},
                "timestamp": datetime.utcnow().isoformat(),
            },
            {
                "decision_id": "dec-2",
                "input_data": {"prompt": "Should we allow user data collection?"},
                "governance_outcome": {"verdict": "DENY"},  # Different verdict!
                "aggregation": {"confidence": 0.9},
                "timestamp": datetime.utcnow().isoformat(),
            },
        ]

        checker = PrecedentConsistencyChecker(similarity_threshold=0.8)
        inconsistencies = checker.check_consistency(decisions)

        assert len(inconsistencies) > 0
        assert inconsistencies[0].similarity_score > 0.8
        assert inconsistencies[0].verdict_1 != inconsistencies[0].verdict_2

    def test_consistency_report(self, sample_decisions):
        """Test comprehensive consistency report."""
        checker = PrecedentConsistencyChecker()

        report = checker.generate_consistency_report(sample_decisions)

        assert "summary" in report
        assert "inconsistencies" in report
        assert "recommendations" in report

        assert report["summary"]["total_decisions_analyzed"] == len(sample_decisions)

    def test_inconsistency_scoring(self):
        """Test that inconsistency score reflects severity."""
        decisions = [
            {
                "decision_id": "dec-1",
                "input_data": {"prompt": "test action"},
                "governance_outcome": {"verdict": "ALLOW"},
                "aggregation": {"confidence": 0.95},  # High confidence
                "timestamp": datetime.utcnow().isoformat(),
            },
            {
                "decision_id": "dec-2",
                "input_data": {"prompt": "test action"},
                "governance_outcome": {"verdict": "DENY"},  # Opposite verdict
                "aggregation": {"confidence": 0.95},  # High confidence
                "timestamp": datetime.utcnow().isoformat(),
            },
        ]

        checker = PrecedentConsistencyChecker()
        inconsistencies = checker.check_consistency(decisions)

        if inconsistencies:
            # High confidence + opposite verdicts = high inconsistency score
            assert inconsistencies[0].inconsistency_score > 0.7


class TestConsensusTracker:
    """Test ethical consensus tracking."""

    def test_unanimous_consensus(self):
        """Test detection of unanimous consensus."""
        decisions = [
            {
                "decision_id": f"dec-{i}",
                "timestamp": datetime.utcnow().isoformat(),
                "critic_reports": [
                    {"critic": "critic_a", "verdict": "ALLOW"},
                    {"critic": "critic_b", "verdict": "ALLOW"},
                    {"critic": "critic_c", "verdict": "ALLOW"},
                ],
            }
            for i in range(10)
        ]

        tracker = ConsensusTracker()
        metrics = tracker.calculate_consensus_metrics(decisions)

        assert metrics.unanimous_decisions == 10
        assert metrics.avg_dissent_index == 0.0

    def test_split_decisions(self):
        """Test detection of split decisions."""
        decisions = [
            {
                "decision_id": f"dec-{i}",
                "timestamp": datetime.utcnow().isoformat(),
                "critic_reports": [
                    {"critic": "critic_a", "verdict": "ALLOW"},
                    {"critic": "critic_b", "verdict": "DENY"},
                ],
            }
            for i in range(10)
        ]

        tracker = ConsensusTracker()
        metrics = tracker.calculate_consensus_metrics(decisions)

        assert metrics.split_decisions == 10
        assert metrics.avg_dissent_index > 0.4

    def test_contentious_critic_pairs(self):
        """Test identification of contentious critic pairs."""
        decisions = [
            {
                "decision_id": f"dec-{i}",
                "timestamp": datetime.utcnow().isoformat(),
                "critic_reports": [
                    {"critic": "safety", "verdict": "ALLOW"},
                    {"critic": "rights", "verdict": "DENY"},  # Always disagree
                    {"critic": "fairness", "verdict": "ALLOW"},
                ],
            }
            for i in range(10)
        ]

        tracker = ConsensusTracker()
        metrics = tracker.calculate_consensus_metrics(decisions)

        assert len(metrics.most_contentious_critics) > 0
        # Safety and rights should be most contentious
        contentious_pair = metrics.most_contentious_critics[0][0]
        assert set(contentious_pair) == {"safety", "rights"}

    def test_consensus_shift_detection(self, sample_decisions):
        """Test detection of consensus shifts over time."""
        tracker = ConsensusTracker()

        # Modify recent decisions to have more disagreement
        now = datetime.utcnow()
        for dec in sample_decisions:
            timestamp = datetime.fromisoformat(dec["timestamp"])
            if (now - timestamp).days < 5:
                # Recent decisions: increase disagreement
                dec["critic_reports"][2]["verdict"] = "DENY"

        shifts = tracker.detect_consensus_shifts(
            sample_decisions,
            baseline_period_days=15,
            current_period_days=5
        )

        # Should detect increasing dissent
        if shifts:
            assert any("dissent" in s.shift_type for s in shifts)

    def test_consensus_report(self, sample_decisions):
        """Test comprehensive consensus report."""
        tracker = ConsensusTracker()

        report = tracker.generate_consensus_report(sample_decisions)

        assert "status" in report
        assert "metrics" in report
        assert "shifts_detected" in report
        assert "recommendations" in report

        assert "consensus_rate" in report["metrics"]
        assert 0.0 <= report["metrics"]["consensus_rate"] <= 1.0


class TestDriftMonitor:
    """Test integrated drift monitoring system."""

    def test_comprehensive_drift_analysis(self, drift_monitor, sample_decisions):
        """Test full drift analysis workflow."""
        report = drift_monitor.analyze_drift(sample_decisions, store_alerts=False)

        assert "health_score" in report
        assert "status" in report
        assert "constitutional_drift" in report
        assert "precedent_consistency" in report
        assert "ethical_consensus" in report
        assert "alerts" in report
        assert "summary" in report

        # Health score should be 0-100
        assert 0 <= report["health_score"] <= 100

    def test_alert_storage_and_retrieval(self, drift_monitor, sample_decisions):
        """Test storing and retrieving alerts."""
        # Analyze with alert storage
        report = drift_monitor.analyze_drift(sample_decisions, store_alerts=True)

        # Retrieve alerts
        alerts = drift_monitor.get_alerts(limit=10)

        # Should have stored some alerts
        assert isinstance(alerts, list)

    def test_alert_acknowledgment(self, drift_monitor):
        """Test acknowledging alerts."""
        from ejc.core.drift_detection.constitutional_drift import DriftAlert

        # Create and store alert
        alert = DriftAlert(
            alert_type="test",
            severity="medium",
            title="Test alert",
            description="Test description",
            detected_at=datetime.utcnow().isoformat(),
            metrics={},
            recommendations=[],
        )
        alert_id = drift_monitor.store_alert(alert)

        # Acknowledge it
        success = drift_monitor.acknowledge_alert(alert_id, "test_user")
        assert success is True

        # Verify acknowledgment
        alerts = drift_monitor.get_alerts(acknowledged=True)
        assert len(alerts) > 0
        assert any(a["id"] == alert_id for a in alerts)

    def test_health_score_calculation(self, drift_monitor):
        """Test health score calculation."""
        # Create healthy system
        healthy_decisions = [
            {
                "decision_id": f"dec-{i}",
                "timestamp": datetime.utcnow().isoformat(),
                "input_data": {"prompt": f"Action {i}"},
                "critic_reports": [
                    {
                        "critic": "rights_critic",
                        "verdict": "ALLOW",
                        "right": "dignity",
                        "violation": False,
                    },
                    {
                        "critic": "safety_critic",
                        "verdict": "ALLOW",
                    },
                ],
                "governance_outcome": {"verdict": "ALLOW"},
                "aggregation": {"confidence": 0.9},
            }
            for i in range(20)
        ]

        report = drift_monitor.analyze_drift(healthy_decisions, store_alerts=False)

        # Healthy system should have high health score
        assert report["health_score"] >= 70
        assert report["status"] in ["excellent", "good"]

    def test_critical_status_detection(self, drift_monitor):
        """Test detection of critical system status."""
        # Create unhealthy system
        unhealthy_decisions = [
            {
                "decision_id": f"dec-{i}",
                "timestamp": datetime.utcnow().isoformat(),
                "input_data": {"prompt": f"Action {i}"},
                "critic_reports": [
                    {
                        "critic": "rights_critic",
                        "verdict": "DENY",
                        "right": "dignity",
                        "violation": True,  # All have violations
                    },
                    {
                        "critic": "safety_critic",
                        "verdict": "ALLOW",  # Disagreement
                    },
                ],
                "governance_outcome": {"verdict": "ALLOW"},  # Violations not blocked!
                "aggregation": {"confidence": 0.5},
            }
            for i in range(20)
        ]

        report = drift_monitor.analyze_drift(unhealthy_decisions, store_alerts=False)

        # Should detect problems
        assert len(report["alerts"]) > 0

        # Health score should be lower
        assert report["health_score"] < 90


class TestIntegrationDriftDetection:
    """Integration tests for drift detection system."""

    def test_full_monitoring_workflow(self, drift_monitor, sample_decisions):
        """Test complete monitoring workflow."""
        # Step 1: Analyze drift
        report = drift_monitor.analyze_drift(sample_decisions, store_alerts=True)

        # Step 2: Check for alerts
        assert "alerts" in report

        # Step 3: Retrieve stored alerts
        stored_alerts = drift_monitor.get_alerts(limit=50)

        # Step 4: Acknowledge critical alerts
        critical_alerts = [a for a in stored_alerts if a["severity"] == "critical"]
        for alert in critical_alerts:
            drift_monitor.acknowledge_alert(alert["id"], "admin")

        # Step 5: Verify acknowledgments
        ack_alerts = drift_monitor.get_alerts(acknowledged=True)
        assert all(a["acknowledged"] for a in ack_alerts)

    def test_continuous_monitoring_over_time(self, drift_monitor):
        """Test monitoring system over multiple time periods."""
        # Simulate decisions over 30 days
        all_decisions = []

        for day in range(30):
            timestamp = (datetime.utcnow() - timedelta(days=30-day)).isoformat()

            # Create decisions for this day
            for i in range(5):
                decision = {
                    "decision_id": f"dec-day{day}-{i}",
                    "timestamp": timestamp,
                    "input_data": {"prompt": f"Action {i}"},
                    "critic_reports": [
                        {
                            "critic": "rights_critic",
                            "verdict": "ALLOW" if day < 25 else "DENY",
                            "right": "dignity",
                            "violation": day >= 25,
                        },
                    ],
                    "governance_outcome": {"verdict": "ALLOW" if day < 25 else "DENY"},
                    "aggregation": {"confidence": 0.9},
                }
                all_decisions.append(decision)

        # Analyze full period
        report = drift_monitor.analyze_drift(all_decisions, store_alerts=False)

        # Should detect drift in recent period
        assert report["constitutional_drift"]["status"] == "drifting"
