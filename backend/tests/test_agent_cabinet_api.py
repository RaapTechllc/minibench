"""Hop A API tests for Real-Work Agent Cabinet (A1–A6)."""
from __future__ import annotations

import os
from copy import deepcopy
from uuid import UUID

import psycopg2

from agentbench.agent_cabinet import (
    AGENT_CABINET_POLICY,
    COMPARABILITY_FIELDS,
    PUBLICATION_REFUSE_REASONS,
    PUBLISH_REFUSE_DRY_RUN,
    REQUIRED_PROVENANCE_KEYS,
    private_split_id,
    publication_receipt,
)
from agentbench.tests.test_import_results import _legacy_artifact
from tests.conftest import PG_HOST, PG_PASS, PG_PORT, PG_USER, TEST_DB

from app.agent_cabinet_present import (
    category_completion_from_trials,
    completion_from_artifact,
    default_view,
    detail_view,
    technician_view,
)


def _base_artifact() -> dict:
    return {
        "generated_at": "2026-08-28T00:00:00+00:00",
        "dry_run": False,
        "provenance": {
            "model": "deterministic-fake-agent",
            "provider": "offline",
            "model_route": "offline/deterministic-fake-agent",
            "harness": "minibench-reference",
            "harness_version": "1",
            "tool_contract": ["filesystem"],
            "tool_contract_sha256": "a" * 64,
            "prompt_config_sha256": "b" * 64,
            "fixture_reference": "offline-text-repair@1",
            "fixture_digest": "sha256:760554a0320df97ccce509047ac3825878a252a4a2852f22f8ced20da7a5aa2c",
            "generator_sha256": "c" * 64,
            "suite": "minibench-agent-v1",
            "task_set_sha256": "d" * 64,
            "budgets": {
                "max_turns": 1,
                "wall_time_seconds": 5,
                "max_tokens": 100,
                "max_cost_usd": 0.0,
            },
            "git_commit": "e" * 40,
            "grader_version": "agent-1",
            "private_split": False,
            "private_split_id": "f" * 64,
            "policy_version": AGENT_CABINET_POLICY,
        },
        "summary": {
            "suite": "minibench-agent-v1",
            "moa_config": {
                "name": "minibench-reference",
                "self_moa": False,
                "models": ["deterministic-fake-agent"],
            },
            "grader_version": "agent-1",
            "n_tasks": 1,
            "n_trials": 2,
            "pass_rate": 1.0,
            "pass_hat_k": 1.0,
            "pass_rate_ci95": [0.34, 1.0],
            "pass_rate_ci95_boot": [1.0, 1.0],
            "n_infra_errors": 0,
            "n_canary_flags": 0,
            "cost_usd_per_task": 0.02,
            "latency_p50_ms": 15,
            "evaluation_type": "agent_harness",
            "false_verification_rate": 0.0,
            "regression_rate": None,
            "termination_reasons": {"completed": 2},
        },
        "trials": [
            {
                "task_id": "mba-offline-text-repair-001",
                "category": "repository-repair",
                "trial": 1,
                "outcome": "success",
                "passed": True,
                "workspace_disposed": True,
                "agent_claimed_success": True,
                "termination_reason": "completed",
            },
            {
                "task_id": "mba-offline-text-repair-001",
                "category": "repository-repair",
                "trial": 2,
                "outcome": "success",
                "passed": True,
                "workspace_disposed": True,
                "agent_claimed_success": True,
                "termination_reason": "completed",
            },
        ],
    }


def _artifact(**provenance_overrides) -> dict:
    artifact = deepcopy(_base_artifact())
    artifact["provenance"].update(provenance_overrides)
    if "private_split" in provenance_overrides:
        artifact["provenance"]["private_split_id"] = private_split_id(
            suite=artifact["provenance"]["suite"],
            private_split=bool(provenance_overrides["private_split"]),
            fixture_digest=artifact["provenance"]["fixture_digest"],
        )
    assert publication_receipt(artifact)["publishable"] is True
    return artifact


