"""A8: operator-manual examples stay aligned with the shipped gates."""
from __future__ import annotations

import json
import re
from pathlib import Path

from agentbench.agent_cabinet import (
    PUBLICATION_REFUSE_REASONS,
    REQUIRED_PROVENANCE_KEYS,
    publication_receipt,
)
from app.agent_cabinet_present import default_view, detail_view, technician_view

REPO = Path(__file__).resolve().parents[2]
MANUAL = REPO / "docs" / "operators" / "agent-cabinet.md"


def _example_artifact() -> dict:
    text = MANUAL.read_text(encoding="utf-8")
    match = re.search(r"```json\n(\{.*?\})\n```", text, flags=re.S)
    assert match, "operator manual must include a JSON artifact example"
    return json.loads(match.group(1))


def test_a8_operator_manual_covers_required_topics():
    text = MANUAL.read_text(encoding="utf-8")
    for heading in (
        "## Authoring",
        "## Fixture validation",
        "## Gold / bad self-checks",
        "## Budget checks",
        "## Private-split handling",
        "## Dry runs",
        "## Comparison",
        "## Publication gates",
    ):
        assert heading in text
    assert "name@version" in text or "`name@version`" in text or "name@version" in text.replace("`", "")
    assert "@latest" in text
    assert "sha256" in text
    assert "invalid_task_self_check" in text
    assert "MINIBENCH_SEED" in text or "raw seed" in text
    assert "never" in text.lower()
    assert "dry_run" in text
    assert "/api/v1/agent-cabinet/compare" in text
    for reason in PUBLICATION_REFUSE_REASONS:
        assert reason in text
    assert "--allow-infra" in text
    assert "no `--allow-infra`" in text or "There is **no**" in text
    readme = (REPO / "agentbench" / "README.md").read_text(encoding="utf-8")
    assert "docs/operators/agent-cabinet.md" in readme
    glossary = (REPO / "CONTEXT.md").read_text(encoding="utf-8")
    assert "Real-Work Agent Cabinet" in glossary


def test_a8_docs_example_is_publishable_and_presents():
    artifact = _example_artifact()
    assert artifact["dry_run"] is False
    receipt = publication_receipt(artifact)
    assert receipt["publishable"] is True
    assert set(REQUIRED_PROVENANCE_KEYS) <= set(artifact["provenance"])

    row = {
        "run_id": "docs-example",
        "submitted_at": artifact["generated_at"],
        "suite": artifact["provenance"]["suite"],
        "model_route": artifact["provenance"]["model_route"],
        "harness": artifact["provenance"]["harness"],
        "harness_version": artifact["provenance"]["harness_version"],
        "completion": 50.0,
        "category_completion": {"repository-repair": 50.0},
        "cost_usd_per_task": 0.01,
        "latency_p50_ms": 12,
        "private_split": False,
        "artifact": artifact,
    }
    default = default_view(row)
    assert default["completion"] == 50.0
    assert default["category_completion"]["repository-repair"] == 50.0
    assert default["cost_usd_per_task"] == 0.01
    assert default["latency_p50_ms"] == 12
    tech = technician_view(row)
    for key in REQUIRED_PROVENANCE_KEYS:
        assert key in tech
    detail = detail_view(row)
    assert detail["technician"] is tech or detail["technician"] == tech
    assert "held_constant" in detail
    assert "changed_variables" in detail
