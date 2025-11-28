# Eleanor Judicial Engine (EJE) TypeScript/JavaScript Client

Official TypeScript/JavaScript client library for the Eleanor Judicial Engine API.

## Installation

```bash
npm install @eleanor-project/eje-client
```

## Quick Start

```typescript
import { EJEClient } from '@eleanor-project/eje-client';

const client = new EJEClient({
  baseUrl: 'https://api.example.com',
  apiKey: 'your-api-key'
});

// Evaluate a case
const result = await client.evaluateCase({
  prompt: 'Share user location data with third parties',
  context: {
    privacy_sensitive: true,
    jurisdiction: 'GDPR'
  }
});

console.log(result.final_decision);  // "blocked"
console.log(result.confidence);      // 0.95
```

## Features

- **Type-safe API**: Full TypeScript type definitions
- **Promise-based**: Native async/await support
- **Comprehensive coverage**: All EJE API endpoints
- **Error handling**: Structured error responses
- **Zero dependencies**: No external runtime dependencies

## API Reference

### Client Initialization

```typescript
const client = new EJEClient({
  baseUrl: string,        // Required: API base URL
  apiKey?: string,        // Optional: Bearer token
  timeout?: number,       // Optional: Request timeout (ms)
  headers?: object        // Optional: Custom headers
});
```

### Case Evaluation

```typescript
const result = await client.evaluateCase({
  prompt: string,
  context?: object,
  case_id?: string,
  require_human_review?: boolean
});
```

### Semantic Precedent Search

```typescript
const results = await client.searchPrecedents({
  prompt: string,
  context?: object,
  top_k?: number,              // Default: 10
  min_similarity?: number,     // Default: 0.70
  search_mode?: 'exact' | 'semantic' | 'hybrid'  // Default: 'hybrid'
});
```

### Human Review Workflow

```typescript
// Create escalation bundle
const bundle = await client.createEscalation({
  case_id: string,
  prompt: string,
  critic_results: Array<object>,
  context?: object,
  priority?: string
});

// Get review queue
const queue = await client.getReviewQueue(
  filter?: string,      // 'all', 'critical', 'high_priority', etc.
  sortBy?: string,      // 'priority_desc', 'dissent_desc', etc.
  limit?: number
);

// Submit feedback
await client.submitFeedback({
  bundle_id: string,
  reviewer_id: string,
  verdict: string,
  confidence: number,
  reasoning: string,
  principles_applied?: string[]
});
```

### Statistics

```typescript
// Precedent store statistics
const precedentStats = await client.getPrecedentStats();

// Review statistics
const reviewStats = await client.getReviewStats(reviewer_id?: string);

// Health check
const health = await client.health();
```

## Examples

See `examples/typescript_example.ts` for comprehensive examples including:
- Basic case evaluation
- Semantic precedent search
- Human review workflows
- Queue management
- Statistics and monitoring

## Error Handling

```typescript
import { EJEClient, EJEAPIError } from '@eleanor-project/eje-client';

try {
  const result = await client.evaluateCase({ prompt: 'Test' });
} catch (error) {
  if (error instanceof EJEAPIError) {
    console.error(`API Error (${error.statusCode}): ${error.message}`);
    console.error('Details:', error.detail);
  } else {
    console.error('Unexpected error:', error);
  }
}
```

## TypeScript Support

This library is written in TypeScript and includes full type definitions. All API methods and response types are fully typed for the best development experience.

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: https://eleanor-project.github.io/EJE/
- Issues: https://github.com/eleanor-project/EJE/issues
- Source: https://github.com/eleanor-project/EJE
