const API_BASE = import.meta.env.VITE_API_URL || '';

export interface Benchmark {
  id: number;
  submission_id: string;
  submitted_at: string;
  cpu_model: string;
  cpu_cores: number | null;
  cpu_threads: number | null;
  gpu_model: string | null;
  igpu_model: string | null;
  total_ram_gb: number;
  vram_gb: number | null;
  memory_type: string | null;
  memory_bandwidth_gbs: number | null;
  system_type: string | null;
  hardware_price_usd: number | null;
  os: string;
  inference_engine: string;
  engine_version: string | null;
  model_name: string;
  model_params_b: number | null;
  quantization: string;
  tokens_per_second: number;
  time_to_first_token: number | null;
  total_power_watts: number | null;
  watts_per_token: number | null;
  thermal_setting: string | null;
  ambient_temp_c: number | null;
  model_quality_score: number | null;
  quality_source: string | null;
  hei: number | null;
  fingerprint: string | null;
  test_duration_secs: number;
  prompt_tokens: number;
  completion_tokens: number;
}

export interface HardwareSpec {
  id: number;
  system_name: string;
  cpu_model: string | null;
  gpu_model: string | null;
  igpu_model: string | null;
  system_ram_gb: number | null;
  vram_gb: number | null;
  memory_type: string | null;
  max_memory_gb: number | null;
  memory_bandwidth_gbs: number | null;
  tdp_watts: number | null;
  msrp_usd: number | null;
  release_year: number | null;
  form_factor: string | null;
}

export interface ModelQuality {
  id: number;
  model_family: string;
  model_variant: string;
  params_b: number | null;
  mmlu_score: number | null;
  lmsys_elo: number | null;
}

export interface LeaderboardEntry {
  rank: number;
  id: number;
  system_type: string | null;
  cpu_model: string;
  total_ram_gb: number;
  vram_gb: number | null;
  memory_bandwidth_gbs: number | null;
  model_name: string;
  quantization: string;
  tokens_per_second: number;
  time_to_first_token: number | null;
  model_quality_score: number | null;
  hardware_price_usd: number | null;
  hei: number | null;
}

export interface Stats {
  total_submissions: number;
  unique_systems: number;
  unique_models: number;
  avg_tokens_per_second: number | null;
  max_tokens_per_second: number | null;
  total_hardware_specs: number;
}

export interface AgentLeaderboardEntry {
  rank: number;
  run_id: string;
  config_name: string | null;
  self_moa: boolean;
  models: string[];
  model_snapshot_date: string | null;
  benchmark_suite: string;
  provider: string | null;
  n_tasks: number;
  n_trials: number;
  pass_rate: number;
  pass_hat_k: number | null;
  ci95_low: number | null;
  ci95_high: number | null;
  cost_usd_per_task: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  on_pareto_frontier: boolean;
}

export interface AgentTaskResult {
  task_id: string;
  category: string | null;
  scenario_type: string | null;
  task_description: string | null;
  trial: number | null;
  passed: boolean;
  passed_format: boolean | null;
  score: number | null;
  cost_usd: number | null;
  latency_ms: number | null;
}

export interface AgentRunDetail {
  id: number;
  run_id: string;
  submitted_at: string;
  harness: string | null;
  harness_version: string | null;
  moa_config: { name?: string; self_moa?: boolean; models?: string[] } | null;
  benchmark_suite: string;
  provider: string | null;
  model_snapshot_date: string | null;
  n_tasks: number;
  n_trials: number;
  pass_rate: number;
  pass_format: number | null;
  pass_hat_k: number | null;
  ci95_low: number | null;
  ci95_high: number | null;
  cost_usd_per_task: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  tokens_in: number | null;
  tokens_out: number | null;
  is_private_split: boolean | null;
  grader_version: string | null;
  calibration_brier: number | null;
  robustness_correct: number | null;
  results: AgentTaskResult[];
}

export interface KnownModel {
  id: number;
  provider: string;
  model_id: string;
  display_name: string | null;
  first_seen: string;
  context_length: number | null;
  prompt_price: number | null;
  completion_price: number | null;
  benchmarked: boolean;
  family: string | null;
  license: string | null;
  snapshot_date: string | null;
}

export interface ModelLeaderboardEntry {
  rank: number;
  model_string: string;
  run_id: string;
  benchmark_suite: string;
  provider: string | null;
  display_name: string | null;
  family: string | null;
  license: string | null;
  prompt_price: number | null;
  completion_price: number | null;
  n_tasks: number;
  n_trials: number;
  pass_rate: number;
  pass_hat_k: number | null;
  ci95_low: number | null;
  ci95_high: number | null;
  cost_usd_per_task: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  submitted_at: string;
  category_pass_rates: Record<string, number>;
  on_pareto_frontier: boolean;
  // Validity signals (served by the backend; surfaced as badges).
  is_private_split: boolean | null;
  grader_version: string | null;
  // minibench-pro-v1 axes (present only for pro runs).
  calibration_brier: number | null;
  robustness_correct: number | null;
}

export interface UsageBoardRow {
  id: string;
  name: string;
  openrouter_url: string;
  prompt_price: number | null;
  completion_price: number | null;
  blended_per_million: number | null;
  daily_tokens: number | null;
  ranking_date: string | null;
  eval_score: number | null;
  eval_source: string | null;
  eval_task: string | null;
  latency_ms: number | null;
  task_shares: Record<string, number>;
  citation: string;
  as_of: string;
}

