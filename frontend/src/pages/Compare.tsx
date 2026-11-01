import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { ModelLeaderboardEntry } from '../api';
import { ErrorState, Skeleton } from '../components/ui';
import { evaluateModel, evidenceStatus, premiumVerdict } from '../lib/valueMetrics.js';

const SUITES = [
  ['minibench-core-v1', 'Core v1 · broad coverage'],
  ['minibench-hard-v1', 'Hard v1 · primary'],
  ['minibench-v2', 'v2 · current'],
];

const numberOrNull = (value: number | string | null | undefined) =>
  value == null || !Number.isFinite(Number(value)) ? null : Number(value);

const modelName = (entry: ModelLeaderboardEntry) => entry.display_name ?? entry.model_string;

const usd = (value: number | null | undefined) => {
  if (value == null || !Number.isFinite(value)) return '—';
  if (value < 0.01) return `$${value.toFixed(4)}`;
  if (value < 1) return `$${value.toFixed(3)}`;
  return `$${value.toFixed(2)}`;
};

const pct = (value: number) => `${(value * 100).toFixed(1)}%`;

const confidenceInterval = (entry: ModelLeaderboardEntry): [number, number] | null => {
  const low = numberOrNull(entry.ci95_low);
  const high = numberOrNull(entry.ci95_high);
  return low == null || high == null ? null : [low / 100, high / 100];
};

function toModel(entry: ModelLeaderboardEntry) {
  const benchmarkCost = numberOrNull(entry.cost_usd_per_task);
  const cost = numberOrNull(entry.cost_usd_per_attempt)
    ?? (benchmarkCost == null ? null : benchmarkCost / Math.max(entry.n_trials, 1));
  const latency = numberOrNull(entry.latency_p50_ms);
  if (cost == null || latency == null) return null;
  return {
    id: entry.run_id,
    entry,
    passRate: Number(entry.pass_rate) / 100,
    costPerAttempt: cost,
    latencyMs: latency,
  };
}

type ComparisonModel = NonNullable<ReturnType<typeof toModel>>;

