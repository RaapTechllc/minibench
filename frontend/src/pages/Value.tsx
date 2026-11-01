import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { ModelLeaderboardEntry } from '../api';
import {
  evaluateModel,
  evidenceStatus,
  paretoFrontier,
  premiumVerdict,
  rankByEconomicValue,
} from '../lib/valueMetrics.js';
import type { ModelEconomics, ValueScenario } from '../lib/valueMetrics.js';
import { ErrorState, Skeleton } from '../components/ui';

const SUITES = [
  { value: 'minibench-core-v1', label: 'Core v1 · broad coverage' },
  { value: 'minibench-hard-v1', label: 'Hard v1 · stronger separation' },
  { value: 'minibench-pro-v1', label: 'Pro v1 · calibration + robustness' },
];

const WORKLOADS = [
  { value: 'overall', label: 'Overall suite' },
  { value: 'coding', label: 'Coding' },
  { value: 'reasoning', label: 'Reasoning' },
  { value: 'tool-use', label: 'Tool use' },
  { value: 'structured-output', label: 'Structured output' },
];

const WORKLOAD_CATEGORY: Record<string, string> = {
  'structured-output': 'instruction',
};

const SOURCES = [
  {
    name: 'Artificial Analysis',
    role: 'Endpoint quality, price, and performance methodology',
    url: 'https://artificialanalysis.ai/methodology',
  },
  {
    name: 'LMArena',
    role: 'Pairwise preference and rank uncertainty',
    url: 'https://lmarena.ai/blog/arena-rank/',
  },
  {
    name: 'LiveBench',
    role: 'Fresh tasks and objective grading',
    url: 'https://livebench.ai/',
  },
  {
    name: 'SWE-bench',
    role: 'Fixed-harness coding evaluation',
    url: 'https://www.swebench.com/verified.html',
  },
  {
    name: 'OpenRouter',
    role: 'Charged usage, model identity, and routing evidence',
    url: 'https://openrouter.ai/docs/cookbook/administration/usage-accounting',
  },
];

type EvidenceGrade = 'official' | 'development' | 'incomplete';

interface DecisionModel {
  id: string;
  name: string;
  passRate: number;
  costPerAttempt: number;
  latencyMs: number;
  ci: [number, number] | null;
  grade: EvidenceGrade;
  row: ModelLeaderboardEntry;
}

interface RankedDecisionModel extends DecisionModel {
  economics: ModelEconomics;
}

const clampNumber = (value: string, min: number, max: number) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return min;
  return Math.min(max, Math.max(min, parsed));
};

const scoreFor = (row: ModelLeaderboardEntry, workload: string) => {
  if (workload === 'overall') return Number(row.pass_rate);
  const score = row.category_pass_rates[WORKLOAD_CATEGORY[workload] ?? workload];
  return score == null ? null : Number(score);
};

const gradeFor = (row: ModelLeaderboardEntry): EvidenceGrade => {
  if (row.is_private_split === true && row.grader_version && row.n_tasks >= 20 && row.n_trials >= 3) {
    return 'official';
  }
  if (row.grader_version && row.n_tasks > 0 && row.n_trials > 0) return 'development';
  return 'incomplete';
};

const toDecisionModel = (row: ModelLeaderboardEntry, workload: string): DecisionModel | null => {
  const score = scoreFor(row, workload);
  const benchmarkCost = row.cost_usd_per_task == null ? null : Number(row.cost_usd_per_task);
  const attemptCost = row.cost_usd_per_attempt == null
    ? (benchmarkCost == null ? null : benchmarkCost / Math.max(row.n_trials, 1))
    : Number(row.cost_usd_per_attempt);
  if (score == null || attemptCost == null || row.latency_p50_ms == null) return null;
  const ci = workload === 'overall' && row.ci95_low != null && row.ci95_high != null
    ? [Number(row.ci95_low) / 100, Number(row.ci95_high) / 100] as [number, number]
    : null;
  return {
    id: row.run_id,
    name: row.display_name ?? row.model_string,
    passRate: score / 100,
    costPerAttempt: attemptCost,
    latencyMs: Number(row.latency_p50_ms),
    ci,
    grade: gradeFor(row),
    row,
  };
};

const formatUsd = (value: number | null | undefined) => {
  if (value == null || !Number.isFinite(value)) return '—';
  if (value === 0) return '$0';
  if (value < 0.0001) return `$${value.toFixed(6)}`;
  if (value < 0.01) return `$${value.toFixed(4)}`;
  if (value < 1) return `$${value.toFixed(2)}`;
  return value.toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 2 });
};

