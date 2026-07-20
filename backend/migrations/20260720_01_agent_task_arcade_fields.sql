BEGIN;

ALTER TABLE agent_task_results
    ADD COLUMN IF NOT EXISTS scenario_type VARCHAR(32),
    ADD COLUMN IF NOT EXISTS task_description TEXT,
    ADD COLUMN IF NOT EXISTS passed_format BOOLEAN;

ALTER TABLE agent_runs
    ADD COLUMN IF NOT EXISTS pass_format NUMERIC(5, 2);

COMMIT;
