"""
Integration tests for FastAPI endpoints with EJE core.

Tests that the API layer correctly integrates with the adjudication pipeline
and precedent engine.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from ejc.server.api import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Eleanor EJE API"
    assert data["version"] == "1.0.0"
    assert "docs" in data


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "uptime_seconds" in data
    assert "components" in data
    assert "api" in data["components"]


def test_metrics_endpoint(client):
    """Test metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_cases_evaluated" in data
    assert "total_escalations" in data


def test_evaluate_endpoint_basic(client):
    """Test basic case evaluation through API."""
    request_data = {
        "prompt": "Should we allow access to basic medical information?",
        "context": {
            "user_role": "healthcare_provider",
            "sensitivity": "medium"
        },
        "require_human_review": False
    }

    response = client.post("/evaluate", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert "case_id" in data
    assert "status" in data
    assert "final_decision" in data
    assert "confidence" in data
    assert "critic_results" in data
    assert isinstance(data["critic_results"], list)
    assert "precedents_applied" in data
    assert "requires_escalation" in data
    assert "audit_log_id" in data
    assert "timestamp" in data
    assert "execution_time_ms" in data


def test_evaluate_endpoint_with_case_id(client):
    """Test evaluation with custom case ID."""
    request_data = {
        "case_id": "test_case_123",
        "prompt": "Test prompt for evaluation",
        "context": {}
    }

    response = client.post("/evaluate", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["case_id"] == "test_case_123"


def test_evaluate_endpoint_requires_escalation(client):
    """Test evaluation that requires human review."""
    request_data = {
        "prompt": "Should we proceed with this highly sensitive action?",
        "context": {"sensitivity": "critical"},
        "require_human_review": True
    }

    response = client.post("/evaluate", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["requires_escalation"] is True


def test_evaluate_endpoint_invalid_input(client):
    """Test evaluation with invalid input."""
    request_data = {
        "prompt": "",  # Empty prompt should fail
        "context": {}
    }

    response = client.post("/evaluate", json=request_data)
    # Should return 422 for validation error or 500 for internal error
    assert response.status_code in [422, 500]


def test_precedent_search_endpoint(client):
    """Test precedent search endpoint."""
    request_data = {
        "query": "medical information access",
        "limit": 5,
        "min_similarity": 0.7
    }

    response = client.post("/precedents/search", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert "query" in data
    assert data["query"] == request_data["query"]
    assert "results" in data
    assert isinstance(data["results"], list)
    assert "total_count" in data
    assert "execution_time_ms" in data

    # Check result structure if any results returned
    if len(data["results"]) > 0:
        result = data["results"][0]
        assert "precedent_id" in result
        assert "case_summary" in result
        assert "decision" in result
        assert "reasoning" in result
        assert "similarity_score" in result
        assert "created_at" in result


def test_precedent_search_with_limits(client):
    """Test precedent search respects limit parameter."""
    request_data = {
        "query": "test query",
        "limit": 3,
        "min_similarity": 0.5
    }

    response = client.post("/precedents/search", json=request_data)
    assert response.status_code == 200

    data = response.json()
    # Results should not exceed requested limit
    assert len(data["results"]) <= request_data["limit"]


def test_precedent_search_invalid_params(client):
    """Test precedent search with invalid parameters."""
    # Limit too high
    request_data = {
        "query": "test",
        "limit": 1000,  # Exceeds max of 100
        "min_similarity": 0.7
    }

    response = client.post("/precedents/search", json=request_data)
    assert response.status_code == 422  # Validation error


def test_evaluate_and_search_integration(client):
    """Test that evaluation creates precedents searchable later."""
    # First, evaluate a case
    eval_request = {
        "prompt": "Integration test: should we grant database access?",
        "context": {"resource": "database", "action": "read"},
        "require_human_review": False
    }

    eval_response = client.post("/evaluate", json=eval_request)
    assert eval_response.status_code == 200
    eval_data = eval_response.json()

    # Now search for similar precedents
    search_request = {
        "query": "database access permissions",
        "limit": 10,
        "min_similarity": 0.5
    }

    search_response = client.post("/precedents/search", json=search_request)
    assert search_response.status_code == 200
    search_data = search_response.json()

    # Verify search completed successfully
    assert "results" in search_data
    assert "total_count" in search_data


def test_concurrent_evaluations(client):
    """Test multiple concurrent evaluations."""
    import concurrent.futures

    def evaluate_case(prompt):
        request_data = {
            "prompt": prompt,
            "context": {}
        }
        response = client.post("/evaluate", json=request_data)
        return response.status_code, response.json()

    prompts = [
        "Should we allow access to resource A?",
        "Should we allow access to resource B?",
        "Should we allow access to resource C?",
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(evaluate_case, prompts))

    # All should succeed
    for status_code, data in results:
        assert status_code == 200
        assert "case_id" in data
        assert "final_decision" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
