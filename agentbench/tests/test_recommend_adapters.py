"""MCP dispatch + localhost REST handler — no CORS app, no key in bodies."""
from __future__ import annotations

import json

from agentbench.board import join_board
from agentbench.mcp_recommend import handle_mcp
from agentbench.openrouter_data import load_fixture_payloads
from agentbench.recommend_http import handle_http


def _board():
    return join_board(load_fixture_payloads())


def test_mcp_tools_list_exposes_recommend_only():
    reply = handle_mcp({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, _board())
    names = [t["name"] for t in reply["result"]["tools"]]
    assert names == ["recommend"]


def test_mcp_call_returns_cited_pick_without_key():
    reply = handle_mcp(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "recommend",
                "arguments": {"task": "code", "budget": 5, "max_latency_ms": 5000},
            },
        },
        _board(),
    )
    text = reply["result"]["content"][0]["text"]
    payload = json.loads(text)
    assert payload["pick"]["id"] == "anthropic/claude-haiku-4.5"
    assert "sk-or-" not in text
    assert "Source: OpenRouter" in payload["citation"]


def test_mcp_rejects_client_key_argument():
    reply = handle_mcp(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "recommend", "arguments": {"task": "code", "api_key": "sk-or-v1-nope"}},
        },
        _board(),
    )
    payload = json.loads(reply["result"]["content"][0]["text"])
    assert payload["pick"] is None
    assert payload["error"] == "client-supplied key is not accepted"


def test_http_recommend_on_path():
    status, headers, body = handle_http(
        "GET",
        "/recommend?task=code&budget=5&max_latency_ms=5000",
        _board(),
    )
    assert status == 200
    assert headers["Content-Type"] == "application/json"
    payload = json.loads(body)
    assert payload["pick"]["id"] == "anthropic/claude-haiku-4.5"


def test_http_rejects_client_key_and_stays_json():
    status, _, body = handle_http("GET", "/recommend?task=code&api_key=sk-or-v1-nope", _board())
    assert status == 400
    payload = json.loads(body)
    assert payload["error"] == "client-supplied key is not accepted"
    assert "sk-or-v1-nope" not in body


def test_http_default_bind_is_localhost():
    from agentbench.recommend_http import DEFAULT_HOST, DEFAULT_PORT

    assert DEFAULT_HOST == "127.0.0.1"
    assert DEFAULT_PORT == 3072


def test_http_access_log_strips_query_and_keys():
    from agentbench.recommend_http import safe_access_log

    rendered = safe_access_log("GET /recommend?task=code&api_key=sk-or-v1-nope HTTP/1.1")
    assert "sk-or-v1-nope" not in rendered
    assert "?[redacted]" in rendered


def test_recommend_not_imported_by_main_app():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[2] / "backend" / "app" / "main.py").read_text()
    assert "recommend_http" not in source
    assert "mcp_recommend" not in source
    assert '"/recommend"' not in source
    assert "'/recommend'" not in source
