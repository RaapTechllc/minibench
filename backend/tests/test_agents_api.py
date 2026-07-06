"""Tests for the agent-benchmark API (/api/v1/agents/*)."""


def _run_payload(**overrides):
    payload = {
        "harness": "inspect-native",
        "benchmark_suite": "our-coding-v1",
        "provider": "openrouter",
        "moa_config": {"name": "moa-v1", "self_moa": False, "models": ["a", "b"]},
        "n_tasks": 4,
        "n_trials": 3,
        "pass_rate": 75.0,
        "pass_hat_k": 60.0,
        "ci95_low": 55.0,
        "ci95_high": 90.0,
        "cost_usd_per_task": 0.12,
        "latency_p50_ms": 800,
        "latency_p95_ms": 1500,
        "tokens_in": 1000,
        "tokens_out": 500,
        "results": [
            {"task_id": "code-two-sum", "category": "coding", "trial": 1, "passed": True, "score": 1.0, "cost_usd": 0.03, "latency_ms": 700},
            {"task_id": "code-two-sum", "category": "coding", "trial": 2, "passed": False, "score": 0.0, "cost_usd": 0.03, "latency_ms": 900},
        ],
    }
    payload.update(overrides)
    return payload


def test_submit_run_returns_run_id_and_persists(client):
    resp = client.post("/api/v1/agents/runs", json=_run_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"]
    assert body["benchmark_suite"] == "our-coding-v1"
    assert float(body["pass_rate"]) == 75.0

    # Detail endpoint returns the child task results.
    detail = client.get(f"/api/v1/agents/runs/{body['run_id']}").json()
    assert len(detail["results"]) == 2
    assert detail["results"][0]["task_id"] == "code-two-sum"


def test_missing_run_returns_404(client):
    r = client.get("/api/v1/agents/runs/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_leaderboard_ranks_and_flags_pareto(client):
    # Cheap+accurate (on frontier), expensive+less-accurate (dominated),
    # expensive+most-accurate (on frontier).
    client.post("/api/v1/agents/runs", json=_run_payload(
        moa_config={"name": "cheap", "self_moa": True}, pass_rate=70.0, cost_usd_per_task=0.05))
    client.post("/api/v1/agents/runs", json=_run_payload(
        moa_config={"name": "dominated"}, pass_rate=60.0, cost_usd_per_task=0.50))
    client.post("/api/v1/agents/runs", json=_run_payload(
        moa_config={"name": "top"}, pass_rate=90.0, cost_usd_per_task=0.50))

    board = client.get("/api/v1/agents/leaderboard").json()
    assert len(board) == 3
    # Default sort is pass_rate desc.
    assert [e["config_name"] for e in board] == ["top", "cheap", "dominated"]
    frontier = {e["config_name"]: e["on_pareto_frontier"] for e in board}
    assert frontier["cheap"] is True
    assert frontier["top"] is True
    assert frontier["dominated"] is False
    # self_moa flag round-trips from moa_config.
    assert next(e for e in board if e["config_name"] == "cheap")["self_moa"] is True


def test_leaderboard_sort_by_cost_ascending(client):
    client.post("/api/v1/agents/runs", json=_run_payload(
        moa_config={"name": "pricey"}, cost_usd_per_task=0.90))
    client.post("/api/v1/agents/runs", json=_run_payload(
        moa_config={"name": "budget"}, cost_usd_per_task=0.02))
    board = client.get("/api/v1/agents/leaderboard?sort_by=cost_usd_per_task").json()
    assert [e["config_name"] for e in board] == ["budget", "pricey"]


def test_leaderboard_filters_by_suite(client):
    client.post("/api/v1/agents/runs", json=_run_payload(benchmark_suite="our-coding-v1"))
    client.post("/api/v1/agents/runs", json=_run_payload(benchmark_suite="our-tooluse-v1"))
    board = client.get("/api/v1/agents/leaderboard?suite=our-tooluse-v1").json()
    assert len(board) == 1
    assert board[0]["benchmark_suite"] == "our-tooluse-v1"


def test_new_models_lists_only_unbenchmarked(client, seed_known_models):
    rows = client.get("/api/v1/agents/models/new").json()
    ids = {r["model_id"] for r in rows}
    assert "openrouter/new/model-a" in ids
    assert "openrouter/old/benchmarked" not in ids


def test_leaderboard_surfaces_models_and_snapshot_date(client):
    client.post("/api/v1/agents/runs", json=_run_payload(
        moa_config={"name": "moa-v1", "self_moa": False, "models": ["a", "b", "c"]},
        model_snapshot_date="2026-06-15",
    ))
    board = client.get("/api/v1/agents/leaderboard").json()
    assert board[0]["models"] == ["a", "b", "c"]
    assert board[0]["model_snapshot_date"] == "2026-06-15"


def test_leaderboard_models_defaults_empty_when_absent(client):
    client.post("/api/v1/agents/runs", json=_run_payload(moa_config=None))
    board = client.get("/api/v1/agents/leaderboard").json()
    assert board[0]["models"] == []
    assert board[0]["model_snapshot_date"] is None