export default function Compare() {
  const [suite, setSuite] = useState('minibench-core-v1');
  const [entries, setEntries] = useState<ModelLeaderboardEntry[]>([]);
  const [baselineId, setBaselineId] = useState('');
  const [challengerId, setChallengerId] = useState('');
  const [tasksPerMonth, setTasksPerMonth] = useState(3000);
  const [failureCostUsd, setFailureCostUsd] = useState(1);
  const [hourlyValueUsd, setHourlyValueUsd] = useState(50);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getModelLeaderboard({ suite })
      .then(result => {
        if (!cancelled) {
          setEntries(result);
          setError(null);
          setLoading(false);
        }
      })
      .catch(reason => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : 'Comparison evidence is unavailable.');
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, [suite]);

  const models = useMemo(() => entries.map(toModel).filter((item): item is ComparisonModel => item !== null), [entries]);
  const cheapest = useMemo(() => [...models].sort((a, b) => a.costPerAttempt - b.costPerAttempt)[0], [models]);
  const strongest = useMemo(() => [...models].sort((a, b) => b.passRate - a.passRate)[0], [models]);
  const baseline = models.find(model => model.id === baselineId) ?? cheapest ?? models[0];
  const challenger = models.find(model => model.id === challengerId)
    ?? (strongest?.id !== baseline?.id ? strongest : models.find(model => model.id !== baseline?.id))
    ?? models[0];

  const scenario = { tasksPerMonth, failureCostUsd, hourlyValueUsd };
  const baselineEconomics = baseline ? evaluateModel(baseline, scenario) : null;
  const challengerEconomics = challenger ? evaluateModel(challenger, scenario) : null;
  const evidence = baseline && challenger
    ? evidenceStatus(confidenceInterval(baseline.entry), confidenceInterval(challenger.entry))
    : 'unavailable';
  const verdict = baseline && challenger
    ? premiumVerdict(baseline, challenger, scenario, evidence)
    : null;

  const retry = () => {
    setLoading(true);
    setError(null);
    api.getModelLeaderboard({ suite })
      .then(result => { setEntries(result); setLoading(false); })
      .catch(reason => { setError(reason instanceof Error ? reason.message : 'Comparison evidence is unavailable.'); setLoading(false); });
  };

  const verdictCopy = !verdict || !baseline || !challenger
    ? 'Select two priced runs to calculate an upgrade threshold.'
    : verdict.reason === 'no-measured-quality-uplift'
      ? `${modelName(challenger.entry)} has no measured quality uplift over ${modelName(baseline.entry)} on this suite.`
      : verdict.reason === 'quality-evidence-unavailable'
        ? 'No upgrade recommendation: confidence bounds are unavailable for this comparison.'
        : verdict.reason === 'quality-uplift-not-demonstrated'
          ? 'No demonstrated uplift: the economic break-even remains conditional.'
          : verdict.worthIt
            ? `Upgrade: the challenger clears your ${usd(failureCostUsd)} failure-cost assumption.`
            : `Stay with the baseline: the challenger needs failure cost above ${usd(verdict.breakEvenFailureCostUsd)} to pay back.`;

  return (
    <div className="space-y-8">
      <header className="max-w-4xl">
        <div className="text-sm font-medium text-accent">Upgrade analysis</div>
        <h1 className="mt-2 text-[30px] font-medium leading-tight tracking-[-0.02em] text-ink sm:text-[34px]">Is the stronger model worth the premium?</h1>
        <p className="mt-3 max-w-3xl text-[15px] leading-6 text-ink-2">
          Compare two measured runs under your task volume, time value, and cost of a failed task. The break-even threshold is the same incremental-cost logic used in investment and health-economics decisions.
        </p>
      </header>

      <section className="scenario-panel p-4" aria-label="Comparison assumptions">
        <div className="scenario-grid">
          <label className="value-field" htmlFor="compare-suite">
            <span>Evaluation suite</span>
            <select id="compare-suite" value={suite} onChange={event => { setLoading(true); setSuite(event.target.value); }}>
              {SUITES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label className="value-field" htmlFor="compare-baseline">
            <span>Baseline</span>
            <select id="compare-baseline" value={baseline?.id ?? ''} onChange={event => setBaselineId(event.target.value)}>
              {models.map(model => <option key={model.id} value={model.id}>{modelName(model.entry)}</option>)}
            </select>
          </label>
          <label className="value-field" htmlFor="compare-challenger">
            <span>Challenger</span>
            <select id="compare-challenger" value={challenger?.id ?? ''} onChange={event => setChallengerId(event.target.value)}>
              {models.map(model => <option key={model.id} value={model.id}>{modelName(model.entry)}</option>)}
            </select>
          </label>
          <label className="value-field">
            <span>Tasks per month</span>
            <input type="number" min="1" step="100" value={tasksPerMonth} onChange={event => setTasksPerMonth(Math.max(1, Number(event.target.value) || 1))} />
          </label>
          <label className="value-field">
            <span>Failure cost · USD</span>
            <input type="number" min="0" step="0.25" value={failureCostUsd} onChange={event => setFailureCostUsd(Math.max(0, Number(event.target.value) || 0))} />
          </label>
          <label className="value-field">
            <span>Time value · USD/hour</span>
            <input type="number" min="0" step="5" value={hourlyValueUsd} onChange={event => setHourlyValueUsd(Math.max(0, Number(event.target.value) || 0))} />
          </label>
        </div>
      </section>

      {loading && <Skeleton rows={8} />}
      {!loading && error && <ErrorState onRetry={retry}>{error}</ErrorState>}
      {!loading && !error && models.length < 2 && (
        <div className="border border-line bg-surface p-8 text-center text-sm text-ink-2">This suite needs at least two runs with both cost and latency evidence.</div>
      )}

      {!loading && !error && baseline && challenger && baselineEconomics && challengerEconomics && verdict && (
        <>
          <section className={`border-l-4 p-5 ${verdict.worthIt ? 'border-positive bg-positive-soft' : 'border-frontier bg-frontier-soft'}`} aria-labelledby="comparison-verdict">
            <div className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-3">Decision</div>
            <h2 id="comparison-verdict" className="mt-2 text-xl font-semibold text-ink">{verdictCopy}</h2>
            <p className="mt-2 text-sm text-ink-2">
              Evidence status: <strong>{evidence === 'indistinguishable' ? 'confidence intervals overlap' : evidence.replaceAll('-', ' ')}</strong>.
              {' '}The economic verdict does not turn an uncertain quality difference into a statistical winner.
            </p>
          </section>

          <section className="grid gap-4 lg:grid-cols-2" aria-label="Side-by-side economics">
            <ModelCard label="Baseline" model={baseline} economics={baselineEconomics} tasks={tasksPerMonth} />
            <ModelCard label="Challenger" model={challenger} economics={challengerEconomics} tasks={tasksPerMonth} />
          </section>

          <section className="research-table-wrap">
            <table className="research-table">
              <thead>
                <tr><th>Incremental measure</th><th>Result</th><th>Interpretation</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td>Measured quality change</td>
                  <td className="tnum">{verdict.qualityDelta >= 0 ? '+' : ''}{pct(verdict.qualityDelta)}</td>
                  <td>Challenger pass probability minus baseline pass probability.</td>
                </tr>
                <tr>
                  <td>Attempt-cost change</td>
                  <td className="tnum">{verdict.attemptCostDeltaUsd >= 0 ? '+' : '−'}{usd(Math.abs(verdict.attemptCostDeltaUsd))}</td>
                  <td>Extra API cost paid on every task before failure or time cost.</td>
                </tr>
                <tr>
                  <td>Break-even failure cost</td>
                  <td className="tnum">{usd(verdict.breakEvenFailureCostUsd)}</td>
                  <td>Choose the challenger above this loss per failed task, subject to evidence confidence.</td>
                </tr>
                <tr>
                  <td>Expected economic difference</td>
                  <td className="tnum">{verdict.economicCostDeltaUsd >= 0 ? '+' : '−'}{usd(Math.abs(verdict.economicCostDeltaUsd))}/task</td>
                  <td>Challenger expected task cost minus baseline under the declared scenario.</td>
                </tr>
              </tbody>
            </table>
          </section>

          <aside className="method-note">
            Expected economic cost = charged cost + latency value + failure probability × declared failure cost. See the <Link to="/methodology" className="font-medium text-accent hover:text-accent-strong">methodology</Link> and return to the <Link to="/" className="font-medium text-accent hover:text-accent-strong">Value desk</Link> for the full frontier.
          </aside>
        </>
      )}
    </div>
  );
}

