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

function fmtDate(value: string | null): string {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

// Grouping tasks by category mirrors LiveBench's per-category breakdown and
// PinchBench's task-by-task detail view — the thing every comparable
// leaderboard treats as core and we were missing entirely.
function groupByCategory(results: AgentTaskResult[]): Map<string, AgentTaskResult[]> {
  const groups = new Map<string, AgentTaskResult[]>();
  for (const r of results) {
    const key = r.category ?? 'uncategorized';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(r);
  }
  return groups;
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

const BackLink = () => (
  <Link to="/agents" className="inline-flex items-center gap-1.5 text-accent hover:text-accent-strong text-sm">
    <ArrowLeft className="w-4 h-4" /> Back to leaderboard
  </Link>
);

export default function RunDetail() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<AgentRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState(false);

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
  const categories = [...groupByCategory(run.results).entries()].sort(([a], [b]) => a.localeCompare(b));
  const hasCI = run.ci95_low != null && run.ci95_high != null;

  return (
    <div className="space-y-6">
      <BackLink />

      <PageHeader eyebrow={run.benchmark_suite} title={configName}>
        {run.provider ?? 'unknown provider'} · submitted {fmtDate(run.submitted_at)}
        {run.model_snapshot_date && ` · snapshot ${run.model_snapshot_date}`}
      </PageHeader>

      <div className="flex flex-wrap items-center gap-2 animate-rise">
        <ValidityBadge isPrivate={run.is_private_split} />
        {run.grader_version && (
          <Badge tone="neutral" title="Grader version used to score this run.">
            grader <span className="tnum">{run.grader_version}</span>
          </Badge>
        )}
        {selfMoa && (
          <Badge tone="frontier" title="Self-mixture-of-agents: one model composed with itself.">Self-MoA</Badge>
        )}
        {models.map(m => (
          <Badge key={m} tone="neutral"><span className="font-mono">{m}</span></Badge>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 animate-rise rise-1">
        <Stat
          label="Pass rate"
          accent
          value={
            hasCI
              ? <CIBar value={Number(run.pass_rate)} lo={Number(run.ci95_low)} hi={Number(run.ci95_high)} />
              : fmtPct(run.pass_rate)
          }
          sub={hasCI ? `95% CI ${Number(run.ci95_low).toFixed(0)}–${Number(run.ci95_high).toFixed(0)}%` : undefined}
        />
        <Stat label="Pass^k" value={fmtPct(run.pass_hat_k)} />
        <Stat label="Cost / task" value={fmtCost(run.cost_usd_per_task)} />
        <Stat
          label="Latency p50 / p95"
          value={run.latency_p50_ms != null && run.latency_p95_ms != null
            ? `${run.latency_p50_ms} / ${run.latency_p95_ms}ms`
            : '—'}
        />
        {run.calibration_brier != null && (
          <Stat
            label="Calibration (Brier)"
            value={Number(run.calibration_brier).toFixed(3)}
            sub="lower is better"
          />
        )}
        {run.robustness_correct != null && (
          <Stat
            label="Robustness"
            value={fmtPct(Number(run.robustness_correct) * 100)}
            sub="solved on both sides of a perturbation"
          />
        )}
        <Stat label="Tasks × trials" value={`${run.n_tasks} × ${run.n_trials}`} />
        <Stat
          label="Tokens in / out"
          value={run.tokens_in != null && run.tokens_out != null
            ? `${run.tokens_in.toLocaleString()} / ${run.tokens_out.toLocaleString()}`
            : '—'}
        />
        <Stat label="Harness" value={run.harness ?? '—'} />
      </div>

      {/* Task-by-task breakdown, grouped by category — the drill-down every
          comparable leaderboard (LiveBench, PinchBench) treats as core. */}
      <div className="space-y-4 animate-rise rise-2">
        <h2 className="text-lg font-semibold text-ink">Task results</h2>
        {run.results.length === 0 ? (
          <EmptyState title="No per-task results">
            No per-task results were recorded for this run.
          </EmptyState>
        ) : (
          categories.map(([category, results]) => (
            <Card key={category} className="overflow-hidden">
              <CardHeader
                title={category.charAt(0).toUpperCase() + category.slice(1)}
                right={<CategoryPassRate results={results} />}
              />
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-ink-3 text-xs border-y border-line">
                    <tr>
                      <th className="px-5 py-2 font-medium">Task</th>
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
                        <td className="px-5 py-2 text-ink font-mono text-xs">{r.task_id}</td>
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
