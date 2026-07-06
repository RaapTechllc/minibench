import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { api } from '../api';
import type { ModelLeaderboardEntry, KnownModel } from '../api';

interface Point {
  name: string;
  family: string | null;
  cost: number;
  pass: number;
  frontier: boolean;
}

const fmtCost = (c: number | null) =>
  c == null ? '—' : c < 0.01 ? `$${c.toFixed(4)}` : `$${c.toFixed(3)}`;

function FrontierDot(props: { cx?: number; cy?: number; payload?: Point }) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null || !payload) return null;
  return (
    <circle
      cx={cx} cy={cy} r={payload.frontier ? 7 : 5}
      fill={payload.frontier ? '#fbbf24' : '#22d3ee'}
      fillOpacity={payload.frontier ? 0.95 : 0.7}
      stroke={payload.frontier ? '#fde68a' : 'none'}
    />
  );
}

function LicenseBadge({ license }: { license: string | null }) {
  if (!license) return null;
  const open = license === 'open';
  return (
    <span className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded ${
      open ? 'bg-green-400/10 text-green-400' : 'bg-gray-700/60 text-gray-300'
    }`}>
      {license}
    </span>
  );
}

export default function Models() {
  const [entries, setEntries] = useState<ModelLeaderboardEntry[]>([]);
  const [newModels, setNewModels] = useState<KnownModel[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getModelLeaderboard().then(setEntries),
      api.getNewModels().then(setNewModels).catch(() => setNewModels([])),
    ]).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-gray-400">Loading...</div>;

  const points: Point[] = entries
    .filter(e => e.cost_usd_per_task != null)
    .map(e => ({
      name: e.display_name ?? e.model_string,
      family: e.family,
      cost: Number(e.cost_usd_per_task),
      pass: Number(e.pass_rate),
      frontier: e.on_pareto_frontier,
    }));

  const categories = Array.from(
    new Set(entries.flatMap(e => Object.keys(e.category_pass_rates))),
  ).sort();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Model Capability</h1>
        <p className="text-gray-400 mt-1">
          Best published minibench run per model — one model string, one call per prompt,
          on a pinned reference profile. Overlapping confidence intervals mean a tie, not a winner.
        </p>
      </div>

      {/* Capability vs cost — the headline chart of the pivot. */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-start justify-between mb-1">
          <h2 className="text-lg font-semibold text-white">Capability vs. Cost</h2>
          <span className="text-xs text-gray-500 mt-1">gold = Pareto-optimal</span>
        </div>
        {points.length === 0 ? (
          <div className="text-center py-10 text-gray-500 text-sm">
            No published single-model runs yet. Score one with{' '}
            <code className="text-cyan-400">python -m agentbench.run --model &lt;model&gt; --tasks agentbench/tasks/minibench-core-v1.json --publish &lt;api&gt;</code>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={380}>
            <ScatterChart margin={{ top: 20, right: 40, bottom: 40, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="cost" name="Cost/task" type="number" stroke="#6b7280"
                label={{ value: 'Cost per task (USD)', position: 'insideBottom', offset: -20, fill: '#9ca3af', fontSize: 12 }}
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickFormatter={(v: number) => `$${v}`}
              />
              <YAxis
                dataKey="pass" name="Pass rate" type="number" domain={[0, 100]} stroke="#6b7280"
                label={{ value: 'Pass rate (%)', angle: -90, position: 'insideLeft', offset: 15, fill: '#9ca3af', fontSize: 12 }}
                tick={{ fill: '#6b7280', fontSize: 11 }}
              />
              <Tooltip
                cursor={{ stroke: '#4b5563', strokeWidth: 1, strokeDasharray: '4 4' }}
                content={({ payload }) => {
                  if (!payload?.length) return null;
                  const d = payload[0].payload as Point;
                  return (
                    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm shadow-xl">
                      <div className="font-semibold text-white">{d.name}</div>
                      {d.family && <div className="text-gray-400 text-xs">{d.family}</div>}
                      <div className="text-cyan-400">{d.pass.toFixed(1)}% pass</div>
                      <div className="text-gray-400">{fmtCost(d.cost)}/task</div>
                      {d.frontier && <div className="text-amber-400 text-xs mt-1">On Pareto frontier</div>}
                    </div>
                  );
                }}
              />
              <Scatter data={points} shape={FrontierDot} />
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Leaderboard table */}
      {entries.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-gray-400 border-b border-gray-800 bg-gray-900/50">
              <tr>
                <th className="p-3">#</th>
                <th className="p-3">Model</th>
                <th className="p-3">Family</th>
                <th className="p-3 font-semibold text-cyan-400">Pass rate</th>
                <th className="p-3">95% CI</th>
                <th className="p-3">Pass^k</th>
                {categories.map(c => <th key={c} className="p-3 capitalize">{c}</th>)}
                <th className="p-3">Cost/task</th>
                <th className="p-3">p50 / p95</th>
                <th className="p-3">Suite</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(e => (
                <tr key={e.model_string} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="p-3 text-gray-400">{e.rank}</td>
                  <td className="p-3">
                    <Link to={`/agents/runs/${e.run_id}`} className="text-white font-medium hover:text-cyan-400">
                      {e.display_name ?? e.model_string}
                    </Link>
                    <span className="ml-2"><LicenseBadge license={e.license} /></span>
                    {e.on_pareto_frontier && <span className="ml-1 text-amber-400 text-xs">★</span>}
                  </td>
                  <td className="p-3 text-gray-400">{e.family ?? '—'}</td>
                  <td className="p-3 text-cyan-400 font-semibold">{Number(e.pass_rate).toFixed(1)}%</td>
                  <td className="p-3 text-gray-400 text-xs">
                    {e.ci95_low != null && e.ci95_high != null
                      ? `${Number(e.ci95_low).toFixed(0)}–${Number(e.ci95_high).toFixed(0)}%` : '—'}
                  </td>
                  <td className="p-3 text-gray-300">{e.pass_hat_k != null ? `${Number(e.pass_hat_k).toFixed(1)}%` : '—'}</td>
                  {categories.map(c => (
                    <td key={c} className="p-3 text-gray-300">
                      {e.category_pass_rates[c] != null ? `${e.category_pass_rates[c].toFixed(0)}%` : '—'}
                    </td>
                  ))}
                  <td className="p-3 text-gray-300">{fmtCost(e.cost_usd_per_task == null ? null : Number(e.cost_usd_per_task))}</td>
                  <td className="p-3 text-gray-400 text-xs">
                    {e.latency_p50_ms ?? '—'} / {e.latency_p95_ms ?? '—'} ms
                  </td>
                  <td className="p-3 text-gray-400 text-xs">{e.benchmark_suite}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Catalog: new, not yet benchmarked */}
      {newModels.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-1">New — not yet benchmarked</h2>
          <p className="text-sm text-gray-400 mb-4">
            Tracked in the master catalog (pinned OpenRouter ids) but without a published run yet.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {newModels.map(m => (
              <div key={m.id} className="border border-gray-800 rounded-lg p-3 bg-gray-950/40">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-white text-sm font-medium truncate">{m.display_name ?? m.model_id}</span>
                  <LicenseBadge license={m.license} />
                </div>
                <div className="text-xs text-gray-500 mt-1 truncate">{m.model_id}</div>
                <div className="text-xs text-gray-400 mt-1 flex gap-3">
                  {m.family && <span>{m.family}</span>}
                  {m.context_length != null && <span>{Math.round(m.context_length / 1024)}k ctx</span>}
                  {m.prompt_price != null && m.completion_price != null && (
                    <span>${(m.prompt_price * 1e6).toFixed(2)}/{(m.completion_price * 1e6).toFixed(2)} per M</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
