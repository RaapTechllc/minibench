"""Smoke tests for the trimmed Era 2 API surface."""


def test_health(client):
    body = client.get("/health").json()
    assert body == {"status": "ok", "service": "minibench-api"}


def test_legacy_hardware_routes_are_gone(client):
    for path in (
        "/api/v1/benchmarks", "/api/v1/leaderboard", "/api/v1/hardware", "/api/v1/profiles",
        "/api/v1/compare?a=1&b=2", "/api/v1/stats", "/api/v1/models",
    ):
        assert client.get(path).status_code == 404, path
    assert client.post("/api/v1/submit", json={}).status_code in (404, 405)


def test_openapi_has_no_legacy_schemas(client):
    spec = client.get("/openapi.json").json()
    names = set(spec.get("components", {}).get("schemas", {}))
    for legacy in ("BenchmarkSubmit", "BenchmarkResponse", "HardwareSpecResponse",
                   "ReferenceProfileResponse", "ModelQualityResponse", "StatsResponse", "CompareResponse"):
        assert legacy not in names
