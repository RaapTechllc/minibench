# Hermes MoA Benchmark Suite

Rigorous comparison of 3 MoA presets for production Hermes deployments.

## Presets

| Preset | References | Aggregator | Focus |
|--------|-----------|------------|-------|
| **budget-open** | GLM-5.2, Qwen 3.7-max, Mimo-v2.5 | DeepSeek V4 Pro | Cost-efficient, open-weight |
| **balanced-hybrid** | Grok 4.3, Composer 2.5, GLM-5.2 | GPT-5.5 | Balanced quality/cost |
| **high-quality** | Grok 4.3, Qwen 3.7-max, Nemotron Ultra | Claude Opus 4.8 | Frontier quality |

All presets use `reference_max_tokens: 600`, `reference_temperature: 0.7`, `aggregator_temperature: 0.4`.

## Setup

```bash
# 1. Install Hermes Agent
pip install hermes-agent
# or: curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# 2. Configure API key
hermes config set OPENROUTER_API_KEY sk-or-v1-...

# 3. Install MoA presets
cp benchmarks/moa-presets.yaml ~/.hermes/config.yaml
# Or merge the moa: section into your existing config

# 4. Verify presets
hermes moa list
```

## Run Benchmarks

```bash
# List tasks (11 across 6 categories)
python benchmarks/run_moa_benchmark.py --list-tasks

# Dry run (no API calls)
python benchmarks/run_moa_benchmark.py --dry-run

# Full benchmark (all 3 presets, 11 tasks)
python benchmarks/run_moa_benchmark.py --trials 1

# Single preset
python benchmarks/run_moa_benchmark.py --preset budget-open

# Filter by category
python benchmarks/run_moa_benchmark.py --filter swe
```

## Task Categories

- **openclaw_productivity** — scheduling, email triage (PinchBench-style)
- **openclaw_research** — structured synthesis
- **webdev_coding** — React/CSS generation (arena.ai-style)
- **swe_terminal** — bug fixes, shell pipelines (SWE-bench/Terminal-Bench)
- **agentic_tooling** — multi-step planning, error recovery, long context
- **file_management** — directory structure design

## Metrics Tracked

- Pass rate (automated verification)
- Quality score (partial credit for near-misses)
- Latency per task
- Error details

Results saved to `benchmarks/results/run_<timestamp>.json`.

## Using /goal for Long-Horizon Tasks

For multi-turn benchmarks with proof-of-work:

```bash
hermes --provider moa --model high-quality
/goal Fix the failing test in tests/test_api.py. Definition of Done: all pytest tests pass. Verification: run pytest and show green output.
```

The goal judge loop auto-continues until DoD is satisfied or turn budget exhausted.

## Model ID Notes

OpenRouter model IDs used (verify availability on your account):

- `z-ai/glm-5.2`
- `qwen/qwen3.7-max`
- `xiaomi/mimo-v2.5`
- `deepseek/deepseek-v4-pro`
- `x-ai/grok-4.3`
- `cursor/composer-2.5`
- `nvidia/nemotron-3-ultra-550b-a55b`
- `openai/gpt-5.5`
- `anthropic/claude-opus-4.8`

If `cursor/composer-2.5` is unavailable, substitute `openai/gpt-5.5` or `anthropic/claude-sonnet-4.6` in balanced-hybrid.