function ModelCard({ label, model, economics, tasks }: {
  label: string;
  model: ComparisonModel;
  economics: ReturnType<typeof evaluateModel>;
  tasks: number;
}) {
  const entry = model.entry;
  const rows = [
    ['Measured success', pct(model.passRate)],
    ['95% confidence interval', `${Number(entry.ci95_low ?? entry.pass_rate).toFixed(1)}–${Number(entry.ci95_high ?? entry.pass_rate).toFixed(1)}%`],
    ['Cost per attempt', usd(model.costPerAttempt)],
    ['Cost per successful task', usd(economics.costPerSuccess)],
    ['Expected economic cost', usd(economics.expectedEconomicCost)],
    ['Expected latency per success', `${(economics.expectedLatencyPerSuccessMs / 1000).toFixed(1)}s`],
    ['Monthly API spend', usd(economics.monthlyApiCost)],
    ['Expected monthly successes', Math.round(model.passRate * tasks).toLocaleString()],
  ];

  return (
    <article className="border border-line bg-surface p-5">
      <div className="text-xs font-semibold uppercase tracking-[0.08em] text-accent">{label}</div>
      <h2 className="mt-2 text-xl font-semibold text-ink">{modelName(entry)}</h2>
      <p className="mt-1 text-xs text-ink-3">{entry.model_string} · {entry.n_tasks}×{entry.n_trials} observations</p>
      <dl className="mt-5 border-t border-line">
        {rows.map(([name, value]) => (
          <div key={name} className="flex items-baseline justify-between gap-4 border-b border-line py-2.5 text-sm">
            <dt className="text-ink-3">{name}</dt>
            <dd className="tnum text-right font-medium text-ink">{value}</dd>
          </div>
        ))}
      </dl>
      <Link to={`/agents/runs/${entry.run_id}`} className="mt-4 inline-block text-sm font-medium text-accent hover:text-accent-strong">Inspect run evidence →</Link>
    </article>
  );
}