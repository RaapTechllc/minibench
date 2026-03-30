import { useEffect, useState } from 'react';
import { api } from '../api';
import type { LeaderboardEntry } from '../api';
import BandwidthBadge from '../components/BandwidthBadge';

export default function Leaderboard() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [sortBy, setSortBy] = useState('hei');
  const [modelFilter, setModelFilter] = useState('');
  const [quantFilter, setQuantFilter] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params: Record<string, string> = { sort_by: sortBy };
    if (modelFilter) params.model = modelFilter;
    if (quantFilter) params.quantization = quantFilter;
    api.getLeaderboard(params).then(setEntries).finally(() => setLoading(false));
  }, [sortBy, modelFilter, quantFilter]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Leaderboard</h1>
        <p className="text-gray-400 mt-1">Ranked by Hardware Efficiency Index (HEI) = (t/s x MMLU) / Price</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <select
          value={sortBy}
          onChange={e => setSortBy(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200"
        >
          <option value="hei">Sort: HEI</option>
          <option value="tokens_per_second">Sort: Tokens/sec</option>
          <option value="memory_bandwidth_gbs">Sort: Bandwidth</option>
        </select>
        <input
          placeholder="Filter by model..."
          value={modelFilter}
          onChange={e => setModelFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 w-48"
        />
        <input
          placeholder="Filter by quantization..."
          value={quantFilter}
          onChange={e => setQuantFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-200 w-48"
        />
      </div>

      {loading ? (
        <div className="text-center py-10 text-gray-400">Loading...</div>
      ) : (
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-gray-400 border-b border-gray-800 bg-gray-900/50">
              <tr>
                <th className="p-3">Rank</th>
                <th className="p-3">System</th>
                <th className="p-3">CPU</th>
                <th className="p-3">System RAM</th>
                <th className="p-3">VRAM</th>
                <th className="p-3">Model</th>
                <th className="p-3">Quant</th>
                <th className="p-3">t/s</th>
                <th className="p-3">TTFT</th>
                <th className="p-3 font-semibold text-yellow-400">Bandwidth</th>
                <th className="p-3">MMLU</th>
                <th className="p-3">Price</th>
                <th className="p-3 font-semibold text-cyan-400">HEI</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(e => (
                <tr key={e.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="p-3 text-gray-500 font-mono">#{e.rank}</td>
                  <td className="p-3 text-white font-medium">{e.system_type || '—'}</td>
                  <td className="p-3 text-gray-300 text-xs">{e.cpu_model}</td>
                  <td className="p-3">{Number(e.total_ram_gb)} GB</td>
                  <td className="p-3">{e.vram_gb ? <span className="text-purple-400">{Number(e.vram_gb)} GB</span> : <span className="text-gray-600">—</span>}</td>
                  <td className="p-3">{e.model_name}</td>
                  <td className="p-3 text-gray-400">{e.quantization}</td>
                  <td className="p-3 text-cyan-400 font-semibold">{Number(e.tokens_per_second).toFixed(1)}</td>
                  <td className="p-3 text-gray-400">{e.time_to_first_token ? `${Number(e.time_to_first_token).toFixed(2)}s` : '—'}</td>
                  <td className="p-3"><BandwidthBadge gbs={e.memory_bandwidth_gbs ? Number(e.memory_bandwidth_gbs) : null} /></td>
                  <td className="p-3 text-gray-300">{e.model_quality_score ? Number(e.model_quality_score).toFixed(1) : '—'}</td>
                  <td className="p-3 text-gray-300">{e.hardware_price_usd ? `$${Number(e.hardware_price_usd).toLocaleString()}` : '—'}</td>
                  <td className="p-3 text-cyan-400 font-bold">{e.hei?.toFixed(2) ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
