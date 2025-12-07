# Eleanor Judicial Engine (EJE) Python Client

Official Python client library for the Eleanor Judicial Engine API with both synchronous and asynchronous support.

## Installation

```bash
pip install eje-client
```

## Quick Start

### Synchronous Client

```python
from eje_client import EJEClient

client = EJEClient(
    base_url='https://api.example.com',
    api_key='your-api-key'
)

# Evaluate a case
result = client.evaluate_case(
    prompt='Share user location data with third parties',
    context={
        'privacy_sensitive': True,
        'jurisdiction': 'GDPR'
    }
)

print(result['final_decision'])  # "blocked"
print(result['confidence'])      # 0.95
```

### Asynchronous Client

```python
import asyncio
from eje_client import AsyncEJEClient

async def main():
    async with AsyncEJEClient(
        base_url='https://api.example.com',
        api_key='your-api-key'
    ) as client:
        result = await client.evaluate_case(
            prompt='Share user location data',
            context={'privacy_sensitive': True}
        )
        print(result['final_decision'])

asyncio.run(main())
```

## Features

- **Dual mode**: Synchronous and asynchronous clients
- **Type hints**: Full type annotations for better IDE support
- **Context managers**: Automatic resource cleanup
- **Comprehensive**: All EJE API endpoints supported
- **Dependencies**: Minimal dependencies (requests, aiohttp)

## Command Line Interface

The Python SDK ships with an ``eje`` CLI for quick interaction with a running
EJE deployment.

```bash
eje --base-url https://api.example.com --api-key $EJE_API_KEY \
  evaluate "Share user location data" --context '{"jurisdiction": "GDPR"}'

eje --base-url https://api.example.com search "privacy" --top-k 5

eje --base-url https://api.example.com health
```

## API Reference

### Client Initialization

**Synchronous:**
```python
from eje_client import EJEClient

client = EJEClient(
    base_url: str,          # Required: API base URL
    api_key: str = None,    # Optional: Bearer token
    timeout: int = 30,      # Optional: Request timeout (seconds)
    headers: dict = None    # Optional: Custom headers
)
```

**Asynchronous:**
```python
from eje_client import AsyncEJEClient

async with AsyncEJEClient(
    base_url: str,
    api_key: str = None,
    timeout: int = 30,
    headers: dict = None
) as client:
    # Use client here
    pass
```

### Case Evaluation

```python
result = client.evaluate_case(
    prompt: str,
    context: dict = None,
    case_id: str = None,
    require_human_review: bool = False
)
```

### Semantic Precedent Search

```python
results = client.search_precedents(
    prompt: str,
    context: dict = None,
    top_k: int = 10,
    min_similarity: float = 0.70,
    search_mode: str = 'hybrid'  # 'exact', 'semantic', or 'hybrid'
)
```

### Human Review Workflow

```python
# Create escalation bundle
bundle = client.create_escalation(
    case_id: str,
    prompt: str,
    critic_results: list,
    context: dict = None,
    priority: str = None
)

# Get review queue
queue = client.get_review_queue(
    filter_by: str = 'all',
    sort_by: str = 'priority_desc',
    assigned_to: str = None,
    limit: int = 50
)

# Submit feedback
client.submit_feedback(
    bundle_id: str,
    reviewer_id: str,
    verdict: str,
    confidence: float,
    reasoning: str,
    responses: dict = None,
    conditions: str = None,
    principles_applied: list = None
)
```

### Statistics

```python
# Precedent store statistics
precedent_stats = client.get_precedent_stats()

# Review statistics
review_stats = client.get_review_stats(reviewer_id=None)

# Health check
health = client.health()
```

## Examples

See `examples/python_example.py` for comprehensive examples including:
- Basic case evaluation
- Semantic precedent search
- Human review workflows
- Queue management
- Statistics and monitoring
- Async/await patterns
- Concurrent requests

## Error Handling

```python
from eje_client import EJEClient, EJEAPIError

client = EJEClient(base_url='https://api.example.com')

try:
    result = client.evaluate_case(prompt='Test case')
except EJEAPIError as e:
    print(f"API Error ({e.status_code}): {e}")
    print(f"Details: {e.detail}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Context Manager Usage

```python
# Automatic cleanup with context manager
with EJEClient(base_url='https://api.example.com') as client:
    result = client.evaluate_case(prompt='Test')
    print(result['final_decision'])
# Session automatically closed

# Async context manager
async with AsyncEJEClient(base_url='https://api.example.com') as client:
    result = await client.evaluate_case(prompt='Test')
    print(result['final_decision'])
# Session automatically closed
```

## Concurrent Requests (Async)

```python
import asyncio
from eje_client import AsyncEJEClient

async def main():
    async with AsyncEJEClient(base_url='https://api.example.com') as client:
        # Run multiple evaluations concurrently
        tasks = [
            client.evaluate_case(prompt='Case 1'),
            client.evaluate_case(prompt='Case 2'),
            client.evaluate_case(prompt='Case 3')
        ]

        results = await asyncio.gather(*tasks)

        for i, result in enumerate(results, 1):
            print(f"Case {i}: {result['final_decision']}")

asyncio.run(main())
```

## Type Hints

This library includes comprehensive type hints for better IDE support and type checking:

```python
from eje_client import EJEClient
from typing import Dict, List, Any

client: EJEClient = EJEClient(base_url='https://api.example.com')

result: Dict[str, Any] = client.evaluate_case(
    prompt='Test',
    context={'privacy_sensitive': True}
)

decision: str = result['final_decision']
confidence: float = result['confidence']
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy eje_client

# Linting
flake8 eje_client

# Formatting
black eje_client
```

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: https://eleanor-project.github.io/EJE/
- Issues: https://github.com/eleanor-project/EJE/issues
- Source: https://github.com/eleanor-project/EJE

## Requirements

- Python 3.8+
- requests >= 2.28.0
- aiohttp >= 3.8.0 (for async client)
