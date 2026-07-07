import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { api } from '../api';
import type { ModelLeaderboardEntry, KnownModel } from '../api';
import {
  Card, CardHeader, PageHeader, Badge, ValidityBadge, Skeleton, EmptyState, ErrorState, CIBar,
} from '../components/ui';
import { CHART, FrontierDot, TooltipCard, axisProps, fmtPct } from '../components/chart';

const num = (v: number | string | null | undefined) => (v === null || v === undefined ? null : Number(v));
const fmtCost = (c: number | null) => (c == null ? '—' : c < 0.01 ? `$${c.toFixed(4)}` : `$${c.toFixed(3)}`);

function LicenseBadge({ license }: { license: string | null }) {
  if (!license) return null;
  return <Badge tone={license === 'open' ? 'pass' : 'neutral'}>{license}</Badge>;
}

interface Point { name: string; family: string | null; cost: number; pass: number; on_pareto_frontier: boolean }

export default function Models() {
  const [entries, setEntries] = useState<ModelLeaderboardEntry[]>([]);
  const [newModels, setNewModels] = useState<KnownModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true); setError(null);
    Promise.all([
      api.getModelLeaderboard().then(setEntries),
      api.getNewModels().then(setNewModels).catch(() => setNewModels([])),
    ]).catch((e) => setError(e.message)).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const isPro = entries.some((e) => e.benchmark_suite?.includes('pro'));
  const hasCalib = entries.some((e) => e.calibration_brier != null);
  const hasRobust = entries.some((e) => e.robustness_correct != null);

  const points: Point[] = entries
    .filter((e) => e.cost_usd_per_task != null)
    .map((e) => ({
      name: e.display_name ?? e.model_string,
      family: e.family,
      cost: Number(e.cost_usd_per_task),
      pass: Number(e.pass_rate),
      on_pareto_frontier: e.on_pareto_frontier,
    }));

  const categories = Array.from(new Set(entries.flatMap((e) => Object.keys(e.category_pass_rates)))).sort();

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Capability leaderboard" title="Models, ranked by what they can do">
        Best published minibench run per model — one model string, one call per prompt, decoding
        pinned. Confidence intervals are shown as range bars: when two bars overlap, it's a tie,
        not a winner.
      </PageHeader>

      {loading ? (
        <Skeleton rows={8} />
      ) : error ? (
        <ErrorState onRetry={load}>{error}</ErrorState>
      ) : entries.length === 0 ? (
        <EmptyState title="No published model runs yet">
          Score a model and publish it, then it appears here on the capability-vs-cost frontier.
        </EmptyState>
      ) : (
        <>
          {/* Signature chart: capability vs cost, Pareto frontier in gold. */}
          <Card className="animate-rise rise-1">
            <CardHeader
              title="Capability vs. cost"
              sub="Each point is a model. Up is more capable; left is cheaper."
              right={<Badge tone="frontier">Gold = Pareto-optimal</Badge>}
            />
            <div className="px-2 pb-4">
              <ResponsiveContainer width="100%" height={380}>
                <ScatterChart margin={{ top: 16, right: 32, bottom: 36, left: 8 }}>
                  <CartesianGrid stroke={CHART.grid} />
                  <XAxis
                    dataKey="cost" name="Cost/task" type="number" {...axisProps}
                    tickFormatter={(v: number) => `$${v}`}
                    label={{ value: 'Cost per task (USD)', position: 'insideBottom', offset: -18, fill: CHART.ink3, fontSize: 12 }}
                  />
                  <YAxis
                    dataKey="pass" name="Pass rate" type="number" domain={[0, 100]} {...axisProps}
                    label={{ value: 'Pass rate (%)', angle: -90, position: 'insideLeft', offset: 16, fill: CHART.ink3, fontSize: 12 }}
                  />
                  <Tooltip
                    cursor={{ stroke: CHART.line, strokeDasharray: '4 4' }}
                    content={({ payload }) => {
                      if (!payload?.length) return null;
                      const d = payload[0].payload as Point;
                      return (
                        <TooltipCard>
                          <div className="font-semibold text-ink">{d.name}</div>
                          {d.family && <div className="text-ink-3">{d.family}</div>}
                          <div className="tnum mt-1 text-accent-strong">{fmtPct(d.pass)} pass</div>
                          <div className="tnum text-ink-2">{fmtCost(d.cost)}/task</div>
                          {d.on_pareto_frontier && <div className="mt-1 text-[11px] text-frontier">On Pareto frontier</div>}
                        </TooltipCard>
                      );
                    }}
                  />
                  <Scatter data={points} shape={FrontierDot} isAnimationActive={false} />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Leaderboard */}
          <Card className="animate-rise rise-2 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[13px]">
                <thead>
                  <tr className="border-b border-line text-[11px] uppercase tracking-wider text-ink-3">
                    <th className="py-3 pl-5 pr-2 font-semibold">#</th>
                    <th className="px-2 py-3 font-semibold">Model</th>
                    <th className="px-2 py-3 font-semibold">Pass rate · 95% CI</th>
                    <th className="px-2 py-3 font-semibold">Pass^k</th>
                    {hasCalib && <th className="px-2 py-3 font-semibold" title="Calibration Brier — lower is better">Calib.</th>}
                    {hasRobust && <th className="px-2 py-3 font-semibold" title="Robustness — solved on both sides of a perturbation">Robust.</th>}
                    {categories.map((c) => <th key={c} className="px-2 py-3 font-semibold capitalize">{c}</th>)}
                    <th className="px-2 py-3 font-semibold">Cost/task</th>
                    <th className="px-2 py-3 font-semibold">Validity</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((e, i) => (
                    <tr key={e.model_string}
                      className={`border-b border-line/70 transition-colors hover:bg-surface-2 ${i % 2 ? 'bg-surface-2/40' : ''}`}>
                      <td className="tnum py-3 pl-5 pr-2 text-ink-3">{e.rank}</td>
                      <td className="px-2 py-3">
                        <div className="flex items-center gap-2">
                          <Link to={`/agents/runs/${e.run_id}`} className="font-medium text-ink hover:text-accent">
                            {e.display_name ?? e.model_string}
                          </Link>
                          {e.on_pareto_frontier && <span className="text-frontier" title="Pareto-optimal">★</span>}
                          <LicenseBadge license={e.license} />
                        </div>
                        {e.family && <div className="text-[12px] text-ink-3">{e.family}</div>}
                      </td>
                      <td className="px-2 py-3 min-w-[160px]">
                        <CIBar value={Number(e.pass_rate)} lo={num(e.ci95_low)} hi={num(e.ci95_high)} />
                      </td>
                      <td className="tnum px-2 py-3 text-ink-2">{e.pass_hat_k != null ? fmtPct(e.pass_hat_k) : '—'}</td>
                      {hasCalib && <td className="tnum px-2 py-3 text-ink-2">{e.calibration_brier != null ? Number(e.calibration_brier).toFixed(3) : '—'}</td>}
                      {hasRobust && <td className="tnum px-2 py-3 text-ink-2">{e.robustness_correct != null ? fmtPct(Number(e.robustness_correct) * 100) : '—'}</td>}
                      {categories.map((c) => (
                        <td key={c} className="tnum px-2 py-3 text-ink-2">
                          {e.category_pass_rates[c] != null ? `${e.category_pass_rates[c].toFixed(0)}%` : '—'}
                        </td>
                      ))}
                      <td className="tnum px-2 py-3 text-ink-2">{fmtCost(num(e.cost_usd_per_task))}</td>
                      <td className="px-2 py-3"><ValidityBadge isPrivate={e.is_private_split} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {isPro && (hasCalib || hasRobust) && (
            <p className="text-[13px] text-ink-3">
              <span className="font-medium text-ink-2">Calib.</span> is the calibration Brier score
              (lower is better — does the model know what it knows?).{' '}
              <span className="font-medium text-ink-2">Robust.</span> is the share of perturbed task
              pairs solved correctly on both sides — resistance to rewording and distractors.
            </p>
          )}
        </>
      )}

      {/* Catalog: tracked but not yet benchmarked */}
      {!loading && newModels.length > 0 && (
        <Card className="p-6">
          <h2 className="text-[15px] font-semibold text-ink">New — not yet benchmarked</h2>
          <p className="mt-1 text-[13px] text-ink-2">
            Tracked in the master catalog (pinned OpenRouter ids) but without a published run yet.
          </p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {newModels.map((m) => (
              <div key={m.id} className="rounded-lg border border-line bg-surface-2/60 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-[13px] font-medium text-ink">{m.display_name ?? m.model_id}</span>
                  <LicenseBadge license={m.license} />
                </div>
                <div className="mt-1 truncate text-[12px] text-ink-3">{m.model_id}</div>
                <div className="mt-1 flex gap-3 text-[12px] text-ink-2">
                  {m.family && <span>{m.family}</span>}
                  {m.context_length != null && <span className="tnum">{Math.round(m.context_length / 1024)}k ctx</span>}
                  {m.prompt_price != null && m.completion_price != null && (
                    <span className="tnum">${(m.prompt_price * 1e6).toFixed(2)}/{(m.completion_price * 1e6).toFixed(2)} per M</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
