"""Committed joined fixtures must match a fresh join of the raw replay."""
from __future__ import annotations

import json
from pathlib import Path

from agentbench.board import join_board
from agentbench.openrouter_data import load_fixture_payloads

ROOT = Path(__file__).resolve().parents[2]


def test_joined_fixtures_match_join():
    expected = join_board(load_fixture_payloads())
    for rel in (
        "agentbench/data/openrouter_board_fixture.json",
        "backend/app/data/openrouter_board_fixture.json",
    ):
        actual = json.loads((ROOT / rel).read_text())
        assert actual == expected
