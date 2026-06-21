from minibench import benchmark, detect


def _hw():
    return {"cpu_model": "Apple M4 Pro", "gpu_model": None, "total_ram_gb": 24, "os": "macOS"}


def test_fingerprint_is_deterministic_16_hex():
    a = benchmark.compute_fingerprint(_hw(), "llama3:8b", "Q4_K_M", "ollama")
    b = benchmark.compute_fingerprint(_hw(), "llama3:8b", "Q4_K_M", "ollama")
    assert a == b
    assert len(a) == 16
    int(a, 16)  # valid hex


def test_fingerprint_varies_with_inputs():
    base = benchmark.compute_fingerprint(_hw(), "llama3:8b", "Q4_K_M", "ollama")
    assert base != benchmark.compute_fingerprint(_hw(), "qwen2:7b", "Q4_K_M", "ollama")
    assert base != benchmark.compute_fingerprint(_hw(), "llama3:8b", "Q8_0", "ollama")


def test_run_benchmark_aggregates_median_and_totals(monkeypatch):
    monkeypatch.setattr(benchmark, "check_ollama", lambda: True)
    samples = [
        {"tokens_per_second": v, "time_to_first_token": 0.1, "duration": 5.0,
         "prompt_tokens": 50, "completion_tokens": 50}
        for v in (10.0, 20.0, 30.0, 40.0, 50.0)
    ]
    it = iter(samples)
    monkeypatch.setattr(benchmark, "run_prompt", lambda model, prompt: next(it))

    result = benchmark.run_benchmark("m", warmup=False)
    assert result["tokens_per_second"] == 30.0       # median of 10..50
    assert result["tokens_per_second_p95"] == 50.0
    assert result["prompt_tokens"] == 250
    assert result["completion_tokens"] == 250
    assert result["runs"] == 5
    assert result["test_duration_secs"] == 25.0


def test_run_benchmark_returns_none_when_ollama_down(monkeypatch):
    monkeypatch.setattr(benchmark, "check_ollama", lambda: False)
    assert benchmark.run_benchmark("m", warmup=False) is None


def test_detect_ram_positive():
    assert detect.detect_ram()["total_ram_gb"] > 0


def test_detect_all_has_required_keys():
    hw = detect.detect_all()
    for key in ("cpu_model", "cpu_cores", "cpu_threads", "total_ram_gb", "os"):
        assert key in hw
