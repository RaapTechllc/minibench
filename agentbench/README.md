# agentbench

A contamination-resistant **agent / Mixture-of-Agents (MoA)** benchmark platform,
built as a clean module alongside the hardware-benchmark product (see
`benchmarks/AGENT-BENCH-BRIEF.md` for the full rationale). It realizes the brief's
first deliverables: MoA-as-a-model, executable grading, real cost accounting, a
new-model tracker, and rigor stats (trials + CIs + pass^k).

## Why this exists

The older `benchmarks/` prototype graded by keyword presence (so nothing could
score below 100%), hardcoded preset names that drifted from its own YAML, and
wrote "live results" to `/tmp` that were never committed. `agentbench` fixes all
three: **executable oracles**, **config validated at load**, and **committed
result artifacts**.

## Layout

| File | Purpose |
|------|---------|
| `config.py` | MoA config schema + YAML loader (proposers, aggregator, layers, Self-MoA). Validates at load. |
| `client.py` | One OpenAI-compatible client for OpenRouter + Ollama. Real `usage.cost`. Network boundary is injectable. |
| `moa.py` | `MoAModel.generate(prompt)` — fans out proposers → aggregator, rolls up cost/latency/tokens. |
| `grading.py` | Executable graders: `exact_match`, `numeric_match`, `json_fields`, `unit_test`. Each fails a bad answer. |
| `stats.py` | `pass_rate`, `pass_hat_k`, Wilson CI, percentiles — the trials-and-CIs guardrail. |
| `tracker.py` | Poll OpenRouter `/models`, diff against known ids → detect new launches. |
| `run.py` | CLI: run a config against a task suite with N trials, grade, summarize, write a committable artifact. |
| `presets/` | MoA configs: `moa-v1` (production), `moa-dev` (cheap testing), Self-MoA baselines. |
| `tasks/` | `coding-v1` (smoke/CI), `coding-v2` (harder eval). |

## Running

Offline smoke test (no keys, no network — also what CI runs, catches config drift):

```bash
python -m agentbench.run --config agentbench/presets/moa-v1.yaml \
    --tasks agentbench/tasks/coding-v1.json --trials 3 --dry-run
```

Cheap live testing (7B-class models, harder tasks — expect <100% pass rate):

```bash
python -m agentbench.run --config agentbench/presets/moa-dev.yaml \
    --tasks agentbench/tasks/coding-v2.json --trials 2 --provider openrouter
```

Production eval (expensive 70B+ MoA, easy smoke tasks — use only when comparing top configs):

```bash
export OPENROUTER_API_KEY=sk-or-...
python -m agentbench.run --config agentbench/presets/moa-v1.yaml \
    --tasks agentbench/tasks/coding-v2.json --trials 5 --provider openrouter
```

Tests:

```bash
cd agentbench && pip install -r requirements-dev.txt && pytest
```

## Reproducibility notes (from the brief — verify before a real run)

- **Pin dated model snapshots**, not floating aliases. On OpenRouter also pin
  `provider.order` + `allow_fallbacks:false` and store the returned `provider`,
  because the same id fans out to different price/quantization upstreams.
- **Always run a matched-cost Self-MoA baseline** (`presets/self-moa-baseline.yaml`).
  A mixed MoA that doesn't beat sampling the best single model N times isn't buying
  anything (arXiv 2502.00674).
- **Keep the real test split private**; publish only a dev slice. Task files carry a
  `canary` string so later leakage is detectable.
- Grade only on executable oracles. If a grader can't fail a deliberately-bad
  answer, it doesn't discriminate.

## Publishing to the leaderboard

`run.py`'s summary maps directly onto the backend `agent_runs` / `agent_task_results`
tables and the `/api/v1/agents/*` endpoints; the React **Agents** page renders the
pass-rate table plus the cost-vs-accuracy Pareto frontier.
