const API_BASE = import.meta.env.VITE_API_URL || '';

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

export const api = {
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
  getAgentCabinetRuns: () => fetchJSON<AgentCabinetListItem[]>('/api/v1/agent-cabinet/runs'),
  getAgentCabinetRun: (runId: string) =>
    fetchJSON<AgentCabinetDetail>(`/api/v1/agent-cabinet/runs/${runId}`),
};
