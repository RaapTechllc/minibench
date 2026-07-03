import json

from agentbench.config import load_moa_config
from agentbench.run import StubModel, run_suite, summarize, load_tasks, main
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


def test_live_run_without_key_errors_cleanly(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    rc = main([
        "--config", MOA_V1,
        "--tasks", CODING_V1,
        "--provider", "openrouter",
    ])
    assert rc == 2  # refuses to pretend; tells the user to use --dry-run
