import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from agentbench.agent_tasks import AgentBudgetGuard, AgentResult, run_agent_trial
from agentbench.generated_sql_repairs import (
    FIXTURE_VERSION,
    GeneratedSqlRepairEnvironment,
    GeneratedSqlRepairGoldAgent,
    _execute_candidate,
    build_generated_sql_artifact,
    generate_fixture,
    manifest_for,
    run_offline,
)


class _SqlAgent:
    def __init__(self, sql: str):
        self.sql = sql

    def execute(self, prompt: str, workspace: Path, budget: AgentBudgetGuard) -> AgentResult:
        del prompt
        budget.consume(turns=1)
        (workspace / "models" / "fact_output.sql").write_text(self.sql, encoding="utf-8")
        return AgentResult(
            termination_reason="completed",
            claimed_success=True,
            turns=1,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
        )


def _run(tmp_path: Path, seed: int, agent) -> object:
    fixture = generate_fixture(seed)
    return run_agent_trial(
        manifest_for(fixture),
        GeneratedSqlRepairEnvironment(fixture, tmp_path / str(seed)),
        agent,
        trial=1,
    )


def test_seeded_generation_replays_and_covers_three_data_failure_modes():
    for seed in (0, 1, 2):
        assert generate_fixture(seed).public_snapshot() == generate_fixture(seed).public_snapshot()

    fixtures = [generate_fixture(seed) for seed in (0, 1, 2)]
    assert {fixture.template.family for fixture in fixtures} == {
        "join-cardinality",
        "aggregation-null",
        "incremental-late-arrival",
    }
    assert len({fixture.public_snapshot() for fixture in fixtures}) == 3


def test_manifest_uses_shared_agent_cabinet_contract():
    fixture = generate_fixture(0)
    manifest = manifest_for(fixture)

    assert manifest.fixture.reference == FIXTURE_VERSION
    assert manifest.category == "data-sql-repair"
    assert manifest.scenario_type == "generated-sql-repair"
    assert manifest.required_capabilities == ("filesystem", "sqlite")
    assert manifest.private is True


def test_public_workspace_and_prompt_exclude_private_rows_and_gold_sql(tmp_path):
    fixture = generate_fixture(0)
    environment = GeneratedSqlRepairEnvironment(fixture, tmp_path)
    prepared = environment.prepare(manifest_for(fixture), trial=1)
    visible = "\n".join(
        path.read_text(encoding="utf-8")
        for path in prepared.handle.workspace.rglob("*")
        if path.is_file()
    )

    assert fixture.gold_sql not in visible
    assert fixture.private_marker not in visible
    assert fixture.template.name not in prepared.prompt
    assert str(fixture.seed) not in prepared.prompt
    assert not list(prepared.handle.workspace.rglob("*.sqlite*"))

    environment.dispose(prepared.handle)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_gold_passes_and_noop_fails_for_every_template(tmp_path, seed):
    fixture = generate_fixture(seed)

    gold = _run(tmp_path / "gold", seed, GeneratedSqlRepairGoldAgent(fixture.gold_sql))
    noop = _run(tmp_path / "noop", seed, _SqlAgent(fixture.broken_sql))

    assert gold.outcome == "success"
    assert gold.workspace_disposed is True
    assert noop.outcome == "verification_failed"
    assert noop.workspace_disposed is True


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_hard_coded_and_plausible_wrong_repairs_fail(tmp_path, seed):
    fixture = generate_fixture(seed)
    columns = ", ".join(
        f"NULL AS {column}" if index else f"-1 AS {column}"
        for index, column in enumerate(fixture.expected_columns)
    )

    hard_coded = _run(tmp_path / "hard-coded", seed, _SqlAgent(f"SELECT {columns}"))
    plausible = _run(tmp_path / "plausible", seed, _SqlAgent(fixture.plausible_wrong_sql))

    assert hard_coded.outcome == "verification_failed"
    assert plausible.outcome == "verification_failed"


def test_oracle_rejects_duplicate_keys_and_null_measures(tmp_path):
    duplicate_rows = """
SELECT o.order_id, s.segment, i.quantity * i.unit_price_cents AS gross_cents
FROM orders AS o
JOIN order_items AS i ON i.order_id = o.order_id
JOIN customer_segments AS s ON s.customer_id = o.customer_id
"""
    null_measure = """
SELECT a.account_id, SUM(p.amount_cents) AS collected_cents
FROM accounts AS a
LEFT JOIN payments AS p ON p.account_id = a.account_id AND p.status = 'settled'
WHERE a.active = 1
GROUP BY a.account_id
"""

    assert _run(tmp_path / "duplicates", 0, _SqlAgent(duplicate_rows)).outcome == "verification_failed"
    assert _run(tmp_path / "nulls", 1, _SqlAgent(null_measure)).outcome == "verification_failed"


