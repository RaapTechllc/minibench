from pathlib import Path

from agentbench.poll_openrouter import poll


def test_poll_without_key_writes_fixture_snapshot(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    out = tmp_path / "board.json"
    board = poll(out=out)
    assert out.exists()
    assert board["live"] is False
    assert board["meta"]["row_count"] == 3
    assert "Source: OpenRouter" in board["meta"]["citation"]


def test_poll_fixture_flag_ignores_key(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-should-not-be-used")
    out = tmp_path / "board.json"
    board = poll(out=out, force_fixture=True)
    assert board["live"] is False
    dumped = Path(out).read_text()
    assert "sk-or-v1-should-not-be-used" not in dumped
