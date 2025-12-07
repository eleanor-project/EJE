# Getting Started

This guide walks through a minimal local setup for the Ethical Jurisprudence Engine (EJE) FastAPI service and CLI.

## Prerequisites

- Python 3.11+
- Recommended: a virtual environment (`python -m venv .venv && source .venv/bin/activate`)
- Access tokens for any LLM critics you plan to enable (e.g., OpenAI, Anthropic, Gemini)

## Installation

1. Install dependencies from the project root:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy the sample environment file and populate keys (only the providers you intend to use are required):

   ```bash
   cp .env.example .env
   # then edit .env to add OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, etc.
   ```

3. Review `config/global.yaml` to confirm which critics and aggregation strategy you want to enable. The default configuration runs a multi-critic ensemble and writes precedents to `precedent/` (SQLite + file bundles).

## Running the FastAPI service

Start the REST API with Uvicorn:

```bash
uvicorn src.ejc.server.api:app --host 0.0.0.0 --port 8000 --reload
```

Optional: set `EJE_API_TOKEN` to enforce a bearer token on incoming requests.

### Health check

```bash
curl http://localhost:8000/health
```

### Evaluate a case

```bash
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $EJE_API_TOKEN" \  
  -d '{
    "prompt": "Should we allow autonomous triage?",
    "context": {"jurisdiction": "us"},
    "require_human_review": false
  }'
```

### Search precedents

```bash
curl -X POST http://localhost:8000/precedents/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $EJE_API_TOKEN" \  
  -d '{
    "query": "autonomous triage",
    "limit": 5,
    "min_similarity": 0.45
  }'
```

Responses include critic breakdowns, governance decisions, and precedent references for auditing.

## CLI quickstart

The CLI evaluates a single case using the same adjudication pipeline as the API:

```bash
python -m ejc.cli.run_engine --config config/global.yaml --case '{"text":"Test case about medical triage"}'
```

You can also supply a file by prefixing the path with `@`:

```bash
python -m ejc.cli.run_engine --case @examples/case.json
```

## Next steps

- Explore the OpenAPI docs at `http://localhost:8000/docs` once the server is running.
- Review `docs/precedent_system.md` and `docs/semantic_precedent_search.md` for advanced precedent configuration.
- Walk through a full request/response in `docs/examples/sample_decision_run.md` to see how governance policy flags show up in decisions.
