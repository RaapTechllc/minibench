import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { api } from '../api';
import type { AgentRunDetail, AgentTaskResult } from '../api';
import {
  PageHeader, Card, CardHeader, Stat, Badge, ValidityBadge,
  Skeleton, EmptyState, ErrorState, CIBar,
} from '../components/ui';
import { fmtPct, fmtCost } from '../components/chart';
import { categoryDisplayName, formatScorecard, orderCategoryKeys } from '../lib/scorecard.js';

function fmtDate(value: string | null): string {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

type ScenarioKind = 'spreadsheet' | 'cursor' | 'slack';

const CATEGORY_SCENARIO_FALLBACK: Record<string, ScenarioKind> = {
  reasoning: 'spreadsheet',
  'tool-use': 'spreadsheet',
  instruction: 'slack',
  coding: 'cursor',
};

const SCENARIO_LABELS: Record<ScenarioKind, string> = {
  spreadsheet: 'Spreadsheet',
  cursor: 'Cursor',
  slack: 'Slack',
};

const SCENARIO_CLASSES: Record<ScenarioKind, string> = {
  spreadsheet: 'border-cyan-400/40 bg-cyan-400/10 text-cyan-200',
  cursor: 'border-violet-400/40 bg-violet-400/10 text-violet-200',
  slack: 'border-amber-400/40 bg-amber-400/10 text-amber-200',
};

function groupByCategory(results: AgentTaskResult[]): Map<string, AgentTaskResult[]> {
  const groups = new Map<string, AgentTaskResult[]>();
  for (const r of results) {
    const key = r.category ?? 'uncategorized';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(r);
  }
  return groups;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function optionalString(source: unknown, key: string): string | null {
  if (!isRecord(source)) return null;
  const value = source[key];
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function optionalNumber(source: unknown, key: string): number | null {
  if (!isRecord(source)) return null;
  const value = source[key];
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function optionalBoolean(source: unknown, key: string): boolean | null {
  if (!isRecord(source)) return null;
  const value = source[key];
  return typeof value === 'boolean' ? value : null;
}

function optionalMetric(source: unknown, keys: string[]): string | null {
  for (const key of keys) {
    const bool = optionalBoolean(source, key);
    if (bool !== null) return bool ? 'PASS' : 'FAIL';

    const num = optionalNumber(source, key);
    if (num !== null) {
      const pct = Math.abs(num) <= 1 ? num * 100 : num;
      return fmtPct(pct);
    }

    const text = optionalString(source, key);
    if (text) return text;
  }
  return null;
}

function nestedMetadata(source: unknown): unknown {
  return isRecord(source) ? source.metadata : null;
}

function taskScenario(result: AgentTaskResult, category: string): { kind: ScenarioKind; fromMetadata: boolean } {
  const metadata = nestedMetadata(result);
  const raw =
    optionalString(result, 'scenario_type') ??
    optionalString(result, 'scenarioType') ??
    optionalString(metadata, 'scenario_type') ??
    optionalString(metadata, 'scenarioType');

  if (raw) {
    const normalized = raw.toLowerCase().replace(/[\s_]+/g, '-');
    if (normalized.includes('cursor') || normalized.includes('ide') || normalized.includes('code')) {
      return { kind: 'cursor', fromMetadata: true };
    }
    if (normalized.includes('slack') || normalized.includes('chat') || normalized.includes('thread')) {
      return { kind: 'slack', fromMetadata: true };
    }
    return { kind: 'spreadsheet', fromMetadata: true };
  }

  return { kind: CATEGORY_SCENARIO_FALLBACK[category] ?? 'spreadsheet', fromMetadata: false };
}

function ScenarioBadge({ result, category }: { result: AgentTaskResult; category: string }) {
  const scenario = taskScenario(result, category);
  return (
    <span
      title={scenario.fromMetadata ? 'Scenario type from task metadata.' : 'Scenario fallback inferred from category.'}
      className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${SCENARIO_CLASSES[scenario.kind]}`}
    >
      {SCENARIO_LABELS[scenario.kind]}
    </span>
  );
}

function humanizeTaskId(taskId: string, index: number): string {
  if (/canary|seed/i.test(taskId)) return `Task ${index + 1}`;
  const cleaned = taskId
    .replace(/[-_]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
  return cleaned || `Task ${index + 1}`;
}

function taskDisplayName(result: AgentTaskResult, index: number): string {
  const metadata = nestedMetadata(result);
  return (
    optionalString(result, 'description') ??
    optionalString(result, 'task_description') ??
    optionalString(result, 'display_name') ??
    optionalString(result, 'title') ??
    optionalString(metadata, 'description') ??
    optionalString(metadata, 'display_name') ??
    humanizeTaskId(result.task_id, index)
  );
}

const FORMAT_KEYS = ['pass_format', 'passed_format', 'format_pass', 'format_passed', 'score_format'];
const CAPABILITY_KEYS = [
  'pass_capability',
  'passed_capability',
  'capability_pass',
  'capability_passed',
  'score_capability',
];

function formatMetric(source: unknown): string | null {
  return optionalMetric(source, FORMAT_KEYS);
}

function capabilityMetric(source: unknown): string | null {
  return optionalMetric(source, CAPABILITY_KEYS);
}

function TechReadout({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-emerald-400/20 bg-black/30 p-3">
      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-400/70">{label}</div>
      <div className="tnum mt-1 text-lg font-semibold text-emerald-100">{value}</div>
      {sub && <div className="mt-1 text-[11px] text-emerald-200/60">{sub}</div>}
    </div>
  );
}

function CategoryPassRate({ results }: { results: AgentTaskResult[] }) {
  const passed = results.filter(r => r.passed).length;
  const pct = (passed / results.length) * 100;
  const tone = pct >= 80 ? 'pass' : pct >= 50 ? 'neutral' : 'fail';
  return (
    <Badge tone={tone}>
      <span className="tnum">{passed}/{results.length} ({pct.toFixed(0)}%)</span>
    </Badge>
  );
}

const BackLink = ({ run }: { run?: AgentRunDetail | null }) => {
  const to = run ? (run.moa_config ? '/agents' : '/models') : '/agents';
  const label = run ? (run.moa_config ? 'Back to Multiplayer Cabinet' : 'Back to Solo Cabinet') : 'Back to leaderboard';
  return (
    <Link to={to} className="inline-flex items-center gap-1.5 text-accent hover:text-accent-strong text-sm">
      <ArrowLeft className="w-4 h-4" /> {label}
    </Link>
  );
};

function TechnicianPanel({ run }: { run: AgentRunDetail }) {
  const hasCI = run.ci95_low != null && run.ci95_high != null;
  const runFormat = formatMetric(run);
  const runCapability = capabilityMetric(run);
  const resultMetrics = run.results
    .map((result, index) => ({
      result,
      index,
      format: formatMetric(result) ?? formatMetric(nestedMetadata(result)),
      capability: capabilityMetric(result) ?? capabilityMetric(nestedMetadata(result)),
    }))
    .filter((row) => row.format !== null || row.capability !== null);

  return (
    <Card className="border-emerald-400/30 bg-slate-950 p-5 font-mono text-emerald-100 shadow-none">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-emerald-400/20 pb-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-400">Technician mode</div>
          <div className="mt-1 text-[12px] text-emerald-200/70">Backstage scoring diagnostics for aggregate score checks.</div>
        </div>
        {run.grader_version && (
          <span className="rounded border border-emerald-400/30 px-2 py-1 text-[11px] text-emerald-200">
            grader {run.grader_version}
          </span>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <TechReadout
          label="95% CI"
          value={hasCI ? `${Number(run.ci95_low).toFixed(1)}-${Number(run.ci95_high).toFixed(1)}%` : '—'}
          sub={hasCI ? 'Wilson interval around score' : 'not included in payload'}
        />
        <TechReadout label="Pass^k" value={run.pass_hat_k != null ? fmtPct(run.pass_hat_k) : '—'} />
        <TechReadout label="Trial grid" value={`${run.n_tasks} tasks x ${run.n_trials} trials`} />
        <TechReadout
          label="Format / capability"
          value={runFormat || runCapability ? `${runFormat ?? '—'} / ${runCapability ?? '—'}` : '—'}
          sub={runFormat || runCapability ? 'strict format vs extractable answer' : 'not included in payload'}
        />
      </div>

      {hasCI && (
        <div className="mt-4 rounded-lg border border-emerald-400/20 bg-black/20 p-3">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-400/70">Score interval</div>
          <CIBar value={Number(run.pass_rate)} lo={Number(run.ci95_low)} hi={Number(run.ci95_high)} />
        </div>
      )}

      {resultMetrics.length > 0 && (
        <div className="mt-4 overflow-x-auto rounded-lg border border-emerald-400/20">
          <table className="w-full text-left text-[12px]">
            <thead className="border-b border-emerald-400/20 text-[10px] uppercase tracking-[0.14em] text-emerald-400/70">
              <tr>
                <th className="px-3 py-2 font-semibold">Task</th>
                <th className="px-3 py-2 font-semibold">Format</th>
                <th className="px-3 py-2 font-semibold">Capability</th>
              </tr>
            </thead>
            <tbody>
              {resultMetrics.map(({ result, index, format, capability }) => (
                <tr key={`${result.task_id}-${result.trial ?? index}`} className="border-t border-emerald-400/10">
                  <td className="px-3 py-2 text-emerald-100">{taskDisplayName(result, index)}</td>
                  <td className="tnum px-3 py-2 text-emerald-200/80">{format ?? '—'}</td>
                  <td className="tnum px-3 py-2 text-emerald-200/80">{capability ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

export default function RunDetail() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<AgentRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState(false);
  const [technicianMode, setTechnicianMode] = useState(false);

  const load = useCallback(() => {
    if (!runId) return () => {};
    let active = true;
    setLoading(true);
    setError(false);
    setNotFound(false);
    api
      .getAgentRun(runId)
      .then(r => {
        if (active) setRun(r);
      })
      .catch((e: unknown) => {
        // A 404 is "no such run"; anything else is a transient/load failure.
        if (!active) return;
        if (e instanceof Error && e.message.includes('404')) setNotFound(true);
        else setError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [runId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    const cleanup = load();
    return cleanup;
  }, [load]);

  if (loading) {
    return (
      <div className="space-y-6">
        <BackLink />
        <Skeleton rows={7} />
      </div>
    );
  }
  if (error) {
    return (
      <div className="space-y-6">
        <BackLink />
        <ErrorState onRetry={load}>Something went wrong loading this run.</ErrorState>
      </div>
    );
  }
  if (notFound || !run) {
    return (
      <div className="space-y-6">
        <BackLink />
        <EmptyState title="Run not found">
          This run may have been removed, or the link is incorrect.
        </EmptyState>
      </div>
    );
  }

  const configName = run.moa_config?.name ?? run.run_id.slice(0, 8);
  const models = run.moa_config?.models ?? [];
  const selfMoa = run.moa_config?.self_moa ?? false;
  const groups = groupByCategory(run.results);
  const categories = orderCategoryKeys([...groups.keys()])
    .map((category) => [category, groups.get(category) ?? []] as const)
    .filter(([, results]) => results.length > 0);
  const scorecard = formatScorecard(run.pass_rate);

  return (
    <div className="space-y-6">
      <BackLink run={run} />

      <PageHeader eyebrow={run.benchmark_suite} title={configName}>
        {run.provider ?? 'unknown provider'} · submitted {fmtDate(run.submitted_at)}
        {run.model_snapshot_date && ` · snapshot ${run.model_snapshot_date}`}
      </PageHeader>

      <div className="flex flex-wrap items-center gap-2 animate-rise">
        <ValidityBadge isPrivate={run.is_private_split} />
        {selfMoa && (
          <Badge tone="frontier" title="Self-mixture-of-agents: one model composed with itself.">Self-MoA</Badge>
        )}
        {models.map(m => (
          <Badge key={m} tone="neutral"><span className="font-mono">{m}</span></Badge>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 animate-rise rise-1">
        <Stat
          label="Scorecard"
          accent
          value={`${scorecard.tier} · ${scorecard.score}`}
          sub="overall run score"
        />
        <Stat label="Cost / task" value={fmtCost(run.cost_usd_per_task)} />
        <Stat
          label="Latency p50 / p95"
          value={run.latency_p50_ms != null && run.latency_p95_ms != null
            ? `${run.latency_p50_ms} / ${run.latency_p95_ms}ms`
            : '—'}
        />
        <Stat label="Harness" value={run.harness ?? '—'} />
      </div>

      <div className="animate-rise rise-1">
        <button
          type="button"
          aria-pressed={technicianMode}
          onClick={() => setTechnicianMode((value) => !value)}
          className="rounded-lg border border-ink-3/30 bg-slate-950 px-4 py-2 font-mono text-[12px] font-semibold uppercase tracking-[0.16em] text-emerald-300 transition hover:border-emerald-400/60 hover:text-emerald-100"
        >
          {technicianMode ? 'RELEASE START to hide Technician mode' : 'HOLD START for Technician mode'}
        </button>
      </div>

      {technicianMode && <TechnicianPanel run={run} />}

      {/* Task-by-task breakdown, grouped by category — the drill-down every
          comparable leaderboard (LiveBench, PinchBench) treats as core. */}
      <div className="space-y-4 animate-rise rise-2">
        <div>
          <h2 className="text-lg font-semibold text-ink">Arcade manual</h2>
          <p className="text-[13px] text-ink-2">Per-task pass/fail grouped into the displayed scorecard categories.</p>
        </div>
        {run.results.length === 0 ? (
          <EmptyState title="No per-task results">
            No per-task results were recorded for this run.
          </EmptyState>
        ) : (
          categories.map(([category, results]) => (
            <Card key={category} className="overflow-hidden">
              <CardHeader
                title={categoryDisplayName(category)}
                right={<CategoryPassRate results={results} />}
              />
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-ink-3 text-xs border-y border-line">
                    <tr>
                      <th className="px-5 py-2 font-medium">Task</th>
                      <th className="px-5 py-2 font-medium">Scenario</th>
                      <th className="px-5 py-2 font-medium">Trial</th>
                      <th className="px-5 py-2 font-medium">Result</th>
                      <th className="px-5 py-2 font-medium">Score</th>
                      <th className="px-5 py-2 font-medium">Cost</th>
                      <th className="px-5 py-2 font-medium">Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r, idx) => (
                      <tr
                        key={`${r.task_id}-${r.trial ?? idx}`}
                        className="border-t border-line hover:bg-surface-2"
                      >
                        <td className="px-5 py-2 text-ink">{taskDisplayName(r, idx)}</td>
                        <td className="px-5 py-2"><ScenarioBadge result={r} category={category} /></td>
                        <td className="px-5 py-2 text-ink-3 tnum">{r.trial ?? '—'}</td>
                        <td className="px-5 py-2">
                          <Badge tone={r.passed ? 'pass' : 'fail'}>{r.passed ? 'PASS' : 'FAIL'}</Badge>
                        </td>
                        <td className="px-5 py-2 text-ink-2 tnum">
                          {r.score != null ? Number(r.score).toFixed(2) : '—'}
                        </td>
                        <td className="px-5 py-2 text-ink-2 tnum">{fmtCost(r.cost_usd)}</td>
                        <td className="px-5 py-2 text-ink-2 tnum">
                          {r.latency_ms != null ? `${r.latency_ms}ms` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
