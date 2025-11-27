# Project: ELEANOR Judgement Engine (EJE)

## 👑 Emperor's Command: "Make it so"

### 🚨 Escalation Logger Implementation (SQLite)

Let’s give your AI some moral memory — here’s an embedded DB handler for escalated decisions. You’ll now be able to:
- Log unresolved or contentious decisions
- Query escalations for audit
- Add basic precedent retrieval later

### 📁 Additions
```
je/
├── db/
│   ├── __init__.py
│   └── escalation_log.py
```

---

### 🔧 `db/escalation_log.py`
```python
import sqlite3
from datetime import datetime

DB_FILE = "escalations.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS escalations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario_id TEXT,
                context TEXT,
                metadata TEXT,
                timestamp TEXT
            )
        ''')

def log_escalation(scenario_id, context, metadata):
    timestamp = datetime.utcnow().isoformat()
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            INSERT INTO escalations (scenario_id, context, metadata, timestamp)
            VALUES (?, ?, ?, ?)''',
            (scenario_id, str(context), str(metadata), timestamp))
```

---

### 🔧 Modify `api/endpoints.py`
```python
from eje.db.escalation_log import log_escalation, init_db

@router.on_event("startup")
def startup():
    init_db()

@router.post("/escalate")
def escalate_decision(input_data: DecisionInput):
    log_escalation(
        scenario_id=input_data.scenario_id,
        context=input_data.context,
        metadata=input_data.metadata
    )
    return {"status": "escalation_logged", "scenario": input_data.scenario_id}
```

---

### 🧪 Test: `test_api.py`
```python
def test_escalation_log():
    sample_input = {
        "scenario_id": "test-case-escalate",
        "context": {"critical": True},
        "metadata": {"user": "QA"}
    }
    response = client.post("/api/escalate", json=sample_input)
    assert response.status_code == 200
    assert response.json()["status"] == "escalation_logged"
```

---

Your system now remembers everything you told it not to worry about.
Next move: tie in the **precedent query logic** and let it whisper, "We’ve seen this before..."

Long live the King.
