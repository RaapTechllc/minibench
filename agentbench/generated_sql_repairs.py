"""Offline, seeded data/SQL-repair tasks for the Real-Work Agent Cabinet."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .agent_tasks import (
    AGENT_GRADER_VERSION,
    AgentAdapter,
    AgentBudget,
    AgentBudgetGuard,
    AgentResult,
    AgentTaskManifest,
    EnvironmentHandle,
    PreparedEnvironment,
    TaskEnvironment,
    VerificationResult,
    build_agent_artifact,
    execute_agent_with_budget,
    run_agent_trial,
)


FIXTURE_VERSION = "generated-sql-repair@1"
HARNESS = "agent-cabinet-generated-sql-repair"
_BUDGET = AgentBudget(max_turns=3, wall_time_seconds=5, max_tokens=300, max_cost_usd=0.0)
_QUERY_STEP_LIMIT = 100_000
_MAX_QUERY_BYTES = 64 * 1024


@dataclass(frozen=True)
class SqlRepairTemplate:
    name: str
    family: str
    build: Callable[[int], "GeneratedSqlRepairFixture"]


@dataclass(frozen=True)
class GeneratedSqlRepairFixture:
    seed: int
    template: SqlRepairTemplate
    public_files: dict[str, str]
    broken_sql: str
    gold_sql: str
    plausible_wrong_sql: str
    private_rows: dict[str, tuple[dict[str, Any], ...]]
    expected_columns: tuple[str, ...]
    expected_rows: tuple[tuple[Any, ...], ...]
    key_columns: tuple[str, ...]
    non_null_columns: tuple[str, ...]
    private_marker: str

    @property
    def seed_hash(self) -> str:
        return hashlib.sha256(str(self.seed).encode()).hexdigest()

    @property
    def template_hash(self) -> str:
        return hashlib.sha256(self.template.name.encode()).hexdigest()

    def public_snapshot(self) -> bytes:
        payload = {"version": FIXTURE_VERSION, "files": self.public_files}
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _variant(seed: int, label: str) -> int:
    return int(hashlib.sha256(f"{seed}:{label}".encode()).hexdigest()[:8], 16)


def _public_files(tag: str, schema: str, prompt: str, broken_sql: str) -> dict[str, str]:
    return {
        "README.md": f"# Mini analytics repair\n\n{prompt}\n",
        "project.json": json.dumps(
            {"fixture_version": FIXTURE_VERSION, "variant": tag},
            sort_keys=True,
            indent=2,
        )
        + "\n",
        "schema.sql": schema.strip() + "\n",
        "models/fact_output.sql": broken_sql.strip() + "\n",
    }


def _join_fixture(seed: int) -> GeneratedSqlRepairFixture:
    base = 1_000 + _variant(seed, "join-base") % 5_000
    tag = hashlib.sha256(f"public:{seed}:join".encode()).hexdigest()[:12]
    marker = "private-" + hashlib.sha256(f"private:{seed}:join".encode()).hexdigest()[:12]
    prompt = (
        "The order-revenue model emits more than one row for some orders and inflates the daily total. "
        "Repair the model while preserving one current customer segment per order."
    )
    schema = """
CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL);
CREATE TABLE order_items (
    order_id INTEGER NOT NULL,
    sku TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL
);
CREATE TABLE customer_segments (
    customer_id INTEGER NOT NULL,
    segment TEXT NOT NULL,
    effective_at TEXT NOT NULL
);
"""
    broken = """
SELECT o.order_id, s.segment, SUM(i.quantity * i.unit_price_cents) AS gross_cents
FROM orders AS o
JOIN order_items AS i ON i.order_id = o.order_id
JOIN customer_segments AS s ON s.customer_id = o.customer_id
GROUP BY o.order_id, s.segment
ORDER BY o.order_id
"""
    gold = """
