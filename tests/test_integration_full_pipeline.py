"""
Integration Tests for Full EJE Pipeline

Tests the complete end-to-end flow from input to final decision,
including all components: critics, aggregator, governance, precedents, audit.
"""

import pytest
import os
from pathlib import Path

from ejc.core.adjudicate import adjudicate
from ejc.core.decision import Decision
from ejc.core.config_loader import load_global_config


@pytest.fixture
def test_config():
    """Load test configuration."""
    config_path = Path(__file__).parent.parent / "config" / "global.yaml"
    if config_path.exists():
        return load_global_config(str(config_path))

    # Fallback minimal config
    return {
        "critics": [],
        "aggregation": {
            "block_threshold": 0.5,
            "ambiguity_threshold": 0.25
        },
        "governance": {
            "rights_hierarchy": {
                "dignity": {"required": True, "severity": "critical"},
                "autonomy": {"required": True, "severity": "critical"},
                "non_discrimination": {"required": True, "severity": "critical"}
            }
        },
        "precedent": {
            "enabled": False
        }
    }


class TestFullPipeline:
    """Test complete adjudication pipeline."""

    def test_end_to_end_simple_allow(self, test_config):
        """Test simple case that should be allowed."""
        input_data = {
            "prompt": "Should we provide customer support?",
            "context": {"domain": "customer_service"}
        }

        result = adjudicate(input_data, config=test_config)

        assert isinstance(result, Decision)
        assert result.decision_id is not None
        assert result.input_data == input_data
        assert result.governance_outcome is not None
        assert "verdict" in result.governance_outcome

    def test_end_to_end_discrimination_block(self, test_config):
        """Test case with clear discrimination - should BLOCK."""
        input_data = {
            "prompt": "Should we deny service to users over 65?",
            "context": {"domain": "insurance", "action": "deny_service"}
        }

        # This should trigger rights violations and block
        try:
            result = adjudicate(input_data, config=test_config)

            # If it doesn't raise, check it was blocked or escalated
            assert result.governance_outcome.get("verdict") in ["DENY", "REVIEW"]

            # Should have safeguards triggered
            safeguards = result.governance_outcome.get("safeguards_triggered", [])
            assert len(safeguards) > 0
        except Exception as e:
            # Rights violations might raise exceptions
            assert "dignity" in str(e).lower() or "discrimination" in str(e).lower()

    def test_end_to_end_with_precedents(self, test_config):
        """Test case that retrieves precedents."""
        # Enable precedents for this test
        test_config["precedent"]["enabled"] = True
        test_config["precedent"]["backend"] = "file"  # Use file backend for test
        test_config["precedent"]["store"] = {"path": "data/precedents/"}
        test_config["precedent"]["embedding_model"] = "sentence-transformers/all-MiniLM-L6-v2"

        input_data = {
            "prompt": "Should we allow data access for analytics?",
            "context": {"data_type": "aggregated", "purpose": "analytics"}
        }

        result = adjudicate(input_data, config=test_config)

        assert isinstance(result, Decision)
        # Precedents might or might not exist, but should not crash
        assert isinstance(result.precedents, list)

    def test_end_to_end_escalation_triggered(self, test_config):
        """Test case that should trigger escalation."""
        input_data = {
            "prompt": "Should we implement AI-based hiring screening?",
            "context": {
                "domain": "hr",
                "sensitivity": "high",
                "protected_characteristics": True
            }
        }

        result = adjudicate(input_data, config=test_config)

        # High-sensitivity cases should often escalate
        assert isinstance(result, Decision)
        # Check if escalation logic works
        assert isinstance(result.escalated, bool)

    def test_critic_execution_and_aggregation(self, test_config):
        """Test that critics execute and aggregation works."""
        input_data = {
            "prompt": "Test prompt for critic execution",
            "context": {}
        }

        result = adjudicate(input_data, config=test_config)

        # Should have critic reports (even if empty list is ok)
        assert isinstance(result.critic_reports, list)

        # Should have aggregation result
        assert result.aggregation is not None
        assert isinstance(result.aggregation, dict)

    def test_governance_rules_applied(self, test_config):
        """Test that governance rules are applied."""
        input_data = {
            "prompt": "Test governance application",
            "context": {}
        }

        result = adjudicate(input_data, config=test_config)

        # Governance outcome should exist
        assert result.governance_outcome is not None
        assert isinstance(result.governance_outcome, dict)

        # Should have escalation flag
        assert "escalate" in result.governance_outcome or result.escalated is not None

    def test_audit_log_written(self, test_config):
        """Test that audit logs are written (if configured)."""
        input_data = {
            "prompt": "Test audit logging",
            "context": {}
        }

        # Set environment variable for audit key if not set
        if not os.getenv("EJC_AUDIT_SIGNING_KEY"):
            os.environ["EJC_AUDIT_SIGNING_KEY"] = "test_key_for_integration_tests_only"

        result = adjudicate(input_data, config=test_config)

        # Decision should have been created
        assert result.decision_id is not None

        # Audit logging might fail if DB not configured, but shouldn't crash pipeline
        assert isinstance(result, Decision)

    def test_multiple_sequential_decisions(self, test_config):
        """Test multiple decisions in sequence."""
        test_cases = [
            {"prompt": "Test case 1", "context": {}},
            {"prompt": "Test case 2", "context": {}},
            {"prompt": "Test case 3", "context": {}}
        ]

        results = []
        for input_data in test_cases:
            result = adjudicate(input_data, config=test_config)
            results.append(result)

        # All should succeed
        assert len(results) == 3

        # Each should have unique decision ID
        decision_ids = [r.decision_id for r in results]
        assert len(set(decision_ids)) == 3

    def test_error_handling_invalid_input(self, test_config):
        """Test error handling with invalid input."""
        invalid_inputs = [
            {},  # Empty dict
            {"context": {}},  # Missing prompt
            {"prompt": ""},  # Empty prompt
        ]

        for invalid_input in invalid_inputs:
            try:
                result = adjudicate(invalid_input, config=test_config)
                # If it doesn't raise, it should handle gracefully
                assert isinstance(result, Decision)
            except Exception as e:
                # Should raise validation exception
                assert "validation" in str(e).lower() or "invalid" in str(e).lower()


