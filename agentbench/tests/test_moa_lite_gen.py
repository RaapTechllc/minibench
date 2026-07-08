"""moa-lite-v1 generator: determinism, gold self-check, MoA suite contract."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from agentbench.grading import grade
from agentbench.moa_lite_gen import (
    CANARY,
    DEV_SEED,
    SUITE_NAME,
    generate_tasks,
    write_suite,
)
from agentbench.run import gold_self_check


def test_suite_name_allows_moa_contract():
    """minibench-* rejects MoA; moa-lite must NOT use that prefix."""
    assert not SUITE_NAME.startswith("minibench")
    assert SUITE_NAME.startswith("moa-")


def test_same_seed_is_deterministic():
    assert generate_tasks(DEV_SEED) == generate_tasks(DEV_SEED)


def test_different_seed_changes_instances():
    assert generate_tasks(DEV_SEED) != generate_tasks(DEV_SEED + 1)


def test_gold_answers_pass_their_grader():
    for task in generate_tasks(DEV_SEED):
        result = grade(task["verification"], task["_gold"])
        assert result.passed, f"{task['id']}: gold failed — {result.detail}"


def test_gold_self_check_clean():
    assert gold_self_check(generate_tasks(DEV_SEED)) == []


def test_deliberately_bad_answers_fail():
    bad = '{"wrong_key": true, "value": -1}'
    for task in generate_tasks(DEV_SEED):
        result = grade(task["verification"], bad)
        assert not result.passed, f"{task['id']}: grader accepted garbage"


def test_majority_trap_not_gold_on_doc_conflict():
    """Doc-conflict items must not reward the majority number."""
    for task in generate_tasks(DEV_SEED):
        if not task["id"].startswith("moal-doc-"):
            continue
        req = task["verification"]["required"]
        assert req["trusts_majority"] is False
        trap = {**req, "trusts_majority": True}
        assert not grade(task["verification"], json.dumps(trap)).passed
        trap_val = {
            **req,
            "value": req["value"] - 1 if req["value"] > 1 else req["value"] + 1,
        }
        assert not grade(task["verification"], json.dumps(trap_val)).passed


def test_evidence_unknown_required_when_tool_timeout():
    tasks = [t for t in generate_tasks(DEV_SEED) if t["id"].startswith("moal-evidence-")]
    unknowns = [
        t for t in tasks if t["verification"]["required"]["root_cause"] == "unknown"
    ]
    assert len(unknowns) >= 2, "suite must include multiple unknown/incomplete-evidence items"
    for task in unknowns:
        for false_cause in ("deploy", "dependency"):
            trap = {
                **task["verification"]["required"],
                "root_cause": false_cause,
                "needs_more_data": False,
                "page_now": True,
            }
            assert not grade(task["verification"], json.dumps(trap)).passed


def test_constraint_pack_catches_naive_optima():
    """Careless mix / unrestricted exact-pack / capacity-only LPT must fail."""
    tasks = {t["id"]: t for t in generate_tasks(DEV_SEED)}
    c1 = tasks["moal-constraint-01"]
    req = c1["verification"]["required"]
    assert "qty_b" in req and "qty_c" in req
    assert req["qty_b"] >= 1 and req["qty_c"] >= 1
    assert not grade(
        c1["verification"],
        json.dumps({**req, "qty_b": 0, "qty_c": req["qty_b"] + req["qty_c"]}),
    ).passed
    assert not grade(
        c1["verification"],
        json.dumps({**req, "qty_b": req["qty_b"] + 1, "spend": req["spend"] + 1}),
    ).passed

    c2 = tasks["moal-constraint-02"]
    req2 = c2["verification"]["required"]
    assert req2["qty_alpha"] % 4 == 0
    assert req2["qty_beta"] <= 6
    assert not grade(
        c2["verification"],
        json.dumps({**req2, "qty_alpha": req2["qty_alpha"] + 2}),
    ).passed

    c3 = tasks["moal-constraint-03"]
    req3 = c3["verification"]["required"]
    assert req3["status"] == "reject"
    assert not grade(
        c3["verification"],
        json.dumps({"status": "ok", "load_a": 10, "load_b": 10}),
    ).passed


def test_arbitrate_reject_reason_traps():
    """reject_reason=none must fail even if winner/answer look right."""
    tasks = {t["id"]: t for t in generate_tasks(DEV_SEED)}
    for tid, reason in (
        ("moal-arbitrate-01", "arithmetic_mean"),
        ("moal-arbitrate-02", "calc_error"),
        ("moal-arbitrate-03", "constraint_violation"),
    ):
        task = tasks[tid]
        req = task["verification"]["required"]
        assert req["reject_reason"] == reason
        none_trap = {**req, "reject_reason": "none"}
        assert not grade(task["verification"], json.dumps(none_trap)).passed
        assert "reject_reason" in task["prompt"].lower()
        # Prompts list allowed labels but do not coach the correct label.
        assert re.search(
            r"arithmetic_mean\|constraint_violation\|calc_error\|none",
            task["prompt"],
        )


def test_write_suite_strips_gold(tmp_path):
    out = tmp_path / "moa-lite-v1.json"
    payload = write_suite(generate_tasks(DEV_SEED), out, seed=DEV_SEED)
    assert payload["canary"] == CANARY
    assert payload["suite"] == SUITE_NAME
    assert all("_gold" not in t for t in payload["tasks"])
    cats = {t["category"] for t in payload["tasks"]}
    assert cats == {
        "doc-conflict",
        "constraint-pack",
        "evidence-gap",
        "proposal-arbitrate",
    }
    assert len(payload["tasks"]) == 12  # 4 cats × 3


def test_repo_suite_file_is_current():
    suite_path = Path(__file__).resolve().parents[1] / "tasks" / "moa-lite-v1.json"
    assert suite_path.exists(), "generate with: python -m agentbench.moa_lite_gen --out ..."
    committed = json.loads(suite_path.read_text(encoding="utf-8"))
    fresh = [
        {**{k: v for k, v in t.items() if k != "_gold"}, "canary": CANARY}
        for t in generate_tasks(committed["generator_seed"])
    ]
    assert committed["tasks"] == fresh
    assert committed["suite"] == SUITE_NAME
    for t in committed["tasks"]:
        assert t["verification"]["strict"] is True
