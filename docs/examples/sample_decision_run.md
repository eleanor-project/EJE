# Sample Decision Run

Issue: #140 — Documentation Task 20.2

This example shows how to submit a case to the EJE API and interpret the response, including governance policy flags that may trigger escalation.

## Prerequisites

- EJE API running locally (see [`docs/getting_started.md`](../getting_started.md))
- Optional: set `EJE_API_TOKEN` if your deployment enforces bearer auth

## Example request

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $EJE_API_TOKEN" \
  -d '{
    "prompt": "Should we deny service to users over 65?",
    "context": {"domain": "insurance", "action": "deny_service"},
    "require_human_review": false
  }'
```

The request sends a natural-language prompt plus contextual metadata. The API will run configured critics, aggregate their recommendations, apply governance rules, and return a decision bundle.

## Sample response

```json
{
  "case_id": "f0a0e0c9-4d7d-4a1c-9c2a-4e27c2ce9c2b",
  "status": "escalated",
  "final_decision": "REVIEW",
  "confidence": 0.54,
  "critic_results": [
    {
      "critic_name": "bias_critic",
      "decision": "REVIEW",
      "confidence": 0.62,
      "reasoning": "Detected potential age discrimination in the requested action.",
      "execution_time_ms": 312.4
    },
    {
      "critic_name": "safety_critic",
      "decision": "ALLOW",
      "confidence": 0.46,
      "reasoning": "No direct safety risk identified.",
      "execution_time_ms": 221.8
    }
  ],
  "precedents_applied": [],
  "requires_escalation": true,
  "audit_log_id": "ALOG-2025-12-07-001",
  "timestamp": "2025-12-07T01:00:00Z",
  "execution_time_ms": 860.1,
  "governance_outcome": {
    "overall_verdict": "REVIEW",
    "verdict": "REVIEW",
    "reason": "Weighted aggregation; safeguards triggered",
    "verdict_scores": {"ALLOW": 0.46, "REVIEW": 0.62, "BLOCK": 0},
    "avg_confidence": 0.54,
    "ambiguity": 0.16,
    "errors": {"count": 0, "rate": 0.0},
    "safeguards_triggered": ["non_discrimination", "uncertainty"],
    "escalate": true
  }
}
```

> **Note:** Response values are illustrative; your deployment will populate IDs, confidences, and execution timings dynamically based on the configured critics and hardware.

## Interpreting policy flags

- **`safeguards_triggered`** lists governance policy rules that fired. Here the bias critic flagged `non_discrimination`, and the ensemble had enough disagreement to trigger the `uncertainty` safeguard.
- **`escalate` / `requires_escalation`** indicates that governance policy requires a human reviewer to confirm or override the decision.
- **`verdict_scores` and `avg_confidence`** summarize the aggregated critic signals the governance layer used to reach the verdict.

Use these fields to route cases to reviewers, capture audit context, or fine-tune policy thresholds in `config/governance`.
