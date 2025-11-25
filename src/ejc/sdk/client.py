"""
Python SDK Client for Eleanor Project's EJE API

Provides a clean, Pythonic interface for interacting with the Ethical
Jurisprudence Engine REST API.

Author: Eleanor Project Contributors
Date: 2025-11-25
Version: 1.0.0
"""

import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class DecisionStatus(str, Enum):
    """Decision status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


@dataclass
class CaseRequest:
    """Request to evaluate a case."""
    prompt: str
    case_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    require_human_review: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        return asdict(self)


@dataclass
class CriticResult:
    """Result from a single critic."""
    critic_name: str
    decision: str
    confidence: float
    reasoning: str
    execution_time_ms: float


@dataclass
class DecisionResponse:
    """Response from case evaluation."""
    case_id: str
    status: DecisionStatus
    final_decision: str
    confidence: float
    critic_results: List[CriticResult]
    precedents_applied: List[str]
    requires_escalation: bool
    audit_log_id: str
    timestamp: datetime
    execution_time_ms: float
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DecisionResponse':
        """Create from API response dictionary."""
        critic_results = [
            CriticResult(**cr) for cr in data.get('critic_results', [])
        ]
        return cls(
            case_id=data['case_id'],
            status=DecisionStatus(data['status']),
            final_decision=data['final_decision'],
            confidence=data['confidence'],
            critic_results=critic_results,
            precedents_applied=data.get('precedents_applied', []),
            requires_escalation=data['requires_escalation'],
            audit_log_id=data['audit_log_id'],
            timestamp=datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')),
            execution_time_ms=data['execution_time_ms']
        )


@dataclass
class PrecedentSearchRequest:
    """Request to search for precedents."""
    query: str
    limit: int = 10
    min_similarity: float = 0.7
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        return asdict(self)


@dataclass
class Precedent:
    """A precedent entry."""
    precedent_id: str
    case_summary: str
    decision: str
    reasoning: str
    similarity_score: float
    created_at: datetime


@dataclass
class PrecedentSearchResponse:
    """Response from precedent search."""
    query: str
    results: List[Precedent]
    total_count: int
    execution_time_ms: float
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PrecedentSearchResponse':
        """Create from API response dictionary."""
        results = [
            Precedent(
                precedent_id=p['precedent_id'],
                case_summary=p['case_summary'],
                decision=p['decision'],
                reasoning=p['reasoning'],
                similarity_score=p['similarity_score'],
                created_at=datetime.fromisoformat(p['created_at'].replace('Z', '+00:00'))
            )
            for p in data.get('results', [])
        ]
        return cls(
            query=data['query'],
            results=results,
            total_count=data['total_count'],
            execution_time_ms=data['execution_time_ms']
        )


@dataclass
class HealthResponse:
    """Health check response."""
    status: str
    version: str
    timestamp: datetime
    uptime_seconds: float
    components: Dict[str, str]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HealthResponse':
        """Create from API response dictionary."""
        return cls(
            status=data['status'],
            version=data['version'],
            timestamp=datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00')),
            uptime_seconds=data['uptime_seconds'],
            components=data.get('components', {})
        )


# ============================================================================
# Exceptions
# ============================================================================

class EJEClientException(Exception):
    """Base exception for SDK client errors."""
    pass


class APIConnectionError(EJEClientException):
    """Failed to connect to API."""
    pass


class AuthenticationError(EJEClientException):
    """Authentication failed."""
    pass


class ValidationError(EJEClientException):
    """Request validation failed."""
    pass


class ServerError(EJEClientException):
    """Server returned an error."""
    pass


# ============================================================================
# EJE Client
# ============================================================================

class EJEClient:
    """Python client for Eleanor Ethical Jurisprudence Engine API.
    
    This client provides a clean interface for evaluating cases, searching
    precedents, and monitoring the EJE system.
    
    Example:
        ```python
        client = EJEClient(
            base_url="https://api.example.com",
            api_token="your-token-here"
        )
        
        # Evaluate a case
        response = client.evaluate_case(
            prompt="Should this content be approved?",
            context={"user_type": "premium"}
        )
        
        print(f"Decision: {response.final_decision}")
        print(f"Confidence: {response.confidence}")
        ```
    """
    
    def __init__(
        self,
        base_url: str,
        api_token: Optional[str] = None,
        timeout: int = 30,
        verify_ssl: bool = True
    ):
        """
        Initialize the EJE client.
        
        Args:
            base_url: Base URL of the EJE API
            api_token: Optional Bearer token for authentication
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'EJE-Python-SDK/1.0.0'
        })
        
        if self.api_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_token}'
            })
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
        
        Returns:
            Parsed JSON response
        
        Raises:
            APIConnectionError: Connection failed
            AuthenticationError: Auth failed
            ValidationError: Invalid request
            ServerError: Server error
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            
            # Handle different status codes
            if response.status_code == 200 or response.status_code == 201:
                return response.json()
            elif response.status_code == 401:
                raise AuthenticationError("Authentication failed - invalid or missing token")
            elif response.status_code == 422:
                raise ValidationError(f"Validation error: {response.text}")
            elif response.status_code >= 500:
                raise ServerError(f"Server error: {response.status_code} - {response.text}")
            else:
                raise EJEClientException(f"Unexpected status {response.status_code}: {response.text}")
        
        except requests.exceptions.ConnectionError as e:
            raise APIConnectionError(f"Failed to connect to API: {e}")
        except requests.exceptions.Timeout as e:
            raise APIConnectionError(f"Request timed out: {e}")
        except requests.exceptions.RequestException as e:
            raise EJEClientException(f"Request failed: {e}")
    
    def health_check(self) -> HealthResponse:
        """Check API health status.
        
        Returns:
            HealthResponse with system status
        """
        data = self._request('GET', '/health')
        return HealthResponse.from_dict(data)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics.
        
        Returns:
            Dictionary with system metrics
        """
        return self._request('GET', '/metrics')
    
    def evaluate_case(
        self,
        prompt: str,
        case_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        require_human_review: bool = False
    ) -> DecisionResponse:
        """Evaluate a case through the EJE pipeline.
        
        Args:
            prompt: Input prompt to evaluate
            case_id: Optional case identifier
            context: Additional context for evaluation
            require_human_review: Force human escalation
        
        Returns:
            DecisionResponse with evaluation results
        """
        request = CaseRequest(
            prompt=prompt,
            case_id=case_id,
            context=context or {},
            require_human_review=require_human_review
        )
        
        logger.info(f"Evaluating case: {request.case_id or 'auto-generated'}")
        data = self._request('POST', '/evaluate', data=request.to_dict())
        return DecisionResponse.from_dict(data)
    
    def search_precedents(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.7
    ) -> PrecedentSearchResponse:
        """Search for similar precedents.
        
        Args:
            query: Search query
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold (0.0-1.0)
        
        Returns:
            PrecedentSearchResponse with matching precedents
        """
        request = PrecedentSearchRequest(
            query=query,
            limit=limit,
            min_similarity=min_similarity
        )
        
        logger.info(f"Searching precedents for: {query}")
        data = self._request('POST', '/precedents/search', data=request.to_dict())
        return PrecedentSearchResponse.from_dict(data)
    
    def close(self):
        """Close the HTTP session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# ============================================================================
# Convenience Functions
# ============================================================================

def create_client(
    base_url: str,
    api_token: Optional[str] = None,
    **kwargs
) -> EJEClient:
    """Create and configure an EJE client.
    
    Args:
        base_url: Base URL of the EJE API
        api_token: Optional Bearer token
        **kwargs: Additional client options
    
    Returns:
        Configured EJEClient instance
    """
    return EJEClient(base_url, api_token, **kwargs)