WITH current_segments AS (
    SELECT customer_id, segment
    FROM (
        SELECT customer_id, segment,
               ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY effective_at DESC) AS recency
        FROM customer_segments
    )
    WHERE recency = 1
)
SELECT o.order_id, s.segment, SUM(i.quantity * i.unit_price_cents) AS gross_cents
FROM orders AS o
JOIN order_items AS i ON i.order_id = o.order_id
JOIN current_segments AS s ON s.customer_id = o.customer_id
GROUP BY o.order_id, s.segment
ORDER BY o.order_id
"""
    plausible_wrong = """
SELECT o.order_id, MAX(s.segment) AS segment,
       SUM(i.quantity * i.unit_price_cents) AS gross_cents
FROM orders AS o
JOIN order_items AS i ON i.order_id = o.order_id
JOIN customer_segments AS s ON s.customer_id = o.customer_id
GROUP BY o.order_id
ORDER BY o.order_id
"""
    first_order, second_order = base + 1, base + 2
    first_customer, second_customer = base + 101, base + 102
    first_total = 2 * (700 + base % 90) + (250 + base % 40)
    second_total = 3 * (400 + base % 60)
    current_segment = f"current-{marker}"
    second_segment = f"steady-{marker}"
    rows = {
        "orders": (
            {"order_id": first_order, "customer_id": first_customer},
            {"order_id": second_order, "customer_id": second_customer},
        ),
        "order_items": (
            {"order_id": first_order, "sku": "A", "quantity": 2, "unit_price_cents": 700 + base % 90},
            {"order_id": first_order, "sku": "B", "quantity": 1, "unit_price_cents": 250 + base % 40},
            {"order_id": second_order, "sku": "C", "quantity": 3, "unit_price_cents": 400 + base % 60},
        ),
        "customer_segments": (
            {"customer_id": first_customer, "segment": f"legacy-{marker}", "effective_at": "2026-01-01"},
            {"customer_id": first_customer, "segment": current_segment, "effective_at": "2026-02-01"},
            {"customer_id": second_customer, "segment": second_segment, "effective_at": "2026-02-01"},
        ),
    }
    template = TEMPLATES[0]
    return GeneratedSqlRepairFixture(
        seed,
        template,
        _public_files(tag, schema, prompt, broken),
        broken.strip() + "\n",
        gold.strip() + "\n",
        plausible_wrong.strip() + "\n",
        rows,
        ("order_id", "segment", "gross_cents"),
        ((first_order, current_segment, first_total), (second_order, second_segment, second_total)),
        ("order_id",),
        ("order_id", "segment", "gross_cents"),
        marker,
    )


def _aggregation_fixture(seed: int) -> GeneratedSqlRepairFixture:
    base = 10_000 + _variant(seed, "aggregation-base") % 5_000
    tag = hashlib.sha256(f"public:{seed}:aggregation".encode()).hexdigest()[:12]
    prompt = (
        "The active-account collections report drops accounts with no settled payments and shows a blank "
        "amount for another active account. Repair the model so every active account has a numeric total."
    )
    schema = """
CREATE TABLE accounts (account_id INTEGER PRIMARY KEY, active INTEGER NOT NULL);
CREATE TABLE payments (
    payment_id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL,
    amount_cents INTEGER,
    status TEXT NOT NULL
);
"""
    broken = """
SELECT a.account_id, SUM(p.amount_cents) AS collected_cents
FROM accounts AS a
JOIN payments AS p ON p.account_id = a.account_id
WHERE a.active = 1 AND p.status = 'settled'
GROUP BY a.account_id
ORDER BY a.account_id
"""
    gold = """
SELECT a.account_id, COALESCE(SUM(COALESCE(p.amount_cents, 0)), 0) AS collected_cents
FROM accounts AS a
LEFT JOIN payments AS p
  ON p.account_id = a.account_id AND p.status = 'settled'
WHERE a.active = 1
GROUP BY a.account_id
ORDER BY a.account_id
"""
    plausible_wrong = """
