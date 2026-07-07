import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { LeaderboardEntry } from '../api';
import BandwidthBadge from '../components/BandwidthBadge';
import { PageHeader, Card, Select, Skeleton, EmptyState, ErrorState } from '../components/ui';

function systemBadge(system: string | null, cpu: string) {
  const s = (system ?? '').toLowerCase();
  const c = cpu.toLowerCase();
  if (s.includes('mac') || c.includes('apple') || /\bm[1-4]\b/.test(c))
    return { label: 'Apple', cls: 'text-accent-strong bg-accent-soft' };
  if (s.includes('nvidia') || s.includes('jetson') || c.includes('nvidia'))
    return { label: 'NVIDIA', cls: 'text-pass bg-pass-soft' };
  if (s.includes('raspberry') || c.includes('broadcom') || c.includes('cortex'))
    return { label: 'ARM', cls: 'text-violet-700 bg-violet-50' };
  if (c.includes('intel') || s.includes('intel') || s.includes('nuc') || s.includes('framework'))
    return { label: 'Intel', cls: 'text-accent bg-accent-soft' };
  if (c.includes('amd') || c.includes('ryzen') || s.includes('minisforum') || s.includes('beelink'))
    return { label: 'AMD', cls: 'text-fail bg-fail-soft' };
  return { label: system?.split(' ')[0] ?? 'PC', cls: 'text-ink-2 bg-surface-2' };
}

function MedalCell({ rank }: { rank: number }) {
  if (rank === 1)
    return (
      <span className="tnum inline-flex items-center justify-center w-7 h-7 rounded-full bg-frontier-soft text-frontier font-bold text-xs border border-frontier/30">
        1
      </span>
    );
  if (rank === 2)
    return (
      <span className="tnum inline-flex items-center justify-center w-7 h-7 rounded-full bg-surface-2 text-ink-2 font-bold text-xs border border-line-strong">
        2
      </span>
    );
  if (rank === 3)
    return (
      <span className="tnum inline-flex items-center justify-center w-7 h-7 rounded-full bg-surface-2 text-ink-3 font-bold text-xs border border-line">
        3
      </span>
    );
  return <span className="tnum text-ink-3 text-sm">#{rank}</span>;
}

