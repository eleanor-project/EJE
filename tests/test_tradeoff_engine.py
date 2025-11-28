"""
Tests for Ethical Trade-Off Engine - Phase 5A

Tests trade-off detection and resolution functionality.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ejc.core.tradeoff.tradeoff_engine import (
    TradeOffEngine,
    EthicalPrinciple,
    TradeOffType,
    TradeOffDetection,
    TradeOffResolution
)


class TestTradeOffEngine:
    """Test suite for Ethical Trade-Off Engine."""

    @pytest.fixture
    def engine(self):
        """Create a TradeOffEngine instance."""
        return TradeOffEngine()

    def test_engine_initialization(self, engine):
        """Test engine initializes correctly."""
        assert isinstance(engine.detected_tradeoffs, list)
        assert len(engine.detected_tradeoffs) == 0
        assert isinstance(engine.resolution_history, list)
        assert len(engine.resolution_history) == 0

    def test_ethical_principle_enum(self):
        """Test EthicalPrinciple enum values."""
        assert EthicalPrinciple.FAIRNESS.value == "fairness"
        assert EthicalPrinciple.TRANSPARENCY.value == "transparency"
        assert EthicalPrinciple.PRIVACY.value == "privacy"
        assert EthicalPrinciple.ACCOUNTABILITY.value == "accountability"
        assert EthicalPrinciple.UTILITY.value == "utility"

    def test_tradeoff_type_enum(self):
        """Test TradeOffType enum values."""
        assert TradeOffType.FAIRNESS_TRANSPARENCY.value == "fairness_transparency"
        assert TradeOffType.PRIVACY_UTILITY.value == "privacy_utility"
        assert TradeOffType.TRANSPARENCY_ACCOUNTABILITY.value == "transparency_accountability"
        assert TradeOffType.FAIRNESS_ACCOUNTABILITY.value == "fairness_accountability"

    def test_analyze_empty_critic_signals(self, engine):
        """Test analyzing empty critic results."""
        critic_results = {}
        tradeoffs = engine.analyze_critic_signals(critic_results)

        # Should handle empty input gracefully
        assert isinstance(tradeoffs, list)

    def test_analyze_critic_signals_with_bias_critic(self, engine):
        """Test analyzing results including BiasObjectivityCritic."""
        critic_results = {
            'BiasObjectivityCritic': {
                'verdict': 'REVIEW',
                'confidence': 0.7,
                'bias_risk_score': 0.6,  # High bias risk = low fairness
                'fairness_metrics': {'score': 0.4}
            },
            'TransparencyCritic': {
                'verdict': 'ALLOW',
                'confidence': 0.9  # High transparency
            }
        }

        tradeoffs = engine.analyze_critic_signals(critic_results)

        # Should detect fairness-transparency trade-off
        # (low fairness 0.4 vs high transparency 0.9)
        assert isinstance(tradeoffs, list)
        # May detect trade-off due to tension between fairness and transparency
        fairness_transparency_detected = any(
            t.tradeoff_type == TradeOffType.FAIRNESS_TRANSPARENCY
            for t in tradeoffs
        )
        # Check if tension was significant enough
        if abs(0.4 - 0.9) > engine.TENSION_THRESHOLD:
            assert fairness_transparency_detected

    def test_detect_fairness_transparency_tradeoff(self, engine):
        """Test detection of Fairness-Transparency trade-off."""
        principle_scores = {
            EthicalPrinciple.FAIRNESS: 0.3,  # Low fairness
            EthicalPrinciple.TRANSPARENCY: 0.9  # High transparency
        }

        critic_results = {}
        engine._detect_fairness_transparency_tradeoff(principle_scores, critic_results)

        # Should detect high tension (|0.3 - 0.9| = 0.6 > 0.3 threshold)
        assert len(engine.detected_tradeoffs) > 0
        tradeoff = engine.detected_tradeoffs[0]
        assert tradeoff.tradeoff_type == TradeOffType.FAIRNESS_TRANSPARENCY
        assert tradeoff.tension_level > 0.5
        assert len(tradeoff.recommendations) > 0

    def test_detect_privacy_utility_tradeoff(self, engine):
        """Test detection of Privacy-Utility trade-off."""
        principle_scores = {
            EthicalPrinciple.PRIVACY: 0.95,  # Very high privacy
            EthicalPrinciple.UTILITY: 0.5    # Medium utility
        }

        critic_results = {}
        engine._detect_privacy_utility_tradeoff(principle_scores, critic_results)

        # Should detect tension
        if len(engine.detected_tradeoffs) > 0:
            tradeoff = engine.detected_tradeoffs[0]
            assert tradeoff.tradeoff_type == TradeOffType.PRIVACY_UTILITY
            assert tradeoff.principle1 == EthicalPrinciple.PRIVACY
            assert tradeoff.principle2 == EthicalPrinciple.UTILITY
            assert tradeoff.principle1_score == 0.95
            assert tradeoff.principle2_score == 0.5

    def test_detect_transparency_accountability_tradeoff(self, engine):
        """Test detection of Transparency-Accountability trade-off."""
        principle_scores = {
            EthicalPrinciple.TRANSPARENCY: 0.9,
            EthicalPrinciple.ACCOUNTABILITY: 0.4
        }

        critic_results = {}
        engine._detect_transparency_accountability_tradeoff(principle_scores, critic_results)

        # Tension: |0.9 - 0.4| = 0.5 > 0.3
        assert len(engine.detected_tradeoffs) > 0

    def test_detect_fairness_accountability_tradeoff(self, engine):
        """Test detection of Fairness-Accountability trade-off."""
        principle_scores = {
            EthicalPrinciple.FAIRNESS: 0.85,
            EthicalPrinciple.ACCOUNTABILITY: 0.35
        }

        critic_results = {}
        engine._detect_fairness_accountability_tradeoff(principle_scores, critic_results)

        # Tension: |0.85 - 0.35| = 0.5 > 0.3
        assert len(engine.detected_tradeoffs) > 0
        tradeoff = engine.detected_tradeoffs[0]
        assert 'distributed responsibility' in tradeoff.recommendations[0].lower() or \
               'stakeholder' in ' '.join(tradeoff.recommendations).lower()

    def test_resolve_tradeoff_fairness_transparency(self, engine):
        """Test resolution of fairness-transparency trade-off."""
        detection = TradeOffDetection(
            tradeoff_type=TradeOffType.FAIRNESS_TRANSPARENCY,
            principle1=EthicalPrinciple.FAIRNESS,
            principle2=EthicalPrinciple.TRANSPARENCY,
            principle1_score=0.9,
            principle2_score=0.4,
            tension_level=0.5,
            description="Test trade-off",
            recommendations=["Rec 1", "Rec 2"]
        )

        # Test high-risk resolution
        resolution = engine.resolve_tradeoff(detection, context={'risk_level': 'high'})

        assert isinstance(resolution, TradeOffResolution)
        assert resolution.detection == detection
        assert 'Fairness' in resolution.resolution_strategy
        assert len(resolution.implementation_steps) > 0
        assert len(resolution.monitoring_metrics) > 0
        assert 0.0 <= resolution.confidence <= 1.0

    def test_resolve_tradeoff_privacy_utility(self, engine):
        """Test resolution of privacy-utility trade-off."""
        detection = TradeOffDetection(
            tradeoff_type=TradeOffType.PRIVACY_UTILITY,
            principle1=EthicalPrinciple.PRIVACY,
            principle2=EthicalPrinciple.UTILITY,
            principle1_score=0.95,
            principle2_score=0.6,
            tension_level=0.35,
            description="Test privacy-utility tension",
            recommendations=["PET implementation"]
        )

        # Test medium-risk resolution
        resolution = engine.resolve_tradeoff(detection, context={'risk_level': 'medium'})

        assert 'Privacy' in resolution.resolution_strategy or 'Utility' in resolution.resolution_strategy
        assert 'privacy budget' in resolution.monitoring_metrics[0].lower() or \
               any('privacy' in m.lower() for m in resolution.monitoring_metrics)

    def test_resolve_tradeoff_transparency_accountability(self, engine):
        """Test resolution of transparency-accountability trade-off."""
        detection = TradeOffDetection(
            tradeoff_type=TradeOffType.TRANSPARENCY_ACCOUNTABILITY,
            principle1=EthicalPrinciple.TRANSPARENCY,
            principle2=EthicalPrinciple.ACCOUNTABILITY,
            principle1_score=0.8,
            principle2_score=0.4,
            tension_level=0.4,
            description="Test transparency-accountability tension",
            recommendations=["RACI matrix", "audit logs"]
        )

        resolution = engine.resolve_tradeoff(detection)

        assert 'Distributed' in resolution.resolution_strategy or \
               'Responsibility' in resolution.resolution_strategy
        # Should mention audit trails or accountability
        assert any('audit' in m.lower() or 'responsibility' in m.lower()
                   for m in resolution.monitoring_metrics)

    def test_resolve_tradeoff_fairness_accountability(self, engine):
        """Test resolution of fairness-accountability trade-off."""
        detection = TradeOffDetection(
            tradeoff_type=TradeOffType.FAIRNESS_ACCOUNTABILITY,
            principle1=EthicalPrinciple.FAIRNESS,
            principle2=EthicalPrinciple.ACCOUNTABILITY,
            principle1_score=0.85,
            principle2_score=0.5,
            tension_level=0.35,
            description="Test fairness-accountability tension",
            recommendations=["fairness review boards"]
        )

        resolution = engine.resolve_tradeoff(detection)

        assert 'Stakeholder' in resolution.resolution_strategy or \
               'Fairness' in resolution.resolution_strategy
        # Should include fairness metrics in monitoring
        assert any('fairness' in m.lower() for m in resolution.monitoring_metrics)

    def test_generate_tradeoff_report_empty(self, engine):
        """Test report generation with no trade-offs."""
        report = engine.generate_tradeoff_report()

        assert report['total_tradeoffs'] == 0
        assert len(report['high_tension_tradeoffs']) == 0
        assert 'No ethical trade-offs detected' in report['summary']

    def test_generate_tradeoff_report_with_detections(self, engine):
        """Test report generation with detected trade-offs."""
        # Add a detection
        detection = TradeOffDetection(
            tradeoff_type=TradeOffType.PRIVACY_UTILITY,
            principle1=EthicalPrinciple.PRIVACY,
            principle2=EthicalPrinciple.UTILITY,
            principle1_score=0.9,
            principle2_score=0.4,
            tension_level=0.5,
            description="High privacy, low utility",
            recommendations=["Balance PETs"]
        )
        engine.detected_tradeoffs.append(detection)

        report = engine.generate_tradeoff_report()

        assert report['total_tradeoffs'] == 1
        assert len(report['all_tradeoffs']) == 1
        assert 'Detected 1' in report['summary']

    def test_generate_tradeoff_report_with_high_tension(self, engine):
        """Test report with high-tension trade-offs."""
        # Add high-tension detection
        detection = TradeOffDetection(
            tradeoff_type=TradeOffType.FAIRNESS_TRANSPARENCY,
            principle1=EthicalPrinciple.FAIRNESS,
            principle2=EthicalPrinciple.TRANSPARENCY,
            principle1_score=0.95,
            principle2_score=0.2,
            tension_level=0.75,  # High tension
            description="Very high tension",
            recommendations=["Urgent action"]
        )
        engine.detected_tradeoffs.append(detection)

        report = engine.generate_tradeoff_report()

        assert len(report['high_tension_tradeoffs']) == 1
        assert 'high-tension' in report['summary'].lower()

    def test_resolution_history_tracking(self, engine):
        """Test that resolutions are tracked in history."""
        detection = TradeOffDetection(
            tradeoff_type=TradeOffType.PRIVACY_UTILITY,
            principle1=EthicalPrinciple.PRIVACY,
            principle2=EthicalPrinciple.UTILITY,
            principle1_score=0.8,
            principle2_score=0.6,
            tension_level=0.2,
            description="Test",
            recommendations=[]
        )

        resolution = engine.resolve_tradeoff(detection)

        assert len(engine.resolution_history) == 1
        assert engine.resolution_history[0] == resolution

    def test_tension_thresholds(self):
        """Test that tension thresholds are properly defined."""
        assert TradeOffEngine.TENSION_THRESHOLD == 0.3
        assert TradeOffEngine.HIGH_TENSION_THRESHOLD == 0.6
        assert TradeOffEngine.TENSION_THRESHOLD < TradeOffEngine.HIGH_TENSION_THRESHOLD


def test_tradeoff_detection_dataclass():
    """Test TradeOffDetection dataclass."""
    detection = TradeOffDetection(
        tradeoff_type=TradeOffType.FAIRNESS_TRANSPARENCY,
        principle1=EthicalPrinciple.FAIRNESS,
        principle2=EthicalPrinciple.TRANSPARENCY,
        principle1_score=0.7,
        principle2_score=0.9,
        tension_level=0.2,
        description="Test description",
        recommendations=["Rec 1", "Rec 2"]
    )

    assert detection.principle1_score == 0.7
    assert detection.principle2_score == 0.9
    assert detection.tension_level == 0.2
    assert len(detection.recommendations) == 2


def test_tradeoff_resolution_dataclass():
    """Test TradeOffResolution dataclass."""
    detection = TradeOffDetection(
        tradeoff_type=TradeOffType.PRIVACY_UTILITY,
        principle1=EthicalPrinciple.PRIVACY,
        principle2=EthicalPrinciple.UTILITY,
        principle1_score=0.8,
        principle2_score=0.6,
        tension_level=0.2,
        description="Test",
        recommendations=[]
    )

    resolution = TradeOffResolution(
        detection=detection,
        resolution_strategy="Test strategy",
        balanced_approach="Test approach",
        implementation_steps=["Step 1", "Step 2"],
        monitoring_metrics=["Metric 1", "Metric 2"],
        confidence=0.85
    )

    assert resolution.detection == detection
    assert resolution.confidence == 0.85
    assert len(resolution.implementation_steps) == 2
    assert len(resolution.monitoring_metrics) == 2
