import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Trophy, Zap, DollarSign, Gem } from 'lucide-react';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { api } from '../api';
import type { AgentLeaderboardEntry, KnownModel } from '../api';
import {
  Card, CardHeader, PageHeader, Badge, Select, Skeleton, EmptyState, ErrorState, CIBar,
} from '../components/ui';
import { TooltipCard, axisProps, fmtPct } from '../components/chart';
import {
  formatScorecard,
  formatScorecardLabel,
  tierChromeClass,
} from '../lib/scorecard.js';

const num = (v: number | string | null | undefined) => (v === null || v === undefined ? null : Number(v));

/** Chart palette for the Multiplayer Cabinet — mirrors Solo Cabinet chrome. */
const ARCADE_CHART = {
  accent: '#39f3ff',
  frontier: '#ffd166',
  line: '#2a3555',
  ink3: '#6b7594',
  grid: '#1a2238',
};

// Cost display keeps sub-cent precision for near-free configs, otherwise 3 dp.
function fmtCost(v: number | null): string {
  if (v == null) return '—';
  // Decimal fields serialize as JSON strings (pydantic), not numbers — coerce
  // before formatting or .toFixed() throws on a string at render time.
  const n = Number(v);
  return n < 0.01 ? `$${n.toFixed(4)}` : `$${n.toFixed(3)}`;
}

function ArcadeFrontierDot(props: {
  cx?: number; cy?: number; payload?: { on_pareto_frontier?: boolean };
}) {
  const { cx, cy, payload } = props;
  if (cx === undefined || cy === undefined) return null;
  const on = payload?.on_pareto_frontier;
  return on ? (
    <g>
      <circle cx={cx} cy={cy} r={7} fill={ARCADE_CHART.frontier} fillOpacity={0.2} />
      <circle cx={cx} cy={cy} r={4} fill={ARCADE_CHART.frontier} stroke="#12182a" strokeWidth={1.5} />
    </g>
  ) : (
    <circle cx={cx} cy={cy} r={4} fill={ARCADE_CHART.accent} fillOpacity={0.9} stroke="#12182a" strokeWidth={1.5} />
  );
}

// Cost-vs-score scatter point. Arcade dot chrome keys off on_pareto_frontier.
interface ParetoPoint {
  cost: number;
  pass: number;
  name: string;
  on_pareto_frontier: boolean;
  self_moa: boolean;
}

// PinchBench-style "quick pick" badges — computed client-side off the same
// leaderboard data, so a viewer gets an instant recommendation without reading
// the whole table. Only entries with a cost figure count for cost/value picks.
interface QuickPick {
  label: string;
  entry: AgentLeaderboardEntry;
  detail: string;
  icon: typeof Trophy;
  tint: string;
}

function computeQuickPicks(entries: AgentLeaderboardEntry[]): QuickPick[] {
  if (entries.length === 0) return [];
  const priced = entries.filter(e => e.cost_usd_per_task != null);
  const picks: QuickPick[] = [];

  const mostAccurate = [...entries].sort((a, b) => Number(b.pass_rate) - Number(a.pass_rate))[0];
  picks.push({
    label: 'Top score',
    entry: mostAccurate,
    detail: formatScorecardLabel(mostAccurate.pass_rate),
    icon: Trophy,
    tint: 'text-accent bg-accent-soft',
  });

  const withLatency = entries.filter(e => e.latency_p50_ms != null);
  if (withLatency.length > 0) {
    const fastest = [...withLatency].sort((a, b) => (a.latency_p50_ms ?? 0) - (b.latency_p50_ms ?? 0))[0];
    picks.push({
      label: 'Fastest',
      entry: fastest,
      detail: `${fastest.latency_p50_ms}ms p50`,
      icon: Zap,
      tint: 'text-frontier bg-frontier-soft',
    });
  }

  if (priced.length > 0) {
    const cheapest = [...priced].sort((a, b) => (a.cost_usd_per_task ?? 0) - (b.cost_usd_per_task ?? 0))[0];
    picks.push({
      label: 'Cheapest',
      entry: cheapest,
      detail: fmtCost(cheapest.cost_usd_per_task),
      icon: DollarSign,
      tint: 'text-pass bg-pass-soft',
    });

    // Value = accuracy per dollar. Guards against a free/near-zero-cost entry
    // dominating by division blow-up.
    const bestValue = [...priced].sort((a, b) => {
      const va = Number(a.pass_rate) / Math.max(Number(a.cost_usd_per_task), 1e-6);
      const vb = Number(b.pass_rate) / Math.max(Number(b.cost_usd_per_task), 1e-6);
      return vb - va;
    })[0];
    picks.push({
      label: 'Best value',
      entry: bestValue,
      detail: `${formatScorecardLabel(bestValue.pass_rate)} @ ${fmtCost(bestValue.cost_usd_per_task)}`,
      icon: Gem,
      tint: 'text-accent-strong bg-accent-soft',
    });
  }

  return picks;
}

