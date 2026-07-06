import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { api } from '../api';
import type { AgentRunDetail, AgentTaskResult } from '../api';

function fmtCost(v: number | null): string {
  if (v == null) return '—';
  // Decimal fields serialize as JSON strings (pydantic), not numbers — coerce
  // before formatting or .toFixed() throws on a string at render time.
  const n = Number(v);
  return n < 0.01 ? `$${n.toFixed(4)}` : `$${n.toFixed(3)}`;
}

function fmtPct(v: number | null): string {
  return v == null ? '—' : `${Number(v).toFixed(1)}%`;
}

function fmtDate(value: string | null): string {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

function StatCard({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-xl font-bold tabular-nums ${accent ?? 'text-white'}`}>{value}</div>
    </div>
  );
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
  const color = pct >= 80 ? 'text-emerald-400' : pct >= 50 ? 'text-amber-400' : 'text-red-400';
  return (
    <span className={`font-mono font-semibold ${color}`}>
      {passed}/{results.length} ({pct.toFixed(0)}%)
    </span>
  );
}

export default function RunDetail() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<AgentRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!runId) return;
    let active = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    api
      .getAgentRun(runId)
      .then(r => {
        if (active) setRun(r);
      })
      .catch(() => {
        if (active) setNotFound(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [runId]);

  if (loading) {
    return <div className="text-center py-10 text-gray-400">Loading...</div>;
  }
  if (notFound || !run) {
    return (
      <div className="space-y-4">
        <Link to="/agents" className="inline-flex items-center gap-1.5 text-cyan-400 hover:text-cyan-300 text-sm">
          <ArrowLeft className="w-4 h-4" /> Back to leaderboard
        </Link>
        <div className="bg-gray-900 border border-gray-800 rounded-xl text-center py-10 text-gray-500">
          Run not found.
        </div>
      </div>
    );
  }

  const configName = run.moa_config?.name ?? run.run_id.slice(0, 8);
  const models = run.moa_config?.models ?? [];
  const selfMoa = run.moa_config?.self_moa ?? false;
  const categories = [...groupByCategory(run.results).entries()].sort(([a], [b]) => a.localeCompare(b));

  return (
    <div className="space-y-6">
      <Link to="/agents" className="inline-flex items-center gap-1.5 text-cyan-400 hover:text-cyan-300 text-sm">
        <ArrowLeft className="w-4 h-4" /> Back to leaderboard
      </Link>

      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <h1 className="text-3xl font-bold text-white">{configName}</h1>
          {selfMoa && (
            <span className="text-xs text-purple-400 bg-purple-400/10 border border-purple-400/25 rounded px-2 py-0.5">
              Self-MoA
            </span>
          )}
        </div>
        <p className="text-gray-400 mt-1 text-sm">
          {run.benchmark_suite} · {run.provider ?? 'unknown provider'} · submitted {fmtDate(run.submitted_at)}
          {run.model_snapshot_date && ` · snapshot ${run.model_snapshot_date}`}
        </p>
        {models.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {models.map(m => (
              <span
                key={m}
                className="text-xs text-gray-300 bg-gray-800 border border-gray-700 rounded px-2 py-0.5 font-mono"
              >
                {m}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Pass rate" value={fmtPct(run.pass_rate)} accent="text-cyan-400" />
        <StatCard label="Pass^k" value={fmtPct(run.pass_hat_k)} />
        <StatCard
          label="95% CI"
          value={run.ci95_low != null && run.ci95_high != null
            ? `${Number(run.ci95_low).toFixed(0)}–${Number(run.ci95_high).toFixed(0)}%`
            : '—'}
        />
        <StatCard label="Cost/task" value={fmtCost(run.cost_usd_per_task)} accent="text-amber-400" />
        <StatCard
          label="Latency p50/p95"
          value={run.latency_p50_ms != null && run.latency_p95_ms != null
            ? `${run.latency_p50_ms} / ${run.latency_p95_ms}ms`
            : '—'}
        />
        <StatCard label="Tasks × trials" value={`${run.n_tasks} × ${run.n_trials}`} />
        <StatCard
          label="Tokens in/out"
          value={run.tokens_in != null && run.tokens_out != null
            ? `${run.tokens_in.toLocaleString()} / ${run.tokens_out.toLocaleString()}`
            : '—'}
        />
        <StatCard label="Harness" value={run.harness ?? '—'} />
      </div>

      {/* Task-by-task breakdown, grouped by category — the drill-down every
          comparable leaderboard (LiveBench, PinchBench) treats as core. */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-white">Task results</h2>
        {run.results.length === 0 ? (
          <div className="bg-gray-900 border border-gray-800 rounded-xl text-center py-10 text-gray-500">
            No per-task results recorded for this run.
          </div>
        ) : (
          categories.map(([category, results]) => (
            <div key={category} className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800 bg-gray-900/60">
                <span className="text-sm font-semibold text-white capitalize">{category}</span>
                <CategoryPassRate results={results} />
              </div>
              <table className="w-full text-sm text-left">
                <thead className="text-gray-500 text-xs">
                  <tr>
                    <th className="px-4 py-2 font-medium">Task</th>
                    <th className="px-4 py-2 font-medium">Trial</th>
                    <th className="px-4 py-2 font-medium">Result</th>
                    <th className="px-4 py-2 font-medium">Score</th>
                    <th className="px-4 py-2 font-medium">Cost</th>
                    <th className="px-4 py-2 font-medium">Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r, idx) => (
                    <tr
                      key={`${r.task_id}-${r.trial ?? idx}`}
                      className="border-t border-gray-800/50 hover:bg-gray-800/30"
                    >
                      <td className="px-4 py-2 text-gray-300 font-mono text-xs">{r.task_id}</td>
                      <td className="px-4 py-2 text-gray-500 tabular-nums">{r.trial ?? '—'}</td>
                      <td className="px-4 py-2">
                        <span
                          className={`text-xs font-semibold px-2 py-0.5 rounded ${
                            r.passed
                              ? 'text-emerald-400 bg-emerald-400/10 border border-emerald-400/25'
                              : 'text-red-400 bg-red-400/10 border border-red-400/25'
                          }`}
                        >
                          {r.passed ? 'PASS' : 'FAIL'}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-gray-300 tabular-nums">
                        {r.score != null ? Number(r.score).toFixed(2) : '—'}
                      </td>
                      <td className="px-4 py-2 text-amber-400 tabular-nums">{fmtCost(r.cost_usd)}</td>
                      <td className="px-4 py-2 text-gray-400 tabular-nums">
                        {r.latency_ms != null ? `${r.latency_ms}ms` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
