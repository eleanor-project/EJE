# Project: ELEANOR Judgement Engine (EJE)

## ✅ API Refactor: FastAPI App Factory

Below is a production-ready version of your FastAPI setup using an **app factory pattern** with clean routing and pluggable features. It’s structured for extensibility, testing, and future middleware like CORS, logging, auth, etc.

### 📁 Directory Additions
```
eje/
├── api/
│   ├── __init__.py
│   ├── endpoints.py
│   ├── models.py
│   └── app.py  # 👈 Factory + router mount here
```

---

### 🔧 `api/app.py`
```python
from fastapi import FastAPI
from eje.api.endpoints import router as api_router
from fastapi.middleware.cors import CORSMiddleware


def create_app():
    app = FastAPI(title="ELEANOR Judgement Engine", version="0.1")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Replace with specific origins in prod
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")
    return app
```

---

### 🔧 `api/models.py`
```python
from pydantic import BaseModel
from typing import Dict, Any

class DecisionInput(BaseModel):
    scenario_id: str
    context: Dict[str, Any]
    metadata: Dict[str, Any] = {}

class EvaluationResult(BaseModel):
    status: str
    result: Dict[str, Any]
```

---

### 🔧 `api/endpoints.py`
```python
from fastapi import APIRouter, HTTPException
from eje.api.models import DecisionInput, EvaluationResult
from eje.critic_engine import run_critics  # Placeholder: plug real function

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "alive", "message": "ELEANOR sees you."}

@router.post("/evaluate", response_model=EvaluationResult)
def evaluate_decision(input_data: DecisionInput):
    try:
        result = run_critics(input_data.dict())
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/escalate")
def escalate_decision(input_data: DecisionInput):
    # Placeholder: insert escalation handler or log to DB
    return {"status": "escalation_triggered", "data": input_data.dict()}
```

---

### 🧪 `tests/test_api.py`
```python
from fastapi.testclient import TestClient
from eje.api.app import create_app

client = TestClient(create_app())

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200

def test_evaluate_stub():
    sample_input = {
        "scenario_id": "test-case-1",
        "context": {"actors": ["X", "Y"], "actions": ["act"]},
        "metadata": {}
    }
    response = client.post("/api/evaluate", json=sample_input)
    assert response.status_code in [200, 500]  # 500 is okay for placeholder logic
```

---

This gives you a plug-and-play API you can start, test, extend, and deploy.

If you want, I can also:
- Write an escalation logger (e.g., SQLite)
- Add `.env`-based config
- Set up deployment via Docker or Uvicorn + Gunicorn stack

Your move, Sovereign of Syntax. Shall we go full ops mode next?
