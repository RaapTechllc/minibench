"""Standard benchmark runner using Ollama HTTP API."""
import hashlib
import json
import time
import statistics
from typing import Optional

import requests

OLLAMA_URL = "http://localhost:11434"

STANDARD_PROMPTS = [
    "Explain quantum computing in simple terms.",
    "Write a Python function that implements binary search.",
    "What are the economic implications of universal basic income?",
    "Describe the process of photosynthesis step by step.",
    "Compare and contrast TCP and UDP protocols.",
]

WARMUP_PROMPTS = [
    "Hello, how are you?",
    "What is 2 + 2?",
    "Say the word 'ready'.",
]


def check_ollama() -> bool:
    """Check if Ollama is running."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False


def list_models() -> list[str]:
    """List available Ollama models."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def run_prompt(model: str, prompt: str) -> dict:
    """Run a single prompt and measure performance."""
    start = time.perf_counter()
    first_token_time = None
    total_tokens = 0
    prompt_tokens = 0
    completion_tokens = 0
    response_text = ""

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": True},
            stream=True,
            timeout=300,
        )
        resp.raise_for_status()

        for line in resp.iter_lines():
            if line:
                data = json.loads(line)
                if first_token_time is None and data.get("response"):
                    first_token_time = time.perf_counter()
                if data.get("response"):
                    response_text += data["response"]
                    completion_tokens += 1
                if data.get("done"):
                    prompt_tokens = data.get("prompt_eval_count", 0)
                    completion_tokens = data.get("eval_count", completion_tokens)
                    break

    except requests.RequestException as e:
        return {"error": str(e)}

    end = time.perf_counter()
    duration = end - start
    ttft = (first_token_time - start) if first_token_time else None
    tps = completion_tokens / duration if duration > 0 else 0

    return {
        "tokens_per_second": round(tps, 2),
        "time_to_first_token": round(ttft, 4) if ttft else None,
        "duration": round(duration, 2),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }


def run_benchmark(model: str, warmup: bool = True) -> Optional[dict]:
    """Run the full standard benchmark suite."""
    if not check_ollama():
        return None

    # Warmup
    if warmup:
        for prompt in WARMUP_PROMPTS:
            run_prompt(model, prompt)

    # Test runs
    results = []
    total_prompt_tokens = 0
    total_completion_tokens = 0

    for prompt in STANDARD_PROMPTS:
        result = run_prompt(model, prompt)
        if "error" in result:
            return None
        results.append(result)
        total_prompt_tokens += result["prompt_tokens"]
        total_completion_tokens += result["completion_tokens"]

    tps_values = [r["tokens_per_second"] for r in results]
    ttft_values = [r["time_to_first_token"] for r in results if r["time_to_first_token"] is not None]
    durations = [r["duration"] for r in results]

    # Median and p95
    tps_sorted = sorted(tps_values)
    median_tps = statistics.median(tps_values)
    p95_idx = int(len(tps_sorted) * 0.95)
    p95_tps = tps_sorted[min(p95_idx, len(tps_sorted) - 1)]

    return {
        "tokens_per_second": round(median_tps, 2),
        "tokens_per_second_p95": round(p95_tps, 2),
        "time_to_first_token": round(statistics.median(ttft_values), 4) if ttft_values else None,
        "test_duration_secs": round(sum(durations), 2),
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "runs": len(results),
        "all_tps": tps_values,
    }


def compute_fingerprint(hw: dict, model: str, quantization: str, engine: str) -> str:
    """Compute SHA256 fingerprint for dedup."""
    fp_str = f"{hw.get('cpu_model', '')}{hw.get('gpu_model', '')}{hw.get('total_ram_gb', '')}{hw.get('os', '')}{engine}{model}{quantization}"
    return hashlib.sha256(fp_str.encode()).hexdigest()[:16]
