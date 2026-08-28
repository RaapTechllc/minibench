import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api } from '../api';
import type { UsageBoardPayload, UsageBoardRow } from '../api';
import { Card, PageHeader, Skeleton, EmptyState, ErrorState, Badge } from '../components/ui';
import {
  citation,
  formatTokens,
  formatUsdPerMillion,
  modelPageUrl,
  sortByCost,
  sortByLatency,
  sortByTask,
  taskShare,
} from '../lib/usageBoard.js';

type View = 'cost' | 'task' | 'latency';

const VIEWS: { id: View; path: string; label: string }[] = [
  { id: 'cost', path: '/usage/cost', label: 'Best by $' },
  { id: 'task', path: '/usage/task', label: 'Best by task' },
  { id: 'latency', path: '/usage/latency', label: 'Best by latency' },
];

function viewFromPath(pathname: string): View {
  if (pathname.endsWith('/task')) return 'task';
  if (pathname.endsWith('/latency')) return 'latency';
  return 'cost';
}

const TH = 'pb-2 pr-4 text-left text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3';
const TD = 'py-2.5 pr-4 align-middle text-[13px]';

export default function UsageBoard() {
  const { pathname } = useLocation();
  const view = viewFromPath(pathname);
  const [payload, setPayload] = useState<UsageBoardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [task, setTask] = useState('code');

  useEffect(() => {
    let cancelled = false;
    api.getOpenRouterBoard()
      .then((body) => { if (!cancelled) setPayload(body); })
      .catch(() => { if (!cancelled) setError('Could not load the OpenRouter Usage Board snapshot.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const rows = useMemo(() => {
    const all = payload?.rows ?? [];
    if (view === 'task') return sortByTask(all, task);
    if (view === 'latency') return sortByLatency(all);
    return sortByCost(all);
  }, [payload, view, task]);

  const asOf = payload?.meta.as_of ?? '';
  const cite = payload?.meta.citation || (asOf ? citation(asOf) : '');
  const live = payload?.meta.live === true;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="OpenRouter · CC BY 4.0" title="Usage Board">
        Daily-fresh usage, price, and official eval republished from the OpenRouter
        Data API. Not the Mini PC hardware board and not a MiniBench cabinet score.
      </PageHeader>

      <div className="flex flex-wrap items-center gap-2">
        {VIEWS.map((item) => {
          const active = view === item.id;
          return (
            <Link
              key={item.id}
              to={item.path}
              aria-current={active ? 'page' : undefined}
              className={`rounded-lg px-3 py-1.5 text-[13px] font-medium ${
                active ? 'bg-accent-soft text-accent-strong' : 'text-ink-2 hover:bg-surface-2'
              }`}
            >
              {item.label}
            </Link>
          );
        })}
        {view === 'task' && (
          <label className="ml-2 flex items-center gap-2 text-[13px] text-ink-2">
            Task
            <input
              value={task}
              onChange={(e) => setTask(e.target.value)}
              className="rounded-md border border-line bg-surface px-2 py-1 text-[13px] text-ink"
            />
          </label>
        )}
        <Badge tone={live ? 'accent' : 'neutral'}>{live ? 'Live poll' : 'Fixture / cache'}</Badge>
      </div>

      {loading ? (
        <Skeleton rows={8} />
      ) : error ? (
        <ErrorState onRetry={() => {
          setLoading(true);
          setError(null);
          api.getOpenRouterBoard()
            .then((body) => { setPayload(body); })
            .catch(() => setError('Could not load the OpenRouter Usage Board snapshot.'))
            .finally(() => setLoading(false));
        }}>{error}</ErrorState>
      ) : rows.length === 0 ? (
        <EmptyState title="No models fit this compare">
          Nothing on the cached board matches this view. The filter is honest — no invented winner.
        </EmptyState>
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="border-b border-line">
              <tr>
                <th className={TH}>Model</th>
                <th className={TH}>Blended $</th>
                <th className={TH}>Daily tokens</th>
                <th className={TH}>Official eval</th>
                <th className={TH}>Latency</th>
                <th className={TH}>Task share</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <BoardRow key={row.id} row={row} task={task} />
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <p className="text-[12px] leading-relaxed text-ink-3">
        {cite || 'Source: OpenRouter (openrouter.ai/rankings). CC BY 4.0.'}
        {' '}Each number is from the cached snapshot. Recommend (MCP / localhost REST) compares this
        same board and is not mounted on the public API.
      </p>
    </div>
  );
}

function BoardRow({ row, task }: { row: UsageBoardRow; task: string }) {
  const share = taskShare(row, task);
  return (
    <tr className="border-b border-line last:border-0">
      <td className={`${TD} font-medium text-ink`}>
        <a
          href={row.openrouter_url || modelPageUrl(row.id)}
          className="text-accent hover:text-accent-strong"
          target="_blank"
          rel="noreferrer"
        >
          {row.name || row.id}
        </a>
        <div className="text-[11px] font-normal text-ink-3">{row.id}</div>
      </td>
      <td className={`${TD} tnum text-ink`}>{formatUsdPerMillion(row.blended_per_million)}</td>
      <td className={`${TD} tnum text-ink-2`}>{formatTokens(row.daily_tokens)}</td>
      <td className={`${TD} text-ink-2`}>
        {row.eval_score != null ? (
          <>
            <span className="tnum text-ink">{row.eval_score}</span>
            <div className="text-[11px] text-ink-3">{row.eval_source}</div>
          </>
        ) : '—'}
      </td>
      <td className={`${TD} tnum text-ink-2`}>{row.latency_ms != null ? `${row.latency_ms} ms` : '—'}</td>
      <td className={`${TD} tnum text-ink-2`}>{share != null ? `${Math.round(share * 100)}%` : '—'}</td>
    </tr>
  );
}
