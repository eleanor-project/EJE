"""
Eleanor Judicial Engine (EJE) Python Client

Provides synchronous and asynchronous clients for the EJE REST API.

Example:
    >>> from eje_client import EJEClient
    >>> client = EJEClient(base_url="https://api.example.com", api_key="your-key")
    >>> result = client.evaluate_case(prompt="Share user data", context={"privacy_sensitive": True})
    >>> print(result["final_decision"])
"""

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import requests
from urllib.parse import urljoin


@dataclass
class EJEClientConfig:
    """Client configuration."""

    base_url: str
    api_key: Optional[str] = None
    timeout: int = 30
    headers: Optional[Dict[str, str]] = None


class EJEAPIError(Exception):
    """API error response."""

    def __init__(self, message: str, status_code: int = 0, detail: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class EJEClient:
    """
    Synchronous Eleanor Judicial Engine API Client.

    Provides methods for:
    - Case evaluation
    - Precedent search (hash-based and semantic)
    - Human review workflows
    - Calibration and drift monitoring
    - Performance analytics

    Example:
        >>> client = EJEClient(base_url="https://api.example.com", api_key="your-key")
        >>> result = client.evaluate_case(
        ...     prompt="Share user location data",
        ...     context={"privacy_sensitive": True}
        ... )
        >>> print(result["final_decision"])
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize EJE client.

        Args:
            base_url: Base URL of the EJE API
            api_key: Optional Bearer token for authentication
            timeout: Request timeout in seconds (default: 30)
            headers: Optional custom headers
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

        self.headers = {
            'Content-Type': 'application/json',
            **(headers or {})
        }

        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'

        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to API."""
        url = urljoin(self.base_url, path)

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=body,
                params=params,
                timeout=self.timeout
            )

            if not response.ok:
                try:
                    error = response.json()
                    detail = error.get('detail', response.text)
                except Exception:
                    detail = response.text

                raise EJEAPIError(
                    f"HTTP {response.status_code}: {detail}",
                    response.status_code,
                    detail
                )

            return response.json()

        except requests.exceptions.Timeout:
            raise EJEAPIError("Request timeout", 408)
        except requests.exceptions.RequestException as e:
            raise EJEAPIError(f"Network error: {str(e)}", 0, e)

    def evaluate_case(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        case_id: Optional[str] = None,
        require_human_review: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluate a case.

        Args:
            prompt: Case description
            context: Additional context
            case_id: Optional case identifier
            require_human_review: Force human review

        Returns:
            Decision response with verdict, confidence, and critic results

        Example:
            >>> result = client.evaluate_case(
            ...     prompt="Access user medical records",
            ...     context={"privacy_sensitive": True, "jurisdiction": "GDPR"}
            ... )
            >>> print(result["final_decision"])
            "blocked"
        """
        return self._request('POST', '/evaluate', {
            'prompt': prompt,
            'context': context or {},
            'case_id': case_id,
            'require_human_review': require_human_review
        })

    def search_precedents(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        min_similarity: float = 0.70,
        search_mode: str = 'hybrid'
    ) -> Dict[str, Any]:
        """
        Search for semantically similar precedents.

        Args:
            prompt: Search query
            context: Search context
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
            search_mode: Search mode: "exact", "semantic", or "hybrid"

        Returns:
            Search results with precedent matches

        Example:
            >>> results = client.search_precedents(
            ...     prompt="Share location data",
            ...     context={"privacy_sensitive": True},
            ...     top_k=5,
            ...     search_mode="hybrid"
            ... )
            >>> for result in results["results"]:
            ...     print(f"{result['precedent_id']}: {result['similarity_score']}")
        """
        return self._request('POST', '/precedents/search/semantic', {
            'prompt': prompt,
            'context': context or {},
            'top_k': top_k,
            'min_similarity': min_similarity,
            'search_mode': search_mode
        })

    def find_similar_precedents(
        self,
        precedent_id: str,
        top_k: int = 10,
        min_similarity: float = 0.75
    ) -> Dict[str, Any]:
        """
        Find precedents similar to an existing precedent.

        Args:
            precedent_id: Reference precedent ID
            top_k: Number of results
            min_similarity: Minimum similarity threshold

        Returns:
            Similar precedents

        Example:
            >>> similar = client.find_similar_precedents("prec_123", top_k=5)
            >>> print(f"Found {len(similar['results'])} similar cases")
        """
        return self._request(
            'GET',
            f'/precedents/{precedent_id}/similar',
            params={'top_k': top_k, 'min_similarity': min_similarity}
        )

    def create_escalation(
        self,
        case_id: str,
        prompt: str,
        critic_results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create escalation bundle for human review.

        Args:
            case_id: Case identifier
            prompt: Case prompt
            critic_results: Critic evaluation results
            context: Case context
            priority: Optional priority override

        Returns:
            Escalation bundle with dissent analysis

        Example:
            >>> bundle = client.create_escalation(
            ...     case_id="case_123",
            ...     prompt="Complex ethical dilemma",
            ...     critic_results=[
            ...         {"critic_name": "privacy", "verdict": "blocked", "confidence": 0.9, "reasoning": "..."},
            ...         {"critic_name": "autonomy", "verdict": "allowed", "confidence": 0.8, "reasoning": "..."}
            ...     ]
            ... )
            >>> print(f"Dissent index: {bundle['dissent_index']}")
        """
        return self._request('POST', '/review/escalate', {
            'case_id': case_id,
            'prompt': prompt,
            'context': context or {},
            'critic_results': critic_results,
            'priority': priority
        })

    def get_review_queue(
        self,
        filter_by: str = 'all',
        sort_by: str = 'priority_desc',
        assigned_to: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get filtered and sorted review queue.

        Args:
            filter_by: Filter option (all, critical, high_priority, high_dissent, etc.)
            sort_by: Sort option (priority_desc, dissent_desc, oldest_first, etc.)
            assigned_to: Filter by assignee
            limit: Maximum items to return

        Returns:
            Queue summary with items and statistics

        Example:
            >>> queue = client.get_review_queue(filter_by="critical", limit=20)
            >>> print(f"Critical items: {queue['summary']['critical']}")
        """
        return self._request('POST', '/review/queue', {
            'filter_by': filter_by,
            'sort_by': sort_by,
            'assigned_to': assigned_to,
            'limit': limit
        })

    def submit_feedback(
        self,
        bundle_id: str,
        reviewer_id: str,
        verdict: str,
        confidence: float,
        reasoning: str,
        responses: Optional[Dict[str, Any]] = None,
        conditions: Optional[str] = None,
        principles_applied: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Submit review feedback.

        Args:
            bundle_id: Escalation bundle ID
            reviewer_id: Reviewer identifier
            verdict: Verdict (allowed, blocked, conditional, defer)
            confidence: Confidence (0.0 to 1.0)
            reasoning: Reasoning for verdict
            responses: Additional responses
            conditions: Conditions for conditional verdict
            principles_applied: Principles applied

        Returns:
            Submission confirmation

        Example:
            >>> client.submit_feedback(
            ...     bundle_id="bundle_123",
            ...     reviewer_id="reviewer_alice",
            ...     verdict="blocked",
            ...     confidence=0.95,
            ...     reasoning="Clear privacy violation...",
            ...     principles_applied=["Privacy Protection"]
            ... )
        """
        return self._request('POST', '/review/submit', {
            'bundle_id': bundle_id,
            'reviewer_id': reviewer_id,
            'verdict': verdict,
            'confidence': confidence,
            'reasoning': reasoning,
            'responses': responses or {},
            'conditions': conditions,
            'principles_applied': principles_applied or []
        })

    def get_review_form(self, bundle_id: str) -> Dict[str, Any]:
        """
        Get feedback form for bundle.

        Args:
            bundle_id: Bundle identifier

        Returns:
            Feedback form with questions

        Example:
            >>> form = client.get_review_form("bundle_123")
            >>> for question in form["questions"]:
            ...     print(f"{question['question_id']}: {question['question_text']}")
        """
        return self._request('GET', f'/review/form/{bundle_id}')

    def get_review_stats(self, reviewer_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get review statistics.

        Args:
            reviewer_id: Optional reviewer ID for personalized stats

        Returns:
            Queue and reviewer statistics

        Example:
            >>> stats = client.get_review_stats("reviewer_alice")
            >>> print(f"Total pending: {stats['queue']['total_pending']}")
            >>> print(f"Total reviews: {stats['reviewer']['total_reviews']}")
        """
        params = {'reviewer_id': reviewer_id} if reviewer_id else None
        return self._request('GET', '/review/stats', params=params)

    def get_precedent_stats(self) -> Dict[str, Any]:
        """
        Get precedent store statistics.

        Returns:
            Vector store statistics

        Example:
            >>> stats = client.get_precedent_stats()
            >>> print(f"Total precedents: {stats['vector_store']['total_precedents']}")
        """
        return self._request('GET', '/precedents/stats')

    def health(self) -> Dict[str, Any]:
        """
        Health check.

        Returns:
            Health status

        Example:
            >>> health = client.health()
            >>> print(health["status"])
        """
        return self._request('GET', '/health')

    def close(self):
        """Close the client session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
