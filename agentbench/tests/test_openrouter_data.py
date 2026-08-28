"""T1: GET-only Data API client — allowlist, env key, fixture fallback."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentbench.openrouter_data import (
    ALLOWED_PATHS,
    DataAPIClient,
    DataAPIError,
    FIXTURE_PATH,
    load_fixture_payloads,
    redact_secrets,
)


class RecordingTransport:
    def __init__(self) -> None:
        self.gets: list[tuple[str, dict[str, str]]] = []

    def get_json(self, url: str, headers: dict[str, str]) -> dict:
        self.gets.append((url, dict(headers)))
        return {"data": [], "meta": {"as_of": "2026-08-28T00:00:00Z"}}


def test_allowlist_is_exactly_the_four_gate1_paths():
    assert ALLOWED_PATHS == frozenset(
        {
            "/models",
            "/datasets/rankings-daily",
            "/benchmarks",
            "/classifications/task",
        }
    )


def test_client_rejects_chat_completions():
    client = DataAPIClient(api_key="sk-or-v1-test", transport=RecordingTransport())
    with pytest.raises(DataAPIError, match="not allowlisted"):
        client.get("/chat/completions")


def test_client_rejects_analytics():
    client = DataAPIClient(api_key="sk-or-v1-test", transport=RecordingTransport())
    with pytest.raises(DataAPIError, match="not allowlisted"):
        client.get("/analytics")


def test_rejected_path_error_does_not_echo_key():
    key = "sk-or-v1-super-secret-value"
    client = DataAPIClient(api_key=key, transport=RecordingTransport())
    with pytest.raises(DataAPIError) as exc:
        client.get("/chat/completions")
    assert key not in str(exc.value)
    assert key not in repr(exc.value)


def test_get_sends_referer_and_title_not_a_client_key(monkeypatch):
    transport = RecordingTransport()
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = DataAPIClient(api_key="sk-or-v1-from-env", transport=transport)
    body = client.get("/models")
    assert body["data"] == []
    url, headers = transport.gets[0]
    assert url.endswith("/models")
    assert headers["HTTP-Referer"]
    assert headers["X-Title"] == "MiniBench"
    assert headers["Authorization"] == "Bearer sk-or-v1-from-env"
    assert "sk-or-v1-from-client" not in json.dumps(body)


def test_client_refuses_constructor_override_from_request_kwargs():
    """No client-supplied key channel — only env or explicit process setup."""
    transport = RecordingTransport()
    client = DataAPIClient(api_key="sk-or-v1-process", transport=transport)
    with pytest.raises(TypeError):
        client.get("/models", api_key="sk-or-v1-injected")  # type: ignore[call-arg]


def test_missing_key_without_transport_does_not_open_a_socket(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = DataAPIClient()
    assert client.can_live_fetch() is False
    with pytest.raises(DataAPIError, match="fixture"):
        client.get("/models")


def test_load_fixture_payloads_has_four_feeds_and_is_not_live():
    payloads = load_fixture_payloads()
    assert payloads["live"] is False
    assert set(payloads["feeds"]) == {
        "/models",
        "/datasets/rankings-daily",
        "/benchmarks",
        "/classifications/task",
    }
    assert FIXTURE_PATH.exists()
    raw = json.loads(Path(FIXTURE_PATH).read_text())
    assert raw["live"] is False


def test_redact_secrets_strips_openrouter_keys():
    text = "boom sk-or-v1-abcdef0123456789 leftover"
    assert "sk-or-v1-abcdef0123456789" not in redact_secrets(text)
    assert "sk-or-v1-" not in redact_secrets(text) or "[redacted]" in redact_secrets(text)
