import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { api } from '../api';
import type { ModelLeaderboardEntry, KnownModel } from '../api';
import { consumeLegacyLeaderboardNotice } from './LegacyLeaderboardRedirect';
import {
  Card, CardHeader, PageHeader, Badge, ValidityBadge, Skeleton, EmptyState, ErrorState,
  CIBar, Select, SortableTh,
} from '../components/ui';
import { CHART, FrontierDot, TooltipCard, axisProps, fmtPct } from '../components/chart';
import {
  CABINET_OPTIONS,
  DEFAULT_CABINET_SUITE,
  categoryDisplayName,
  formatScorecardLabel,
  cabinetForSuite,
  orderCategoryKeys,
} from '../lib/scorecard.js';

const num = (v: number | string | null | undefined) => (v === null || v === undefined ? null : Number(v));
const fmtCost = (c: number | null) => (c == null ? '—' : c < 0.01 ? `$${c.toFixed(4)}` : `$${c.toFixed(3)}`);

const SUITE_OPTIONS = [
  ...CABINET_OPTIONS.map((c) => ({
    value: c.suite,
    label: `${c.label} · ${c.season}`,
  })),
  { value: '', label: 'All cabinets' },
] as const;

type SortKey = 'pass_rate' | 'pass_hat_k' | 'cost_usd_per_task' | string;
type SortDir = 'asc' | 'desc';

function sortValue(e: ModelLeaderboardEntry, key: SortKey): number {
  if (key === 'pass_rate') return Number(e.pass_rate);
  if (key === 'pass_hat_k') return Number(e.pass_hat_k ?? -1);
  if (key === 'cost_usd_per_task') return Number(e.cost_usd_per_task ?? Number.POSITIVE_INFINITY);
  return e.category_pass_rates[key] ?? -1;
}

function LicenseBadge({ license }: { license: string | null }) {
  if (!license) return null;
  return <Badge tone={license === 'open' ? 'pass' : 'neutral'}>{license}</Badge>;
}

interface Point {
  name: string;
  family: string | null;
  cost: number;
  pass: number;
  on_pareto_frontier: boolean;
}

