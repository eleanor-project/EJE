"""
Eleanor Judicial Engine (EJE) Python Client

Synchronous and asynchronous clients for the EJE REST API.

Example (sync):
    >>> from eje_client import EJEClient
    >>> client = EJEClient(base_url="https://api.example.com", api_key="your-key")
    >>> result = client.evaluate_case(prompt="Share user data", context={"privacy_sensitive": True})
    >>> print(result["final_decision"])

Example (async):
    >>> import asyncio
    >>> from eje_client import AsyncEJEClient
    >>>
    >>> async def main():
    ...     async with AsyncEJEClient(base_url="https://api.example.com") as client:
    ...         result = await client.evaluate_case(prompt="Share user data")
    ...         print(result["final_decision"])
    >>>
    >>> asyncio.run(main())
"""

from .client import EJEClient, EJEAPIError, EJEClientConfig
from .async_client import AsyncEJEClient

__version__ = "1.0.0"

__all__ = [
    "EJEClient",
    "AsyncEJEClient",
    "EJEAPIError",
    "EJEClientConfig"
]
