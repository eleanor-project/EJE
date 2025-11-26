import yaml
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from eje.api.app import create_app
from eje.config.settings import Settings
from eje.db import escalation_log


def build_app(tmp_path, *, token=None, dynamic_weights=False):
    config_path = tmp_path / "ops_config.yaml"
    with open("config/global.yaml", "r") as base_config:
        config = yaml.safe_load(base_config)

    config["precedent_backend"] = "json"
    config.setdefault("precedent", {})["store"] = {
        "path": str(tmp_path / "precedents"),
        "format": "jsonl",
    }

    with open(config_path, "w") as temp_config:
        yaml.safe_dump(config, temp_config)

    settings = Settings(
        config_path=str(config_path),
        db_path=str(tmp_path / "ops_center.db"),
        api_token=token,
        dynamic_weights=dynamic_weights,
    )
    return create_app(settings)


def test_health_requires_token(tmp_path):
    app = build_app(tmp_path, token="secret-token")
    with TestClient(app) as client:
        unauth = client.get("/health")
        assert unauth.status_code == 401

        auth = client.get("/health", headers={"Authorization": "Bearer secret-token"})
        assert auth.status_code == 200
        assert auth.json()["status"] == "ok"


def test_evaluate_persists_precedent(tmp_path):
    app = build_app(tmp_path)
    payload = {
        "prompt": "Should we allow this request?",
        "context": {"actor": "tester"},
        "require_human_review": False,
    }

    with TestClient(app) as client:
        response = client.post("/evaluate", json=payload)
        assert response.status_code == 200
        body = response.json()["result"]
        assert body["case_id"]
        assert body["verdict"]

        records = escalation_log.fetch_recent(app.state.engine, limit=5)
        assert len(records) == 1
        assert records[0].case_id == body["case_id"]
        assert records[0].prompt == payload["prompt"]


def test_escalate_writes_record(tmp_path):
    app = build_app(tmp_path)
    payload = {"case_id": "case-123", "reason": "requires supervisor", "metadata": {"foo": "bar"}}

    with TestClient(app) as client:
        response = client.post("/escalate", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["recorded"] is True

        engine = app.state.engine
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        with Session() as session:
            rows = session.query(escalation_log.EscalationRecord).all()
            assert len(rows) == 1
            assert rows[0].case_id == payload["case_id"]
            assert rows[0].reason == payload["reason"]
