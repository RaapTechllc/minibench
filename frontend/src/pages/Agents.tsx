import { useEffect, useState } from 'react';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { api } from '../api';
import type { AgentLeaderboardEntry, KnownModel } from '../api';

// Cost-vs-accuracy scatter point. Frontier dots are drawn gold + larger.
interface ParetoPoint {
  cost: number;
  pass: number;
  name: string;
  frontier: boolean;
  self_moa: boolean;
}

function fmtCost(v: number | null): string {
  if (v == null) return '—';
  return v < 0.01 ? `$${v.toFixed(4)}` : `$${v.toFixed(3)}`;
}

function fmtPct(v: number | null): string {
  return v == null ? '—' : `${Number(v).toFixed(1)}%`;
}

interface FrontierDotProps {
  cx?: number;
  cy?: number;
  payload?: ParetoPoint;
}

function FrontierDot({ cx, cy, payload }: FrontierDotProps) {
  if (cx == null || cy == null || !payload) return null;
  const onFrontier = payload.frontier;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={onFrontier ? 7 : 5}
      fill={onFrontier ? '#fbbf24' : '#22d3ee'}
      opacity={onFrontier ? 0.95 : 0.6}
      stroke={onFrontier ? '#030712' : 'none'}
      strokeWidth={onFrontier ? 1.5 : 0}
    />
  );
}

