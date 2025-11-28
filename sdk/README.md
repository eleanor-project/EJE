# Eleanor Judicial Engine (EJE) SDKs

Official client libraries for the Eleanor Judicial Engine API in multiple languages.

## Available SDKs

### TypeScript/JavaScript

Full-featured TypeScript client with zero runtime dependencies.

```bash
npm install @eleanor-project/eje-client
```

See [typescript/README.md](typescript/README.md) for detailed documentation.

### Python

Synchronous and asynchronous Python client with full type hints.

```bash
pip install eje-client
```

See [python/README.md](python/README.md) for detailed documentation.

## Quick Comparison

| Feature | TypeScript/JavaScript | Python |
|---------|----------------------|--------|
| **Language** | TypeScript, JavaScript | Python 3.8+ |
| **Type Safety** | Full TypeScript types | Type hints included |
| **Async Support** | Native async/await | Sync + async clients |
| **Dependencies** | Zero runtime deps | requests, aiohttp |
| **Context Managers** | N/A | ✓ (both sync/async) |
| **Package Manager** | npm | pip |

## Common Operations

### Case Evaluation

**TypeScript:**
```typescript
import { EJEClient } from '@eleanor-project/eje-client';

const client = new EJEClient({ baseUrl: 'https://api.example.com', apiKey: 'key' });
const result = await client.evaluateCase({ prompt: 'Test case' });
```

**Python (sync):**
```python
from eje_client import EJEClient

client = EJEClient(base_url='https://api.example.com', api_key='key')
result = client.evaluate_case(prompt='Test case')
```

**Python (async):**
```python
from eje_client import AsyncEJEClient

async with AsyncEJEClient(base_url='https://api.example.com') as client:
    result = await client.evaluate_case(prompt='Test case')
```

### Semantic Search

**TypeScript:**
```typescript
const results = await client.searchPrecedents({
  prompt: 'Share location data',
  top_k: 10,
  search_mode: 'hybrid'
});
```

**Python:**
```python
results = client.search_precedents(
    prompt='Share location data',
    top_k=10,
    search_mode='hybrid'
)
```

### Human Review

**TypeScript:**
```typescript
const bundle = await client.createEscalation({
  case_id: 'case_123',
  prompt: 'Complex case',
  critic_results: [...]
});

await client.submitFeedback({
  bundle_id: bundle.bundle_id,
  reviewer_id: 'alice',
  verdict: 'blocked',
  confidence: 0.95,
  reasoning: 'Privacy violation...'
});
```

**Python:**
```python
bundle = client.create_escalation(
    case_id='case_123',
    prompt='Complex case',
    critic_results=[...]
)

client.submit_feedback(
    bundle_id=bundle['bundle_id'],
    reviewer_id='alice',
    verdict='blocked',
    confidence=0.95,
    reasoning='Privacy violation...'
)
```

## Examples

Comprehensive examples for both SDKs are available in the `examples/` directory:

- **TypeScript:** [examples/typescript_example.ts](examples/typescript_example.ts)
- **Python:** [examples/python_example.py](examples/python_example.py)

Examples cover:
- Basic case evaluation
- Semantic precedent search
- Human review workflows
- Queue management
- Statistics and monitoring
- Error handling
- Concurrent requests (async)

## Error Handling

**TypeScript:**
```typescript
import { EJEClient, EJEAPIError } from '@eleanor-project/eje-client';

try {
  const result = await client.evaluateCase({ prompt: 'Test' });
} catch (error) {
  if (error instanceof EJEAPIError) {
    console.error(`API Error (${error.statusCode}): ${error.message}`);
  }
}
```

**Python:**
```python
from eje_client import EJEClient, EJEAPIError

try:
    result = client.evaluate_case(prompt='Test')
except EJEAPIError as e:
    print(f"API Error ({e.status_code}): {e}")
```

## API Coverage

All SDKs provide full coverage of the EJE API:

### Core Evaluation
- ✓ Case evaluation (`/evaluate`)
- ✓ Precedent search (`/precedents/search/semantic`)
- ✓ Find similar precedents (`/precedents/{id}/similar`)

### Human Review
- ✓ Create escalation bundle (`/review/escalate`)
- ✓ Get review queue (`/review/queue`)
- ✓ Submit feedback (`/review/submit`)
- ✓ Get review form (`/review/form/{bundle_id}`)
- ✓ Review statistics (`/review/stats`)

### Statistics
- ✓ Precedent store stats (`/precedents/stats`)
- ✓ Health check (`/health`)

## Installation from Source

### TypeScript

```bash
cd sdk/typescript
npm install
npm run build
```

### Python

```bash
cd sdk/python
pip install -e .
```

## Development

### TypeScript

```bash
cd sdk/typescript
npm install
npm run build    # Compile TypeScript
npm test         # Run tests
npm run lint     # Run linter
```

### Python

```bash
cd sdk/python
pip install -e ".[dev]"
pytest                  # Run tests
mypy eje_client        # Type checking
black eje_client       # Formatting
flake8 eje_client      # Linting
```

## Version Compatibility

| SDK Version | API Version | Python | Node.js | TypeScript |
|-------------|-------------|--------|---------|------------|
| 1.0.0       | ≥ 1.0       | ≥ 3.8  | ≥ 18.0  | ≥ 5.0      |

## License

All SDKs are released under the MIT License. See individual LICENSE files in each SDK directory.

## Support

- **Documentation:** https://eleanor-project.github.io/EJE/
- **Issues:** https://github.com/eleanor-project/EJE/issues
- **Source Code:** https://github.com/eleanor-project/EJE

## Contributing

Contributions are welcome! Please see the main repository CONTRIBUTING.md for guidelines.

## Changelog

See CHANGELOG.md in each SDK directory for version history and changes.
