"""T3: recommend compare over a cached/fixture board."""
from __future__ import annotations

import json

from agentbench.board import join_board, load_board
from agentbench.openrouter_data import load_fixture_payloads
from agentbench.recommend import recommend, recommend_from_query


def _board():
    return join_board(load_fixture_payloads())


def test_recommend_picks_haiku_for_code_under_budget():
    result = recommend(_board(), task="code", budget=5.0, max_latency_ms=5000)
    assert result["pick"] is not None
    assert result["pick"]["id"] == "anthropic/claude-haiku-4.5"
    assert "Source: OpenRouter (openrouter.ai/rankings), as of" in result["citation"]
    assert result["as_of"] == result["pick"]["as_of"]
    assert result["live"] is False


def test_recommend_miss_when_budget_too_low():
    result = recommend(_board(), task="code", budget=0.01)
    assert result["pick"] is None
    assert "no model" in result["reason"].lower()
    assert "Source: OpenRouter" in result["citation"]


def test_recommend_excludes_unknown_latency_when_capped():
    board = _board()
    for row in board["rows"]:
        if row["id"] == "anthropic/claude-haiku-4.5":
            row["latency_ms"] = None
    result = recommend(board, task="code", max_latency_ms=2000)
    assert result["pick"] is None or result["pick"]["id"] != "anthropic/claude-haiku-4.5"


def test_recommend_prefers_higher_task_share_then_price():
    result = recommend(_board(), task="code")
    assert result["pick"]["id"] == "anthropic/claude-haiku-4.5"


def test_query_rejects_client_supplied_key():
    result = recommend_from_query(_board(), {"task": "code", "api_key": "sk-or-v1-injected"})
    assert result["pick"] is None
    assert result.get("error") == "client-supplied key is not accepted"
    assert "sk-or-v1" not in json.dumps(result)


def test_query_parses_budget_and_latency():
    result = recommend_from_query(
        _board(),
        {"task": "code", "budget": "5", "max_latency_ms": "5000"},
    )
    assert result["pick"]["id"] == "anthropic/claude-haiku-4.5"


def test_load_board_then_recommend_is_the_dogfood_path(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = recommend(load_board(), task="code", budget=5.0)
    assert result["pick"]["id"] == "anthropic/claude-haiku-4.5"
    assert result["live"] is False