const formatPercent = (value: number) => `${(value * 100).toFixed(1)}%`;
const formatLatency = (value: number) => value < 1_000 ? `${Math.round(value)} ms` : `${(value / 1_000).toFixed(1)} s`;
const formatGrade = (grade: EvidenceGrade) => grade === 'official' ? 'Official evidence' : grade === 'development' ? 'Development evidence' : 'Incomplete evidence';

function ScenarioField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="value-field">
      <span>{label}</span>
      {children}
    </label>
  );
}

function EvidencePill({ grade }: { grade: EvidenceGrade }) {
  return <span className={`evidence-pill evidence-${grade}`}>{formatGrade(grade)}</span>;
}

function RecommendationCard({
  label,
  model,
  reason,
  tasksPerMonth,
}: {
  label: string;
  model: RankedDecisionModel | null;
  reason: string;
  tasksPerMonth: number;
}) {
  if (!model) return null;
  return (
    <article className="decision-card">
      <div className="decision-card-label">{label}</div>
      <div className="mt-3 flex items-start justify-between gap-4">
        <div>
          <h3 className="text-[17px] font-semibold text-ink">{model.name}</h3>
          <p className="mt-1 text-sm leading-5 text-ink-2">{reason}</p>
        </div>
        <EvidencePill grade={model.grade} />
      </div>
      <dl className="metric-grid mt-5">
        <div>
          <dt>Measured success</dt>
          <dd>{formatPercent(model.passRate)}</dd>
        </div>
        <div>
          <dt>Cost / success</dt>
          <dd>{formatUsd(model.economics.costPerSuccess)}</dd>
        </div>
        <div>
          <dt>API cost / month</dt>
          <dd>{formatUsd(model.costPerAttempt * tasksPerMonth)}</dd>
        </div>
        <div>
          <dt>Median latency</dt>
          <dd>{formatLatency(model.latencyMs)}</dd>
        </div>
      </dl>
      <Link to={`/agents/runs/${model.id}`} className="mt-5 inline-flex text-sm font-medium text-accent hover:text-accent-strong">
        Inspect run evidence →
      </Link>
    </article>
  );
}