export default function Agents() {
  const [entries, setEntries] = useState<AgentLeaderboardEntry[]>([]);
  const [newModels, setNewModels] = useState<KnownModel[]>([]);
  const [sortBy, setSortBy] = useState('pass_rate');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    api.getAgentLeaderboard({ sort_by: sortBy }).then(setEntries).finally(() => setLoading(false));
  }, [sortBy]);

  useEffect(() => {
    api.getNewModels().then(setNewModels).catch(() => setNewModels([]));
  }, []);

  const paretoData: ParetoPoint[] = entries
    .filter(e => e.cost_usd_per_task != null)
    .map(e => ({
      cost: Number(e.cost_usd_per_task),
      pass: Number(e.pass_rate),
      name: e.config_name ?? e.run_id.slice(0, 8),
      frontier: e.on_pareto_frontier,
      self_moa: e.self_moa,
    }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Agent Leaderboard</h1>
        <p className="text-gray-400 mt-1">
          MoA &amp; agentic configs on contamination-resistant tasks. Ranked by pass rate;
          the gold Pareto frontier is what actually matters — expensive setups rarely sit on it.
        </p>
      </div>

      {newModels.length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl px-4 py-3">
          <span className="text-amber-400 font-semibold text-sm">
            {newModels.length} new model{newModels.length > 1 ? 's' : ''} — not yet benchmarked:
          </span>{' '}
          <span className="text-gray-300 text-sm">
            {newModels.slice(0, 5).map(m => m.display_name || m.model_id).join(', ')}
            {newModels.length > 5 ? ` +${newModels.length - 5} more` : ''}
          </span>
        </div>
      )}

      {/* Cost vs Accuracy Pareto frontier — the signature agent chart. */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-start justify-between mb-1">
          <h2 className="text-lg font-semibold text-white">Cost vs. Accuracy</h2>
          <span className="text-xs text-gray-500 mt-1">gold = Pareto-optimal</span>
        </div>
        <p className="text-sm text-gray-400 mb-4">
          Pass rate vs. cost per task. Gold dots are on the efficiency frontier — no other
          config is both cheaper and at least as accurate.
        </p>
        {paretoData.length === 0 ? (
          <div className="text-center py-10 text-gray-500 text-sm">
            No priced runs yet. Publish a run via <code className="text-cyan-400">agentbench.run</code>.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={380}>
            <ScatterChart margin={{ top: 20, right: 40, bottom: 40, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="cost"
                name="Cost/task"
                type="number"
                stroke="#6b7280"
                label={{ value: 'Cost per task (USD)', position: 'insideBottom', offset: -20, fill: '#9ca3af', fontSize: 12 }}
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickFormatter={(v: number) => `$${v}`}
              />
              <YAxis
                dataKey="pass"
                name="Pass rate"
                type="number"
                domain={[0, 100]}
                stroke="#6b7280"
                label={{ value: 'Pass rate (%)', angle: -90, position: 'insideLeft', offset: 15, fill: '#9ca3af', fontSize: 12 }}
                tick={{ fill: '#6b7280', fontSize: 11 }}
              />
              <Tooltip
                cursor={{ stroke: '#4b5563', strokeWidth: 1, strokeDasharray: '4 4' }}
                content={({ payload }) => {
                  if (!payload?.length) return null;
                  const d = payload[0].payload as ParetoPoint;
                  return (
                    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm shadow-xl">
                      <div className="font-semibold text-white">
                        {d.name}
                        {d.self_moa && <span className="ml-1 text-purple-400 text-xs">(Self-MoA)</span>}
                      </div>
                      <div className="text-cyan-400">{d.pass.toFixed(1)}% pass</div>
                      <div className="text-gray-400">{fmtCost(d.cost)}/task</div>
                      {d.frontier && <div className="text-amber-400 text-xs mt-1">On Pareto frontier</div>}
                    </div>
                  );
                }}
              />
              <Scatter data={paretoData} shape={FrontierDot} />
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Leaderboard table */}
      <div className="flex flex-wrap gap-3">
        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-gray-600"
        >
          <option value="pass_rate">Sort: Pass rate</option>
          <option value="pass_hat_k">Sort: Pass^k (consistency)</option>
          <option value="cost_usd_per_task">Sort: Cost/task</option>
        </select>
      </div>

      {loading ? (
        <div className="text-center py-10 text-gray-400">Loading...</div>
      ) : entries.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl text-center py-10 text-gray-500">
          No agent runs yet.
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-gray-400 border-b border-gray-700 bg-gray-900 sticky top-14 z-10">
              <tr>
                <th className="p-3 font-medium whitespace-nowrap">Rank</th>
                <th className="p-3 font-medium whitespace-nowrap">Config</th>
                <th className="p-3 font-medium whitespace-nowrap">Suite</th>
                <th className="p-3 font-medium whitespace-nowrap">Provider</th>
                <th className="p-3 font-medium text-cyan-400 whitespace-nowrap">Pass rate</th>
                <th className="p-3 font-medium whitespace-nowrap">Pass^k</th>
                <th className="p-3 font-medium whitespace-nowrap">95% CI</th>
                <th className="p-3 font-medium text-amber-400 whitespace-nowrap">Cost/task</th>
                <th className="p-3 font-medium whitespace-nowrap">Latency p50/p95</th>
                <th className="p-3 font-medium whitespace-nowrap">Trials</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, idx) => (
                <tr
                  key={e.run_id}
                  className={`border-b border-gray-800/50 hover:bg-gray-800/40 transition-colors ${idx % 2 === 1 ? 'bg-gray-800/20' : ''}`}
                >
                  <td className="p-3 text-gray-500 font-mono text-sm">#{e.rank}</td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <span className="text-white font-medium whitespace-nowrap">
                        {e.config_name ?? e.run_id.slice(0, 8)}
                      </span>
                      {e.self_moa && (
                        <span className="text-xs text-purple-400 bg-purple-400/10 border border-purple-400/25 rounded px-1.5 py-0.5">
                          Self-MoA
                        </span>
                      )}
                      {e.on_pareto_frontier && (
                        <span className="text-xs text-amber-400 bg-amber-400/10 border border-amber-400/25 rounded px-1.5 py-0.5">
                          Pareto
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="p-3 text-gray-400 text-xs whitespace-nowrap">{e.benchmark_suite}</td>
                  <td className="p-3 text-gray-400 text-xs whitespace-nowrap">{e.provider ?? '—'}</td>
                  <td className="p-3">
                    <span className="text-cyan-400 font-semibold font-mono tabular-nums">
                      {fmtPct(e.pass_rate)}
                    </span>
                  </td>
                  <td className="p-3 text-gray-300 tabular-nums whitespace-nowrap">{fmtPct(e.pass_hat_k)}</td>
                  <td className="p-3 text-gray-500 text-xs tabular-nums whitespace-nowrap">
                    {e.ci95_low != null && e.ci95_high != null
                      ? `${Number(e.ci95_low).toFixed(0)}–${Number(e.ci95_high).toFixed(0)}%`
                      : '—'}
                  </td>
                  <td className="p-3 text-amber-400 tabular-nums whitespace-nowrap">
                    {fmtCost(e.cost_usd_per_task)}
                  </td>
                  <td className="p-3 text-gray-400 text-xs tabular-nums whitespace-nowrap">
                    {e.latency_p50_ms != null ? `${e.latency_p50_ms}` : '—'}
                    {' / '}
                    {e.latency_p95_ms != null ? `${e.latency_p95_ms}ms` : '—'}
                  </td>
                  <td className="p-3 text-gray-500 text-xs tabular-nums whitespace-nowrap">
                    {e.n_tasks}×{e.n_trials}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
