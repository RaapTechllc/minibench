import { useEffect, useState } from 'react';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend, LineChart, Line,
} from 'recharts';
import { api } from '../api';
import type { Benchmark, Stats } from '../api';
import StatCard from '../components/StatCard';
import BandwidthBadge, { bandwidthColor } from '../components/BandwidthBadge';

const SYSTEM_COLORS: Record<string, string> = {
  'Mac Mini M4': '#06b6d4',
  'Mac Mini M4 Pro': '#22d3ee',
  'Mac Mini M4 Max': '#67e8f9',
  'Minisforum UM790 Pro': '#f59e0b',
  'Minisforum MS-01': '#d97706',
  'Beelink SER8': '#ef4444',
  'Intel NUC 14 Pro': '#3b82f6',
  'NVIDIA Jetson AGX Orin': '#10b981',
  'Framework 16': '#8b5cf6',
  'Raspberry Pi 5': '#ec4899',
};

function getColor(system: string | null) {
  if (!system) return '#6b7280';
  return SYSTEM_COLORS[system] || '#6b7280';
}

export default function Dashboard() {
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getBenchmarks(), api.getStats()])
      .then(([b, s]) => { setBenchmarks(b); setStats(s); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-gray-400">Loading...</div>;

  // Efficiency Frontier scatter data
  const scatterData = benchmarks.map(b => ({
    x: Number(b.tokens_per_second),
    y: Number(b.model_quality_score ?? 0),
    system: b.system_type || 'Unknown',
    model: b.model_name,
    quant: b.quantization,
    bw: Number(b.memory_bandwidth_gbs ?? 0),
    ram: Number(b.total_ram_gb),
    fill: getColor(b.system_type),
  }));

  // Pareto frontier
  const sorted = [...scatterData].sort((a, b) => a.x - b.x);
  const pareto: typeof sorted = [];
  let maxY = -Infinity;
  for (const pt of sorted) {
    if (pt.y > maxY) { pareto.push(pt); maxY = pt.y; }
  }

  // Bandwidth vs t/s correlation
  const bwData = benchmarks
    .filter(b => b.memory_bandwidth_gbs)
    .map(b => ({
      bandwidth: Number(b.memory_bandwidth_gbs),
      tps: Number(b.tokens_per_second),
      system: b.system_type || 'Unknown',
    }))
    .sort((a, b) => a.bandwidth - b.bandwidth);

  const systems = [...new Set(benchmarks.map(b => b.system_type).filter(Boolean))];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">MiniBench Dashboard</h1>
        <p className="text-gray-400 mt-1">Crowdsourced LLM benchmarks for Mini PCs. Memory bandwidth is king.</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Total Submissions" value={stats.total_submissions} />
          <StatCard label="Unique Systems" value={stats.unique_systems} />
          <StatCard label="Avg t/s" value={stats.avg_tokens_per_second?.toFixed(1) ?? '—'} />
          <StatCard label="Max t/s" value={stats.max_tokens_per_second?.toFixed(1) ?? '—'} />
        </div>
      )}

      {/* Efficiency Frontier */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Efficiency Frontier</h2>
        <p className="text-sm text-gray-400 mb-4">X = Tokens/sec, Y = Model Quality (MMLU). Pareto frontier shows optimal tradeoffs.</p>
        <ResponsiveContainer width="100%" height={400}>
          <ScatterChart margin={{ top: 10, right: 30, bottom: 10, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="x" name="Tokens/sec" type="number" stroke="#6b7280" label={{ value: 'Tokens/sec', position: 'bottom', fill: '#9ca3af' }} />
            <YAxis dataKey="y" name="Model Quality" type="number" stroke="#6b7280" label={{ value: 'MMLU Score', angle: -90, position: 'insideLeft', fill: '#9ca3af' }} />
            <Tooltip
              content={({ payload }) => {
                if (!payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm">
                    <div className="font-semibold text-white">{d.system}</div>
                    <div className="text-gray-300">{d.model} ({d.quant})</div>
                    <div className="text-cyan-400">{d.x} t/s</div>
                    <div className="text-gray-400">MMLU: {d.y}</div>
                    <div className={bandwidthColor(d.bw)}>Bandwidth: {d.bw} GB/s</div>
                    <div className="text-gray-400">System RAM: {d.ram} GB</div>
                  </div>
                );
              }}
            />
            <Legend />
            {systems.map(sys => (
              <Scatter
                key={sys}
                name={sys!}
                data={scatterData.filter(d => d.system === sys)}
                fill={getColor(sys!)}
              />
            ))}
            {pareto.length > 1 && (
              <Scatter name="Pareto Frontier" data={pareto} fill="none" line={{ stroke: '#fbbf24', strokeWidth: 2, strokeDasharray: '5 5' }} shape={() => null} />
            )}
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Bandwidth vs t/s correlation */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-2">Memory Bandwidth vs Throughput</h2>
        <p className="text-sm text-gray-400 mb-4">Near-linear correlation expected for memory-bound LLM inference.</p>
        <ResponsiveContainer width="100%" height={300}>
          <ScatterChart margin={{ top: 10, right: 30, bottom: 10, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="bandwidth" name="Bandwidth (GB/s)" type="number" stroke="#6b7280" label={{ value: 'Memory Bandwidth (GB/s)', position: 'bottom', fill: '#9ca3af' }} />
            <YAxis dataKey="tps" name="Tokens/sec" type="number" stroke="#6b7280" label={{ value: 'Tokens/sec', angle: -90, position: 'insideLeft', fill: '#9ca3af' }} />
            <Tooltip
              content={({ payload }) => {
                if (!payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm">
                    <div className="font-semibold text-white">{d.system}</div>
                    <div className="text-yellow-400">{d.bandwidth} GB/s</div>
                    <div className="text-cyan-400">{d.tps} t/s</div>
                  </div>
                );
              }}
            />
            <Scatter name="Benchmarks" data={bwData} fill="#22d3ee" />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Recent submissions */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Recent Submissions</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-gray-400 border-b border-gray-800">
              <tr>
                <th className="pb-2 pr-4">System</th>
                <th className="pb-2 pr-4">Model</th>
                <th className="pb-2 pr-4">Quant</th>
                <th className="pb-2 pr-4">t/s</th>
                <th className="pb-2 pr-4">TTFT</th>
                <th className="pb-2 pr-4">Bandwidth</th>
                <th className="pb-2 pr-4">System RAM</th>
                <th className="pb-2">VRAM</th>
              </tr>
            </thead>
            <tbody>
              {benchmarks.slice(0, 10).map(b => (
                <tr key={b.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="py-2 pr-4 text-white">{b.system_type || '—'}</td>
                  <td className="py-2 pr-4">{b.model_name}</td>
                  <td className="py-2 pr-4 text-gray-400">{b.quantization}</td>
                  <td className="py-2 pr-4 text-cyan-400 font-semibold">{Number(b.tokens_per_second).toFixed(1)}</td>
                  <td className="py-2 pr-4 text-gray-400">{b.time_to_first_token ? `${Number(b.time_to_first_token).toFixed(2)}s` : '—'}</td>
                  <td className="py-2 pr-4"><BandwidthBadge gbs={b.memory_bandwidth_gbs ? Number(b.memory_bandwidth_gbs) : null} /></td>
                  <td className="py-2 pr-4">{Number(b.total_ram_gb)} GB</td>
                  <td className="py-2">{b.vram_gb ? <span className="text-purple-400">{Number(b.vram_gb)} GB</span> : <span className="text-gray-600">—</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
