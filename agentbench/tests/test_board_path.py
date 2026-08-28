"""persist-live A2: honor OPENROUTER_BOARD_PATH; fixture default is never live."""
from __future__ import annotations

import json
from pathlib import Path

from agentbench.board import load_board
from agentbench.poll_openrouter import poll
from agentbench.recommend import recommend

LIVE_AS_OF = "2026-08-28T06:20:00Z"
LIVE_CITE = (
    f"Source: OpenRouter (openrouter.ai/rankings), as of {LIVE_AS_OF}. CC BY 4.0."
)
ROOT = Path(__file__).resolve().parents[2]


def _live_snapshot() -> dict:
    return {
        "live": True,
        "meta": {
            "as_of": LIVE_AS_OF,
            "citation": LIVE_CITE,
            "live": True,
            "source": "openrouter",
            "row_count": 1,
        },
        "rows": [
            {
                "id": "persist-live/path-honor",
                "name": "Path Honor",
                "openrouter_url": "https://openrouter.ai/persist-live/path-honor",
                "prompt_price": 1e-6,
                "completion_price": 2e-6,
                "blended_per_million": 1.75,
                "daily_tokens": 1,
                "ranking_date": "2026-08-28",
                "eval_score": 1.0,
                "eval_source": "openrouter",
                "eval_task": "intelligence_index",
                "latency_ms": 100,
                "task_shares": {"code": 0.99, "code:general_impl": 0.99},
                "citation": LIVE_CITE,
                "as_of": LIVE_AS_OF,
            }
        ],
    }


def test_poll_writes_openrouter_board_path_when_set(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    dest = tmp_path / "durable-board.json"
    monkeypatch.setenv("OPENROUTER_BOARD_PATH", str(dest))
    board = poll()
    assert dest.is_file()
    dumped = json.loads(dest.read_text())
    assert dumped["meta"]["as_of"] == board["meta"]["as_of"]
    assert "Source: OpenRouter (openrouter.ai/rankings), as of" in dumped["meta"]["citation"]
    assert dumped["meta"]["as_of"] in dumped["meta"]["citation"]
    assert dumped["live"] is False


def test_load_board_honors_env_path_when_file_exists(tmp_path, monkeypatch):
    dest = tmp_path / "live.json"
    dest.write_text(json.dumps(_live_snapshot()) + "\n")
    monkeypatch.setenv("OPENROUTER_BOARD_PATH", str(dest))
    board = load_board()
    assert board["live"] is True
    assert board["meta"]["live"] is True
    assert board["meta"]["as_of"] == LIVE_AS_OF
    assert board["rows"][0]["id"] == "persist-live/path-honor"
    assert board["rows"][0]["as_of"] == LIVE_AS_OF
    assert board["meta"]["citation"] == LIVE_CITE


def test_recommend_reads_env_board_path(tmp_path, monkeypatch):
    dest = tmp_path / "live.json"
    dest.write_text(json.dumps(_live_snapshot()) + "\n")
    monkeypatch.setenv("OPENROUTER_BOARD_PATH", str(dest))
    result = recommend(load_board(), task="code", budget=5.0, max_latency_ms=5000)
    assert result["pick"]["id"] == "persist-live/path-honor"
    assert result["live"] is True
    assert result["as_of"] == LIVE_AS_OF
    assert result["citation"] == LIVE_CITE


def test_load_board_unset_path_serves_fixture_not_live(monkeypatch):
    monkeypatch.delenv("OPENROUTER_BOARD_PATH", raising=False)
    board = load_board()
    assert board["live"] is False
    assert board["meta"]["live"] is False
    assert board["meta"]["source"] == "fixture"
    assert "persist-live/path-honor" not in [row["id"] for row in board["rows"]]
    assert board["meta"]["as_of"]
    assert board["meta"]["as_of"] in board["meta"]["citation"]


def test_load_board_missing_path_serves_fixture_not_live(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_BOARD_PATH", str(tmp_path / "missing.json"))
    board = load_board()
    assert board["live"] is False
    assert board["meta"]["live"] is False
    assert board["meta"]["source"] == "fixture"
    assert board["meta"]["as_of"] in board["meta"]["citation"]
    for row in board["rows"]:
        assert row["as_of"] == board["meta"]["as_of"]
        assert "Source: OpenRouter" in row["citation"]


def test_workflow_does_not_treat_tmp_as_durable_live_board():
    workflow = (ROOT / ".github/workflows/openrouter-board.yml").read_text()
    assert "/tmp/board-live.json" not in workflow
    assert "OPENROUTER_BOARD_PATH" in workflow
    assert "upload-artifact" in workflow
