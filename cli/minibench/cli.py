"""MiniBench CLI — benchmark your Mini PC for local LLM inference."""
import json
import os
from pathlib import Path

import click
import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from minibench import __version__
from minibench.detect import detect_all
from minibench.benchmark import (
    run_benchmark,
    check_ollama,
    list_models,
    compute_fingerprint,
)

console = Console()
API_URL = os.environ.get("MINIBENCH_API_URL", "http://localhost:3070")
RESULTS_DIR = Path.home() / ".minibench"
RESULTS_FILE = RESULTS_DIR / "results.json"


def load_results() -> list:
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text())
    return []


def save_result(result: dict):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results = load_results()
    results.append(result)
    RESULTS_FILE.write_text(json.dumps(results, indent=2, default=str))


@click.group()
@click.version_option(version=__version__)
def main():
    """MiniBench — Benchmark your Mini PC for local LLM inference."""
    pass


@main.command()
@click.option("--model", default=None, help="Ollama model to test (e.g. llama3:8b)")
@click.option("--engine", default="ollama", help="Inference engine (ollama, mlx, llama.cpp)")
@click.option("--quantization", default="Q4_K_M", help="Quantization format")
@click.option("--no-warmup", is_flag=True, help="Skip warmup prompts")
@click.option("--system-type", default=None, help="System name (e.g. 'Mac Mini M4 Pro')")
@click.option("--price", default=None, type=float, help="Hardware price USD")
@click.option("--bandwidth", default=None, type=float, help="Memory bandwidth GB/s")
def run(model, engine, quantization, no_warmup, system_type, price, bandwidth):
    """Run the standard benchmark suite."""
    console.print(Panel.fit(
        "[bold cyan]MiniBench[/bold cyan] v{}\n[dim]Benchmarking your hardware for local LLM inference[/dim]".format(__version__),
        border_style="cyan"
    ))

    # Check Ollama
    if not check_ollama():
        console.print("[red]Error:[/red] Ollama is not running. Start it with: ollama serve")
        return

    # Auto-detect model if not specified
    if not model:
        models = list_models()
        if not models:
            console.print("[red]Error:[/red] No models found. Pull one with: ollama pull llama3:8b")
            return
        model = models[0]
        console.print(f"[yellow]Auto-selected model:[/yellow] {model}")

    # Detect hardware
    console.print("\n[bold]Detecting hardware...[/bold]")
    hw = detect_all()

    table = Table(title="Hardware Detected", box=box.ROUNDED)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("CPU", hw.get("cpu_model", "Unknown"))
    table.add_row("Cores / Threads", f"{hw.get('cpu_cores', '?')} / {hw.get('cpu_threads', '?')}")
    table.add_row("System RAM", f"{hw.get('total_ram_gb', '?')} GB")
    if hw.get("gpu_model"):
        table.add_row("GPU (Discrete)", hw["gpu_model"])
    if hw.get("vram_gb"):
        table.add_row("VRAM", f"{hw['vram_gb']} GB")
    if hw.get("igpu_model"):
        table.add_row("iGPU", hw["igpu_model"])
    table.add_row("Memory Type", hw.get("memory_type") or "Unknown")
    if bandwidth:
        table.add_row("Memory Bandwidth", f"[bold yellow]{bandwidth} GB/s[/bold yellow]")
    table.add_row("OS", hw.get("os", "Unknown"))
    console.print(table)

    # Run benchmark
    console.print(f"\n[bold]Running benchmark with {model} ({quantization})...[/bold]")
    console.print("[dim]3 warmup + 5 test prompts[/dim]\n")

    result = run_benchmark(model, warmup=not no_warmup)
    if not result:
        console.print("[red]Benchmark failed.[/red] Check that Ollama is running and the model is available.")
        return

    # Display results
    res_table = Table(title="Benchmark Results", box=box.ROUNDED)
    res_table.add_column("Metric", style="cyan")
    res_table.add_column("Value", style="bold white")
    res_table.add_row("Tokens/sec (median)", f"[bold green]{result['tokens_per_second']}[/bold green]")
    res_table.add_row("Tokens/sec (p95)", str(result["tokens_per_second_p95"]))
    if result["time_to_first_token"]:
        res_table.add_row("Time to First Token", f"{result['time_to_first_token']}s")
    res_table.add_row("Total Duration", f"{result['test_duration_secs']}s")
    res_table.add_row("Prompt Tokens", str(result["prompt_tokens"]))
    res_table.add_row("Completion Tokens", str(result["completion_tokens"]))
    if bandwidth:
        # Show bandwidth efficiency
        bw_eff = round(result["tokens_per_second"] / bandwidth, 2) if bandwidth else None
        res_table.add_row("Bandwidth Efficiency", f"{bw_eff} t/s per GB/s")
    console.print(res_table)

    # Build submission payload
    fingerprint = compute_fingerprint(hw, model, quantization, engine)
    submission = {
        "cpu_model": hw.get("cpu_model", "Unknown"),
        "cpu_cores": hw.get("cpu_cores"),
        "cpu_threads": hw.get("cpu_threads"),
        "gpu_model": hw.get("gpu_model"),
        "igpu_model": hw.get("igpu_model"),
        "total_ram_gb": hw.get("total_ram_gb", 0),
        "vram_gb": hw.get("vram_gb"),
        "memory_type": hw.get("memory_type"),
        "memory_bandwidth_gbs": bandwidth,
        "system_type": system_type,
        "hardware_price_usd": price,
        "os": hw.get("os", "Unknown"),
        "inference_engine": engine,
        "model_name": model,
        "quantization": quantization,
        "tokens_per_second": result["tokens_per_second"],
        "time_to_first_token": result["time_to_first_token"],
        "prompt_tokens": result["prompt_tokens"],
        "completion_tokens": result["completion_tokens"],
        "test_duration_secs": result["test_duration_secs"],
        "fingerprint": fingerprint,
        "client_version": __version__,
    }

    # Save locally
    save_result(submission)
    console.print(f"\n[green]Results saved locally to {RESULTS_FILE}[/green]")

    return submission