export default function Models() {
  const [entries, setEntries] = useState<ModelLeaderboardEntry[]>([]);
  const [newModels, setNewModels] = useState<KnownModel[]>([]);
  const [suite, setSuite] = useState(DEFAULT_CABINET_SUITE);
  const [sortKey, setSortKey] = useState<SortKey>('pass_rate');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [chartMetric, setChartMetric] = useState<string>('pass_rate');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [legacyNotice, setLegacyNotice] = useState(false);

  useEffect(() => {
    if (consumeLegacyLeaderboardNotice()) setLegacyNotice(true);
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    const params: Record<string, string> = {};
    if (suite) params.suite = suite;
    Promise.all([
      api.getModelLeaderboard(params).then(setEntries),
      api.getNewModels().then(setNewModels).catch(() => setNewModels([])),
    ]).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [suite]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const categories = useMemo(
    () => orderCategoryKeys(entries.flatMap((e) => Object.keys(e.category_pass_rates))),
    [entries],
  );

  const activeCabinet = cabinetForSuite(suite);

  const sortedEntries = useMemo(() => {
    const copy = [...entries];
    copy.sort((a, b) => {
      const diff = sortValue(a, sortKey) - sortValue(b, sortKey);
      return sortDir === 'asc' ? diff : -diff;
    });
    return copy.map((e, i) => ({ ...e, rank: i + 1 }));
  }, [entries, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortKey(key);
      setSortDir(key === 'cost_usd_per_task' ? 'asc' : 'desc');
    }
  };

  const chartPass = (e: ModelLeaderboardEntry) =>
    chartMetric === 'pass_rate'
      ? Number(e.pass_rate)
      : (e.category_pass_rates[chartMetric] ?? 0);

  const points: Point[] = sortedEntries
    .filter((e) => e.cost_usd_per_task != null)
    .map((e) => ({
      name: e.display_name ?? e.model_string,
      family: e.family,
      cost: Number(e.cost_usd_per_task),
      pass: chartPass(e),
      on_pareto_frontier: e.on_pareto_frontier,
    }));

  const isPro = entries.some((e) => e.benchmark_suite?.includes('pro'));
  const hasCalib = entries.some((e) => e.calibration_brier != null);
  const hasRobust = entries.some((e) => e.robustness_correct != null);

  const saturatedCount = entries.filter((e) => Number(e.pass_rate) >= 99.9).length;
  const showSaturation =
    (suite === 'minibench-core-v1' || suite === '') &&
    entries.length >= 3 &&
    saturatedCount / entries.length >= 0.3;

  const chartMetricLabel =
    chartMetric === 'pass_rate' ? 'Score' : categoryDisplayName(chartMetric);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Solo Cabinet"
        title={activeCabinet ? `${activeCabinet.label} · ${activeCabinet.season}` : 'Model scorecard'}
      >
        Scores that spread models apart on work you&apos;d actually do — tier · score on the active
        cabinet, with 95% CI bars underneath. When two bars overlap, it&apos;s a tie, not a winner.
      </PageHeader>

      {legacyNotice && (
        <Card className="border-accent/30 bg-accent-soft/40 px-5 py-4">
          <p className="text-[13px] text-ink">
            The hardware throughput leaderboard has been retired — too many uncontrolled variables
            (machine × engine × quantization × model) made rows incomparable. Model capability
            scores on pinned reference profiles are now the primary ranking. Reference rig docs
            live on <Link to="/hardware" className="text-accent hover:text-accent-strong font-medium">Test Rigs</Link>.
          </p>
          <button
            type="button"
            onClick={() => setLegacyNotice(false)}
            className="mt-2 text-xs text-ink-3 hover:text-ink transition-colors"
          >
            Dismiss
          </button>
        </Card>
      )}

      <div className="flex flex-wrap items-end gap-4">
        <Select label="Cabinet" value={suite} onChange={(e) => setSuite(e.target.value)}>
          {SUITE_OPTIONS.map((o) => (
            <option key={o.value || 'all'} value={o.value}>{o.label}</option>
          ))}
        </Select>
        <Select label="Chart Y-axis" value={chartMetric} onChange={(e) => setChartMetric(e.target.value)}>
          <option value="pass_rate">Score</option>
          {categories.map((c) => (
            <option key={c} value={c}>{categoryDisplayName(c)}</option>
          ))}
        </Select>
      </div>

      {showSaturation && (
        <Card className="border-frontier/40 bg-frontier-soft/30 px-5 py-4">
          <p className="text-[13px] text-ink">
            <span className="font-semibold text-frontier">core-v1 is saturated</span>
            {' '}— {saturatedCount} of {entries.length} models score ≥99.9%.
            Switch to <strong>minibench-v2</strong> for frontier separation, or sort by category
            below to see where models still differ.
          </p>
        </Card>
      )}

      {loading ? (
        <Skeleton rows={8} />
      ) : error ? (
        <ErrorState onRetry={load}>{error}</ErrorState>
      ) : entries.length === 0 ? (
        <EmptyState title="No published runs for this suite yet">
          {suite === 'minibench-v2'
            ? 'Publish Season 2 runs with agentbench.run --tasks agentbench/tasks/minibench-v2.json to populate the cabinet.'
            : 'Score a model and publish it, then it appears here on the Solo Cabinet leaderboard.'}
        </EmptyState>
      ) : (
        <>
          <Card className="animate-rise rise-1">
            <CardHeader
              title="Capability vs. cost"
              sub={`Each point is a model. Up is higher ${chartMetricLabel}; left is cheaper.`}
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
                    label={{ value: `${chartMetricLabel} (%)`, angle: -90, position: 'insideLeft', offset: 16, fill: CHART.ink3, fontSize: 12 }}
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
                          <div className="tnum mt-1 text-accent-strong">{fmtPct(d.pass)} {chartMetricLabel}</div>
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

          <Card className="animate-rise rise-2 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[13px]">
                <thead>
                  <tr className="border-b border-line text-[11px] uppercase tracking-wider">
                    <th className="py-3 pl-5 pr-2 font-semibold text-ink-3">#</th>
                    <th className="px-2 py-3 font-semibold text-ink-3">Model</th>
                    <SortableTh
                      label="Score · 95% CI"
                      active={sortKey === 'pass_rate'}
                      dir={sortDir}
                      onClick={() => toggleSort('pass_rate')}
                      className="px-2 py-3"
                    />
                    <SortableTh
                      label="Pass^k"
                      active={sortKey === 'pass_hat_k'}
                      dir={sortDir}
                      onClick={() => toggleSort('pass_hat_k')}
                      className="px-2 py-3"
                    />
                    {hasCalib && <th className="px-2 py-3 font-semibold text-ink-3" title="Calibration Brier — lower is better">Calib.</th>}
                    {hasRobust && <th className="px-2 py-3 font-semibold text-ink-3" title="Robustness — solved on both sides of a perturbation">Robust.</th>}
                    {categories.map((c) => (
                      <SortableTh
                        key={c}
                        label={categoryDisplayName(c)}
                        active={sortKey === c}
                        dir={sortDir}
                        onClick={() => toggleSort(c)}
                        className="px-2 py-3"
                      />
                    ))}
                    <SortableTh
                      label="Cost/task"
                      active={sortKey === 'cost_usd_per_task'}
                      dir={sortDir}
                      onClick={() => toggleSort('cost_usd_per_task')}
                      className="px-2 py-3"
                    />
                    <th className="px-2 py-3 font-semibold text-ink-3">Validity</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedEntries.map((e, i) => (
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
                      <td className="px-2 py-3 min-w-[180px]">
                        <div className="font-medium text-ink">{formatScorecardLabel(e.pass_rate)}</div>
                        <CIBar value={Number(e.pass_rate)} lo={num(e.ci95_low)} hi={num(e.ci95_high)} />
                      </td>
                      <td className="tnum px-2 py-3 text-ink-2">{e.pass_hat_k != null ? fmtPct(e.pass_hat_k) : '—'}</td>
                      {hasCalib && <td className="tnum px-2 py-3 text-ink-2">{e.calibration_brier != null ? Number(e.calibration_brier).toFixed(3) : '—'}</td>}
                      {hasRobust && <td className="tnum px-2 py-3 text-ink-2">{e.robustness_correct != null ? fmtPct(Number(e.robustness_correct) * 100) : '—'}</td>}
                      {categories.map((c) => (
                        <td key={c} className={`tnum px-2 py-3 ${sortKey === c ? 'text-accent font-medium' : 'text-ink-2'}`}>
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
