"""EJE Python Client SDK

Provides typed client interfaces for the EJE governance engine.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
from pydantic import BaseModel, Field


# Pydantic Models

class DecisionRequest(BaseModel):
    """Request model for decision evaluation."""
    principal: str = Field(..., description="Actor making the request")
    action: str = Field(..., description="Action being requested")
    resource: str = Field(..., description="Resource being acted upon")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    profile: Optional[str] = Field(None, description="Governance profile to use")
    
class CriticEvaluation(BaseModel):
    """Individual critic evaluation result."""
    name: str
    verdict: str  # ALLOW, BLOCK, REVIEW
    confidence: float
    reasoning: str
    weight: float
    
class DecisionResponse(BaseModel):
    """Response model for decision evaluation."""
    decision_id: str
    verdict: str  # ALLOW, BLOCK, REVIEW
    confidence: float
    reasoning: str
    critics: List[CriticEvaluation]
    precedents: List[str] = Field(default_factory=list)
    timestamp: datetime
    profile_used: Optional[str] = None
    
class PrecedentRequest(BaseModel):
    """Request model for precedent search."""
    query: str = Field(..., description="Search query")
    category: Optional[str] = Field(None, description="Precedent category filter")
    domain: Optional[str] = Field(None, description="Domain filter")
    limit: int = Field(10, description="Maximum results to return")
    similarity_threshold: float = Field(0.7, description="Minimum similarity score")
    
class Precedent(BaseModel):
    """Precedent model."""
    id: str
    category: str
    description: str
    decision: str
    rationale: str
    timestamp: datetime
    similarity_score: Optional[float] = None
    
class PrecedentResponse(BaseModel):
    """Response model for precedent search."""
    results: List[Precedent]
    total_count: int
    query: str
    
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    critics_loaded: int
    uptime_seconds: float
    

# Client

class EJEClient:
    """EJE Python Client.
    
    Provides typed interfaces to the EJE governance engine.
    
    Example:
        client = EJEClient(base_url="http://localhost:8000")
        
        # Make a decision request
        response = client.decide(
            principal="user:alice",
            action="delete",
            resource="document:sensitive",
            context={"department": "engineering"},
            profile="hr_governance"
        )
        
        print(f"Decision: {response.verdict}")
        print(f"Confidence: {response.confidence}")
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        api_key: Optional[str] = None
    ):
        """Initialize EJE client.
        
        Args:
            base_url: Base URL of EJE API
            timeout: Request timeout in seconds
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self.headers
        )
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def close(self):
        """Close the client connection."""
        self.client.close()
    
    # Decision API
    
    def decide(
        self,
        principal: str,
        action: str,
        resource: str,
        context: Optional[Dict[str, Any]] = None,
        profile: Optional[str] = None
    ) -> DecisionResponse:
        """Request a governance decision.
        
        Args:
            principal: Actor making the request
            action: Action being requested
            resource: Resource being acted upon
            context: Additional context dict
            profile: Governance profile name (e.g., 'hr_governance', 'content_moderation')
        
        Returns:
            DecisionResponse with verdict, reasoning, and critic evaluations
        
        Raises:
            httpx.HTTPError: On API communication error
        """
        request = DecisionRequest(
            principal=principal,
            action=action,
            resource=resource,
            context=context or {},
            profile=profile
        )
        
        response = self.client.post(
            "/api/v1/decide",
            json=request.model_dump()
        )
        response.raise_for_status()
        
        return DecisionResponse(**response.json())
    
    def batch_decide(
        self,
        requests: List[DecisionRequest]
    ) -> List[DecisionResponse]:
        """Request multiple governance decisions in batch.
        
        Args:
            requests: List of DecisionRequest objects
        
        Returns:
            List of DecisionResponse objects
        """
        response = self.client.post(
            "/api/v1/decide/batch",
            json=[req.model_dump() for req in requests]
        )
        response.raise_for_status()
        
        return [DecisionResponse(**item) for item in response.json()]
    
    # Precedent API
    
    def search_precedents(
        self,
        query: str,
        category: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> PrecedentResponse:
        """Search for similar precedents.
        
        Args:
            query: Search query describing the case
            category: Optional category filter
            domain: Optional domain filter (e.g., 'hr', 'healthcare', 'legal')
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0.0-1.0)
        
        Returns:
            PrecedentResponse with matching precedents
        """
        request = PrecedentRequest(
            query=query,
            category=category,
            domain=domain,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
        
        response = self.client.post(
            "/api/v1/precedents/search",
            json=request.model_dump(exclude_none=True)
        )
        response.raise_for_status()
        
        return PrecedentResponse(**response.json())
    
    def add_precedent(
        self,
        category: str,
        description: str,
        decision: str,
        rationale: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Precedent:
        """Add a new precedent to the system.
        
        Args:
            category: Precedent category
            description: Case description
            decision: Decision made
            rationale: Reasoning for the decision
            metadata: Additional metadata
        
        Returns:
            Created Precedent object
        """
        payload = {
            "category": category,
            "description": description,
            "decision": decision,
            "rationale": rationale,
            "metadata": metadata or {}
        }
        
        response = self.client.post(
            "/api/v1/precedents",
            json=payload
        )
        response.raise_for_status()
        
        return Precedent(**response.json())
    
    # Health API
    
    def health(self) -> HealthResponse:
        """Check EJE service health.
        
        Returns:
            HealthResponse with service status
        """
        response = self.client.get("/api/v1/health")
        response.raise_for_status()
        
        return HealthResponse(**response.json())
    
    def ping(self) -> bool:
        """Simple ping check.
        
        Returns:
            True if service is reachable, False otherwise
        """
        try:
            response = self.client.get("/api/v1/ping")
            return response.status_code == 200
        except Exception:
            return False
