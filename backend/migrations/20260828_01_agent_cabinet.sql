BEGIN;

CREATE TABLE IF NOT EXISTS agent_cabinet_runs (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    suite VARCHAR(64) NOT NULL,
    model_route VARCHAR(256) NOT NULL,
    harness VARCHAR(64) NOT NULL,
    harness_version VARCHAR(32) NOT NULL,
    tool_contract_sha256 VARCHAR(64) NOT NULL,
    fixture_digest VARCHAR(80) NOT NULL,
    budgets JSONB NOT NULL,
    budgets_canonical TEXT NOT NULL,
    grader_version VARCHAR(32) NOT NULL,
    private_split BOOLEAN NOT NULL DEFAULT FALSE,
    private_split_id VARCHAR(64) NOT NULL,
    completion NUMERIC(5, 2) NOT NULL,
    pass_rate NUMERIC(5, 2) NOT NULL,
    cost_usd_per_task NUMERIC(10, 6),
    latency_p50_ms INTEGER,
    category_completion JSONB NOT NULL,
    provenance JSONB NOT NULL,
    summary JSONB NOT NULL,
    artifact JSONB NOT NULL,
    publication_receipt JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_cabinet_task_results (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES agent_cabinet_runs(run_id),
    task_id VARCHAR(128) NOT NULL,
    category VARCHAR(64),
    trial INTEGER,
    passed BOOLEAN NOT NULL,
    outcome VARCHAR(64),
    trial_payload JSONB
);

CREATE INDEX IF NOT EXISTS ix_agent_cabinet_runs_best_key
    ON agent_cabinet_runs (
        suite,
        model_route,
        harness,
        harness_version,
        tool_contract_sha256,
        fixture_digest,
        budgets_canonical,
        grader_version,
        private_split_id
    );

CREATE INDEX IF NOT EXISTS ix_agent_cabinet_task_results_run_id
    ON agent_cabinet_task_results (run_id);

COMMIT;
