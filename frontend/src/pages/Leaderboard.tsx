import { useEffect, useState } from 'react';
import { api } from '../api';
import type { LeaderboardEntry } from '../api';
import BandwidthBadge from '../components/BandwidthBadge';

function systemBadge(system: string | null, cpu: string) {
  const s = (system ?? '').toLowerCase();
  const c = cpu.toLowerCase();
  if (s.includes('mac') || c.includes('apple') || /\bm[1-4]\b/.test(c))
    return { label: 'Apple', cls: 'text-sky-400 bg-sky-400/10 border border-sky-400/25' };
  if (s.includes('nvidia') || s.includes('jetson') || c.includes('nvidia'))
    return { label: 'NVIDIA', cls: 'text-green-400 bg-green-400/10 border border-green-400/25' };
  if (s.includes('raspberry') || c.includes('broadcom') || c.includes('cortex'))
    return { label: 'ARM', cls: 'text-purple-400 bg-purple-400/10 border border-purple-400/25' };
  if (c.includes('intel') || s.includes('intel') || s.includes('nuc') || s.includes('framework'))
    return { label: 'Intel', cls: 'text-blue-400 bg-blue-400/10 border border-blue-400/25' };
  if (c.includes('amd') || c.includes('ryzen') || s.includes('minisforum') || s.includes('beelink'))
    return { label: 'AMD', cls: 'text-red-400 bg-red-400/10 border border-red-400/25' };
  return { label: system?.split(' ')[0] ?? 'PC', cls: 'text-gray-400 bg-gray-400/10 border border-gray-400/20' };
}

function MedalCell({ rank }: { rank: number }) {
  if (rank === 1)
    return (
      <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-yellow-500/20 text-yellow-400 font-bold text-xs border border-yellow-500/40">
        1
      </span>
    );
  if (rank === 2)
    return (
      <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-gray-400/15 text-gray-300 font-bold text-xs border border-gray-400/30">
        2
      </span>
    );
  if (rank === 3)
    return (
      <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-amber-700/20 text-amber-500 font-bold text-xs border border-amber-600/35">
        3
      </span>
    );
  return <span className="text-gray-500 font-mono text-sm">#{rank}</span>;
}

export default function Leaderboard() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [sortBy, setSortBy] = useState('hei');
  const [modelFilter, setModelFilter] = useState('');
  const [quantFilter, setQuantFilter] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Show the spinner while we refetch on a sort/filter change. This intentional
    // setState-in-effect drives the refetch loading state and is safe here.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    const params: Record<string, string> = { sort_by: sortBy };
    if (modelFilter) params.model = modelFilter;
    if (quantFilter) params.quantization = quantFilter;
    api.getLeaderboard(params).then(setEntries).finally(() => setLoading(false));
  }, [sortBy, modelFilter, quantFilter]);

  const maxTps = entries.length > 0 ? Math.max(...entries.map(e => Number(e.tokens_per_second))) : 1;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Leaderboard</h1>
        <p className="text-gray-400 mt-1">
          Ranked by Hardware Efficiency Index — (t/s × MMLU) / Price. Higher is better.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:outline-none focus:border-gray-600"
        >
          <option value="hei">Sort: HEI</option>
          <option value="tokens_per_second">Sort: Tokens/sec</option>
          <option value="memory_bandwidth_gbs">Sort: Bandwidth</option>
        </select>
        <input
          placeholder="Filter by model..."
          value={modelFilter}
          onChange={e => setModelFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 w-48 focus:outline-none focus:border-gray-600"
        />
        <input
          placeholder="Filter by quantization..."
          value={quantFilter}
          onChange={e => setQuantFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 w-48 focus:outline-none focus:border-gray-600"
        />
      </div>

      {loading ? (
        <div className="text-center py-10 text-gray-400">Loading...</div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-gray-400 border-b border-gray-700 bg-gray-900 sticky top-14 z-10">
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
                <th className="p-3 font-medium text-yellow-400 whitespace-nowrap">Bandwidth</th>
                <th className="p-3 font-medium whitespace-nowrap">MMLU</th>
                <th className="p-3 font-medium whitespace-nowrap">Price</th>
                <th className="p-3 font-medium text-cyan-400 whitespace-nowrap">HEI</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e, idx) => {
                const badge = systemBadge(e.system_type, e.cpu_model);
                const tpsPct = Math.max(2, (Number(e.tokens_per_second) / maxTps) * 100);
                return (
                  <tr
                    key={e.id}
                    className={`border-b border-gray-800/50 hover:bg-gray-800/40 transition-colors ${idx % 2 === 1 ? 'bg-gray-800/20' : ''}`}
                  >
                    <td className="p-3">
                      <MedalCell rank={e.rank} />
                    </td>
                    <td className="p-3">
                      <div className="flex flex-col gap-1.5">
                        <span className="text-white font-medium whitespace-nowrap">{e.system_type || '—'}</span>
                        <span className={`inline-flex items-center self-start px-1.5 py-0.5 rounded text-xs font-semibold ${badge.cls}`}>
                          {badge.label}
                        </span>
                      </div>
                    </td>
                    <td className="p-3 text-gray-400 text-xs max-w-[140px] truncate" title={e.cpu_model}>
                      {e.cpu_model}
                    </td>
                    <td className="p-3 text-gray-300 whitespace-nowrap">{Number(e.total_ram_gb)} GB</td>
                    <td className="p-3 whitespace-nowrap">
                      {e.vram_gb
                        ? <span className="text-purple-400">{Number(e.vram_gb)} GB</span>
                        : <span className="text-gray-600">—</span>}
                    </td>
                    <td className="p-3 text-gray-300 max-w-[160px] truncate" title={e.model_name}>
                      {e.model_name}
                    </td>
                    <td className="p-3 text-gray-500 font-mono text-xs whitespace-nowrap">{e.quantization}</td>
                    <td className="p-3">
                      <div className="flex items-center gap-2 min-w-[90px]">
                        <span className="text-cyan-400 font-semibold font-mono text-sm w-10 shrink-0 text-right">
                          {Number(e.tokens_per_second).toFixed(0)}
                        </span>
                        <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden min-w-[40px]">
                          <div
                            className="h-full bg-cyan-400 rounded-full"
                            style={{ width: `${tpsPct}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="p-3 text-gray-400 whitespace-nowrap">
                      {e.time_to_first_token ? `${Number(e.time_to_first_token).toFixed(2)}s` : '—'}
                    </td>
                    <td className="p-3">
                      <BandwidthBadge gbs={e.memory_bandwidth_gbs ? Number(e.memory_bandwidth_gbs) : null} />
                    </td>
                    <td className="p-3 text-gray-300 whitespace-nowrap">
                      {e.model_quality_score ? Number(e.model_quality_score).toFixed(1) : '—'}
                    </td>
                    <td className="p-3 text-gray-300 whitespace-nowrap">
                      {e.hardware_price_usd ? `$${Number(e.hardware_price_usd).toLocaleString()}` : '—'}
                    </td>
                    <td className="p-3">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-md bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 font-bold text-sm tabular-nums whitespace-nowrap">
                        {e.hei?.toFixed(2) ?? '—'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
