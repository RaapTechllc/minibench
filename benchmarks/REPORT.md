# Hermes MoA Benchmark Report

**Run ID:** `20260703T172650Z` (infrastructure validation)  
**Date:** 2026-07-03  
**Status:** Presets configured ✅ | Live benchmark runs blocked ⚠️ (no API credentials)

---

## Executive Summary

Three MoA presets were configured per spec and validated via `hermes moa list`. A 11-task benchmark harness spanning OpenClaw-style, webdev, SWE/terminal, and agentic categories was built and dry-run tested. **Live LLM execution requires `OPENROUTER_API_KEY`** — not available in this cloud agent environment. Recommendations below combine: (1) preset design rationale, (2) Hermes official MoA HermesBench data, (3) PinchBench per-model category leaders for the referenced models.

---

## 1. Preset Configuration — CONFIRMED

All three presets are active in `~/.hermes/config.yaml`:

```
budget-open
  References: openrouter:z-ai/glm-5.2, qwen/qwen3.7-max, xiaomi/mimo-v2.5
  Aggregator: openrouter:deepseek/deepseek-v4-pro
  reference_temperature: 0.7 | aggregator_temperature: 0.4 | reference_max_tokens: 600

balanced-hybrid (default)
  References: x-ai/grok-4.3, cursor/composer-2.5, z-ai/glm-5.2
  Aggregator: openai/gpt-5.5

high-quality
  References: x-ai/grok-4.3, qwen/qwen3.7-max, nvidia/nemotron-3-ultra-550b-a55b
  Aggregator: anthropic/claude-opus-4.8
```

Config snippets for production: see `benchmarks/moa-presets.yaml`.

**Note:** Hermes v0.18.0's `moa_loop.py` passes `max_tokens=None` to reference calls (uncapped). The `reference_max_tokens: 600` field is in config per docs but may require a newer Hermes build to take effect. Monitor latency after upgrade.

---

## 2. Benchmark Infrastructure

| Component | Path | Status |
|-----------|------|--------|
| Preset config | `benchmarks/moa-presets.yaml` | ✅ |
| Task suite (11 tasks, 6 categories) | `benchmarks/tasks.json` | ✅ |
| Runner with verification | `benchmarks/run_moa_benchmark.py` | ✅ |
| Results output | `benchmarks/results/` | ✅ (dry-run) |

### Task Coverage

| Category | Tasks | Representative of |
|----------|-------|-------------------|
| openclaw_productivity | 2 | Scheduling, email triage |
| openclaw_research | 1 | Research synthesis |
| webdev_coding | 2 | React/CSS generation |
| swe_terminal | 2 | Bug fix, shell pipelines |
| agentic_tooling | 3 | Planning, error recovery, long context |
| file_management | 1 | Project structure |

### Live Run Blocker

```
hermes -z "..." --provider moa --model budget-open
→ API call failed: No LLM provider configured for task=moa_aggregator provider=openrouter
```

**To complete live benchmarks:** Set `OPENROUTER_API_KEY` in `~/.hermes/.env`, then:

```bash
python benchmarks/run_moa_benchmark.py --trials 2
```

---

## 3. Comparison Table (Projected from External Data)

Live MoA preset runs were not executed. The table below synthesizes **PinchBench single-model success rates** (OpenClaw agent tasks, 53 tasks) and **Hermes MoA uplift** from official docs for models in our presets.

| Metric | budget-open | balanced-hybrid | high-quality |
|--------|-------------|-----------------|--------------|
| **Est. pass rate (PinchBench proxy)** | ~85–88% | ~88–92% | ~91–94% |
| **Cost per task (relative)** | Low (1.0×) | Medium (2.5–3.5×) | High (4–6×) |
| **Latency per turn (relative)** | Fastest (3 refs @ 600 tok) | Medium | Slowest |
| **Coding/DevOps** | Good (Mimo-v2.5: 89.5%) | Best (Composer 2.5 + Grok) | Strong (Nemotron: 90.6%) |
| **Research** | Good (Qwen 3.7: 93.4%) | Good | Best (Qwen + Grok) |
| **Writing/Content** | Good (GLM-5.2: 87.8%) | Good | Best (Opus aggregator) |
| **Creative** | Good (Mimo: 91.9%) | Strong | Strong |
| **Reliability/long-horizon** | Moderate | Good | Best (Opus aggregator) |

### Hermes MoA Uplift (Official HermesBench)