SELECT a.account_id, COALESCE(SUM(p.amount_cents), 0) AS collected_cents
FROM accounts AS a
LEFT JOIN payments AS p ON p.account_id = a.account_id
WHERE a.active = 1 AND p.status = 'settled'
GROUP BY a.account_id
ORDER BY a.account_id
"""
    active_paid, active_empty, active_null, inactive = base + 1, base + 2, base + 3, base + 4
    amount = 1_200 + base % 300
    rows = {
        "accounts": (
            {"account_id": active_paid, "active": 1},
            {"account_id": active_empty, "active": 1},
            {"account_id": active_null, "active": 1},
            {"account_id": inactive, "active": 0},
        ),
        "payments": (
            {"payment_id": base + 101, "account_id": active_paid, "amount_cents": amount, "status": "settled"},
            {"payment_id": base + 102, "account_id": active_paid, "amount_cents": 999, "status": "void"},
            {"payment_id": base + 103, "account_id": active_null, "amount_cents": None, "status": "settled"},
            {"payment_id": base + 104, "account_id": inactive, "amount_cents": 50_000, "status": "settled"},
        ),
    }
    template = TEMPLATES[1]
    return GeneratedSqlRepairFixture(
        seed,
        template,
        _public_files(tag, schema, prompt, broken),
        broken.strip() + "\n",
        gold.strip() + "\n",
        plausible_wrong.strip() + "\n",
        rows,
        ("account_id", "collected_cents"),
        ((active_paid, amount), (active_empty, 0), (active_null, 0)),
        ("account_id",),
        ("account_id", "collected_cents"),
        str(amount),
    )


def _incremental_fixture(seed: int) -> GeneratedSqlRepairFixture:
    base = 20_000 + _variant(seed, "incremental-base") % 5_000
    tag = hashlib.sha256(f"public:{seed}:incremental".encode()).hexdigest()[:12]
    marker = "private-" + hashlib.sha256(f"private:{seed}:incremental".encode()).hexdigest()[:12]
    prompt = (
        "The incremental event refresh leaves a corrected historical event stale and can emit more than one "
        "candidate for repeat arrivals. Repair the batch query without rebuilding the full target."
    )
    schema = """
CREATE TABLE source_events (
    event_id INTEGER NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE TABLE target_events (
    event_id INTEGER PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    loaded_at TEXT NOT NULL
);
"""
    broken = """
SELECT event_id, value, updated_at, ingested_at AS loaded_at
FROM source_events
WHERE event_id > (SELECT COALESCE(MAX(event_id), 0) FROM target_events)
ORDER BY event_id
"""
    gold = """
WITH candidates AS (
    SELECT event_id, value, updated_at, ingested_at,
           ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY ingested_at DESC) AS arrival_rank
    FROM source_events
    WHERE ingested_at > (SELECT COALESCE(MAX(loaded_at), '') FROM target_events)
)
SELECT event_id, value, updated_at, ingested_at AS loaded_at
FROM candidates
WHERE arrival_rank = 1
ORDER BY event_id
"""
    plausible_wrong = """
