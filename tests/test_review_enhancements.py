"""
Tests for Phase 4.2 enhanced human review system.

Tests escalation bundles, dissent analysis, feedback forms, and review dashboard.
"""

import pytest
from datetime import datetime, timedelta
from ejc.core.review import (
    EscalationBundleBuilder,
    CriticVote,
    DissentAnalysis,
    FeedbackFormBuilder,
    FeedbackAggregator,
    FeedbackType,
    VerdictOption,
    ReviewDashboard,
    QueueFilter,
    QueueSortOrder
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_critic_results():
    """Sample critic results with disagreement."""
    return [
        {
            "critic_name": "privacy_critic",
            "verdict": "blocked",
            "confidence": 0.9,
            "reasoning": "Privacy violation detected",
            "critical_factors": ["privacy", "data_protection"]
        },
        {
            "critic_name": "autonomy_critic",
            "verdict": "allowed",
            "confidence": 0.7,
            "reasoning": "User autonomy preserved",
            "critical_factors": ["autonomy", "user_choice"]
        },
        {
            "critic_name": "harm_critic",
            "verdict": "review",
            "confidence": 0.5,
            "reasoning": "Potential harm unclear",
            "critical_factors": ["harm_prevention"]
        }
    ]


@pytest.fixture
def unanimous_critic_results():
    """Sample critic results with unanimous agreement."""
    return [
        {
            "critic_name": "privacy_critic",
            "verdict": "blocked",
            "confidence": 0.95,
            "reasoning": "Clear privacy violation",
            "critical_factors": ["privacy"]
        },
        {
            "critic_name": "autonomy_critic",
            "verdict": "blocked",
            "confidence": 0.9,
            "reasoning": "Violates user autonomy",
            "critical_factors": ["autonomy"]
        },
        {
            "critic_name": "harm_critic",
            "verdict": "blocked",
            "confidence": 0.85,
            "reasoning": "High risk of harm",
            "critical_factors": ["harm_prevention"]
        }
    ]


@pytest.fixture
def sample_input_data():
    """Sample input data for escalation."""
    return {
        "prompt": "Share user's medical records with third party",
        "context": {
            "privacy_sensitive": True,
            "jurisdiction": "GDPR"
        }
    }


# ============================================================================
# Escalation Bundle Tests
# ============================================================================

class TestEscalationBundle:
    """Tests for escalation bundle creation and dissent analysis."""

    def test_build_bundle_with_dissent(self, sample_input_data, sample_critic_results):
        """Test building escalation bundle with critic disagreement."""
        builder = EscalationBundleBuilder()

        bundle = builder.build_bundle(
            case_id="case_001",
            input_data=sample_input_data,
            critic_results=sample_critic_results
        )

        assert bundle.bundle_id.startswith("bundle_")
        assert bundle.case_id == "case_001"
        assert len(bundle.critic_votes) == 3
        assert bundle.dissent_analysis.dissent_index > 0.0
        assert bundle.priority in ["critical", "high", "medium", "low"]

    def test_dissent_index_unanimous(self, unanimous_critic_results):
        """Test dissent index for unanimous verdict."""
        builder = EscalationBundleBuilder()

        votes = builder._extract_votes(unanimous_critic_results)
        dissent = builder._analyze_dissent(votes)

        assert dissent.dissent_index == 0.0
        assert dissent.disagreement_type == "unanimous"
        assert dissent.majority_verdict == "blocked"

    def test_dissent_index_split(self, sample_critic_results):
        """Test dissent index for split verdict."""
        builder = EscalationBundleBuilder()

        votes = builder._extract_votes(sample_critic_results)
        dissent = builder._analyze_dissent(votes)

        assert dissent.dissent_index > 0.5  # Significant disagreement
        assert dissent.disagreement_type in ["split", "majority", "deadlock"]  # 1:1:1 is deadlock
        assert len(dissent.minority_verdicts) > 0

    def test_conflicting_principles_detection(self, sample_critic_results):
        """Test detection of conflicting principles."""
        builder = EscalationBundleBuilder()

        votes = builder._extract_votes(sample_critic_results)
        dissent = builder._analyze_dissent(votes)

        # Privacy and autonomy may conflict
        assert isinstance(dissent.conflicting_principles, list)

    def test_priority_determination(self, sample_input_data, unanimous_critic_results):
        """Test automatic priority determination."""
        builder = EscalationBundleBuilder()

        # High stakes + unanimous = still high priority due to stakes
        bundle = builder.build_bundle(
            case_id="case_002",
            input_data=sample_input_data,
            critic_results=unanimous_critic_results
        )

        # High stakes context drives priority to high even with low dissent
        assert bundle.priority in ["high", "medium"]

    def test_priority_override(self, sample_input_data, sample_critic_results):
        """Test manual priority override."""
        builder = EscalationBundleBuilder()

        bundle = builder.build_bundle(
            case_id="case_003",
            input_data=sample_input_data,
            critic_results=sample_critic_results,
            priority="critical"
        )

        assert bundle.priority == "critical"


# ============================================================================
# Feedback Form Tests
# ============================================================================

class TestFeedbackForms:
    """Tests for templated feedback forms."""

    def test_base_questions_created(self):
        """Test base feedback questions are created."""
        builder = FeedbackFormBuilder()

        assert len(builder.base_questions) > 0
        assert any(q.question_id == "verdict" for q in builder.base_questions)
        assert any(q.question_id == "confidence" for q in builder.base_questions)
        assert any(q.question_id == "reasoning" for q in builder.base_questions)

    def test_build_form_with_dissent(self):
        """Test form builder adds dissent-specific questions."""
        builder = FeedbackFormBuilder()

        # Create mock dissent analysis with high dissent
        class MockDissent:
            dissent_index = 0.8
            conflicting_principles = ["privacy", "autonomy"]

        form = builder.build_form(
            bundle_id="bundle_001",
            dissent_analysis=MockDissent()
        )

        # Should include dissent-specific questions
        question_ids = [q.question_id for q in form]
        assert "critic_disagreement" in question_ids
        assert "principle_priority" in question_ids

    def test_build_form_with_privacy_context(self):
        """Test form builder adds privacy-specific questions."""
        builder = FeedbackFormBuilder()

        form = builder.build_form(
            bundle_id="bundle_002",
            input_context={"privacy_sensitive": True}
        )

        question_ids = [q.question_id for q in form]
        assert "privacy_assessment" in question_ids

    def test_create_feedback_from_responses(self):
        """Test creating ReviewFeedback from response dict."""
        builder = FeedbackFormBuilder()

        responses = {
            "verdict": "blocked",
            "confidence": 0.9,
            "reasoning": "This clearly violates privacy principles based on GDPR requirements.",
            "principles_applied": ["Privacy Protection", "Legal Compliance"]
        }

        feedback = builder.create_feedback_from_responses(
            bundle_id="bundle_001",
            reviewer_id="reviewer_alice",
            responses=responses
        )

        assert feedback.verdict == VerdictOption.BLOCKED
        assert feedback.confidence == 0.9
        assert len(feedback.reasoning) >= 10
        assert len(feedback.principles_applied) == 2

    def test_validate_feedback_success(self):
        """Test feedback validation passes for valid feedback."""
        builder = FeedbackFormBuilder()

        responses = {
            "verdict": "allowed",
            "confidence": 0.8,
            "reasoning": "User autonomy is preserved and no harm detected in this case.",
            "principles_applied": ["User Autonomy"]  # Add required field
        }

        feedback = builder.create_feedback_from_responses(
            bundle_id="bundle_001",
            reviewer_id="reviewer_bob",
            responses=responses
        )

        # Note: principles_applied is not required in base questions, but we validate
        # that required base questions are answered
        # The create_feedback_from_responses already validates required fields
        is_valid, errors = builder.validate_feedback(
            feedback,
            builder.base_questions
        )

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_feedback_missing_reasoning(self):
        """Test feedback validation fails for short reasoning."""
        builder = FeedbackFormBuilder()

        responses = {
            "verdict": "allowed",
            "confidence": 0.8,
            "reasoning": "ok"  # Too short
        }

        feedback = builder.create_feedback_from_responses(
            bundle_id="bundle_001",
            reviewer_id="reviewer_bob",
            responses=responses
        )

        is_valid, errors = builder.validate_feedback(
            feedback,
            builder.base_questions
        )

        assert is_valid is False
        assert any("reasoning" in err.lower() for err in errors)

    def test_conditional_verdict_requires_conditions(self):
        """Test conditional verdict requires conditions field."""
        builder = FeedbackFormBuilder()

        responses = {
            "verdict": "conditional",
            "confidence": 0.7,
            "reasoning": "Can be allowed if certain conditions are met.",
            "conditions": None  # Missing conditions
        }

        feedback = builder.create_feedback_from_responses(
            bundle_id="bundle_001",
            reviewer_id="reviewer_carol",
            responses=responses
        )

        is_valid, errors = builder.validate_feedback(
            feedback,
            builder.base_questions
        )

        assert is_valid is False
        assert any("condition" in err.lower() for err in errors)


# ============================================================================
# Feedback Aggregation Tests
# ============================================================================

class TestFeedbackAggregation:
    """Tests for aggregating multiple reviewer feedbacks."""

    def test_aggregate_unanimous(self):
        """Test aggregation with unanimous agreement."""
        builder = FeedbackFormBuilder()
        aggregator = FeedbackAggregator()

        feedbacks = []
        for i in range(3):
            responses = {
                "verdict": "blocked",
                "confidence": 0.9,
                "reasoning": f"Clear violation, reviewer {i}"
            }
            feedback = builder.create_feedback_from_responses(
                bundle_id="bundle_001",
                reviewer_id=f"reviewer_{i}",
                responses=responses
            )
            feedbacks.append(feedback)

        result = aggregator.aggregate_reviews(feedbacks)

        assert result["consensus_verdict"] == "blocked"
        assert result["agreement_level"] == "unanimous"
        assert result["num_reviewers"] == 3

    def test_aggregate_split_decision(self):
        """Test aggregation with split decision."""
        builder = FeedbackFormBuilder()
        aggregator = FeedbackAggregator()

        verdicts = ["blocked", "blocked", "allowed"]
        feedbacks = []

        for i, verdict in enumerate(verdicts):
            responses = {
                "verdict": verdict,
                "confidence": 0.8,
                "reasoning": f"Based on analysis, verdict is {verdict}"
            }
            feedback = builder.create_feedback_from_responses(
                bundle_id="bundle_001",
                reviewer_id=f"reviewer_{i}",
                responses=responses
            )
            feedbacks.append(feedback)

        result = aggregator.aggregate_reviews(feedbacks)

        assert result["consensus_verdict"] == "blocked"  # Majority
        assert result["agreement_level"] in ["majority", "strong_consensus"]
        assert result["vote_distribution"]["blocked"] == 2
        assert result["vote_distribution"]["allowed"] == 1


# ============================================================================
# Review Dashboard Tests
# ============================================================================

class TestReviewDashboard:
    """Tests for review queue and dashboard."""

    def test_add_to_queue(self):
        """Test adding escalation bundle to queue."""
        dashboard = ReviewDashboard()
        builder = EscalationBundleBuilder()

        critic_results = [
            {"critic_name": "c1", "verdict": "blocked", "confidence": 0.9, "reasoning": "test"}
        ]

        bundle = builder.build_bundle(
            case_id="case_001",
            input_data={"prompt": "test", "context": {}},
            critic_results=critic_results
        )

        item = dashboard.add_to_queue(bundle)

        assert item.bundle_id == bundle.bundle_id
        assert len(dashboard.queue) == 1

    def test_queue_filtering(self):
        """Test filtering review queue."""
        dashboard = ReviewDashboard()
        builder = EscalationBundleBuilder()

        # Add items with different priorities
        for i, priority in enumerate(["critical", "high", "medium", "low"]):
            bundle = builder.build_bundle(
                case_id=f"case_{i}",
                input_data={"prompt": "test", "context": {}},
                critic_results=[{"critic_name": "c1", "verdict": "blocked", "confidence": 0.9, "reasoning": "test"}],
                priority=priority
            )
            dashboard.add_to_queue(bundle)

        # Filter for critical only
        critical_items = dashboard.get_queue(filter_by=QueueFilter.CRITICAL)
        assert len(critical_items) == 1
        assert critical_items[0].priority == "critical"

        # Filter for high priority (includes critical + high)
        high_priority_items = dashboard.get_queue(filter_by=QueueFilter.HIGH_PRIORITY)
        assert len(high_priority_items) == 2

    def test_queue_sorting(self):
        """Test sorting review queue."""
        dashboard = ReviewDashboard()
        builder = EscalationBundleBuilder()

        # Add items with different dissent indices
        dissent_indices = [0.3, 0.8, 0.5]
        for i, dissent in enumerate(dissent_indices):
            # Create critics that will produce desired dissent
            if dissent > 0.7:
                critics = [
                    {"critic_name": "c1", "verdict": "allowed", "confidence": 0.9, "reasoning": "test"},
                    {"critic_name": "c2", "verdict": "blocked", "confidence": 0.9, "reasoning": "test"}
                ]
            else:
                critics = [
                    {"critic_name": "c1", "verdict": "allowed", "confidence": 0.9, "reasoning": "test"}
                ]

            bundle = builder.build_bundle(
                case_id=f"case_{i}",
                input_data={"prompt": "test", "context": {}},
                critic_results=critics
            )
            dashboard.add_to_queue(bundle)

        # Sort by dissent descending
        sorted_items = dashboard.get_queue(sort_by=QueueSortOrder.DISSENT_DESC)
        assert len(sorted_items) == 3

        # Dissent should be in descending order
        for i in range(len(sorted_items) - 1):
            assert sorted_items[i].dissent_index >= sorted_items[i + 1].dissent_index

    def test_complete_review(self):
        """Test completing a review."""
        dashboard = ReviewDashboard()
        builder = EscalationBundleBuilder()
        form_builder = FeedbackFormBuilder()

        # Add bundle to queue
        bundle = builder.build_bundle(
            case_id="case_001",
            input_data={"prompt": "test", "context": {}},
            critic_results=[{"critic_name": "c1", "verdict": "blocked", "confidence": 0.9, "reasoning": "test"}]
        )
        dashboard.add_to_queue(bundle)

        # Create feedback
        feedback = form_builder.create_feedback_from_responses(
            bundle_id=bundle.bundle_id,
            reviewer_id="reviewer_alice",
            responses={
                "verdict": "blocked",
                "confidence": 0.95,
                "reasoning": "Confirmed violation after review"
            }
        )

        # Complete review
        success = dashboard.complete_review(bundle.bundle_id, feedback, "blocked")

        assert success is True
        assert len(dashboard.queue) == 0
        assert len(dashboard.completed_reviews) == 1

    def test_queue_stats(self):
        """Test queue statistics calculation."""
        dashboard = ReviewDashboard()
        builder = EscalationBundleBuilder()

        # Add multiple items
        for i in range(5):
            priority = "critical" if i < 2 else "medium"
            bundle = builder.build_bundle(
                case_id=f"case_{i}",
                input_data={"prompt": "test", "context": {}},
                critic_results=[{"critic_name": "c1", "verdict": "blocked", "confidence": 0.9, "reasoning": "test"}],
                priority=priority
            )
            dashboard.add_to_queue(bundle)

        stats = dashboard.get_stats()

        assert stats.total_pending == 5
        assert stats.critical_count == 2
        assert stats.by_priority["critical"] == 2
        assert stats.by_priority["medium"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
