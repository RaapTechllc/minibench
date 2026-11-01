import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { api } from '../api';
import type { ModelLeaderboardEntry, KnownModel } from '../api';
import { consumeLegacyLeaderboardNotice } from '../lib/legacyNotice';
import { heatBand, compositeScore } from '../lib/scoreScale';
import {
  Card, CardHeader, PageHeader, Badge, ValidityBadge, Skeleton, EmptyState, ErrorState,
  CIBar, Select, SortableTh,
} from '../components/ui';
import { axisProps, fmtPct, TooltipCard } from '../components/chart';
import {
  BENCHMARK_SUITE_OPTIONS,
  DEFAULT_FEATURED_SUITE,
  SATURATION_THRESHOLD,
  categoryDisplayName,
  evaluateSaturation,
  suiteMetadata,
  orderCategoryKeys,
} from '../lib/scorecard.js';

const num = (v: number | string | null | undefined) => (v === null || v === undefined ? null : Number(v));
const fmtCost = (c: number | null) => {
  if (c == null) return '—';
  if (c === 0) return '$0';
  if (c < 0.0001) return `$${c.toFixed(6)}`;
  if (c < 0.01) return `$${c.toFixed(4)}`;
  return `$${c.toFixed(2)}`;
};
const attemptCost = (entry: ModelLeaderboardEntry): number | null => {
  if (entry.cost_usd_per_attempt != null) return Number(entry.cost_usd_per_attempt);
  const benchmarkItemCost = num(entry.cost_usd_per_task);
  const trials = Number(entry.n_trials);
  return benchmarkItemCost != null && Number.isFinite(trials) && trials > 0
    ? benchmarkItemCost / trials
    : null;
};
const MANUAL_SUITE_OVERRIDE_KEY = 'minibench.suite.override';
const SEASON_2_SUITE = 'minibench-v2';

/** High-contrast chart palette for the daylight research surface. */
const CHART = {
  accent: '#0b5cad',
  frontier: '#147d55',
  line: '#aebbc7',
  ink3: '#667788',
  grid: '#e5eaee',
};

function FrontierDot(props: {
  cx?: number; cy?: number; payload?: { on_pareto_frontier?: boolean };
}) {
  const { cx, cy, payload } = props;
  if (cx === undefined || cy === undefined) return null;
  const on = payload?.on_pareto_frontier;
  return on ? (
    <g>
      <circle cx={cx} cy={cy} r={7} fill={CHART.frontier} fillOpacity={0.2} />
      <circle cx={cx} cy={cy} r={4} fill={CHART.frontier} stroke="#ffffff" strokeWidth={1.5} />
    </g>
  ) : (
    <circle cx={cx} cy={cy} r={4} fill={CHART.accent} fillOpacity={0.9} stroke="#ffffff" strokeWidth={1.5} />
  );
}

type SuiteOption = (typeof BENCHMARK_SUITE_OPTIONS)[number];

const suiteOptionLabel = (suiteOption: SuiteOption) => {
  if (suiteOption.suite === 'minibench-core-v1') {
    return `${suiteOption.label} · ${suiteOption.season} · optional`;
  }
  if (suiteOption.label === suiteOption.season) return suiteOption.label;
  return `${suiteOption.label} · ${suiteOption.season}`;
};

const readManualSuiteOverride = () => {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(MANUAL_SUITE_OVERRIDE_KEY);
};

const initialSuite = () => readManualSuiteOverride() ?? DEFAULT_FEATURED_SUITE;

const SUITE_OPTIONS = [
  ...BENCHMARK_SUITE_OPTIONS.map((c) => ({
    value: c.suite,
    label: suiteOptionLabel(c),
  })),
  { value: '', label: 'All suites' },
] as const;

type SortKey = 'pass_rate' | 'pass_hat_k' | 'cost_usd_per_attempt' | string;
type SortDir = 'asc' | 'desc';

function sortValue(e: ModelLeaderboardEntry, key: SortKey): number {
  if (key === 'pass_rate') return Number(e.pass_rate);
  if (key === 'pass_hat_k') return Number(e.pass_hat_k ?? -1);
  if (key === 'cost_usd_per_attempt') return attemptCost(e) ?? Number.POSITIVE_INFINITY;
  if (key === 'composite') return compositeScore(e.category_pass_rates) ?? -1;
  return e.category_pass_rates[key] ?? -1;
}

