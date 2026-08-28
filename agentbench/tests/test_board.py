"""T2: join four Data API feeds into a cited Usage Board snapshot."""
from __future__ import annotations

from agentbench.board import (
    CITE_TEMPLATE,
    best_by_cost,
    best_by_latency,
    best_by_task,
    join_board,
    load_board,
)
from agentbench.openrouter_data import load_fixture_payloads


def _board():
    return join_board(load_fixture_payloads())


def test_fixture_board_is_not_live_and_cites_openrouter():
    board = _board()
    assert board["live"] is False
    assert board["meta"]["as_of"] == "2026-08-27T00:00:00Z"  # classifications date is earliest
    cite = board["meta"]["citation"]
    assert cite == CITE_TEMPLATE.format(as_of=board["meta"]["as_of"])
    assert "openrouter.ai/rankings" in cite
    assert "CC BY 4.0" in cite


def test_other_ranking_row_is_not_a_model():
    ids = [row["id"] for row in _board()["rows"]]
    assert "other" not in ids
    assert set(ids) == {
        "anthropic/claude-haiku-4.5",
        "openai/gpt-4o",
        "anthropic/claude-sonnet-5",
    }


def test_rows_carry_price_usage_eval_task_latency():
    haiku = next(r for r in _board()["rows"] if r["id"] == "anthropic/claude-haiku-4.5")
    assert haiku["prompt_price"] == 0.0000008
    assert haiku["completion_price"] == 0.000004
    # 1:3 mix: 0.25 * 0.8 + 0.75 * 4.0 = 3.2 USD / 1M
    assert haiku["blended_per_million"] == 3.2
    assert haiku["daily_tokens"] == 321000000
    assert haiku["ranking_date"] == "2026-08-27"
    assert haiku["eval_score"] == 62.0
    assert haiku["eval_source"] == "artificial-analysis"
    assert haiku["latency_ms"] == 1200
    assert haiku["task_shares"]["code:general_impl"] == 0.40
    assert haiku["task_shares"]["code"] == 0.40
    assert haiku["openrouter_url"] == "https://openrouter.ai/anthropic/claude-haiku-4.5"
    assert haiku["as_of"] == "2026-08-27T00:00:00Z"
    assert "Source: OpenRouter" in haiku["citation"]


def test_best_by_cost_orders_cheapest_first():
    ordered = best_by_cost(_board())
    assert [r["id"] for r in ordered] == [
        "anthropic/claude-haiku-4.5",
        "openai/gpt-4o",
        "anthropic/claude-sonnet-5",
    ]


def test_best_by_task_orders_by_task_share():
    ordered = best_by_task(_board(), "code")
    assert ordered[0]["id"] == "anthropic/claude-haiku-4.5"
    assert ordered[1]["id"] == "anthropic/claude-sonnet-5"


def test_best_by_latency_orders_fastest_known_first():
    ordered = best_by_latency(_board())
    assert [r["id"] for r in ordered] == [
        "anthropic/claude-haiku-4.5",
        "openai/gpt-4o",
        "anthropic/claude-sonnet-5",
    ]


def test_load_board_without_key_uses_fixture(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    board = load_board()
    assert board["live"] is False
    assert len(board["rows"]) == 3


def test_load_board_does_not_live_fetch_when_key_is_set(monkeypatch):
    """Recommend reads cache/fixture only. A process key must not open a socket."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-must-not-leave-the-process")
    board = load_board()
    assert board["live"] is False
    assert board["meta"]["source"] == "fixture"
    dumped = str(board)
    assert "sk-or-v1-must-not-leave-the-process" not in dumped
