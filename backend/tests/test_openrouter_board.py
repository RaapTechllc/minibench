"""Public Usage Board reads — fixture snapshot, no recommend, no live key."""


def test_board_serves_cited_fixture_rows(client):
    body = client.get("/api/v1/openrouter/board").json()
    assert body["meta"]["live"] is False
    assert "Source: OpenRouter (openrouter.ai/rankings), as of" in body["meta"]["citation"]
    assert "CC BY 4.0" in body["meta"]["citation"]
    assert body["meta"]["as_of"]
    ids = [row["id"] for row in body["rows"]]
    assert "other" not in ids
    assert "anthropic/claude-haiku-4.5" in ids
    for row in body["rows"]:
        assert row["citation"] == body["meta"]["citation"]
        assert row["openrouter_url"].startswith("https://openrouter.ai/")


def test_best_by_cost_orders_haiku_first(client):
    rows = client.get("/api/v1/openrouter/compare/best-by-cost").json()["rows"]
    assert rows[0]["id"] == "anthropic/claude-haiku-4.5"
    prices = [r["blended_per_million"] for r in rows]
    assert prices == sorted(prices)


def test_best_by_task_code(client):
    rows = client.get("/api/v1/openrouter/compare/best-by-task", params={"task": "code"}).json()["rows"]
    assert rows[0]["id"] == "anthropic/claude-haiku-4.5"


def test_best_by_latency(client):
    rows = client.get("/api/v1/openrouter/compare/best-by-latency").json()["rows"]
    assert rows[0]["id"] == "anthropic/claude-haiku-4.5"
    assert [r["latency_ms"] for r in rows] == sorted(r["latency_ms"] for r in rows)


def test_board_endpoints_are_get_only(client):
    for path in (
        "/api/v1/openrouter/board",
        "/api/v1/openrouter/compare/best-by-cost",
        "/api/v1/openrouter/compare/best-by-latency",
    ):
        assert client.post(path).status_code == 405


def test_main_app_has_no_recommend_route(client):
    assert client.get("/recommend").status_code == 404
    assert client.get("/api/v1/recommend").status_code == 404
    # query-string key must not create a recommend surface
    assert client.get("/api/v1/openrouter/board", params={"api_key": "sk-or-v1-nope"}).status_code == 200
