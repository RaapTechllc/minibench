-- Recover the missing upgrade path identified by the July E2E branch.
-- Run explicitly before starting the API against an older database.
BEGIN;

ALTER TABLE agent_runs
    ADD COLUMN IF NOT EXISTS grader_version VARCHAR(8),
    ADD COLUMN IF NOT EXISTS decoding JSONB,
    ADD COLUMN IF NOT EXISTS seed_sha256 VARCHAR(64),
    ADD COLUMN IF NOT EXISTS generator_sha256 VARCHAR(64),
    ADD COLUMN IF NOT EXISTS git_commit VARCHAR(64),
    ADD COLUMN IF NOT EXISTS is_private_split BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS n_infra_errors INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS n_canary_flags INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS calibration_brier NUMERIC(6, 4),
    ADD COLUMN IF NOT EXISTS robustness_correct NUMERIC(6, 4);

ALTER TABLE known_models
    ADD COLUMN IF NOT EXISTS family VARCHAR(64),
    ADD COLUMN IF NOT EXISTS license VARCHAR(16),
    ADD COLUMN IF NOT EXISTS snapshot_date DATE;

COMMIT;