def _table_count(table: str) -> int:
    conn = psycopg2.connect(
        host=os.environ.get("MINIBENCH_TEST_PG_HOST", PG_HOST),
        port=os.environ.get("MINIBENCH_TEST_PG_PORT", PG_PORT),
        user=os.environ.get("MINIBENCH_TEST_PG_USER", PG_USER),
        password=os.environ.get("MINIBENCH_TEST_PG_PASSWORD", PG_PASS),
        dbname=os.environ.get("MINIBENCH_TEST_PG_DB", TEST_DB),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {table}")
            return cur.fetchone()[0]
    finally:
        conn.close()


def _post(client, artifact):
    return client.post("/api/v1/agent-cabinet/runs", json=artifact)


# ─── A1: ingest + list best valid runs ────────────────────────────────────────


def test_a1_post_publishable_and_list_best_valid_runs(client):
    high = _artifact()
    high["summary"]["pass_rate"] = 0.75
    low = _artifact()
    low["summary"]["pass_rate"] = 0.25

    first = _post(client, low)
    second = _post(client, high)
    assert first.status_code == 200
    assert second.status_code == 200
    assert publication_receipt(high)["publishable"] is True

    listed = client.get("/api/v1/agent-cabinet/runs").json()
    assert len(listed) == 1
    item = listed[0]
    assert item["completion"] == 75.0
    assert item["pass_rate"] == 75.0
    assert item["category_completion"] == {"repository-repair": 100.0}
    assert item["cost_usd_per_task"] == 0.02
    assert item["latency_p50_ms"] == 15
    assert item["run_id"] == second.json()["run_id"]

    detail = client.get(f"/api/v1/agent-cabinet/runs/{item['run_id']}").json()
    for key in REQUIRED_PROVENANCE_KEYS:
        assert key in detail["technician"]


# ─── A2: isolation from Solo / MoA / hardware; no composite ───────────────────


def test_a2_cabinet_does_not_touch_other_leaderboards_or_add_composite(client):
    before_runs = _table_count("agent_runs")
    before_hardware = _table_count("benchmarks")
    posted = _post(client, _artifact())
    assert posted.status_code == 200
    body = posted.json()
    assert "composite" not in body
    assert "technician" in body and isinstance(body["technician"], dict)

    assert _table_count("agent_runs") == before_runs
    assert _table_count("agent_cabinet_runs") == 1
    assert _table_count("benchmarks") == before_hardware

    assert client.get("/api/v1/agents/leaderboard").json() == []
    assert client.get("/api/v1/agents/models/leaderboard").json() == []
    hardware = client.get("/api/v1/leaderboard").json()
    assert all("run_id" not in row for row in hardware)
    assert all(row.get("id") != body["run_id"] for row in hardware)

    listed = client.get("/api/v1/agent-cabinet/runs").json()
    assert "composite" not in listed[0]
    missing = client.get(f"/api/v1/agents/runs/{body['run_id']}")
    assert missing.status_code == 404


# ─── A3: default view fields ──────────────────────────────────────────────────


def test_a3_default_view_is_completion_category_cost_latency(client):
    artifact = _artifact()
    artifact["trials"][1]["category"] = "feature-implementation"
    artifact["trials"][1]["passed"] = False
    artifact["summary"]["pass_rate"] = 0.5
    posted = _post(client, artifact)
    assert posted.status_code == 200

    item = client.get("/api/v1/agent-cabinet/runs").json()[0]
    assert item["completion"] == 50.0
    assert item["category_completion"] == {
        "repository-repair": 100.0,
        "feature-implementation": 0.0,
    }
    assert item["cost_usd_per_task"] == 0.02
    assert item["latency_p50_ms"] == 15
    assert "technician" not in item
    assert "false_verification_rate" not in item

    row = {
        "run_id": "x",
        "completion": completion_from_artifact(artifact),
        "category_completion": category_completion_from_trials(artifact["trials"]),
        "cost_usd_per_task": 0.02,
        "latency_p50_ms": 15,
        "private_split": False,
        "suite": "minibench-agent-v1",
        "model_route": "offline/deterministic-fake-agent",
        "harness": "minibench-reference",
        "harness_version": "1",
        "artifact": artifact,
    }
    view = default_view(row)
    assert set(view) >= {
        "completion",
        "category_completion",
        "cost_usd_per_task",
        "latency_p50_ms",
    }


# ─── A4: nested technician ────────────────────────────────────────────────────


def test_a4_technician_is_nested_and_lists_required_fields(client):
    posted = _post(client, _artifact())
    run_id = posted.json()["run_id"]
    detail = client.get(f"/api/v1/agent-cabinet/runs/{run_id}").json()
    tech = detail["technician"]
    assert "technician" not in tech
    for key in REQUIRED_PROVENANCE_KEYS:
        assert key in tech
        assert tech[key] not in (None, "", [], {})
    assert tech["false_verification_rate"] == 0.0
    assert tech["regression_rate"] is None
    assert tech["termination_reasons"] == {"completed": 2}
    assert tech["pass_hat_k"] == 100.0
    assert tech["ci95_low"] == 34.0
    assert tech["ci95_high"] == 100.0
    assert tech["budgets"]["max_turns"] == 1
    assert len(tech["trials"]) == 2

    listed = client.get("/api/v1/agent-cabinet/runs?view=technician").json()
    assert "technician" in listed[0]
    assert listed[0]["technician"]["harness"] == "minibench-reference"
    assert listed[0]["completion"] == 100.0


# ─── A5: held_constant, changed variables, compare ────────────────────────────


def test_a5_compare_and_held_constant_contract(client):
    left = _artifact()
    right = _artifact(model_route="offline/other-agent")
    right["provenance"]["model"] = "other-agent"
    right["summary"]["moa_config"] = {
        "name": "other",
        "self_moa": False,
        "models": ["other-agent"],
    }
    right["trials"][1]["passed"] = False
    right["trials"][1]["outcome"] = "verification_failed"
    right["summary"]["pass_rate"] = 0.5

    a = _post(client, left).json()
    b = _post(client, right).json()
    assert a["held_constant"] == list(COMPARABILITY_FIELDS)
    assert "model_route" in a["changed_variables"]
    assert "harness" in a["changed_variables"]

    compared = client.get(
        f"/api/v1/agent-cabinet/compare?a={a['run_id']}&b={b['run_id']}"
    )
    assert compared.status_code == 200
    body = compared.json()
    assert body["receipt"]["comparable"] is True
    assert body["held_constant"] == list(COMPARABILITY_FIELDS)
    assert body["changed_variables"] == "Changed variable: model_route."
    assert "verdict" in body["comparison"]

    mismatch = _artifact(harness="other-harness")
    other = _post(client, mismatch).json()
    refused = client.get(
        f"/api/v1/agent-cabinet/compare?a={a['run_id']}&b={other['run_id']}"
    )
    assert refused.status_code == 409
    assert refused.json()["detail"]["comparable"] is False
    assert "harness" in refused.json()["detail"]["failing_fields"]

    solo = client.post(
        "/api/v1/agents/runs",
        json={
            "harness": "inspect-native",
            "benchmark_suite": "our-coding-v1",
            "provider": "openrouter",
            "moa_config": {"name": "moa-v1", "self_moa": False, "models": ["a"]},
            "n_tasks": 1,
            "n_trials": 1,
            "pass_rate": 50.0,
            "results": [{"task_id": "x", "category": "coding", "trial": 1, "passed": True}],
        },
    )
    assert solo.status_code == 200
    cross = client.get(
        f"/api/v1/agent-cabinet/compare?a={a['run_id']}&b={solo.json()['run_id']}"
    )
    assert cross.status_code == 409
    assert "evaluation_type" in cross.json()["detail"]["failing_fields"]


def test_a5_solo_artifact_is_evaluation_type_mismatch(client):
    resp = _post(client, _legacy_artifact())
    assert resp.status_code == 422
    assert resp.json()["detail"]["failing_fields"] == ["evaluation_type"]
    assert resp.json()["detail"]["reasons"] == ["evaluation_type mismatch"]


# ─── A6: publication 422 + private supersession + tie break ───────────────────


def test_a6_unpublishable_is_422_with_receipt(client):
    dry = _artifact()
    dry["dry_run"] = True
    resp = _post(client, dry)
    assert resp.status_code == 422
    receipt = resp.json()["detail"]
    assert receipt["publishable"] is False
    assert PUBLISH_REFUSE_DRY_RUN in receipt["reasons"]
    assert receipt["policy_version"] == AGENT_CABINET_POLICY
    assert _table_count("agent_cabinet_runs") == 0


def test_a6_private_split_supersedes_higher_public(client):
    public = _artifact(private_split=False)
    public["summary"]["pass_rate"] = 0.9
    private = _artifact(private_split=True)
    private["summary"]["pass_rate"] = 0.1
    _post(client, public)
    private_id = _post(client, private).json()["run_id"]

    listed = client.get("/api/v1/agent-cabinet/runs").json()
    assert len(listed) == 1
    assert listed[0]["run_id"] == private_id
    assert listed[0]["completion"] == 10.0
    assert listed[0]["private_split"] is True


def test_a6_tie_breaks_to_latest_submitted_at(client):
    first = _post(client, _artifact()).json()
    second = _post(client, _artifact()).json()
    listed = client.get("/api/v1/agent-cabinet/runs").json()
    assert len(listed) == 1
    assert listed[0]["run_id"] == second["run_id"]
    assert listed[0]["run_id"] != first["run_id"]
    UUID(listed[0]["run_id"])


def test_missing_cabinet_run_returns_404(client):
    resp = client.get("/api/v1/agent-cabinet/runs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_a6_different_model_route_lists_both(client):
    _post(client, _artifact())
    _post(client, _artifact(model_route="offline/other"))
    listed = client.get("/api/v1/agent-cabinet/runs").json()
    assert len(listed) == 2
    assert {item["model_route"] for item in listed} == {
        "offline/deterministic-fake-agent",
        "offline/other",
    }


def test_present_helpers_do_not_flatten_technician():
    artifact = _artifact()
    row = {
        "run_id": "row-1",
        "submitted_at": "2026-08-28T00:00:00+00:00",
        "suite": "minibench-agent-v1",
        "model_route": artifact["provenance"]["model_route"],
        "harness": "minibench-reference",
        "harness_version": "1",
        "completion": 100.0,
        "category_completion": {"repository-repair": 100.0},
        "cost_usd_per_task": 0.02,
        "latency_p50_ms": 15,
        "private_split": False,
        "artifact": artifact,
    }
    default = default_view(row)
    tech = technician_view(row)
    detail = detail_view(row)
    assert "false_verification_rate" not in default
    assert set(REQUIRED_PROVENANCE_KEYS) <= set(tech)
    assert detail["technician"] == tech
    assert set(PUBLICATION_REFUSE_REASONS)