@main.command()
def results():
    """Show local benchmark history."""
    data = load_results()
    if not data:
        console.print("[yellow]No local results found.[/yellow] Run 'minibench run' first.")
        return

    table = Table(title=f"Local Results ({len(data)} entries)", box=box.ROUNDED)
    table.add_column("#", style="dim")
    table.add_column("Model", style="cyan")
    table.add_column("Quant", style="white")
    table.add_column("t/s", style="bold green")
    table.add_column("TTFT", style="white")
    table.add_column("System RAM", style="white")
    table.add_column("VRAM", style="yellow")
    table.add_column("Bandwidth", style="bold yellow")
    table.add_column("CPU", style="dim")

    for i, r in enumerate(data, 1):
        bw = r.get("memory_bandwidth_gbs")
        bw_str = f"{bw} GB/s" if bw else "—"
        vram = r.get("vram_gb")
        vram_str = f"{vram} GB" if vram else "—"
        table.add_row(
            str(i),
            r.get("model_name", "?"),
            r.get("quantization", "?"),
            str(r.get("tokens_per_second", "?")),
            str(r.get("time_to_first_token", "—")),
            f"{r.get('total_ram_gb', '?')} GB",
            vram_str,
            bw_str,
            r.get("cpu_model", "?")[:30],
        )
    console.print(table)


@main.command()
@click.option("--api-url", default=None, help="API URL override")
def upload(api_url):
    """Upload most recent result to MiniBench API."""
    url = api_url or API_URL
    data = load_results()
    if not data:
        console.print("[yellow]No local results to upload.[/yellow]")
        return

    latest = data[-1]
    console.print(f"[bold]Uploading to {url}/api/v1/submit...[/bold]")

    try:
        resp = requests.post(f"{url}/api/v1/submit", json=latest, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            console.print(f"[green]Uploaded successfully![/green] Submission ID: {result.get('submission_id')}")
        else:
            console.print(f"[red]Upload failed ({resp.status_code}):[/red] {resp.text}")
    except requests.ConnectionError:
        console.print(f"[red]Could not connect to API at {url}[/red]")


@main.command()
def detect():
    """Show auto-detected hardware info."""
    hw = detect_all()
    table = Table(title="Hardware Detection", box=box.ROUNDED)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("CPU", hw.get("cpu_model", "Unknown"))
    table.add_row("Cores", str(hw.get("cpu_cores", "?")))
    table.add_row("Threads", str(hw.get("cpu_threads", "?")))
    table.add_row("System RAM", f"{hw.get('total_ram_gb', '?')} GB")
    table.add_row("GPU (Discrete)", hw.get("gpu_model") or "None")
    table.add_row("VRAM", f"{hw.get('vram_gb', 'N/A')} GB" if hw.get("vram_gb") else "N/A (System RAM only)")
    table.add_row("iGPU", hw.get("igpu_model") or "None")
    table.add_row("Memory Type", hw.get("memory_type") or "Unknown")
    table.add_row("OS", hw.get("os", "Unknown"))
    console.print(table)


if __name__ == "__main__":
    main()