export default function Value() {
  const [suite, setSuite] = useState('minibench-core-v1');
  const [workload, setWorkload] = useState('overall');
  const [tasksPerMonth, setTasksPerMonth] = useState(3_000);
  const [failureCostUsd, setFailureCostUsd] = useState(1);
  const [hourlyValueUsd, setHourlyValueUsd] = useState(50);
  const [qualityFloor, setQualityFloor] = useState(80);
  const [entries, setEntries] = useState<ModelLeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [baselineId, setBaselineId] = useState('');
  const [challengerId, setChallengerId] = useState('');

  useEffect(() => {
    let cancelled = false;
    api.getModelLeaderboard({ suite })
      .then(list => {
        if (!cancelled) {
          setEntries(list);
          setError(null);
          setLoading(false);
        }
      })
      .catch(reason => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : 'Model results are unavailable.');
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [suite]);

  const scenario: ValueScenario = useMemo(() => ({
    tasksPerMonth,
    failureCostUsd,
    hourlyValueUsd,
  }), [failureCostUsd, hourlyValueUsd, tasksPerMonth]);

  const models = useMemo(
    () => entries.map(entry => toDecisionModel(entry, workload)).filter((entry): entry is DecisionModel => entry !== null),
    [entries, workload],
  );

  const eligible = useMemo(() => {
    const aboveFloor = models.filter(model => model.passRate * 100 >= qualityFloor);
    return aboveFloor.length > 0 ? aboveFloor : models;
  }, [models, qualityFloor]);

  const ranked = useMemo(
    () => rankByEconomicValue(eligible, scenario) as RankedDecisionModel[],
    [eligible, scenario],
  );

  const bestValue = ranked[0] ?? null;
  const lowerCost = useMemo(() => [...ranked].sort((a, b) => (
    a.economics.costPerSuccess - b.economics.costPerSuccess
    || b.passRate - a.passRate
  ))[0] ?? null, [ranked]);
  const premium = useMemo(() => [...ranked].sort((a, b) => (
    b.passRate - a.passRate
    || a.economics.expectedEconomicCostPerSuccess - b.economics.expectedEconomicCostPerSuccess
  ))[0] ?? null, [ranked]);
  const frontier = useMemo(() => paretoFrontier(models), [models]);
  const visibleRanked = ranked.slice(0, 10);

  const baseline = models.find(model => model.id === baselineId) ?? lowerCost ?? models[0] ?? null;
  const challenger = models.find(model => model.id === challengerId)
    ?? (premium?.id !== baseline?.id ? premium : models.find(model => model.id !== baseline?.id))
    ?? null;
  const confidence = baseline && challenger ? evidenceStatus(baseline.ci, challenger.ci) : 'unavailable';
  const upgrade = baseline && challenger
    ? premiumVerdict(baseline, challenger, scenario, confidence)
    : null;
  const baselineEconomics = baseline ? evaluateModel(baseline, scenario) : null;
  const challengerEconomics = challenger ? evaluateModel(challenger, scenario) : null;

  const retry = () => {
    setLoading(true);
    setError(null);
    api.getModelLeaderboard({ suite })
      .then(list => { setEntries(list); setLoading(false); })
      .catch(reason => { setError(reason instanceof Error ? reason.message : 'Model results are unavailable.'); setLoading(false); });
  };

  return (
    <div className="space-y-8">
      <header className="max-w-4xl">
        <div className="text-sm font-medium text-accent">MiniBench Value Intelligence</div>
        <h1 className="mt-2 text-[30px] font-medium leading-tight tracking-[-0.02em] text-ink sm:text-[34px]">
          Choose the model that earns its keep.
        </h1>
        <p className="mt-3 max-w-3xl text-[15px] leading-6 text-ink-2">
          Turn measured task success, actual run cost, latency, and uncertainty into a defensible buying decision. No opaque value score and no universal champion—every recommendation is tied to your workload and economics.
        </p>
      </header>

      <section className="scenario-panel" aria-labelledby="scenario-heading">
        <div className="flex items-center justify-between gap-4 border-b border-line px-4 py-3 sm:px-5">
          <div>
            <h2 id="scenario-heading" className="text-sm font-semibold text-ink">Decision assumptions</h2>
            <p className="mt-0.5 text-xs text-ink-3">Projections change; measured benchmark evidence does not.</p>
          </div>
          <Link to="/methodology" className="text-xs font-medium text-accent hover:text-accent-strong">Audit the method</Link>
        </div>
        <div className="scenario-grid p-4 sm:p-5">
          <ScenarioField label="Benchmark suite">
            <select
              value={suite}
              onChange={event => { setLoading(true); setSuite(event.target.value); }}
            >
              {SUITES.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </ScenarioField>
          <ScenarioField label="Workload lens">
            <select value={workload} onChange={event => setWorkload(event.target.value)}>
              {WORKLOADS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </ScenarioField>
          <ScenarioField label="Tasks / month">
            <input
              type="number"
              min="1"
              max="10000000"
              step="100"
              value={tasksPerMonth}
              onChange={event => setTasksPerMonth(clampNumber(event.target.value, 1, 10_000_000))}
            />
          </ScenarioField>
          <ScenarioField label="Cost of one failure">
            <input
              type="number"
              min="0"
              max="1000000"
              step="0.1"
              value={failureCostUsd}
              onChange={event => setFailureCostUsd(clampNumber(event.target.value, 0, 1_000_000))}
            />
          </ScenarioField>
          <ScenarioField label="Time value / hour">
            <input
              type="number"
              min="0"
              max="100000"
              step="5"
              value={hourlyValueUsd}
              onChange={event => setHourlyValueUsd(clampNumber(event.target.value, 0, 100_000))}
            />
          </ScenarioField>
          <ScenarioField label="Minimum measured success">
            <div className="quality-input">
              <input
                type="number"
                min="0"
                max="100"
                step="1"
                value={qualityFloor}
                onChange={event => setQualityFloor(clampNumber(event.target.value, 0, 100))}
              />
              <span>%</span>
            </div>
          </ScenarioField>
        </div>
      </section>

      {loading && <Skeleton rows={8} />}
      {!loading && error && <ErrorState onRetry={retry}>{error}</ErrorState>}

      {!loading && !error && models.length === 0 && (
        <div className="border border-line bg-surface p-8 text-center">
          <h2 className="font-semibold text-ink">No comparable measured runs</h2>
          <p className="mt-2 text-sm text-ink-2">This workload and suite do not yet have cost, latency, and success evidence on the same runs.</p>
        </div>
      )}

      {!loading && !error && bestValue && (
        <>
          <section className="decision-summary" aria-labelledby="decision-heading">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <div className="text-xs font-semibold uppercase tracking-[0.08em] text-positive">Best fit under these assumptions</div>
                <EvidencePill grade={bestValue.grade} />
              </div>
              <h2 id="decision-heading" className="mt-2 text-xl font-semibold text-ink">
                {bestValue.name} minimizes risk-adjusted cost per successful task at {formatPercent(bestValue.passRate)} measured success.
              </h2>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-ink-2">
                Risk-adjusted cost is {formatUsd(bestValue.economics.expectedEconomicCostPerSuccess)} per successful task: expected API spend, time cost, and failure loss divided by measured success probability. {eligible.length < models.length ? `${models.length - eligible.length} option${models.length - eligible.length === 1 ? '' : 's'} fell below the ${qualityFloor}% quality floor.` : 'Every measured option cleared the quality floor.'}
              </p>
            </div>
            <div className="decision-number">
              <span>Projected API spend</span>
              <strong>{formatUsd(bestValue.economics.monthlyApiCost)}</strong>
              <small>{tasksPerMonth.toLocaleString()} tasks / month</small>
            </div>
          </section>

          <section aria-labelledby="shortlist-heading">
            <div className="section-heading-row">
              <div>
                <h2 id="shortlist-heading">Scenario shortlist</h2>
                <p>Different mandates produce different leaders. These are explicit rules, not a blended magic score.</p>
              </div>
            </div>
            <div className="grid gap-4 lg:grid-cols-3">
              <RecommendationCard
                label="Economic fit"
                model={bestValue}
                reason={`Lowest risk-adjusted cost per successful task when a failure costs ${formatUsd(failureCostUsd)} and time is valued at ${formatUsd(hourlyValueUsd)}/hour.`}
                tasksPerMonth={tasksPerMonth}
              />
              <RecommendationCard
                label="Lowest cost per success"
                model={lowerCost}
                reason="Lowest measured API spend after charging failed attempts instead of hiding them."
                tasksPerMonth={tasksPerMonth}
              />
              <RecommendationCard
                label="Highest measured success"
                model={premium}
                reason="Strongest point estimate in the selected lane; inspect uncertainty before paying a premium."
                tasksPerMonth={tasksPerMonth}
              />
            </div>
          </section>

          {baseline && challenger && upgrade && baselineEconomics && challengerEconomics && (
            <section className="upgrade-panel" aria-labelledby="upgrade-heading">
              <div className="upgrade-controls">
                <div>
                  <div className="text-sm font-semibold text-ink">Baseline</div>
                  <select value={baseline.id} onChange={event => setBaselineId(event.target.value)}>
                    {models.map(model => <option key={model.id} value={model.id}>{model.name}</option>)}
                  </select>
                </div>
                <div>
                  <div className="text-sm font-semibold text-ink">Challenger</div>
                  <select value={challenger.id} onChange={event => setChallengerId(event.target.value)}>
                    {models.map(model => <option key={model.id} value={model.id}>{model.name}</option>)}
                  </select>
                </div>
              </div>
              <div className="upgrade-conclusion">
                <div className="text-xs font-semibold uppercase tracking-[0.08em] text-accent">Upgrade check</div>
                <h2 id="upgrade-heading" className="mt-2 text-xl font-semibold text-ink">
                  {upgrade.reason === 'no-measured-quality-uplift'
                    ? `${challenger.name} has no measured quality uplift over ${baseline.name}.`
                    : upgrade.reason === 'quality-evidence-unavailable'
                      ? 'No upgrade recommendation: confidence bounds are unavailable.'
                      : upgrade.reason === 'quality-uplift-not-demonstrated'
                        ? 'No demonstrated uplift: the economic threshold remains conditional.'
                        : upgrade.worthIt
                          ? `${challenger.name} earns its premium under this failure-cost assumption.`
                          : `${challenger.name} does not earn its premium under this failure-cost assumption.`}
                </h2>
                <p className="mt-2 text-sm leading-6 text-ink-2">
                  {upgrade.breakEvenFailureCost == null
                    ? 'A higher price cannot be justified by quality when the measured success rate does not increase.'
                    : `${upgrade.reason === 'premium-justified' || upgrade.reason === 'premium-not-justified' ? '' : 'Conditional '}break-even failure cost: ${formatUsd(upgrade.breakEvenFailureCost)} per task. Your assumption is ${formatUsd(failureCostUsd)}.`}
                  {' '}Confidence: {confidence === 'indistinguishable' ? 'the 95% intervals overlap, so no quality winner is demonstrated' : confidence === 'challenger-higher' ? 'the challenger interval is higher' : confidence === 'baseline-higher' ? 'the baseline interval is higher' : 'paired significance is unavailable for this view'}.
                </p>
                <dl className="upgrade-metrics">
                  <div><dt>Success delta</dt><dd>{upgrade.qualityDelta >= 0 ? '+' : ''}{(upgrade.qualityDelta * 100).toFixed(1)} pts</dd></div>
                  <div><dt>API cost delta</dt><dd>{formatUsd(challenger.costPerAttempt - baseline.costPerAttempt)}</dd></div>
                  <div><dt>Monthly API delta</dt><dd>{formatUsd(challengerEconomics.monthlyApiCost - baselineEconomics.monthlyApiCost)}</dd></div>
                  <div><dt>Latency delta</dt><dd>{formatLatency(Math.abs(challenger.latencyMs - baseline.latencyMs))} {challenger.latencyMs >= baseline.latencyMs ? 'slower' : 'faster'}</dd></div>
                </dl>
              </div>
            </section>
          )}

          <section aria-labelledby="frontier-heading">
            <div className="section-heading-row">
              <div>
                <h2 id="frontier-heading">Value frontier</h2>
                <p>{frontier.length} of {models.length} measured options are not strictly worse on quality, cost, and median latency. Showing the 10 strongest scenario fits.</p>
              </div>
              <Link to="/models" className="text-sm font-medium text-accent hover:text-accent-strong">Open full model research →</Link>
            </div>
            <div className="research-table-wrap hidden md:block">
              <table className="research-table">
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Measured success</th>
                    <th>95% CI</th>
                    <th>Cost / attempt</th>
                    <th>Cost / success</th>
                    <th>Risk-adjusted cost / success</th>
                    <th>p50 latency</th>
                    <th>Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleRanked.map(model => (
                    <tr key={model.id} className={frontier.some(item => item.id === model.id) ? 'frontier-row' : undefined}>
                      <td>
                        <Link to={`/agents/runs/${model.id}`} className="font-medium text-ink hover:text-accent">{model.name}</Link>
                        {frontier.some(item => item.id === model.id) && <div className="mt-1 text-[11px] font-medium text-positive">Pareto frontier</div>}
                      </td>
                      <td>{formatPercent(model.passRate)}</td>
                      <td>{model.ci ? `${formatPercent(model.ci[0])}–${formatPercent(model.ci[1])}` : 'Not available'}</td>
                      <td>{formatUsd(model.costPerAttempt)}</td>
                      <td>{formatUsd(model.economics.costPerSuccess)}</td>
                      <td>{formatUsd(model.economics.expectedEconomicCostPerSuccess)}</td>
                      <td>{formatLatency(model.latencyMs)}</td>
                      <td><EvidencePill grade={model.grade} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="grid gap-3 md:hidden">
              {visibleRanked.map(model => (
                <article key={model.id} className="mobile-research-row">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <Link to={`/agents/runs/${model.id}`} className="font-semibold text-ink">{model.name}</Link>
                      <div className="mt-1 text-xs text-ink-3">{formatGrade(model.grade)}</div>
                    </div>
                    <div className="tnum text-right font-semibold text-ink">{formatPercent(model.passRate)}</div>
                  </div>
                  <dl>
                    <div><dt>Cost / success</dt><dd>{formatUsd(model.economics.costPerSuccess)}</dd></div>
                    <div><dt>Risk-adjusted cost / success</dt><dd>{formatUsd(model.economics.expectedEconomicCostPerSuccess)}</dd></div>
                    <div><dt>Median latency</dt><dd>{formatLatency(model.latencyMs)}</dd></div>
                  </dl>
                </article>
              ))}
            </div>
          </section>
        </>
      )}

      <section className="source-ledger" aria-labelledby="source-heading">
        <div className="section-heading-row">
          <div>
            <h2 id="source-heading">External evidence ledger</h2>
            <p>MiniBench borrows proven methods; it does not silently copy third-party scores into its recommendation.</p>
          </div>
          <a href="https://github.com/RaapTechllc/minibench/blob/main/docs/research/llm-value-intelligence-2026-07.md" target="_blank" rel="noreferrer" className="text-sm font-medium text-accent hover:text-accent-strong">Read the research note →</a>
        </div>
        <div className="source-grid">
          {SOURCES.map(source => (
            <a key={source.name} href={source.url} target="_blank" rel="noreferrer" className="source-item">
              <strong>{source.name}</strong>
              <span>{source.role}</span>
            </a>
          ))}
        </div>
        <div className="method-note">
          <strong>The governing metric:</strong> cost per successful on-time task = full episode cost ÷ probability of an acceptable result within the deadline. Premium models are justified only when their incremental quality is worth more than incremental cost, delay, and risk.
        </div>
      </section>
    </div>
  );
}
