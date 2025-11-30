# Project: ELEANOR Judgement Engine (EJE)

## 🧠 Precedent Lookup Integration

Your escalation logger now becomes a **living moral archive**. We’ll make it search past decisions before spending cycles on new deliberation — because dignity deserves *efficiency* too.

---

### 🔧 `db/escalation_log.py` – Add Precedent Lookup
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

def find_similar_scenario(scenario_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT scenario_id, context, metadata, timestamp FROM escalations
            WHERE scenario_id = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (scenario_id,))
        row = cursor.fetchone()
        if row:
            return {
                "scenario_id": row[0],
                "context": row[1],
                "metadata": row[2],
                "timestamp": row[3]
            }
        return None
```

---

### 🔧 `api/endpoints.py` – Add Precedent Check Before Evaluation
```python
from eje.db.escalation_log import find_similar_scenario

@router.post("/evaluate", response_model=EvaluationResult)
def evaluate_decision(input_data: DecisionInput):
    precedent = find_similar_scenario(input_data.scenario_id)
    if precedent:
        return {
            "status": "precedent_used",
            "result": {"message": "Precedent match found", "precedent": precedent}
        }
    try:
        result = run_critics(input_data.dict())
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 🧪 `test_api.py` – Add Precedent Test
```python
def test_precedent_lookup():
    # Log first
    client.post("/api/escalate", json={
        "scenario_id": "reused-case",
        "context": {"flag": True},
        "metadata": {"role": "tester"}
    })
    # Evaluate same case
    response = client.post("/api/evaluate", json={
        "scenario_id": "reused-case",
        "context": {"flag": True},
        "metadata": {}
    })
    assert response.status_code == 200
    assert response.json()["status"] == "precedent_used"
```

---

You now have:
- 📚 A moral precedent system
- ⚡ Faster evaluation on familiar cases
- 📜 Audit trail of what’s been judged and when

This is how machines start having institutional memory. Creepy? Maybe. Useful? Definitely.

Shall we wire in similarity scoring next, or auto-log decisions *after* they’re evaluated for future lookup?
