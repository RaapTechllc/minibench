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
  trial: number | null;
  passed: boolean;
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
  pass_hat_k: number | null;
  ci95_low: number | null;
  ci95_high: number | null;
  cost_usd_per_task: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  tokens_in: number | null;
  tokens_out: number | null;
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
  getCompare: (a: number, b: number) =>
    fetchJSON<{ a: Benchmark; b: Benchmark }>(`/api/v1/compare?a=${a}&b=${b}`),
  getStats: () => fetchJSON<Stats>('/api/v1/stats'),
  getModels: () => fetchJSON<ModelQuality[]>('/api/v1/models'),
  getAgentLeaderboard: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchJSON<AgentLeaderboardEntry[]>(`/api/v1/agents/leaderboard${qs}`);
  },
  getNewModels: () => fetchJSON<KnownModel[]>('/api/v1/agents/models/new'),
  getAgentRun: (runId: string) => fetchJSON<AgentRunDetail>(`/api/v1/agents/runs/${runId}`),
};
