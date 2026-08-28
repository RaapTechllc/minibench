import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { AgentCabinetListItem } from '../api';
import {
  PageHeader, Card, CardHeader, Badge, ValidityBadge, Skeleton, EmptyState, ErrorState,
} from '../components/ui';
import { fmtCost, fmtPct } from '../components/chart';
import {
  AGENT_CABINET_COPY,
  categoryTitle,
  sortedCategoryEntries,
} from '../lib/agentCabinet.js';

function fmtDate(value: string | null): string {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

function CategoryChips({ completion }: { completion: Record<string, number> }) {
  const entries = sortedCategoryEntries(completion);
  if (entries.length === 0) return <span className="text-ink-3">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {entries.map(([key, value]) => (
        <Badge key={key} tone={value >= 80 ? 'pass' : value >= 50 ? 'neutral' : 'fail'}>
          {categoryTitle(key)} <span className="tnum">{Number(value).toFixed(0)}%</span>
        </Badge>
      ))}
    </div>
  );
}

export default function AgentCabinet() {
  const [runs, setRuns] = useState<AgentCabinetListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api
      .getAgentCabinetRuns()
      .then(setRuns)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Real-Work Agent Cabinet" title="Agent harnesses on real work, held constant">
        {AGENT_CABINET_COPY.tagline} {AGENT_CABINET_COPY.controlledVariables}{' '}
        {AGENT_CABINET_COPY.notSoloNotMultiplayer}
      </PageHeader>

      {loading ? (
        <Skeleton rows={6} />
      ) : error ? (
        <ErrorState onRetry={load}>{error}</ErrorState>
      ) : runs.length === 0 ? (
        <EmptyState title={AGENT_CABINET_COPY.emptyTitle}>
          {AGENT_CABINET_COPY.emptyBody}
        </EmptyState>
      ) : (
        <Card className="animate-rise rise-1 overflow-hidden">
          <CardHeader
            title="Published runs"
            sub="Best valid run per identity key; private split supersedes public. Rank is board order, not a composite score."
          />
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-y border-line text-[11px] uppercase tracking-wider">
                  <th className="py-3 pl-5 pr-2 font-semibold whitespace-nowrap text-ink-3">#</th>
                  <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">Model route</th>
                  <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">Suite</th>
                  <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">Harness</th>
                  <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">Completion</th>
                  <th className="px-2 py-3 font-semibold text-ink-3">Category completion</th>
                  <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">Cost / task</th>
                  <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">Latency p50</th>
                  <th className="px-2 py-3 font-semibold whitespace-nowrap text-ink-3">Split</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run, index) => (
                  <tr key={run.run_id} className="border-t border-line hover:bg-surface-2">
                    <td className="tnum py-3 pl-5 pr-2 text-ink-3">#{index + 1}</td>
                    <td className="px-2 py-3">
                      <Link
                        to={`/agent-cabinet/runs/${run.run_id}`}
                        className="font-medium text-ink whitespace-nowrap hover:text-accent"
                      >
                        {run.model_route ?? run.run_id.slice(0, 8)}
                      </Link>
                      <div className="mt-0.5 text-[12px] text-ink-3 whitespace-nowrap">
                        submitted {fmtDate(run.submitted_at)}
                      </div>
                    </td>
                    <td className="px-2 py-3 text-[12px] text-ink-2 whitespace-nowrap">{run.suite ?? '—'}</td>
                    <td className="px-2 py-3 text-[12px] text-ink-2 whitespace-nowrap">
                      {run.harness ?? '—'}
                      {run.harness_version != null && (
                        <span className="text-ink-3"> v{run.harness_version}</span>
                      )}
                    </td>
                    <td className="tnum px-2 py-3 font-semibold text-accent whitespace-nowrap">
                      {fmtPct(run.completion)}
                    </td>
                    <td className="px-2 py-3 min-w-[220px]">
                      <CategoryChips completion={run.category_completion} />
                    </td>
                    <td className="tnum px-2 py-3 text-ink-2 whitespace-nowrap">
                      {fmtCost(run.cost_usd_per_task)}
                    </td>
                    <td className="tnum px-2 py-3 text-ink-2 whitespace-nowrap">
                      {run.latency_p50_ms != null ? `${run.latency_p50_ms}ms` : '—'}
                    </td>
                    <td className="px-2 py-3 whitespace-nowrap">
                      <ValidityBadge isPrivate={run.private_split} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