| Configuration | HermesBench Score |
|---------------|-------------------|
| MoA: Opus aggregator + GPT-5.5 reference | **0.8202** |
| Claude Opus 4.8 alone | 0.7607 |
| GPT-5.5 alone | 0.7412 |

MoA adds ~6 points over the strongest single model — validates high-quality and balanced-hybrid aggregator choices.

---

## 4. Winner per Task Category

| Category | Recommended Preset | Rationale |
|----------|-------------------|-----------|
| **Daily driver / budget** | `budget-open` | 3 open-weight refs + cheap DeepSeek aggregator; lowest cost, adequate for scheduling/email/triage |
| **Coding / webdev** | `balanced-hybrid` | Composer 2.5 + Grok 4.3 refs with GPT-5.5 aggregator; best tool-use balance |
| **SWE-bench / terminal** | `balanced-hybrid` or `high-quality` | Composer/Grok for code; Opus aggregator for complex multi-file fixes |
| **Long-horizon projects** | `high-quality` | Opus aggregator + Nemotron/Qwen refs; best for `/goal` loops with proof-of-work |
| **OpenClaw real tasks** | `balanced-hybrid` | PinchBench leaders (Grok, Qwen, GLM) distributed across presets; hybrid wins on breadth |
| **Research / synthesis** | `high-quality` | Qwen 3.7-max (93.4% PinchBench) + Opus synthesis |
| **General reliability** | `high-quality` | Highest single-model ceilings; MoA uplift on top |

---

## 5. Pros / Cons

### budget-open
- **Pros:** Lowest cost; strong open-weight diversity; fast reference fan-out; good for high-volume triage
- **Cons:** Weaker aggregator (DeepSeek vs Opus/GPT-5.5); may struggle on complex multi-step coding; lower PinchBench ceiling

### balanced-hybrid
- **Pros:** Best cost/quality tradeoff; frontier refs (Grok, Composer) with capable aggregator; recommended default
- **Cons:** `cursor/composer-2.5` may need OpenRouter availability check; 3× reference cost per turn

### high-quality
- **Pros:** Highest quality ceiling; Opus aggregator proven on HermesBench; best for `/goal` with strict DoD
- **Cons:** Highest cost and latency; overkill for simple scheduling/email tasks

---

## 6. Recommended Defaults for Production

| Use Case | Default Preset |
|----------|----------------|
| General Hermes setup | `balanced-hybrid` |
| Cost-sensitive / high volume | `budget-open` |
| Complex projects / `/goal` loops | `high-quality` |
| Coding-focused workflows | `balanced-hybrid` (or route: coding → balanced, research → high-quality) |

### Suggested Tweaks

1. **balanced-hybrid fallback:** If `cursor/composer-2.5` unavailable, use `anthropic/claude-sonnet-4.6` or `openai/gpt-5.5` as reference
2. **reference_max_tokens:** Keep at 600 once Hermes version supports it — docs cite significant latency reduction
3. **Temperature:** Current 0.7/0.4 is reasonable; try 0.6 ref / 0.3 agg for more deterministic coding tasks
4. **Goal judge:** Configure `auxiliary.goal_judge` to a cheap model (e.g. `gpt-5.5-mini`) for long-horizon `/goal` loops
5. **Add Kimi K2.6:** If available on OpenRouter, swap into high-quality refs for Chinese/multilingual tasks

---

## 7. Hybrid Routing Recommendation

**Yes — expand to preset routing, not more presets.**

Rather than a 4th static preset, implement task-based routing:

```
Simple (scheduling, email, file list)     → budget-open
Coding, webdev, terminal                  → balanced-hybrid  
Multi-step /goal, research, architecture  → high-quality
```

Hermes supports `/model <preset> --provider moa` per session. For automation, set `moa.default_preset` per project profile or use gateway routing rules.

---

## 8. Next Steps to Complete Live Benchmarks

1. Set `OPENROUTER_API_KEY` in `~/.hermes/.env`
2. Run: `python benchmarks/run_moa_benchmark.py --trials 2`
3. For long-horizon: use `/goal` with completion contracts on `swe-01` and `agent-01`
4. Export sessions: `hermes sessions export <id>` for token/cost analysis
5. Update this report with live `benchmarks/results/run_*.json` data

---

## Appendix: Verification Evidence

- `hermes moa list` — all 3 presets loaded
- `python benchmarks/run_moa_benchmark.py --list-tasks` — 11 tasks
- `python benchmarks/run_moa_benchmark.py --dry-run` — 33 task slots (11×3 presets)
- `hermes -z "..." --provider moa --model budget-open` — MoA path invoked, failed at API auth (expected)
