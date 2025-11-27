"""
Eleanor Judicial Engine (EJE) Asynchronous Python Client

Provides async/await support for the EJE REST API using aiohttp.

Example:
    >>> import asyncio
    >>> from eje_client import AsyncEJEClient
    >>>
    >>> async def main():
    ...     async with AsyncEJEClient(base_url="https://api.example.com", api_key="your-key") as client:
    ...         result = await client.evaluate_case(prompt="Share user data", context={"privacy_sensitive": True})
    ...         print(result["final_decision"])
    >>>
    >>> asyncio.run(main())
"""

from typing import Any, Dict, List, Optional
import aiohttp
from urllib.parse import urljoin

from .client import EJEAPIError


class AsyncEJEClient:
    """
    Asynchronous Eleanor Judicial Engine API Client.

    Provides async/await methods for:
    - Case evaluation
    - Precedent search
    - Human review workflows
    - Performance analytics

    Example:
        >>> async with AsyncEJEClient(base_url="https://api.example.com") as client:
        ...     result = await client.evaluate_case(
        ...         prompt="Share user location data",
        ...         context={"privacy_sensitive": True}
        ...     )
        ...     print(result["final_decision"])
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize async EJE client.

        Args:
            base_url: Base URL of the EJE API
            api_key: Optional Bearer token for authentication
            timeout: Request timeout in seconds (default: 30)
            headers: Optional custom headers
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        self.headers = {
            'Content-Type': 'application/json',
            **(headers or {})
        }

        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'

        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=self.timeout
            )
        return self._session

    async def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make async HTTP request to API."""
        url = urljoin(self.base_url, path)

        try:
            async with self.session.request(
                method=method,
                url=url,
                json=body,
                params=params
            ) as response:
                if response.status >= 400:
                    try:
                        error = await response.json()
                        detail = error.get('detail', await response.text())
                    except Exception:
                        detail = await response.text()

                    raise EJEAPIError(
                        f"HTTP {response.status}: {detail}",
                        response.status,
                        detail
                    )

                return await response.json()

        except aiohttp.ClientError as e:
            raise EJEAPIError(f"Network error: {str(e)}", 0, e)

    async def evaluate_case(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        case_id: Optional[str] = None,
        require_human_review: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluate a case (async).

        Args:
            prompt: Case description
            context: Additional context
            case_id: Optional case identifier
            require_human_review: Force human review

        Returns:
            Decision response

        Example:
            >>> result = await client.evaluate_case(
            ...     prompt="Access user medical records",
            ...     context={"privacy_sensitive": True}
            ... )
        """
        return await self._request('POST', '/evaluate', {
            'prompt': prompt,
            'context': context or {},
            'case_id': case_id,
            'require_human_review': require_human_review
        })

    async def search_precedents(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        min_similarity: float = 0.70,
        search_mode: str = 'hybrid'
    ) -> Dict[str, Any]:
        """
        Search for semantically similar precedents (async).

        Args:
            prompt: Search query
            context: Search context
            top_k: Number of results
            min_similarity: Minimum similarity threshold
            search_mode: Search mode

        Returns:
            Search results

        Example:
            >>> results = await client.search_precedents(
            ...     prompt="Share location data",
            ...     top_k=5
            ... )
        """
        return await self._request('POST', '/precedents/search/semantic', {
            'prompt': prompt,
            'context': context or {},
            'top_k': top_k,
            'min_similarity': min_similarity,
            'search_mode': search_mode
        })

    async def find_similar_precedents(
        self,
        precedent_id: str,
        top_k: int = 10,
        min_similarity: float = 0.75
    ) -> Dict[str, Any]:
        """Find similar precedents (async)."""
        return await self._request(
            'GET',
            f'/precedents/{precedent_id}/similar',
            params={'top_k': top_k, 'min_similarity': min_similarity}
        )

    async def create_escalation(
        self,
        case_id: str,
        prompt: str,
        critic_results: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create escalation bundle (async)."""
        return await self._request('POST', '/review/escalate', {
            'case_id': case_id,
            'prompt': prompt,
            'context': context or {},
            'critic_results': critic_results,
            'priority': priority
        })

    async def get_review_queue(
        self,
        filter_by: str = 'all',
        sort_by: str = 'priority_desc',
        assigned_to: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get review queue (async)."""
        return await self._request('POST', '/review/queue', {
            'filter_by': filter_by,
            'sort_by': sort_by,
            'assigned_to': assigned_to,
            'limit': limit
        })

    async def submit_feedback(
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
        """Submit review feedback (async)."""
        return await self._request('POST', '/review/submit', {
            'bundle_id': bundle_id,
            'reviewer_id': reviewer_id,
            'verdict': verdict,
            'confidence': confidence,
            'reasoning': reasoning,
            'responses': responses or {},
            'conditions': conditions,
            'principles_applied': principles_applied or []
        })

    async def get_review_form(self, bundle_id: str) -> Dict[str, Any]:
        """Get feedback form (async)."""
        return await self._request('GET', f'/review/form/{bundle_id}')

    async def get_review_stats(self, reviewer_id: Optional[str] = None) -> Dict[str, Any]:
        """Get review statistics (async)."""
        params = {'reviewer_id': reviewer_id} if reviewer_id else None
        return await self._request('GET', '/review/stats', params=params)

    async def get_precedent_stats(self) -> Dict[str, Any]:
        """Get precedent store statistics (async)."""
        return await self._request('GET', '/precedents/stats')

    async def health(self) -> Dict[str, Any]:
        """Health check (async)."""
        return await self._request('GET', '/health')

    async def close(self):
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
