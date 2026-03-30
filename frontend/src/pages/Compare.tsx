import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { api } from '../api';
import type { Benchmark } from '../api';
import BandwidthBadge from '../components/BandwidthBadge';

export default function Compare() {
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [idA, setIdA] = useState<number | null>(null);
  const [idB, setIdB] = useState<number | null>(null);
  const [compare, setCompare] = useState<{ a: Benchmark; b: Benchmark } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getBenchmarks({ limit: '50' }).then(b => {
      setBenchmarks(b);
      if (b.length >= 2) { setIdA(b[0].id); setIdB(b[1].id); }
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (idA && idB) {
      api.getCompare(idA, idB).then(setCompare);
    }
  }, [idA, idB]);

  if (loading) return <div className="text-center py-20 text-gray-400">Loading...</div>;

  const barData = compare ? [
    { metric: 'Tokens/sec', A: Number(compare.a.tokens_per_second), B: Number(compare.b.tokens_per_second) },
    { metric: 'Bandwidth (GB/s)', A: Number(compare.a.memory_bandwidth_gbs ?? 0), B: Number(compare.b.memory_bandwidth_gbs ?? 0) },
    { metric: 'System RAM (GB)', A: Number(compare.a.total_ram_gb), B: Number(compare.b.total_ram_gb) },
    { metric: 'MMLU', A: Number(compare.a.model_quality_score ?? 0), B: Number(compare.b.model_quality_score ?? 0) },
  ] : [];

  function Card({ b, label }: { b: Benchmark; label: string }) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex-1">
        <div className="text-xs text-gray-500 mb-1">{label}</div>
        <div className="text-xl font-bold text-white mb-3">{b.system_type || 'Unknown'}</div>
        <div className="space-y-2 text-sm">
          <Row label="CPU" value={b.cpu_model} />
          <Row label="System RAM" value={`${Number(b.total_ram_gb)} GB ${b.memory_type || ''}`} />
          <Row label="VRAM" value={b.vram_gb ? `${Number(b.vram_gb)} GB` : 'None (System RAM only)'} highlight={!!b.vram_gb} />
          <div className="flex justify-between">
            <span className="text-gray-400">Bandwidth</span>
            <BandwidthBadge gbs={b.memory_bandwidth_gbs ? Number(b.memory_bandwidth_gbs) : null} />
          </div>
          <Row label="Model" value={`${b.model_name} (${b.quantization})`} />
          <Row label="Engine" value={b.inference_engine} />
          <Row label="t/s" value={Number(b.tokens_per_second).toFixed(1)} highlight />
          <Row label="TTFT" value={b.time_to_first_token ? `${Number(b.time_to_first_token).toFixed(2)}s` : '—'} />
          <Row label="HEI" value={b.hei?.toFixed(2) ?? '—'} highlight />
          <Row label="Price" value={b.hardware_price_usd ? `$${Number(b.hardware_price_usd).toLocaleString()}` : '—'} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Compare Hardware</h1>
        <p className="text-gray-400 mt-1">Side-by-side comparison of benchmark results.</p>
      </div>

      <div className="flex gap-4 flex-wrap">
        <select
          value={idA ?? ''}
          onChange={e => setIdA(Number(e.target.value))}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 flex-1 min-w-[200px]"
        >
          {benchmarks.map(b => (
            <option key={b.id} value={b.id}>{b.system_type || b.cpu_model} — {b.model_name} ({b.quantization})</option>
          ))}
        </select>
        <span className="text-gray-500 self-center">vs</span>
        <select
          value={idB ?? ''}
          onChange={e => setIdB(Number(e.target.value))}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 flex-1 min-w-[200px]"
        >
          {benchmarks.map(b => (
            <option key={b.id} value={b.id}>{b.system_type || b.cpu_model} — {b.model_name} ({b.quantization})</option>
          ))}
        </select>
      </div>

      {compare && (
        <>
          <div className="flex gap-4 flex-col md:flex-row">
            <Card b={compare.a} label="System A" />
            <Card b={compare.b} label="System B" />
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Metric Comparison</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={barData} margin={{ top: 10, right: 30, bottom: 10, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="metric" stroke="#6b7280" />
                <YAxis stroke="#6b7280" />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} />
                <Legend />
                <Bar dataKey="A" name={compare.a.system_type || 'A'} fill="#22d3ee" radius={[4, 4, 0, 0]} />
                <Bar dataKey="B" name={compare.b.system_type || 'B'} fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}

function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-400">{label}</span>
      <span className={highlight ? 'text-cyan-400 font-semibold' : 'text-gray-200'}>{value}</span>
    </div>
  );
}