def test_candidate_result_materialization_is_bounded():
    fixture = generate_fixture(1)
    oversized_rows = """
WITH RECURSIVE sequence(value) AS (
    SELECT 1
    UNION ALL
    SELECT value + 1 FROM sequence WHERE value < 100
)
SELECT value AS account_id, 0 AS collected_cents
FROM sequence
"""

    columns, rows = _execute_candidate(fixture, oversized_rows)

    assert columns == fixture.expected_columns
    assert len(rows) == len(fixture.expected_rows) + 1


def test_candidate_cell_size_is_limited_before_materialization():
    fixture = generate_fixture(1)
    oversized_cell = "SELECT 1 AS account_id, zeroblob(70000) AS collected_cents"

    with pytest.raises(sqlite3.DataError, match="too big"):
        _execute_candidate(fixture, oversized_cell)


def test_repeated_trials_get_identical_clean_isolated_workspaces(tmp_path):
    fixture = generate_fixture(2)
    manifest = manifest_for(fixture)
    environment = GeneratedSqlRepairEnvironment(fixture, tmp_path)
    first = environment.prepare(manifest, trial=1)
    second = environment.prepare(manifest, trial=2)

    assert first.handle.workspace != second.handle.workspace
    assert first.handle.initial_state_sha256 == second.handle.initial_state_sha256
    assert (first.handle.workspace / "models" / "fact_output.sql").read_text(encoding="utf-8") == fixture.broken_sql
    assert (second.handle.workspace / "models" / "fact_output.sql").read_text(encoding="utf-8") == fixture.broken_sql

    environment.dispose(first.handle)
    environment.dispose(second.handle)
    assert environment.is_disposed(first.handle)
    assert environment.is_disposed(second.handle)


def test_digest_mismatch_fails_preparation_and_cleans_workspace(tmp_path):
    fixture = generate_fixture(0)
    manifest = manifest_for(fixture)
    other = manifest_for(generate_fixture(3))
    mismatched = replace(manifest, fixture=replace(manifest.fixture, digest=other.fixture.digest))

    result = run_agent_trial(
        mismatched,
        GeneratedSqlRepairEnvironment(fixture, tmp_path),
        GeneratedSqlRepairGoldAgent(fixture.gold_sql),
        trial=1,
    )

    assert result.outcome == "preparation_failed"
    assert result.workspace_disposed is True
    assert list(tmp_path.iterdir()) == []


def test_artifact_uses_shared_shape_and_sanitizes_sql_provenance(tmp_path):
    fixture = generate_fixture(987654321)
    manifest = manifest_for(fixture)
    trial = run_agent_trial(
        manifest,
        GeneratedSqlRepairEnvironment(fixture, tmp_path),
        GeneratedSqlRepairGoldAgent(fixture.gold_sql),
        trial=1,
    )
    artifact = build_generated_sql_artifact(manifest, fixture, [trial])
    encoded = json.dumps(artifact)

    assert artifact["summary"]["evaluation_type"] == "agent_harness"
    assert artifact["provenance"]["fixture_version"] == FIXTURE_VERSION
    assert artifact["provenance"]["generator_sha256"]
    assert artifact["provenance"]["mutation_template_sha256"] == fixture.template_hash
    assert artifact["provenance"]["seed_sha256"] == fixture.seed_hash
    assert artifact["provenance"]["harness"] == "agent-cabinet-generated-sql-repair"
    assert artifact["provenance"]["budgets"]["max_turns"] == 3
    assert artifact["provenance"]["terminal_outcome"] == "success"
    assert str(fixture.seed) not in encoded
    assert fixture.private_marker not in encoded
    assert fixture.gold_sql not in encoded


def test_offline_cli_requires_no_model_and_writes_artifact(tmp_path):
    out = tmp_path / "generated-sql.json"

    assert run_offline(5, 2, out) == 0

    artifact = json.loads(out.read_text(encoding="utf-8"))
    assert artifact["dry_run"] is True
    assert artifact["summary"]["n_trials"] == 2
    assert all(trial["workspace_disposed"] for trial in artifact["trials"])