const HEAT_LEGEND = [
  { range: '85–100', sample: 92 },
  { range: '70–84', sample: 77 },
  { range: '55–69', sample: 62 },
  { range: '40–54', sample: 47 },
  { range: '<40', sample: 20 },
] as const;

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
  const [suite, setSuite] = useState(initialSuite);
  const [hasManualSuiteOverride, setHasManualSuiteOverride] = useState(
    () => readManualSuiteOverride() !== null,
  );
  const [advancedSuiteAvailable, setAdvancedSuiteAvailable] = useState(false);
  // One-shot: if the default suite has no published runs yet, widen to all
  // suites instead of opening on an empty page. A ref (read at response time,
  // set synchronously on any user choice or prior widen) rather than state,
  // so a stale in-flight response can never override the user's selection.
  const suitePinned = useRef(false);
  const [sortKey, setSortKey] = useState<SortKey>('pass_rate');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [chartMetric, setChartMetric] = useState<string>('pass_rate');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Lazy initializer: consume the one-shot flag during first render, no effect.
  const [legacyNotice, setLegacyNotice] = useState(() => consumeLegacyLeaderboardNotice());

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    const params: Record<string, string> = {};
    if (suite) params.suite = suite;
    Promise.all([
      api.getModelLeaderboard(params).then((list) => {
        // Covers both the default suite and an automatic promotion landing on
        // a board with no published runs yet — widen to all suites rather
        // than open empty. Never fires over a user's own suite choice.
        if (list.length === 0 && !suitePinned.current && !hasManualSuiteOverride) {
          suitePinned.current = true;
          setSuite('');
          return;
        }
        setEntries(list);
      }),
      api.getNewModels().then(setNewModels).catch(() => setNewModels([])),
    ]).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [suite, hasManualSuiteOverride]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const saturationState = evaluateSaturation(entries);

  useEffect(() => {
    if (suite !== DEFAULT_FEATURED_SUITE || saturationState !== 'promote') return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAdvancedSuiteAvailable(true);
    if (!hasManualSuiteOverride) {
      setSuite(SEASON_2_SUITE);
    }
  }, [hasManualSuiteOverride, saturationState, suite]);

  const categories = useMemo(
    () => orderCategoryKeys(entries.flatMap((e) => Object.keys(e.category_pass_rates))),
    [entries],
  );

  const activeSuite = suiteMetadata(suite);

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
      setSortDir(key === 'cost_usd_per_attempt' ? 'asc' : 'desc');
    }
  };

  const chartPass = (e: ModelLeaderboardEntry) =>
    chartMetric === 'pass_rate'
      ? Number(e.pass_rate)
      : (e.category_pass_rates[chartMetric] ?? 0);

  const points: Point[] = sortedEntries
    .filter((e) => attemptCost(e) != null)
    .map((e) => ({
      name: e.display_name ?? e.model_string,
      family: e.family,
      cost: attemptCost(e)!,
      pass: chartPass(e),
      on_pareto_frontier: e.on_pareto_frontier,
    }));

  const isPro = entries.some((e) => e.benchmark_suite?.includes('pro'));
  const hasCalib = entries.some((e) => e.calibration_brier != null);
  const hasRobust = entries.some((e) => e.robustness_correct != null);
  const officialCount = entries.filter((e) => e.is_private_split).length;

  const showSaturation = advancedSuiteAvailable || (suite === DEFAULT_FEATURED_SUITE && saturationState === 'promote');
  const handleSuiteChange = (value: string) => {
    suitePinned.current = true;
    setSuite(value);
    setHasManualSuiteOverride(true);
    window.localStorage.setItem(MANUAL_SUITE_OVERRIDE_KEY, value);
  };

  const chartMetricLabel =
    chartMetric === 'pass_rate' ? 'Measured success' : categoryDisplayName(chartMetric);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Model research"
        title={activeSuite
          ? (activeSuite.label === activeSuite.season
            ? activeSuite.label
            : `${activeSuite.label} · ${activeSuite.season}`)
          : 'Model evidence'}
      >
        Measured task success, cost, latency, and uncertainty on pinned evaluation lanes. Confidence
        intervals are evidence—not decoration. When intervals overlap, MiniBench does not claim a winner.
      </PageHeader>

      {legacyNotice && (
        <Card className="border-accent/30 bg-accent-soft/40 px-5 py-4">
          <p className="text-[13px] text-ink">
            The hardware throughput leaderboard has been retired — too many uncontrolled variables
            (machine × engine × quantization × model) made rows incomparable. Model capability
            scores on pinned reference profiles are now the primary ranking. Reference rig docs
            live under <Link to="/hardware" className="text-accent hover:text-accent-strong font-medium">Deployment evidence</Link>.
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
        <Select label="Evaluation suite" value={suite} onChange={(e) => handleSuiteChange(e.target.value)}>
          {SUITE_OPTIONS.map((o) => (
            <option key={o.value || 'all'} value={o.value}>{o.label}</option>
          ))}
        </Select>
        <Select label="Chart Y-axis" value={chartMetric} onChange={(e) => setChartMetric(e.target.value)}>
          <option value="pass_rate">Measured success</option>
          {categories.map((c) => (
            <option key={c} value={c}>{categoryDisplayName(c)}</option>
          ))}
        </Select>
      </div>

      {showSaturation && (
        <Card className="border-frontier/40 bg-frontier-soft/30 px-5 py-4">
          <p className="text-[13px] text-ink">
            <span className="font-semibold text-frontier">The current suite is saturated.</span>
            {' '}More than {Math.round(SATURATION_THRESHOLD * 100)}% of measured models cleared the
            saturation threshold, so new visitors now start on <strong>minibench-v2</strong>. You can
            still select any historical suite for regression research.
          </p>
        </Card>
      )}

      {!loading && !error && entries.length > 0 && officialCount === 0 && (
        <Card className="border-frontier/30 bg-frontier-soft/20 px-5 py-4">
          <p className="text-[13px] text-ink">
            <strong>Development evidence only.</strong> This suite currently contains public dev-slice runs and no private-split official run. Use the rows to inspect coverage and economics, not to make a formal winner claim.
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
            ? 'Publish v2 runs with agentbench.run --tasks agentbench/tasks/minibench-v2.json to populate this lane.'
            : 'Score and publish a model on this pinned suite to add comparable evidence.'}
        </EmptyState>
      ) : (
        <>
          <Card className="animate-rise rise-1">
            <CardHeader
              title="Capability vs. cost"
              sub={`Each point is a model. Up is higher ${chartMetricLabel}; left is cheaper.`}
              right={<Badge tone="frontier">Highlighted = Pareto frontier</Badge>}
            />
            <div className="px-2 pb-4">
              <ResponsiveContainer width="100%" height={380}>
                <ScatterChart margin={{ top: 16, right: 32, bottom: 36, left: 8 }}>
                  <CartesianGrid stroke={CHART.grid} />
                  <XAxis
                    dataKey="cost" name="Cost/attempt" type="number"
                    {...axisProps}
                    stroke={CHART.ink3}
                    tick={{ fill: CHART.ink3, fontSize: 11 }}
                    tickFormatter={(v: number) => `$${v}`}
                    label={{ value: 'Cost per attempt (USD)', position: 'insideBottom', offset: -18, fill: CHART.ink3, fontSize: 12 }}
                  />
                  <YAxis
                    dataKey="pass" name="Pass rate" type="number" domain={[0, 100]}
                    {...axisProps}
                    stroke={CHART.ink3}
                    tick={{ fill: CHART.ink3, fontSize: 11 }}
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
                          <div className="tnum text-ink-2">{fmtCost(d.cost)}/attempt</div>
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
                  <tr className="text-[11px] uppercase tracking-wider">
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
                    <SortableTh
                      label="Composite"
                      title="Equal-weight mean of the category pass rates — every category counts the same, so specializing in one can't game the number"
                      active={sortKey === 'composite'}
                      dir={sortDir}
                      onClick={() => toggleSort('composite')}
                      className="px-2 py-3"
                    />
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
                      label="Cost/attempt"
                      active={sortKey === 'cost_usd_per_attempt'}
                      dir={sortDir}
                      onClick={() => toggleSort('cost_usd_per_attempt')}
                      className="px-2 py-3"
                    />
                    <th className="px-2 py-3 font-semibold text-ink-3">Validity</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedEntries.map((e) => {
                    return (
                      <tr key={e.model_string}>
                        <td className="tnum py-3 pl-5 pr-2 text-ink-3">{e.rank}</td>
                        <td className="px-2 py-3">
                          <div className="flex items-center gap-2">
                            <Link to={`/agents/runs/${e.run_id}`} className="font-medium text-ink hover:text-accent">
                              {e.display_name ?? e.model_string}
                            </Link>
                            {e.on_pareto_frontier && <Badge tone="frontier">Pareto</Badge>}
                            <LicenseBadge license={e.license} />
                          </div>
                          {e.family && <div className="text-[12px] text-ink-3">{e.family}</div>}
                        </td>
                        <td className="px-2 py-3 min-w-[200px]">
                          <div className="tnum text-[13px] font-semibold text-ink">{fmtPct(e.pass_rate)} measured success</div>
                          <CIBar value={Number(e.pass_rate)} lo={num(e.ci95_low)} hi={num(e.ci95_high)} />
                        </td>
                        <td className="tnum px-2 py-3 text-ink-2">{e.pass_hat_k != null ? fmtPct(e.pass_hat_k) : '—'}</td>
                        {hasCalib && <td className="tnum px-2 py-3 text-ink-2">{e.calibration_brier != null ? Number(e.calibration_brier).toFixed(3) : '—'}</td>}
                        {hasRobust && <td className="tnum px-2 py-3 text-ink-2">{e.robustness_correct != null ? fmtPct(Number(e.robustness_correct) * 100) : '—'}</td>}
                        <td className="px-2 py-3 min-w-[110px]">
                          {(() => {
                            const comp = compositeScore(e.category_pass_rates);
                            const band = heatBand(comp);
                            if (comp == null || band == null) return <span className="text-ink-3">—</span>;
                            return (
                              <div className="flex items-center gap-2" title={`Composite ${comp.toFixed(1)} — equal-weight mean of ${Object.keys(e.category_pass_rates).length} categories`}>
                                <span className="tnum w-10 text-right text-[13px] font-semibold" style={{ color: band.text }}>
                                  {comp.toFixed(1)}
                                </span>
                                <div className="relative h-1.5 min-w-[48px] flex-1 rounded-full bg-line">
                                  <div className="absolute inset-y-0 left-0 rounded-full"
                                    style={{ width: `${Math.max(2, Math.min(100, comp))}%`, backgroundColor: band.text }} />
                                </div>
                              </div>
                            );
                          })()}
                        </td>
                        {categories.map((c) => {
                          const v = e.category_pass_rates[c];
                          const band = heatBand(v);
                          return (
                            <td key={c} className="px-1 py-2">
                              <div
                                className={`tnum rounded-md px-2 py-1.5 text-center ${sortKey === c ? 'font-semibold' : ''}`}
                                style={band ? { backgroundColor: band.bg, color: band.text } : undefined}
                              >
                                {v != null ? `${v.toFixed(0)}%` : <span className="text-ink-3">—</span>}
                              </div>
                            </td>
                          );
                        })}
                        <td className="tnum px-2 py-3 text-ink-2">{fmtCost(attemptCost(e))}</td>
                        <td className="px-2 py-3"><ValidityBadge isPrivate={e.is_private_split} /></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-line/70 px-5 py-3 text-[11px] text-ink-3">
              <span className="font-medium text-ink-2">Category heat scale</span>
              {HEAT_LEGEND.map(({ range, sample }) => {
                const band = heatBand(sample)!;
                return (
                  <span key={range} className="inline-flex items-center gap-1.5">
                    <span className="inline-block h-3 w-3 rounded-sm" style={{ backgroundColor: band.bg, boxShadow: `inset 0 0 0 1px ${band.text}33` }} />
                    <span>{range}</span>
                  </span>
                );
              })}
              <span>· Composite = equal-weight category mean</span>
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
          <h2 className="text-[15px] font-semibold text-ink">Coverage gaps</h2>
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
