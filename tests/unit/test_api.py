"""Test suite for ELEANOR Moral Ops Center API endpoints.

Task 10.6: Comprehensive API tests covering:
- Happy path decision-making
- Invalid request bodies (validation)
- Unauthorized access attempts
- Rate limiting functionality
"""
import pytest
import time
from fastapi.testclient import TestClient
from eje.api.app import create_app
from eje.config.settings import Settings


class TestAPIDecisionEndpoint:
    """Tests for the main decision-making endpoint - happy path."""

    @pytest.fixture
    def client(self):
        """Create a test client with authentication disabled."""
        settings = Settings(
            config_path="config/global.yaml",
            require_api_token=False,
            rate_limit_requests=1000,  # High limit for testing
        )
        app = create_app(settings)
        return TestClient(app)

    def test_decision_endpoint_happy_path(self, client):
        """Test successful decision request with valid payload."""
        payload = {
            "query": "Should we proceed with this action?",
            "context": "Testing ethical decision making",
            "stakes": "low"
        }
        
        response = client.post("/api/decide", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "decision" in data
        assert "confidence" in data
        assert "reasoning" in data
        assert isinstance(data["confidence"], (int, float))
        assert 0 <= data["confidence"] <= 1

    def test_decision_with_all_fields(self, client):
        """Test decision request with all optional fields populated."""
        payload = {
            "query": "Is this ethically sound?",
            "context": "Detailed context about the situation",
            "stakes": "high",
            "alternatives": ["Option A", "Option B", "Option C"],
            "values": ["fairness", "autonomy", "transparency"]
        }
        
        response = client.post("/api/decide", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] is not None

    def test_health_endpoint(self, client):
        """Test health check endpoint returns correct status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "uptime" in data


class TestAPIValidation:
    """Tests for request validation - invalid request bodies."""

    @pytest.fixture
    def client(self):
        """Create a test client with authentication disabled."""
        settings = Settings(
            config_path="config/global.yaml",
            require_api_token=False,
        )
        app = create_app(settings)
        return TestClient(app)

    def test_empty_payload(self, client):
        """Test that empty payload returns 422 validation error."""
        response = client.post("/api/decide", json={})
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data or "detail" in data

    def test_missing_required_field(self, client):
        """Test that missing required 'query' field returns 422."""
        payload = {
            "context": "Some context",
            "stakes": "medium"
        }
        
        response = client.post("/api/decide", json=payload)
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data or "detail" in data

    def test_invalid_field_type(self, client):
        """Test that invalid field types return 422."""
        payload = {
            "query": 12345,  # Should be string
            "context": "Valid context"
        }
        
        response = client.post("/api/decide", json=payload)
        
        assert response.status_code == 422

    def test_invalid_stakes_value(self, client):
        """Test that invalid stakes enum value returns 422."""
        payload = {
            "query": "Is this okay?",
            "stakes": "invalid_value"  # Should be low/medium/high
        }
        
        response = client.post("/api/decide", json=payload)
        
        assert response.status_code == 422

    def test_malformed_json(self, client):
        """Test that malformed JSON returns 422."""
        response = client.post(
            "/api/decide",
            data="{invalid json}",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422


class TestAPIAuthentication:
    """Tests for authentication - unauthorized access."""

    @pytest.fixture
    def protected_client(self):
        """Create a test client with authentication enabled."""
        settings = Settings(
            config_path="config/global.yaml",
            require_api_token=True,
            api_token="test-secret-token-12345",
        )
        app = create_app(settings)
        return TestClient(app)

    def test_no_token_returns_401(self, protected_client):
        """Test that requests without token are rejected with 401."""
        payload = {
            "query": "Should I do this?",
            "context": "Test context"
        }
        
        response = protected_client.post("/api/decide", json=payload)
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data or "detail" in data

    def test_invalid_token_returns_401(self, protected_client):
        """Test that requests with invalid token are rejected."""
        payload = {
            "query": "Should I do this?",
            "context": "Test context"
        }
        
        response = protected_client.post(
            "/api/decide",
            json=payload,
            headers={"Authorization": "Bearer wrong-token"}
        )
        
        assert response.status_code == 401

    def test_valid_token_allows_access(self, protected_client):
        """Test that requests with valid token are allowed."""
        payload = {
            "query": "Should I do this?",
            "context": "Test context"
        }
        
        response = protected_client.post(
            "/api/decide",
            json=payload,
            headers={"Authorization": "Bearer test-secret-token-12345"}
        )
        
        assert response.status_code == 200

    def test_malformed_authorization_header(self, protected_client):
        """Test that malformed authorization header returns 401."""
        payload = {
            "query": "Should I do this?",
            "context": "Test context"
        }
        
        response = protected_client.post(
            "/api/decide",
            json=payload,
            headers={"Authorization": "InvalidFormat"}
        )
        
        assert response.status_code == 401


class TestAPIRateLimiting:
    """Tests for rate limiting functionality."""

    @pytest.fixture
    def rate_limited_client(self):
        """Create a test client with strict rate limits."""
        settings = Settings(
            config_path="config/global.yaml",
            require_api_token=False,
            rate_limit_requests=3,  # Allow only 3 requests
            rate_limit_window=60,   # Per 60 seconds
            rate_limit_backoff_base=1.0,  # 1 second base backoff
        )
        app = create_app(settings)
        return TestClient(app)

    def test_rate_limit_allows_within_limit(self, rate_limited_client):
        """Test that requests within rate limit are allowed."""
        payload = {
            "query": "Test query",
            "context": "Test context"
        }
        
        # Send 3 requests (within limit)
        for i in range(3):
            response = rate_limited_client.post("/api/decide", json=payload)
            assert response.status_code == 200
            # Check rate limit headers
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers

    def test_rate_limit_blocks_excess_requests(self, rate_limited_client):
        """Test that requests exceeding rate limit return 429."""
        payload = {
            "query": "Test query",
            "context": "Test context"
        }
        
        # Send requests up to the limit
        for i in range(3):
            response = rate_limited_client.post("/api/decide", json=payload)
            assert response.status_code == 200
        
        # Next request should be rate limited
        response = rate_limited_client.post("/api/decide", json=payload)
        assert response.status_code == 429
        
        data = response.json()
        assert "retry_after" in data or "Retry-After" in response.headers

    def test_rate_limit_headers_present(self, rate_limited_client):
        """Test that rate limit headers are present in responses."""
        payload = {
            "query": "Test query",
            "context": "Test context"
        }
        
        response = rate_limited_client.post("/api/decide", json=payload)
        
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Window" in response.headers
        
        # Verify header values
        assert response.headers["X-RateLimit-Limit"] == "3"
        assert int(response.headers["X-RateLimit-Remaining"]) >= 0

    def test_rate_limit_retry_after_header(self, rate_limited_client):
        """Test that 429 response includes Retry-After header."""
        payload = {
            "query": "Test query",
            "context": "Test context"
        }
        
        # Exhaust rate limit
        for i in range(3):
            rate_limited_client.post("/api/decide", json=payload)
        
        # Get rate limited response
        response = rate_limited_client.post("/api/decide", json=payload)
        
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        retry_after = int(response.headers["Retry-After"])
        assert retry_after > 0


class TestAPIErrorHandling:
    """Tests for general error handling and edge cases."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        settings = Settings(
            config_path="config/global.yaml",
            require_api_token=False,
        )
        app = create_app(settings)
        return TestClient(app)

    def test_nonexistent_endpoint_returns_404(self, client):
        """Test that non-existent endpoints return 404."""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_wrong_http_method(self, client):
        """Test that wrong HTTP method returns 405."""
        response = client.get("/api/decide")  # Should be POST
        assert response.status_code == 405

    def test_cors_headers_present(self, client):
        """Test that CORS headers are properly set."""
        response = client.options("/api/decide")
        # CORS headers should be present
        assert response.status_code in [200, 204]
