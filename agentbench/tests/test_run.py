import json
from unittest.mock import patch, MagicMock

from agentbench.config import load_moa_config
from agentbench.run import StubModel, run_suite, summarize, load_tasks, main, to_agent_run_submit, publish_run
from agentbench.resources import MOA_V1, CODING_V1


def test_dry_run_end_to_end_passes_seed_tasks():
    config = load_moa_config(MOA_V1)
    suite, tasks = load_tasks(CODING_V1)
    results = run_suite(config, tasks, trials=3, model=None, stub=StubModel())

    # 4 tasks x 3 trials.
    assert len(results) == 12
    # The stub answers satisfy every seed oracle, so all trials pass.
    assert all(r.passed for r in results)

    summary = summarize(config, suite, 3, results)
    assert summary["n_tasks"] == 4
    assert summary["n_trials"] == 3
    assert summary["pass_rate"] == 1.0
    assert summary["pass_hat_k"] == 1.0
    assert summary["latency_p95_ms"] == 0.0  # stub is instantaneous


def test_cli_dry_run_writes_artifact(tmp_path):
    out = tmp_path / "result.json"
    rc = main([
        "--config", MOA_V1,
        "--tasks", CODING_V1,
        "--trials", "2",
        "--dry-run",
        "--out", str(out),
    ])
    assert rc == 0
    payload = json.loads(out.read_text())
    assert payload["dry_run"] is True
    assert payload["summary"]["pass_rate"] == 1.0
    assert len(payload["trials"]) == 8  # 4 tasks x 2 trials


def test_to_agent_run_submit_scales_percentages():
    config = load_moa_config(MOA_V1)
    suite, tasks = load_tasks(CODING_V1)
    results = run_suite(config, tasks, trials=2, model=None, stub=StubModel())
    summary = summarize(config, suite, 2, results)
    payload = to_agent_run_submit(summary, results, provider="openrouter")

    assert payload["benchmark_suite"] == suite
    assert payload["pass_rate"] == 100.0
    assert payload["pass_hat_k"] == 100.0
    assert payload["ci95_low"] is not None
    assert len(payload["results"]) == len(results)


def test_live_run_without_key_errors_cleanly(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("agentbench.run._load_env_files", lambda: None)
    rc = main([
        "--config", MOA_V1,
        "--tasks", CODING_V1,
        "--provider", "openrouter",
    ])
    assert rc == 2  # refuses to pretend; tells the user to use --dry-run


def test_publish_run_raises_on_http_error():
    """publish_run wraps HTTPError into RuntimeError with status + detail."""
    import urllib.error

    with patch("agentbench.run.urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://fake", 500, "Server Error", {}, None,
        )
        try:
            publish_run("http://localhost:3070", {"pass_rate": 100.0})
            assert False, "Expected RuntimeError"
        except RuntimeError as exc:
            assert "500" in str(exc)


def test_cli_publish_flag_invokes_publish(tmp_path):
    """main() with --publish calls publish_run with the transformed payload."""
    out = tmp_path / "result.json"
    with patch("agentbench.run.publish_run", return_value={"run_id": "abc-123"}) as mock_pub:
        rc = main([
            "--config", MOA_V1,
            "--tasks", CODING_V1,
            "--trials", "1",
            "--dry-run",
            "--out", str(out),
            "--publish", "http://localhost:3070",
        ])
    assert rc == 0
    mock_pub.assert_called_once()
    call_args, _ = mock_pub.call_args
    assert call_args[0] == "http://localhost:3070"
    assert "pass_rate" in call_args[1]


def test_cli_publish_returns_1_on_runtime_error(tmp_path):
    """If publish_run raises RuntimeError, main() returns exit code 1."""
    out = tmp_path / "result.json"
    with patch("agentbench.run.publish_run", side_effect=RuntimeError("publish failed (500): boom")):
        rc = main([
            "--config", MOA_V1,
            "--tasks", CODING_V1,
            "--trials", "1",
            "--dry-run",
            "--out", str(out),
            "--publish", "http://localhost:3070",
        ])
    assert rc == 1
