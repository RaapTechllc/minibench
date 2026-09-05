"""The legacy upgrade must preserve rows and be safe to run twice."""
from pathlib import Path

from conftest import TEST_DB, _connect


def test_legacy_provenance_upgrade_preserves_rows(client):
    migration = Path(__file__).resolve().parents[1] / "migrations" / "20260904_01_legacy_provenance.sql"
    conn = _connect(TEST_DB)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT model_id FROM known_models ORDER BY model_id")
            model_ids = cur.fetchall()
            assert model_ids
            cur.execute("ALTER TABLE known_models DROP COLUMN family, DROP COLUMN license, DROP COLUMN snapshot_date")
            cur.execute("ALTER TABLE agent_runs DROP COLUMN grader_version, DROP COLUMN decoding, "
                        "DROP COLUMN seed_sha256, DROP COLUMN generator_sha256, DROP COLUMN git_commit, "
                        "DROP COLUMN is_private_split, DROP COLUMN n_infra_errors, DROP COLUMN n_canary_flags, "
                        "DROP COLUMN calibration_brier, DROP COLUMN robustness_correct")
            for _ in range(2):
                cur.execute(migration.read_text(encoding="utf-8"))
            cur.execute("SELECT model_id FROM known_models ORDER BY model_id")
            assert cur.fetchall() == model_ids
        # ORM SELECTs reference every mapped column, including the restored ones.
        assert client.get("/api/v1/agents/leaderboard").status_code == 200
        assert client.get("/api/v1/agents/models/new").status_code == 200
    finally:
        conn.close()