export default function Leaderboard() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [sortBy, setSortBy] = useState('hei');
  const [modelFilter, setModelFilter] = useState('');
  const [quantFilter, setQuantFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(false);
    const params: Record<string, string> = { sort_by: sortBy };
    if (modelFilter) params.model = modelFilter;
    if (quantFilter) params.quantization = quantFilter;
    api
      .getLeaderboard(params)
      .then(setEntries)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [sortBy, modelFilter, quantFilter]);

  useEffect(() => {
    // Show the spinner while we refetch on a sort/filter change. This intentional
    // setState-in-effect drives the refetch loading state and is safe here.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const maxTps = entries.length > 0 ? Math.max(...entries.map(e => Number(e.tokens_per_second))) : 1;

  const inputCls =
    'rounded-lg border border-line-strong bg-surface px-3 py-1.5 text-[13px] text-ink w-48 ' +
    'placeholder:text-ink-3 hover:border-ink-3 focus:border-accent transition-colors';

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Hardware" title="Leaderboard">
        Ranked by Hardware Efficiency Index — (t/s × MMLU) / Price. Higher is better.
      </PageHeader>

      <div className="flex flex-wrap items-center gap-3 animate-rise rise-1">
        <Select label="Sort" value={sortBy} onChange={e => setSortBy(e.target.value)}>
          <option value="hei">HEI</option>
          <option value="tokens_per_second">Tokens/sec</option>
          <option value="memory_bandwidth_gbs">Bandwidth</option>
        </Select>
        <input
          placeholder="Filter by model..."
          value={modelFilter}
          onChange={e => setModelFilter(e.target.value)}
          className={inputCls}
        />
        <input
          placeholder="Filter by quantization..."
          value={quantFilter}
          onChange={e => setQuantFilter(e.target.value)}
          className={inputCls}
        />
      </div>

      {loading ? (
        <Skeleton rows={8} />
      ) : error ? (
        <ErrorState onRetry={load}>The leaderboard couldn't be fetched. Check your connection and try again.</ErrorState>
      ) : entries.length === 0 ? (
        <EmptyState title="No results">No benchmarks match these filters. Try clearing the model or quantization filter.</EmptyState>
      ) : (
        <Card className="overflow-x-auto animate-rise rise-1">
          <table className="w-full text-sm text-left">
            <thead className="text-ink-2 border-b border-line bg-surface sticky top-14 z-10">
              <tr>
                <th className="p-3 font-medium whitespace-nowrap">Rank</th>
                <th className="p-3 font-medium whitespace-nowrap">System</th>
                <th className="p-3 font-medium whitespace-nowrap">CPU</th>
                <th className="p-3 font-medium whitespace-nowrap">RAM</th>
                <th className="p-3 font-medium whitespace-nowrap">VRAM</th>
                <th className="p-3 font-medium whitespace-nowrap">Model</th>
                <th className="p-3 font-medium whitespace-nowrap">Quant</th>
                <th className="p-3 font-medium whitespace-nowrap">t/s</th>
                <th className="p-3 font-medium whitespace-nowrap">TTFT</th>
                <th className="p-3 font-medium text-frontier whitespace-nowrap">Bandwidth</th>
                <th className="p-3 font-medium whitespace-nowrap">MMLU</th>
                <th className="p-3 font-medium whitespace-nowrap">Price</th>
                <th className="p-3 font-medium text-accent whitespace-nowrap">HEI</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, idx) => {
                const badge = systemBadge(e.system_type, e.cpu_model);
                const tpsPct = Math.max(2, (Number(e.tokens_per_second) / maxTps) * 100);
                return (
                  <tr
                    key={e.id}
                    className={`border-b border-line hover:bg-surface-2 transition-colors ${idx % 2 === 1 ? 'bg-surface-2' : ''}`}
                  >
                    <td className="p-3">
                      <MedalCell rank={e.rank} />
                    </td>
                    <td className="p-3">
                      <div className="flex flex-col gap-1.5">
                        <Link
                          to={`/benchmarks/${e.id}`}
                          className="text-ink font-medium whitespace-nowrap hover:text-accent transition-colors"
                        >
                          {e.system_type || `#${e.id}`}
                        </Link>
                        <span className={`inline-flex items-center self-start px-1.5 py-0.5 rounded text-xs font-semibold ${badge.cls}`}>
                          {badge.label}
                        </span>
                      </div>
                    </td>
                    <td className="p-3 text-ink-2 text-xs max-w-[140px] truncate" title={e.cpu_model}>
                      {e.cpu_model}
                    </td>
                    <td className="p-3 text-ink whitespace-nowrap">
                      <span className="tnum">{Number(e.total_ram_gb)}</span> GB
                    </td>
                    <td className="p-3 whitespace-nowrap">
                      {e.vram_gb
                        ? <span className="text-accent"><span className="tnum">{Number(e.vram_gb)}</span> GB</span>
                        : <span className="text-ink-3">—</span>}
                    </td>
                    <td className="p-3 text-ink max-w-[160px] truncate" title={e.model_name}>
                      {e.model_name}
                    </td>
                    <td className="p-3 text-ink-3 tnum text-xs whitespace-nowrap">{e.quantization}</td>
                    <td className="p-3">
                      <div className="flex items-center gap-2 min-w-[90px]">
                        <span className="tnum text-accent font-semibold text-sm w-10 shrink-0 text-right">
                          {Number(e.tokens_per_second).toFixed(0)}
                        </span>
                        <div className="flex-1 h-1.5 bg-line rounded-full overflow-hidden min-w-[40px]">
                          <div
                            className="h-full bg-accent rounded-full"
                            style={{ width: `${tpsPct}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="p-3 text-ink-2 whitespace-nowrap tnum">
                      {e.time_to_first_token ? `${Number(e.time_to_first_token).toFixed(2)}s` : '—'}
                    </td>
                    <td className="p-3">
                      <BandwidthBadge gbs={e.memory_bandwidth_gbs ? Number(e.memory_bandwidth_gbs) : null} />
                    </td>
                    <td className="p-3 text-ink whitespace-nowrap tnum">
                      {e.model_quality_score ? Number(e.model_quality_score).toFixed(1) : '—'}
                    </td>
                    <td className="p-3 text-ink whitespace-nowrap tnum">
                      {e.hardware_price_usd ? `$${Number(e.hardware_price_usd).toLocaleString()}` : '—'}
                    </td>
                    <td className="p-3">
                      <span className="tnum inline-flex items-center px-2.5 py-1 rounded-md bg-accent-soft text-accent-strong font-bold text-sm whitespace-nowrap">
                        {e.hei?.toFixed(2) ?? '—'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