export default function Agents() {
  const [entries, setEntries] = useState<AgentLeaderboardEntry[]>([]);
  const [newModels, setNewModels] = useState<KnownModel[]>([]);
  const [sortBy, setSortBy] = useState('pass_rate');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api.getAgentLeaderboard({ sort_by: sortBy })
      .then(setEntries)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [sortBy]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  useEffect(() => {
    api.getNewModels().then(setNewModels).catch(() => setNewModels([]));
  }, []);

  const paretoData: ParetoPoint[] = entries
    .filter(e => e.cost_usd_per_task != null)
    .map(e => ({
      cost: Number(e.cost_usd_per_task),
      pass: Number(e.pass_rate),
      name: e.config_name ?? e.run_id.slice(0, 8),
      on_pareto_frontier: e.on_pareto_frontier,
      self_moa: e.self_moa,
    }));

  const quickPicks = computeQuickPicks(entries);

  return (
    <div className="arcade-cabinet space-y-8">
      <PageHeader eyebrow="Multiplayer Cabinet" title="MoA scorecards, on the frontier">
        Multi-agent and agentic configs ranked by tier · score on contamination-resistant tasks.
        Confidence bars stay underneath for receipts; the gold Pareto frontier still marks the
        configs that earn their quarters.
      </PageHeader>

      {newModels.length > 0 && (
        <Card className="animate-rise rise-1 flex flex-wrap items-baseline gap-x-2 gap-y-1 px-5 py-4">
          <span className="text-[13px] font-semibold text-frontier">
            {newModels.length} new model{newModels.length > 1 ? 's' : ''} — not yet benchmarked:
          </span>
          <span className="text-[13px] text-ink-2">
            {newModels.slice(0, 5).map(m => m.display_name || m.model_id).join(', ')}
            {newModels.length > 5 ? ` +${newModels.length - 5} more` : ''}
          </span>
        </Card>
      )}

      {quickPicks.length > 0 && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {quickPicks.map(({ label, entry, detail, icon: Icon, tint }) => (
            <Link
              key={label}
              to={`/agents/runs/${entry.run_id}`}
              className="group flex items-start gap-3 rounded-xl border border-line bg-surface p-4 shadow-card transition-colors hover:border-line-strong"
            >
              <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${tint}`}>
                <Icon className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <div className="text-[11px] font-semibold uppercase tracking-[0.1em] text-ink-3">{label}</div>
                <div className="truncate text-[13px] font-medium text-ink group-hover:text-accent">
                  {entry.config_name ?? entry.run_id.slice(0, 8)}
                </div>
                <div className="tnum text-[12px] text-ink-2">{detail}</div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {loading ? (
        <Skeleton rows={8} />
      ) : error ? (
        <ErrorState onRetry={load}>{error}</ErrorState>
      ) : entries.length === 0 ? (
        <EmptyState title="No agent runs yet">
          Publish a run via <code className="text-accent">agentbench.run</code> and it appears here
          on the cost-vs-accuracy frontier.
        </EmptyState>
      ) : (
        <>
          {/* Signature chart: Cost vs Accuracy Pareto frontier. */}
          <Card className="animate-rise rise-2">
            <CardHeader
              title="Score vs. $/quarter"
              sub="Tier score vs. cost per task. Up is stronger; left is cheaper."
              right={<Badge tone="frontier">Gold = Pareto-optimal</Badge>}
            />
            <div className="px-2 pb-4">
              {paretoData.length === 0 ? (
                <div className="px-4 py-10 text-center text-[13px] text-ink-3">
                  No priced runs yet. Publish a run via{' '}
                  <code className="text-accent">agentbench.run</code>.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={380}>
                  <ScatterChart margin={{ top: 16, right: 32, bottom: 36, left: 8 }}>
                    <CartesianGrid stroke={ARCADE_CHART.grid} />
                    <XAxis
                      dataKey="cost" name="$/quarter" type="number" {...axisProps}
                      stroke={ARCADE_CHART.ink3}
                      tick={{ fill: ARCADE_CHART.ink3, fontSize: 11 }}
                      tickFormatter={(v: number) => `$${v}`}
                      label={{ value: '$/quarter (USD)', position: 'insideBottom', offset: -18, fill: ARCADE_CHART.ink3, fontSize: 12 }}
                    />
                    <YAxis
                      dataKey="pass" name="Score" type="number" domain={[0, 100]} {...axisProps}
                      stroke={ARCADE_CHART.ink3}
                      tick={{ fill: ARCADE_CHART.ink3, fontSize: 11 }}
                      label={{ value: 'Score', angle: -90, position: 'insideLeft', offset: 16, fill: ARCADE_CHART.ink3, fontSize: 12 }}
                    />
                    <Tooltip
                      cursor={{ stroke: ARCADE_CHART.line, strokeDasharray: '4 4' }}
                      content={({ payload }) => {
                        if (!payload?.length) return null;
                        const d = payload[0].payload as ParetoPoint;
                        return (
                          <TooltipCard>
                            <div className="font-semibold text-ink">
                              {d.name}
                              {d.self_moa && <span className="ml-1 text-[11px] text-accent-strong">(Self-MoA)</span>}
                            </div>
                            <div className="tnum mt-1 text-accent-strong">{formatScorecardLabel(d.pass)}</div>
                            <div className="tnum text-ink-2">{fmtCost(d.cost)}/quarter</div>
                            {d.on_pareto_frontier && <div className="mt-1 text-[11px] text-frontier">On Pareto frontier</div>}
                          </TooltipCard>
                        );
                      }}
                    />
                    <Scatter data={paretoData} shape={ArcadeFrontierDot} isAnimationActive={false} />
                  </ScatterChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>

          {/* Leaderboard table */}
          <div className="flex flex-wrap items-center gap-3">
            <Select label="Sort" value={sortBy} onChange={e => setSortBy(e.target.value)}>
              <option value="pass_rate">Pass rate</option>
              <option value="pass_hat_k">Pass^k (consistency)</option>
              <option value="cost_usd_per_task">$/quarter</option>
            </Select>
          </div>

          <Card className="animate-rise rise-3 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="arcade-highscore-table w-full text-left text-[13px]">
                <thead>
                  <tr className="text-[11px] uppercase tracking-wider">
                    <th className="py-3 pl-5 pr-2 font-semibold whitespace-nowrap text-ink-3">#</th>
                    <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">Config</th>
                    <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">Suite</th>
                    <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">Provider</th>
                    <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">Score · 95% CI</th>
                    <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">Pass^k</th>
                    <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">$/quarter</th>
                    <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">Latency p50/p95</th>
                    <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">Trials</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((e) => {
                    const card = formatScorecard(e.pass_rate);
                    return (
                      <tr key={e.run_id}>
                        <td className="arcade-rank tnum py-3 pl-5 pr-2 text-ink-3">#{e.rank}</td>
                        <td className="px-2 py-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <Link
                              to={`/agents/runs/${e.run_id}`}
                              className="font-medium text-ink whitespace-nowrap hover:text-accent"
                            >
                              {e.config_name ?? e.run_id.slice(0, 8)}
                            </Link>
                            {e.self_moa && (
                              <Badge tone="accent" title="Self-MoA — one model aggregating its own samples">Self-MoA</Badge>
                            )}
                            {e.on_pareto_frontier && (
                              <Badge tone="frontier" title="On the cost/accuracy Pareto frontier">Pareto</Badge>
                            )}
                          </div>
                          {e.model_snapshot_date && (
                            <div className="mt-0.5 text-[12px] text-ink-3">snapshot {e.model_snapshot_date}</div>
                          )}
                        </td>
                        <td className="px-2 py-3 text-[12px] text-ink-2 whitespace-nowrap">{e.benchmark_suite}</td>
                        <td className="px-2 py-3 text-[12px] text-ink-2 whitespace-nowrap">{e.provider ?? '—'}</td>
                        <td className="px-2 py-3 min-w-[200px]">
                          <div className={`arcade-score ${tierChromeClass(card.tierId)}`}>
                            {formatScorecardLabel(e.pass_rate)}
                          </div>
                          <CIBar value={Number(e.pass_rate)} lo={num(e.ci95_low)} hi={num(e.ci95_high)} />
                        </td>
                        <td className="tnum px-2 py-3 text-ink-2 whitespace-nowrap">{fmtPct(e.pass_hat_k)}</td>
                        <td className="tnum px-2 py-3 text-ink-2 whitespace-nowrap">{fmtCost(e.cost_usd_per_task)}</td>
                        <td className="tnum px-2 py-3 text-[12px] text-ink-2 whitespace-nowrap">
                          {e.latency_p50_ms != null ? `${e.latency_p50_ms}` : '—'}
                          {' / '}
                          {e.latency_p95_ms != null ? `${e.latency_p95_ms}ms` : '—'}
                        </td>
                        <td className="tnum px-2 py-3 text-[12px] text-ink-3 whitespace-nowrap">
                          {e.n_tasks}×{e.n_trials}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
