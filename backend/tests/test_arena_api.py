"""Tests for Arena-style model catalog and voting."""


def test_arena_models_seeded_and_filterable(client):
    rows = client.get("/api/v1/arena/models").json()
    assert len(rows) >= 6
    assert rows[0]["model_id"] == "openai/gpt-5.5"
    assert rows[0]["source_url"]

    coding = client.get("/api/v1/arena/models?task=agentic_coding").json()
    assert coding
    assert all("agentic_coding" in row["task_tags"] for row in coding)


def test_arena_vote_counts_and_dedupes_per_ip(client):
    payload = {"task": "agentic_coding", "model_id": "openai/gpt-5.5"}
    first = client.post("/api/v1/arena/votes", json=payload)
    assert first.status_code == 200
    assert first.json()["accepted"] is True
    assert first.json()["vote_count"] == 1

    second = client.post("/api/v1/arena/votes", json=payload)
    assert second.status_code == 200
    assert second.json()["accepted"] is False
    assert second.json()["vote_count"] == 1

    rows = client.get("/api/v1/arena/models?task=agentic_coding").json()
    voted = next(row for row in rows if row["model_id"] == "openai/gpt-5.5")
    assert voted["vote_count"] == 1


def test_arena_vote_rejects_wrong_task(client):
    resp = client.post("/api/v1/arena/votes", json={"task": "image", "model_id": "anthropic/claude-opus-4.5"})
    assert resp.status_code == 400


def test_arena_vote_rejects_nonexistent_model(client):
    """Voting for a model_id that doesn't exist returns 404."""
    resp = client.post(
        "/api/v1/arena/votes",
        json={"task": "overall", "model_id": "nonexistent/model-xyz"},
    )
    assert resp.status_code == 404


def test_arena_models_unfiltered_returns_all_categories(client):
    """Without a task filter, models from every modality are returned."""
    rows = client.get("/api/v1/arena/models").json()
    modalities = {row["modality"] for row in rows}
    assert "text" in modalities
    assert "multimodal" in modalities
    assert "image" in modalities
    # Every row should have a non-empty task_tags list
    assert all(row["task_tags"] for row in rows)
