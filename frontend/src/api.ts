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

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  getBenchmarks: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchJSON<Benchmark[]>(`/api/v1/benchmarks${qs}`);
  },
  getBenchmark: (id: number) => fetchJSON<Benchmark>(`/api/v1/benchmarks/${id}`),
  getLeaderboard: (params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return fetchJSON<LeaderboardEntry[]>(`/api/v1/leaderboard${qs}`);
  },
  getHardware: () => fetchJSON<HardwareSpec[]>('/api/v1/hardware'),
  getCompare: (a: number, b: number) =>
    fetchJSON<{ a: Benchmark; b: Benchmark }>(`/api/v1/compare?a=${a}&b=${b}`),
  getStats: () => fetchJSON<Stats>('/api/v1/stats'),
  getModels: () => fetchJSON<ModelQuality[]>('/api/v1/models'),
};