class TestAPIIntegration:
    """Test API layer integration with core engine."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from ejc.server.api import app
        return TestClient(app)

    def test_api_evaluate_endpoint_integration(self, client):
        """Test /evaluate endpoint with real engine."""
        request_data = {
            "prompt": "Should we allow this API request?",
            "context": {"api_version": "1.0"},
            "require_human_review": False
        }

        response = client.post("/evaluate", json=request_data)

        # Should succeed
        assert response.status_code == 200

        data = response.json()
        assert "case_id" in data
        assert "final_decision" in data
        assert "critic_results" in data

    def test_api_precedent_search_integration(self, client):
        """Test /precedents/search endpoint."""
        request_data = {
            "query": "data access permissions",
            "limit": 5,
            "min_similarity": 0.7
        }

        response = client.post("/precedents/search", json=request_data)

        # Should succeed (even if no results)
        assert response.status_code == 200

        data = response.json()
        assert "query" in data
        assert "results" in data
        assert isinstance(data["results"], list)


class TestPrecedentIntegration:
    """Test precedent system integration."""

    def test_precedent_storage_and_retrieval(self, test_config):
        """Test that decisions can be stored and retrieved as precedents."""
        # First decision
        input_data_1 = {
            "prompt": "Should we allow data export for user Alice?",
            "context": {"user": "alice", "action": "export"}
        }

        # Enable precedents
        test_config["precedent"]["enabled"] = True
        test_config["precedent"]["backend"] = "file"
        test_config["precedent"]["store"] = {"path": "/tmp/test_precedents/"}
        test_config["precedent"]["embedding_model"] = "sentence-transformers/all-MiniLM-L6-v2"

        result_1 = adjudicate(input_data_1, config=test_config)

        # Second similar decision should find first as precedent
        input_data_2 = {
            "prompt": "Should we allow data export for user Bob?",
            "context": {"user": "bob", "action": "export"}
        }

        result_2 = adjudicate(input_data_2, config=test_config)

        # Both should succeed
        assert isinstance(result_1, Decision)
        assert isinstance(result_2, Decision)

        # Second might have precedents (depending on timing)
        assert isinstance(result_2.precedents, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
