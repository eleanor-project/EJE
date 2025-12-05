# EJE Schemas

This directory contains JSON schemas for core EJE data structures.

## Evidence Bundle Schema

**File**: `evidence_bundle.json`

### Purpose

The Evidence Bundle Schema defines the structure for critic outputs in the ELEANOR system. Evidence bundles are the atomic unit of reasoning across critics and ensure consistency for safe aggregation.

### Key Components

1. **Bundle Identification**
   - `bundle_id`: Unique identifier
   - `version`: Schema version (semantic versioning)

2. **Critic Output**
   - `critic_name`: Name of the evaluating critic
   - `verdict`: Decision (ALLOW, DENY, ESCALATE, ABSTAIN, ERROR)
   - `confidence`: Score from 0.0 to 1.0
   - `justification`: Detailed explanation
   - `risk_flags`: Optional risk indicators
   - `sub_verdicts`: Multi-dimensional evaluations
   - `precedents_referenced`: Related precedents

3. **Metadata**
   - `timestamp`: ISO 8601 creation time
   - `critic_name`: Critic identifier
   - `config_version`: Configuration version
   - `aggregator_run_id`: Aggregation batch ID
   - `execution_time_ms`: Performance metrics
   - `trace_id`: Distributed tracing
   - `request_id`: Original request correlation

4. **Input Snapshot**
   - `prompt`: The evaluated input
   - `context`: Situational information
     - Jurisdiction, domain, consent status
     - Privacy sensitivity, stakes level
   - `input_hash`: SHA-256 for deduplication

5. **Validation** (optional)
   - Validation status and errors
   - Validation timestamp

### Usage

#### Validation

Use a JSON schema validator to check evidence bundles:

```python
import json
import jsonschema

# Load schema
with open('schemas/evidence_bundle.json') as f:
    schema = json.load(f)

# Load bundle to validate
with open('my_evidence_bundle.json') as f:
    bundle = json.load(f)

# Validate
try:
    jsonschema.validate(bundle, schema)
    print("✅ Bundle is valid")
except jsonschema.ValidationError as e:
    print(f"❌ Validation error: {e.message}")
```

#### Creating a Bundle

```python
bundle = {
    "bundle_id": "bundle-abc123",
    "version": "1.0",
    "critic_output": {
        "critic_name": "PrivacyCritic",
        "verdict": "ALLOW",
        "confidence": 0.92,
        "justification": "Request aligns with privacy principles...",
        "risk_flags": []
    },
    "metadata": {
        "timestamp": "2025-12-04T10:30:00Z",
        "critic_name": "PrivacyCritic",
        "config_version": "1.0",
        "execution_time_ms": 145.7
    },
    "input_snapshot": {
        "prompt": "User requests to delete account",
        "context": {
            "jurisdiction": "EU",
            "user_consent": true
        }
    }
}
```

### Validation Rules

- **Required fields**: `bundle_id`, `version`, `critic_output`, `metadata`, `input_snapshot`
- **Verdict values**: Must be one of ALLOW, DENY, ESCALATE, ABSTAIN, ERROR
- **Confidence**: Must be between 0.0 and 1.0
- **Timestamps**: Must be ISO 8601 format
- **Versions**: Must follow semantic versioning (e.g., "1.0", "2.1.0")

### Examples

See the `examples` array in `evidence_bundle.json` for complete working examples.

### Version History

- **1.0** (2025-12-04): Initial schema definition
  - Core critic output fields
  - Metadata block with observability support
  - Input snapshot with context
  - Validation framework

### Related

- Task 1.1: Define Evidence Bundle Schema ✅
- Task 1.2: Implement Evidence Normalizer (next)
- Task 1.3: Add Metadata Enrichment (next)