export interface UsageBoardPayload {
  meta: {
    as_of: string;
    citation: string;
    live: boolean;
    source?: string;
    row_count?: number;
  };
  rows: UsageBoardRow[];
}

export interface ReferenceProfile {
  id: number;
  profile_key: string;
  display_name: string;
  description: string | null;
  engine: string | null;
  engine_version_min: string | null;
  quantization: string | null;
  context_length: number | null;
  temperature: number | null;
  top_p: number | null;
  max_tokens: number | null;
  representative_system: string | null;
}

/* ── Real-Work Agent Cabinet (/api/v1/agent-cabinet) ───────────────────────
   Distinct board for published agent-harness runs. Read-only product surface;
   these types mirror backend/app/agent_cabinet_present.py and never mix with
   the Solo (/models) or Multiplayer (/agents) contracts above. */

export interface AgentCabinetListItem {
  run_id: string;
  submitted_at: string;
  suite: string | null;
  model_route: string | null;
  harness: string | null;
  harness_version: string | null;
  /** 0–100. */
  completion: number;
  /** Same value as completion; carried for contract parity. */
  pass_rate: number;
  /** Raw backend category keys → completion 0–100 (never Arcade labels). */
  category_completion: Record<string, number>;
  cost_usd_per_task: number | null;
  latency_p50_ms: number | null;
  private_split: boolean;
}

export interface AgentCabinetTechnician {
  model: string | null;
  provider: string | null;
  model_route: string | null;
  harness: string | null;
  harness_version: string | null;
  tool_contract: string[] | null;
  tool_contract_sha256: string | null;
  prompt_config_sha256: string | null;
  fixture_reference: string | null;
  fixture_digest: string | null;
  generator_sha256: string | null;
  suite: string | null;
  task_set_sha256: string | null;
  budgets: Record<string, number> | null;
  git_commit: string | null;
  grader_version: string | null;
  private_split: boolean | null;
  private_split_id: string | null;
  policy_version: string | null;
  /** Raw 0–1 fractions from the run summary (null when not measured). */
  false_verification_rate: number | null;
  regression_rate: number | null;
  termination_reasons: Record<string, number>;
  /** 0–100 (backend pre-scales these). */
  pass_hat_k: number | null;
  ci95_low: number | null;
  ci95_high: number | null;
  pass_rate_ci95: (number | null)[];
  pass_rate_ci95_boot: (number | null)[];
  trials: Record<string, unknown>[];
}

export interface AgentCabinetDetail extends AgentCabinetListItem {
  technician: AgentCabinetTechnician;
  held_constant: string[];
  changed_variables: string;
}

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    // FastAPI errors carry a `detail` — a string for HTTPException,
    // a list of {loc, msg} for 422 validation errors.
    let message = `API error: ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data.detail === 'string') {
        message = data.detail;
      } else if (Array.isArray(data.detail)) {
        message = data.detail
          .map((d: { loc?: (string | number)[]; msg: string }) =>
            `${(d.loc ?? []).slice(1).join('.')}: ${d.msg}`)
          .join('; ');
      }
    } catch { /* keep generic message */ }
    throw new Error(message);
  }
  return res.json();
}

export const api = {
  getBenchmarks: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchJSON<Benchmark[]>(`/api/v1/benchmarks${qs}`);
  },
  getBenchmark: (id: number) => fetchJSON<Benchmark>(`/api/v1/benchmarks/${id}`),
  submitBenchmark: (payload: unknown) => postJSON<Benchmark>('/api/v1/submit', payload),
  getLeaderboard: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchJSON<LeaderboardEntry[]>(`/api/v1/leaderboard${qs}`);
  },
  getHardware: () => fetchJSON<HardwareSpec[]>('/api/v1/hardware'),
  getReferenceProfiles: () => fetchJSON<ReferenceProfile[]>('/api/v1/profiles'),
  getCompare: (a: number, b: number) =>
    fetchJSON<{ a: Benchmark; b: Benchmark }>(`/api/v1/compare?a=${a}&b=${b}`),
  getStats: () => fetchJSON<Stats>('/api/v1/stats'),
  getModels: () => fetchJSON<ModelQuality[]>('/api/v1/models'),
  getAgentLeaderboard: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchJSON<AgentLeaderboardEntry[]>(`/api/v1/agents/leaderboard${qs}`);
  },
  getNewModels: () => fetchJSON<KnownModel[]>('/api/v1/agents/models/new'),
  getModelLeaderboard: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchJSON<ModelLeaderboardEntry[]>(`/api/v1/agents/models/leaderboard${qs}`);
  },
  getAgentRun: (runId: string) => fetchJSON<AgentRunDetail>(`/api/v1/agents/runs/${runId}`),
  getOpenRouterBoard: () => fetchJSON<UsageBoardPayload>('/api/v1/openrouter/board'),
  getOpenRouterCompare: (by: 'cost' | 'task' | 'latency', task?: string) => {
    const path = `/api/v1/openrouter/compare/best-by-${by}`;
    const qs = by === 'task' && task ? `?task=${encodeURIComponent(task)}` : '';
    return fetchJSON<UsageBoardPayload>(`${path}${qs}`);
  },
  getAgentCabinetRuns: () => fetchJSON<AgentCabinetListItem[]>('/api/v1/agent-cabinet/runs'),
  getAgentCabinetRun: (runId: string) =>
    fetchJSON<AgentCabinetDetail>(`/api/v1/agent-cabinet/runs/${runId}`),
};