WITH candidates AS (
    SELECT event_id, value, updated_at, ingested_at,
           ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY updated_at DESC) AS update_rank
    FROM source_events
    WHERE updated_at > (SELECT COALESCE(MAX(updated_at), '') FROM target_events)
)
SELECT event_id, value, updated_at, ingested_at AS loaded_at
FROM candidates
WHERE update_rank = 1
ORDER BY event_id
"""
    corrected, current, new = base + 1, base + 2, base + 3
    corrected_value = f"corrected-{marker}"
    new_value = f"new-{marker}"
    rows = {
        "target_events": (
            {"event_id": corrected, "value": f"stale-{marker}", "updated_at": "2026-01-01T00:00:00Z", "loaded_at": "2026-01-02T00:00:00Z"},
            {"event_id": current, "value": f"current-{marker}", "updated_at": "2026-02-10T00:00:00Z", "loaded_at": "2026-02-15T00:00:00Z"},
        ),
        "source_events": (
            {"event_id": corrected, "value": f"older-repeat-{marker}", "updated_at": "2026-01-02T00:00:00Z", "ingested_at": "2026-03-01T00:00:00Z"},
            {"event_id": corrected, "value": corrected_value, "updated_at": "2026-01-03T00:00:00Z", "ingested_at": "2026-03-02T00:00:00Z"},
            {"event_id": new, "value": new_value, "updated_at": "2026-03-03T00:00:00Z", "ingested_at": "2026-03-03T00:00:00Z"},
        ),
    }
    template = TEMPLATES[2]
    return GeneratedSqlRepairFixture(
        seed,
        template,
        _public_files(tag, schema, prompt, broken),
        broken.strip() + "\n",
        gold.strip() + "\n",
        plausible_wrong.strip() + "\n",
        rows,
        ("event_id", "value", "updated_at", "loaded_at"),
        (
            (corrected, corrected_value, "2026-01-03T00:00:00Z", "2026-03-02T00:00:00Z"),
            (new, new_value, "2026-03-03T00:00:00Z", "2026-03-03T00:00:00Z"),
        ),
        ("event_id",),
        ("event_id", "value", "updated_at", "loaded_at"),
        marker,
    )


TEMPLATES = (
    SqlRepairTemplate("current-segment-join", "join-cardinality", _join_fixture),
    SqlRepairTemplate("active-account-collection", "aggregation-null", _aggregation_fixture),
    SqlRepairTemplate("arrival-watermark", "incremental-late-arrival", _incremental_fixture),
)


def generate_fixture(seed: int, *, fixture_version: str = FIXTURE_VERSION) -> GeneratedSqlRepairFixture:
    if fixture_version != FIXTURE_VERSION:
        raise ValueError(f"unsupported fixture version: {fixture_version}")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    return TEMPLATES[seed % len(TEMPLATES)].build(seed)


def manifest_for(fixture: GeneratedSqlRepairFixture) -> AgentTaskManifest:
    digest = "sha256:" + hashlib.sha256(fixture.public_snapshot()).hexdigest()
    return AgentTaskManifest.from_dict(
        {
            "manifest_version": "1",
            "suite": "minibench-agent-generated-sql-repair-v1",
            "task_id": f"mba-sql-{fixture.seed_hash[:16]}",
            "category": "data-sql-repair",
            "scenario_type": "generated-sql-repair",
            "fixture": {"reference": FIXTURE_VERSION, "digest": digest},
            "public_prompt": fixture.public_files["README.md"].split("\n\n", 1)[1].strip(),
            "preparation": {"strategy": FIXTURE_VERSION},
            "verification": {"strategy": FIXTURE_VERSION},
            "required_capabilities": ["filesystem", "sqlite"],
            "budget": {
                "max_turns": _BUDGET.max_turns,
                "wall_time_seconds": _BUDGET.wall_time_seconds,
                "max_tokens": _BUDGET.max_tokens,
                "max_cost_usd": _BUDGET.max_cost_usd,
            },
            "private": True,
        }
    )


def _load_private_database(fixture: GeneratedSqlRepairFixture) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.executescript(fixture.public_files["schema.sql"])
    for table, rows in fixture.private_rows.items():
        if not rows:
            continue
        columns = tuple(rows[0])
        placeholders = ", ".join("?" for _ in columns)
        connection.executemany(
            f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
            [tuple(row[column] for column in columns) for row in rows],
        )
    connection.commit()
    connection.execute("PRAGMA query_only = ON")
    return connection


def _execute_candidate(fixture: GeneratedSqlRepairFixture, sql: str) -> tuple[tuple[str, ...], tuple[tuple[Any, ...], ...]]:
    if len(sql.encode("utf-8")) > _MAX_QUERY_BYTES:
        raise ValueError("candidate query is too large")
    connection = _load_private_database(fixture)
    steps = 0

    def stop_long_query() -> int:
        nonlocal steps
        steps += 1_000
        return int(steps > _QUERY_STEP_LIMIT)

    allowed_actions = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
    if hasattr(sqlite3, "SQLITE_RECURSIVE"):
        allowed_actions.add(sqlite3.SQLITE_RECURSIVE)

    def authorize(action: int, _one: str | None, _two: str | None, _db: str | None, _source: str | None) -> int:
        return sqlite3.SQLITE_OK if action in allowed_actions else sqlite3.SQLITE_DENY

    try:
        connection.set_authorizer(authorize)
        connection.set_progress_handler(stop_long_query, 1_000)
        cursor = connection.execute(sql)
        if cursor.description is None:
            raise ValueError("candidate must return a table")
        columns = tuple(column[0] for column in cursor.description)
        rows = tuple(tuple(row) for row in cursor.fetchall())
        return columns, rows
    finally:
        connection.close()


def _matches_oracle(
    fixture: GeneratedSqlRepairFixture,
    columns: tuple[str, ...],
    rows: tuple[tuple[Any, ...], ...],
) -> bool:
    if columns != fixture.expected_columns or len(rows) != len(fixture.expected_rows):
        return False
    indexes = {column: index for index, column in enumerate(columns)}
    key_indexes = tuple(indexes[column] for column in fixture.key_columns)
    non_null_indexes = tuple(indexes[column] for column in fixture.non_null_columns)
    keys = [tuple(row[index] for index in key_indexes) for row in rows]
    if len(keys) != len(set(keys)):
        return False
    if any(row[index] is None for row in rows for index in non_null_indexes):
        return False
    expected = tuple(sorted(fixture.expected_rows, key=lambda row: tuple(row[index] for index in key_indexes)))
    actual = tuple(sorted(rows, key=lambda row: tuple(row[index] for index in key_indexes)))
    return actual == expected


class GeneratedSqlRepairEnvironment(TaskEnvironment):
    def __init__(self, fixture: GeneratedSqlRepairFixture, root: str | Path | None = None):
        self.fixture = fixture
        self.root = Path(root) if root is not None else Path(tempfile.mkdtemp(prefix="mba-sql-"))
        self._owns_root = root is None

    def prepare(self, manifest: AgentTaskManifest, trial: int) -> PreparedEnvironment:
        if manifest.scenario_type != "generated-sql-repair":
            raise ValueError("unsupported scenario type")
        if manifest.fixture.reference != FIXTURE_VERSION:
            raise ValueError("unsupported fixture reference")
        if manifest.preparation.strategy != FIXTURE_VERSION:
            raise ValueError("unsupported preparation strategy")
        if manifest.verification.strategy != FIXTURE_VERSION:
            raise ValueError("unsupported verification strategy")
        workspace = self.root / f"{manifest.task_id}-trial-{trial}"
        workspace.mkdir(parents=True, exist_ok=False)
        try:
            for relative, content in self.fixture.public_files.items():
                path = workspace / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            digest = "sha256:" + hashlib.sha256(self.fixture.public_snapshot()).hexdigest()
            if digest != manifest.fixture.digest:
                raise RuntimeError("generated SQL fixture digest mismatch")
            return PreparedEnvironment(manifest.public_prompt, EnvironmentHandle(workspace, digest))
        except BaseException:
            shutil.rmtree(workspace, ignore_errors=True)
            raise

    def execute(
        self,
        agent: AgentAdapter,
        handle: EnvironmentHandle,
        prompt: str,
        budget: AgentBudget,
    ) -> AgentResult:
        return execute_agent_with_budget(agent, prompt, handle.workspace, budget, start_method="spawn")

    def verify(self, handle: EnvironmentHandle) -> VerificationResult:
        try:
            actual_paths = {
                path.relative_to(handle.workspace).as_posix()
                for path in handle.workspace.rglob("*")
                if path.is_file()
            }
            if actual_paths != set(self.fixture.public_files):
                raise ValueError("workspace shape changed")
            for relative, expected in self.fixture.public_files.items():
                if relative == "models/fact_output.sql":
                    continue
                if (handle.workspace / relative).read_text(encoding="utf-8") != expected:
                    raise ValueError("non-model fixture changed")
            sql = (handle.workspace / "models" / "fact_output.sql").read_text(encoding="utf-8")
            columns, rows = _execute_candidate(self.fixture, sql)
            passed = _matches_oracle(self.fixture, columns, rows)
        except BaseException:
            passed = False
        detail = "hidden table and invariant checks passed" if passed else "hidden table or invariant check failed"
        return VerificationResult(passed, detail)

    def dispose(self, handle: EnvironmentHandle | None) -> None:
        if handle is not None:
            shutil.rmtree(handle.workspace, ignore_errors=True)
        if self._owns_root:
            shutil.rmtree(self.root, ignore_errors=True)

    def is_disposed(self, handle: EnvironmentHandle | None) -> bool:
        return (handle is None or not handle.workspace.exists()) and (
            not self._owns_root or not self.root.exists()
        )


class GeneratedSqlRepairGoldAgent:
    """Offline oracle self-check adapter; never used to grade a model run."""

    def __init__(self, gold_sql: str):
        self.gold_sql = gold_sql

    def execute(self, prompt: str, workspace: Path, budget: AgentBudgetGuard) -> AgentResult:
        del prompt
        budget.consume(turns=1)
        (workspace / "models" / "fact_output.sql").write_text(self.gold_sql, encoding="utf-8")
        return AgentResult(
            termination_reason="completed",
            claimed_success=True,
            turns=1,
            tokens_in=0,
            tokens_out=0,
            cost_usd=0.0,
        )


def build_generated_sql_artifact(
    manifest: AgentTaskManifest,
    fixture: GeneratedSqlRepairFixture,
    trials: list[Any],
) -> dict[str, Any]:
    artifact = build_agent_artifact(manifest, trials)
    generator_identity = "|".join(f"{template.name}:{template.family}" for template in TEMPLATES)
    artifact["provenance"].update(
        {
            "fixture_version": FIXTURE_VERSION,
            "generator_sha256": hashlib.sha256(generator_identity.encode()).hexdigest(),
            "mutation_template_sha256": fixture.template_hash,
            "seed_sha256": fixture.seed_hash,
            "harness": HARNESS,
            "harness_version": AGENT_GRADER_VERSION,
            "budgets": {
                "max_turns": manifest.budget.max_turns,
                "wall_time_seconds": manifest.budget.wall_time_seconds,
                "max_tokens": manifest.budget.max_tokens,
                "max_cost_usd": manifest.budget.max_cost_usd,
            },
            "terminal_outcome": "success" if all(trial.passed for trial in trials) else "verification_failed",
        }
    )
    for trial in artifact["trials"]:
        trial["detail"] = "pass" if trial["passed"] else "fail"
    return artifact


def run_offline(seed: int, trials: int, out: str | Path) -> int:
    fixture = generate_fixture(seed)
    manifest = manifest_for(fixture)
    results = [
        run_agent_trial(
            manifest,
            GeneratedSqlRepairEnvironment(fixture),
            GeneratedSqlRepairGoldAgent(fixture.gold_sql),
            trial=trial,
        )
        for trial in range(1, trials + 1)
    ]
    artifact = build_generated_sql_artifact(manifest, fixture, results)
    destination = Path(out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact["summary"], indent=2))
    return 0 if all(result.passed and result.workspace_disposed for result in results) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a seeded generated data/SQL-repair task offline.")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.trials < 1:
        parser.error("--trials must be positive")
    return run_offline(args.seed, args.trials, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
