"""Public Usage Board loader honors OPENROUTER_BOARD_PATH; missing path is fixture."""
from __future__ import annotations

import json

from app.openrouter_board import load_snapshot

LIVE_AS_OF = "2026-08-28T06:20:00Z"
LIVE_CITE = (
    f"Source: OpenRouter (openrouter.ai/rankings), as of {LIVE_AS_OF}. CC BY 4.0."
)


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
                "citation": LIVE_CITE,
                "as_of": LIVE_AS_OF,
            }
        ],
    }


def test_public_loader_honors_env_path_when_file_exists(tmp_path, monkeypatch):
    dest = tmp_path / "live.json"
    dest.write_text(json.dumps(_live_snapshot()) + "\n")
    monkeypatch.setenv("OPENROUTER_BOARD_PATH", str(dest))
    board = load_snapshot()
    assert board["meta"]["live"] is True
    assert board["meta"]["as_of"] == LIVE_AS_OF
    assert board["rows"][0]["id"] == "persist-live/path-honor"
    assert LIVE_AS_OF in board["meta"]["citation"]


def test_public_loader_unset_path_serves_fixture_not_live(monkeypatch):
    monkeypatch.delenv("OPENROUTER_BOARD_PATH", raising=False)
    board = load_snapshot()
    assert board["meta"]["live"] is False
    assert board["meta"]["source"] == "fixture"
    assert "persist-live/path-honor" not in [row["id"] for row in board["rows"]]
    assert board["meta"]["as_of"] in board["meta"]["citation"]


def test_public_loader_missing_path_serves_fixture_not_live(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_BOARD_PATH", str(tmp_path / "missing.json"))
    board = load_snapshot()
    assert board["meta"]["live"] is False
    assert board["meta"]["source"] == "fixture"
    assert board["meta"]["as_of"] in board["meta"]["citation"]
    for row in board["rows"]:
        assert row["as_of"] == board["meta"]["as_of"]
