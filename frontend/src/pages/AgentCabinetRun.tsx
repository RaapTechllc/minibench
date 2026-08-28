import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { api } from '../api';
import type { AgentCabinetDetail } from '../api';
import {
  PageHeader, Card, CardHeader, Stat, Badge, ValidityBadge,
  Skeleton, EmptyState, ErrorState, CIBar,
} from '../components/ui';
import { fmtCost, fmtPct } from '../components/chart';
import {
  AGENT_CABINET_COPY,
  categoryTitle,
  controlledVariableSentence,
  sortedCategoryEntries,
} from '../lib/agentCabinet.js';

function fmtDate(value: string | null): string {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

/** Summary reliability rates ship as raw 0–1 fractions; display as percent. */
function fmtRate(value: number | null): string {
  return value == null ? '—' : fmtPct(Number(value) * 100);
}

function TechReadout({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-emerald-400/20 bg-black/30 p-3">
      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-400/70">{label}</div>
      <div className="tnum mt-1 text-lg font-semibold text-emerald-100 break-all">{value}</div>
      {sub && <div className="mt-1 text-[11px] text-emerald-200/60">{sub}</div>}
    </div>
  );
}

function TechnicianPanel({ run }: { run: AgentCabinetDetail }) {
  const technician = run.technician;
  const hasCI = technician.ci95_low != null && technician.ci95_high != null;
  const budgets = Object.entries(technician.budgets ?? {});
  const terminations = Object.entries(technician.termination_reasons ?? {});

  return (
    <Card className="border-emerald-400/30 bg-slate-950 p-5 font-mono text-emerald-100 shadow-none">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-emerald-400/20 pb-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-400">Technician mode</div>
          <div className="mt-1 text-[12px] text-emerald-200/70">
            Provenance and reliability diagnostics for this published run.
          </div>
        </div>
        {technician.grader_version && (
          <span className="rounded border border-emerald-400/30 px-2 py-1 text-[11px] text-emerald-200">
            grader {technician.grader_version}
          </span>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <TechReadout
          label="Harness"
          value={`${technician.harness ?? '—'} v${technician.harness_version ?? '—'}`}
        />
        <TechReadout
          label="Model / provider"
          value={technician.model ?? '—'}
          sub={technician.provider ?? undefined}
        />
        <TechReadout label="Model route" value={technician.model_route ?? '—'} />
        <TechReadout label="Trials" value={String(technician.trials.length)} sub="recorded trials" />
        <TechReadout
          label="95% CI"
          value={hasCI ? `${Number(technician.ci95_low).toFixed(1)}-${Number(technician.ci95_high).toFixed(1)}%` : '—'}
          sub={hasCI ? 'around completion' : 'not included in payload'}
        />
        <TechReadout label="Pass^k" value={technician.pass_hat_k != null ? fmtPct(technician.pass_hat_k) : '—'} />
        <TechReadout label="Regression rate" value={fmtRate(technician.regression_rate)} />
        <TechReadout label="False verification" value={fmtRate(technician.false_verification_rate)} />
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-lg border border-emerald-400/20 bg-black/20 p-3">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-400/70">Fixture</div>
          <div className="text-[12px] text-emerald-100">{technician.fixture_reference ?? '—'}</div>
          <div className="tnum mt-1 break-all text-[11px] text-emerald-200/60">{technician.fixture_digest ?? '—'}</div>
        </div>
        <div className="rounded-lg border border-emerald-400/20 bg-black/20 p-3">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-400/70">Budgets</div>
          {budgets.length === 0 ? (
            <div className="text-[12px] text-emerald-200/60">—</div>
          ) : (
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-[12px]">
              {budgets.map(([key, value]) => (
                <div key={key} className="flex items-baseline justify-between gap-2">
                  <dt className="text-emerald-200/60">{key}</dt>
                  <dd className="tnum text-emerald-100">{String(value)}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </div>

      {hasCI && (
        <div className="mt-4 rounded-lg border border-emerald-400/20 bg-black/20 p-3">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-400/70">
            Completion interval
          </div>
          <CIBar
            value={Number(run.completion)}
            lo={Number(technician.ci95_low)}
            hi={Number(technician.ci95_high)}
          />
        </div>
      )}

      <div className="mt-4 rounded-lg border border-emerald-400/20 bg-black/20 p-3">
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-400/70">
          Termination reasons
        </div>
        {terminations.length === 0 ? (
          <div className="text-[12px] text-emerald-200/60">—</div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {terminations.map(([reason, count]) => (
              <span
                key={reason}
                className="rounded border border-emerald-400/30 px-2 py-1 text-[11px] text-emerald-200"
              >
                {reason} <span className="tnum">×{count}</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

export default function AgentCabinetRun() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<AgentCabinetDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState(false);
  const [technicianMode, setTechnicianMode] = useState(false);

  const load = useCallback(() => {
    if (!runId) return () => {};
    let active = true;
    setLoading(true);
    setError(false);
    setNotFound(false);
    api
      .getAgentCabinetRun(runId)
      .then((r) => {
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

  const backLink = (
    <Link to="/agent-cabinet" className="inline-flex items-center gap-1.5 text-accent hover:text-accent-strong text-sm">
      <ArrowLeft className="w-4 h-4" /> Back to Agent Cabinet
    </Link>
  );

  if (loading) {
    return <div className="space-y-6">{backLink}<Skeleton rows={7} /></div>;
  }
  if (error) {
    return (
      <div className="space-y-6">
        {backLink}
        <ErrorState onRetry={load}>Something went wrong loading this run.</ErrorState>
      </div>
    );
  }
  if (notFound || !run) {
    return (
      <div className="space-y-6">
        {backLink}
        <EmptyState title="Run not found">
          This run may have been removed, or the link is incorrect.
        </EmptyState>
      </div>
    );
  }

  const categories = sortedCategoryEntries(run.category_completion);
  const controlledSentence = controlledVariableSentence(run);

  return (
    <div className="space-y-6">
      {backLink}

      <PageHeader eyebrow={run.suite ?? 'Real-Work Agent Cabinet'} title={run.model_route ?? run.run_id.slice(0, 8)}>
        {run.harness ?? 'unknown harness'}
        {run.harness_version != null && ` v${run.harness_version}`}
        {' · submitted '}{fmtDate(run.submitted_at)}
      </PageHeader>

      <div className="flex flex-wrap items-center gap-2 animate-rise">
        <ValidityBadge isPrivate={run.private_split} />
        <Badge tone="neutral" title={AGENT_CABINET_COPY.notSoloNotMultiplayer}>Agent harness</Badge>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 animate-rise rise-1">
        <Stat label="Completion" accent value={fmtPct(run.completion)} sub="tasks completed" />
        <Stat label="Cost / task" value={fmtCost(run.cost_usd_per_task)} />
        <Stat
          label="Latency p50"
          value={run.latency_p50_ms != null ? `${run.latency_p50_ms}ms` : '—'}
        />
        <Stat
          label="Harness"
          value={run.harness ?? '—'}
          sub={run.harness_version != null ? `v${run.harness_version}` : undefined}
        />
      </div>

      <Card className="animate-rise rise-1">
        <CardHeader
          title="Category completion"
          sub="Raw task-family keys from the run artifact — no Arcade relabeling."
        />
        <div className="px-5 pb-5">
          {categories.length === 0 ? (
            <div className="text-[13px] text-ink-3">No category breakdown recorded for this run.</div>
          ) : (
            <div className="space-y-2">
              {categories.map(([key, value]) => (
                <div key={key} className="flex items-center gap-3">
                  <span className="w-48 shrink-0 text-[13px] text-ink">{categoryTitle(key)}</span>
                  <div className="relative h-1.5 flex-1 rounded-full bg-line">
                    <div
                      className="absolute inset-y-0 left-0 rounded-full bg-accent"
                      style={{ width: `${Math.max(0, Math.min(100, Number(value)))}%` }}
                    />
                  </div>
                  <span className="tnum w-14 text-right text-[13px] font-semibold text-ink">
                    {fmtPct(value)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      <Card className="animate-rise rise-2 px-5 py-4">
        <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3">
          Controlled variables
        </div>
        <p className="mt-1.5 text-[13px] leading-relaxed text-ink-2">
          {controlledSentence || AGENT_CABINET_COPY.controlledVariables}
        </p>
        <p className="mt-1 text-[13px] leading-relaxed text-ink-3">
          {AGENT_CABINET_COPY.notSoloNotMultiplayer}
        </p>
      </Card>

      <div className="animate-rise rise-2">
        <button
          type="button"
          aria-pressed={technicianMode}
          onClick={() => setTechnicianMode((value) => !value)}
          className="rounded-lg border border-ink-3/30 bg-slate-950 px-4 py-2 font-mono text-[12px] font-semibold uppercase tracking-[0.16em] text-emerald-300 transition hover:border-emerald-400/60 hover:text-emerald-100"
        >
          {technicianMode ? 'RELEASE START to hide Technician mode' : 'HOLD START for Technician mode'}
        </button>
      </div>

      {technicianMode && <TechnicianPanel run={run} />}
    </div>
  );
}
