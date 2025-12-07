# EJE/ELEANOR Quickstart Guide

**Get started with the Ethical Justice Engine in under 5 minutes**

---

## What is EJE/ELEANOR?

EJE (Ethical Justice Engine) is a production-ready AI governance framework that applies ethical principles, legal frameworks, and precedent-based reasoning to ensure responsible, accountable, and compliant AI decision-making. ELEANOR (Ethical Legal Explanation And Normative Operations Repository) serves as the knowledge base storing precedents, governance frameworks, and ethical guidelines.

---

## Installation

### Prerequisites
- Python 3.9+
- Docker & Docker Compose (optional, for containerized deployment)
- API keys for LLM providers (OpenAI, Anthropic, or Google Gemini)

### Quick Install

```bash
# Clone the repository
git clone https://github.com/eleanor-project/EJE.git
cd EJE

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# Run initial setup
python -m eje.setup
```

### Docker Installation (Recommended for Production)

```bash
# Clone and navigate
git clone https://github.com/eleanor-project/EJE.git
cd EJE

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Build and run with Docker Compose
docker-compose up -d

# Verify deployment
curl http://localhost:8000/health
```

---

## Example API Usage

### Basic Decision Request

```python
import requests
import json

# EJE API endpoint
EJE_URL = "http://localhost:8000/api/v1"

# Example: Healthcare decision with governance
decision_request = {
    "domain": "healthcare",
    "context": {
        "patient_id": "P12345",
        "condition": "diabetes_type2",
        "requested_action": "treatment_recommendation",
        "patient_data": {
            "age": 45,
            "hba1c": 8.2,
            "comorbidities": ["hypertension"]
        }
    },
    "governance": {
        "require_precedent_validation": True,
        "enable_critics": True,
        "fallback_on_low_confidence": True,
        "confidence_threshold": 0.85
    }
}

# Submit decision request
response = requests.post(
    f"{EJE_URL}/decisions",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json=decision_request
)

result = response.json()

# Extract decision and governance info
print(f"Decision: {result['decision']['recommendation']}")
print(f"Confidence: {result['decision']['confidence']}")
print(f"Precedents Applied: {len(result['governance']['precedents_matched'])}")
print(f"Critic Assessments: {result['governance']['critic_summary']}")
print(f"Audit Trail ID: {result['audit']['trace_id']}")
```

### Response Structure

```json
{
  "decision": {
    "recommendation": "Recommend metformin 500mg twice daily with lifestyle modifications",
    "confidence": 0.92,
    "reasoning": "Based on clinical guidelines and precedent analysis..."
  },
  "governance": {
    "precedents_matched": [
      {
        "id": "HC-2024-0847",
        "relevance": 0.94,
        "summary": "Type 2 diabetes initial treatment protocol"
      }
    ],
    "critic_summary": {
      "safety_critic": "PASS",
      "ethics_critic": "PASS",
      "compliance_critic": "PASS (HIPAA, FDA guidelines)"
    },
    "overrides_triggered": [],
    "fallback_activated": false
  },
  "audit": {
    "trace_id": "ej-20250107-a8f2c1d",
    "timestamp": "2025-01-07T10:23:47Z",
    "domain": "healthcare",
    "compliance_logs": ["logged to secure audit store"]
  },
  "explainability": {
    "summary": "Decision based on ADA guidelines, validated against 12 precedents...",
    "evidence_bundles": [
      {
        "source": "clinical_guidelines_critic",
        "assessment": "Recommendation aligns with ADA Standards of Care 2024"
      }
    ]
  }
}
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       USER / APPLICATION                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      EJE API LAYER                           │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐  │
│  │ REST API     │  │ Batch Jobs    │  │ CLI Interface   │  │
│  └──────────────┘  └───────────────┘  └─────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   GOVERNANCE LAYER                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Domain Governance Modules                             │ │
│  │  ├─ Healthcare  ├─ Financial  ├─ Education  ├─ Legal  │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Precedent    │  │ Critics &    │  │ Override &      │  │
│  │ Validator    │  │ Evidence     │  │ Fallback Mgr    │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   ELEANOR REPOSITORY                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Precedents   │  │ Ethical      │  │ Legal/Regulatory│  │
│  │ Database     │  │ Frameworks   │  │ Frameworks      │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   AI/ML MODEL LAYER                          │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ OpenAI GPT-4 │  │ Claude 3     │  │ Gemini Pro      │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              AUDIT & MONITORING LAYER                        │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Immutable    │  │ Metrics &    │  │ Compliance      │  │
│  │ Audit Logs   │  │ Dashboards   │  │ Reports         │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Glossary of Critical Terms

**Critics**  
Specialized analytical modules that evaluate AI outputs against specific criteria (ethics, safety, legal compliance). Critics generate evidence bundles documenting their assessments.

**Evidence Bundle**  
Structured documentation produced by critics containing: source, criteria, assessment results, supporting evidence, recommendations, and metadata.

**Precedent**  
A previously adjudicated decision that serves as a reference for future similar cases. Includes case description, decision, reasoning, and applicability conditions.

**Drift**  
Gradual deviation of system configurations, policies, or behaviors from their intended state. EJE monitors configuration drift, model drift, policy drift, and precedent drift.

**Override**  
Mechanism allowing authorized actors to supersede AI decisions. Types include human override, policy override, emergency override, and ethical override.

**Fallback Model**  
Alternative decision-making mechanism activated when primary models fail, confidence is low, or governance violations are detected. Ensures system resilience.

**Governance Layer**  
Architectural component enforcing governance rules, precedent validation, ethical constraints, and audit requirements before decisions are finalized.

**Domain Governance**  
Application of domain-specific rules, regulations, and ethical frameworks (e.g., HIPAA for healthcare, GDPR for data privacy).

**Audit Trail**  
Immutable record of all decisions, actions, and events enabling accountability, compliance verification, and forensic analysis.

**ELEANOR Repository**  
Comprehensive knowledge base storing precedents, governance frameworks, legal interpretations, and ethical guidelines.

---

## Next Steps

### Explore Documentation
- **[Full Documentation](../README.md)** — Comprehensive system guide
- **[Domain Guides](domains/)** — Healthcare, Financial, Education, Legal implementations
- **[API Reference](api/)** — Complete API specification
- **[System Glossary](GLOSSARY.md)** — Detailed terminology reference
- **[Architecture Overview](architecture/)** — Deep dive into system design

### Run Examples

```bash
# Healthcare decision example
python examples/healthcare_decision.py

# Financial compliance check
python examples/financial_compliance.py

# Batch processing example
python examples/batch_processing.py
```

### Configure for Your Domain

1. Review domain-specific governance modules in `eje/domains/`
2. Customize precedent validation rules
3. Configure critic modules for your use case
4. Set up compliance reporting for your jurisdiction
5. Define override policies and authorization

### Monitoring & Operations

```bash
# View Grafana dashboards (if using Docker)
open http://localhost:3000

# Check system health
curl http://localhost:8000/health

# View audit logs
python -m eje.cli audit-logs --last 24h

# Generate compliance report
python -m eje.cli compliance-report --domain healthcare --format pdf
```

---

## Support & Community

- **GitHub Issues:** [github.com/eleanor-project/EJE/issues](https://github.com/eleanor-project/EJE/issues)
- **Documentation:** [docs/](../docs/)
- **Contributing:** [CONTRIBUTING.md](../CONTRIBUTING.md)
- **License:** MIT (see [LICENSE](../LICENSE))

---

**Ready to build ethical AI systems? Start with a simple decision request and expand from there!**
