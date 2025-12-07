import io
import json
import os
import pathlib
import sys
from typing import Any, Dict, List

import pytest


class _RequestsModule:
    class exceptions:
        class Timeout(Exception):
            ...

        class RequestException(Exception):
            ...

    class Session:
        def __init__(self) -> None:
            self.headers = {}

        def request(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - unused
            raise RuntimeError("Network calls are stubbed during tests")

        def close(self) -> None:  # pragma: no cover - unused
            ...

        def update(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - unused
            ...


sys.modules.setdefault("requests", _RequestsModule())
sys.modules.setdefault(
    "aiohttp",
    type(
        "_AiohttpModule",
        (),
        {
            "ClientTimeout": lambda total=None: total,
            "ClientError": Exception,
            "ClientSession": type(
                "_ClientSession",
                (),
                {
                    "__init__": lambda self, *args, **kwargs: None,
                    "closed": False,
                    "request": lambda self, *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Network stub")),
                    "close": lambda self: None,
                },
            ),
        },
    )(),
)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from eje_client import cli


class _StubClient:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self.closed = False

    def evaluate_case(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append({"method": "evaluate", **kwargs})
        return {"final_decision": "allowed", "echo": kwargs}

    def search_precedents(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append({"method": "search", **kwargs})
        return {"results": ["p1", "p2"], "echo": kwargs}

    def health(self) -> Dict[str, str]:
        self.calls.append({"method": "health"})
        return {"status": "ok"}

    def close(self) -> None:
        self.closed = True


def _run(argv: List[str], client: _StubClient, tmp_env: Dict[str, str]):
    env_backup = {key: os.environ.get(key) for key in tmp_env}
    os.environ.update(tmp_env)
    try:
        out, err = io.StringIO(), io.StringIO()
        exit_code = cli.run(argv, client_factory=lambda: client, out=out, err=err)
        return exit_code, out.getvalue(), err.getvalue()
    finally:
        for key, value in env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_evaluate_command_uses_context_json_and_env_defaults():
    client = _StubClient()
    exit_code, stdout, stderr = _run(
        [
            "evaluate",
            "Review a contract",
            "--context",
            "{\"domain\": \"legal\"}",
            "--case-id",
            "case-123",
            "--require-human-review",
        ],
        client,
        {"EJE_BASE_URL": "https://api", "EJE_API_KEY": "token"},
    )
    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout.strip())
    assert payload["final_decision"] == "allowed"
    assert client.calls == [
        {
            "method": "evaluate",
            "prompt": "Review a contract",
            "context": {"domain": "legal"},
            "case_id": "case-123",
            "require_human_review": True,
        }
    ]
    assert client.closed is True


def test_search_command_with_headers_and_options():
    client = _StubClient()
    exit_code, stdout, stderr = _run(
        [
            "--base-url",
            "https://api",
            "--api-key",
            "token",
            "-H",
            "X-Test:1",
            "search",
            "Safe data use",
            "--top-k",
            "5",
            "--min-similarity",
            "0.5",
            "--search-mode",
            "semantic",
        ],
        client,
        {},
    )
    assert exit_code == 0
    assert stderr == ""
    payload = json.loads(stdout.strip())
    assert payload["results"] == ["p1", "p2"]
    assert client.calls == [
        {
            "method": "search",
            "prompt": "Safe data use",
            "context": {},
            "top_k": 5,
            "min_similarity": 0.5,
            "search_mode": "semantic",
        }
    ]


def test_health_command_reports_error_on_missing_base_url():
    client = _StubClient()
    exit_code, stdout, stderr = _run(["health"], client, {})
    assert exit_code == 2
    assert stdout == ""
    assert "EJE_BASE_URL" in stderr
    assert client.calls == []


def test_rejects_invalid_context_json():
    client = _StubClient()
    exit_code, stdout, stderr = _run(
        ["--base-url", "https://api", "evaluate", "Prompt", "--context", "[1,2,3]"],
        client,
        {},
    )
    assert exit_code == 2
    assert stdout == ""
    assert "context must be a JSON object" in stderr
    assert client.calls == []

