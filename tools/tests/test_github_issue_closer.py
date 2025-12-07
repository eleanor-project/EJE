import sys
import requests
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import github_issue_closer as closer


class DummyResponse:
    def __init__(self, status_code=200, text="", raise_exc=None):
        self.status_code = status_code
        self.text = text
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc:
            raise self._raise_exc


class DummySession:
    def __init__(self, response):
        self.response = response
        self.patched = []
        self.headers = {}

    def patch(self, url, json=None, timeout=None):
        self.patched.append(SimpleNamespace(url=url, payload=json, timeout=timeout))
        return self.response


def test_parse_issue_numbers_supports_commas_and_spaces():
    numbers = closer.parse_issue_numbers(["140", "150, 151", "  200 "])
    assert numbers == [140, 150, 151, 200]


def test_parse_issue_numbers_rejects_invalid_input():
    with pytest.raises(ValueError):
        closer.parse_issue_numbers(["abc", "123"])


def test_resolve_token_prefers_explicit_and_env_fallback(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    with pytest.raises(closer.TokenNotProvidedError):
        closer.resolve_token(None)

    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    assert closer.resolve_token(None) == "env-token"
    assert closer.resolve_token("arg-token") == "arg-token"


def test_close_issue_dry_run_prints_and_skips_network(capsys):
    session = DummySession(DummyResponse())
    closer.close_issue(session, "owner/repo", 99, dry_run=True)
    assert session.patched == []
    out = capsys.readouterr().out
    assert "Would close issue #99" in out


def test_close_issue_handles_not_found():
    session = DummySession(DummyResponse(status_code=404))
    with pytest.raises(closer.IssueClosingError):
        closer.close_issue(session, "owner/repo", 5)


def test_close_issue_raises_on_http_error():
    error = requests.HTTPError("boom")
    session = DummySession(DummyResponse(status_code=500, raise_exc=error))
    with pytest.raises(closer.IssueClosingError):
        closer.close_issue(session, "owner/repo", 6)


def test_close_issues_invokes_patch_for_each(monkeypatch):
    responses = [DummyResponse(), DummyResponse()]
    dummy_session = DummySession(responses[0])

    def fake_make_session(token):
        assert token == "token"
        return dummy_session

    monkeypatch.setattr(closer, "make_session", fake_make_session)

    closer.close_issues("owner/repo", [1, 2], token="token", dry_run=False)
    assert len(dummy_session.patched) == 2
    assert dummy_session.patched[0].url.endswith("/issues/1")
    assert dummy_session.patched[1].url.endswith("/issues/2")
