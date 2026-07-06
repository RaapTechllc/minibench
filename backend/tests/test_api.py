"""End-to-end API tests against a seeded test database."""
from decimal import Decimal


def _valid_payload(**overrides):
    payload = {
        "cpu_model": "Apple M4 Pro",
        "total_ram_gb": 24,
        "os": "macOS 15.2",
        "inference_engine": "MLX",
        "model_name": "Llama-3-8B-Instruct",
        "quantization": "Q4_K_M",
        "tokens_per_second": 45.0,
        "prompt_tokens": 200,
        "completion_tokens": 300,
        "test_duration_secs": 15,
        "memory_bandwidth_gbs": 273.0,
        "hardware_price_usd": 1399.0,
        "system_type": "Mac Mini M4 Pro",
        "fingerprint": "test_default_fp",
    }
    payload.update(overrides)
    return payload


def test_health(client):
    body = client.get("/health").json()
    assert body == {"status": "ok", "service": "minibench-api"}


def test_stats_reflects_seed(client):
    body = client.get("/api/v1/stats").json()
    assert body["total_submissions"] == 8
    assert body["total_hardware_specs"] == 10
    assert body["unique_systems"] == 8
    assert body["max_tokens_per_second"] == 52.3


def test_models_sorted_by_mmlu_desc(client):
    models = client.get("/api/v1/models").json()
    assert len(models) == 7
    scores = [float(m["mmlu_score"]) for m in models]
    assert scores == sorted(scores, reverse=True)
    assert models[0]["model_variant"] == "Qwen2.5-72B-Instruct"


def test_hardware_sorted_by_bandwidth_desc(client):
    specs = client.get("/api/v1/hardware").json()
    assert len(specs) == 10
    bandwidths = [float(s["memory_bandwidth_gbs"]) for s in specs]
    assert bandwidths == sorted(bandwidths, reverse=True)


def test_reference_profiles_seeded_and_pinned(client):
    profiles = client.get("/api/v1/profiles").json()
    keys = [p["profile_key"] for p in profiles]
    assert keys == ["consumer-gpu-24gb", "apple-unified-32gb", "cpu-only-mini-pc", "provider-api"]
    by_key = {p["profile_key"]: p for p in profiles}
    # Local profiles pin an engine + quantization; the API profile pins neither.
    assert by_key["consumer-gpu-24gb"]["quantization"] == "Q4_K_M"
    assert by_key["apple-unified-32gb"]["engine"] == "MLX"
    assert by_key["provider-api"]["engine"] is None
    # Every profile documents why it's the official setting.
    assert all(p["description"] for p in profiles)


def test_list_benchmarks_total_count_header(client):
    resp = client.get("/api/v1/benchmarks")
    assert resp.status_code == 200
    assert resp.headers["X-Total-Count"] == "8"
    assert len(resp.json()) == 8


def test_list_benchmarks_total_count_ignores_pagination(client):
    resp = client.get("/api/v1/benchmarks", params={"limit": 3, "offset": 2})
    assert resp.headers["X-Total-Count"] == "8"
    assert len(resp.json()) == 3


def test_list_benchmarks_total_count_respects_filters(client):
    resp = client.get("/api/v1/benchmarks", params={"model": "Llama-3", "limit": 2})
    body = resp.json()
    assert resp.headers["X-Total-Count"] == "4"
    assert len(body) == 2
    assert all("Llama-3" in b["model_name"] for b in body)


def test_submit_valid_autofills_quality_and_hei(client):
    resp = client.post("/api/v1/submit", json=_valid_payload())
    assert resp.status_code == 200
    body = resp.json()
    # quality is auto-looked-up from the model_quality table
    assert body["model_quality_score"] is not None
    assert float(body["model_quality_score"]) == 68.4
    assert body["quality_source"] == "mmlu"
    # HEI = (t/s * MMLU) / price
    expected = round(45.0 * 68.4 / 1399.0, 4)
    assert body["hei"] == expected
    # raw IP is never stored
    assert body["ip_hash"] and len(body["ip_hash"]) == 16


def test_submit_rejects_out_of_range_tps(client):
    resp = client.post("/api/v1/submit", json=_valid_payload(tokens_per_second=999, fingerprint="fp_tps"))
    assert resp.status_code == 422


def test_submit_rejects_short_duration(client):
    resp = client.post("/api/v1/submit", json=_valid_payload(test_duration_secs=3, fingerprint="fp_dur"))
    assert resp.status_code == 422


def test_submit_rejects_low_token_total(client):
    resp = client.post(
        "/api/v1/submit",
        json=_valid_payload(prompt_tokens=10, completion_tokens=10, fingerprint="fp_tok"),
    )
    assert resp.status_code == 400


def test_submit_duplicate_fingerprint_blocked(client):
    payload = _valid_payload(fingerprint="dup_fp")
    assert client.post("/api/v1/submit", json=payload).status_code == 200
    assert client.post("/api/v1/submit", json=payload).status_code == 429


def test_leaderboard_hei_ordering_respects_limit(client):
    # A modest-throughput but very high-HEI machine (cheap + high-quality model).
    # With the old "limit then sort" logic this row would be excluded from a
    # small limit; the SQL-side ordering must surface it as rank #1.
    bargain = _valid_payload(
        system_type="Bargain Box",
        cpu_model="Bargain CPU",
        model_name="Qwen2.5-72B-Instruct",
        tokens_per_second=20.0,
        hardware_price_usd=50.0,
        memory_bandwidth_gbs=60.0,
        fingerprint="bargain_fp",
    )
    assert client.post("/api/v1/submit", json=bargain).status_code == 200

    entries = client.get("/api/v1/leaderboard", params={"sort_by": "hei", "limit": 3}).json()
    assert len(entries) == 3
    assert entries[0]["system_type"] == "Bargain Box"
    assert [e["rank"] for e in entries] == [1, 2, 3]
    heis = [e["hei"] for e in entries]
    assert heis == sorted(heis, reverse=True)


def test_leaderboard_sort_by_tps(client):
    entries = client.get("/api/v1/leaderboard", params={"sort_by": "tokens_per_second"}).json()
    tps = [float(e["tokens_per_second"]) for e in entries]
    assert tps == sorted(tps, reverse=True)
    assert entries[0]["rank"] == 1


def test_compute_hei_unit():
    from app.main import compute_hei

    assert compute_hei(Decimal("10"), Decimal("80"), Decimal("100")) == 8.0
    assert compute_hei(Decimal("10"), None, Decimal("100")) is None
    assert compute_hei(Decimal("10"), Decimal("80"), Decimal("0")) is None
    assert compute_hei(Decimal("10"), Decimal("80"), None) is None
