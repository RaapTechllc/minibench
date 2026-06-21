import { useEffect, useState } from 'react';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend, Customized,
} from 'recharts';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { Benchmark, Stats } from '../api';
import BandwidthBadge from '../components/BandwidthBadge';
import { bandwidthColor } from '../lib/bandwidth';

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

function truncate(str: string, n: number) {
  return str.length > n ? str.slice(0, n - 1) + '…' : str;
}

function relativeTime(dateStr: string) {
  const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  const days = Math.floor(diff / 86400);
  return days === 1 ? 'yesterday' : `${days}d ago`;
}

function linearRegression(data: { x: number; y: number }[]) {
  const n = data.length;
  if (n < 2) return null;
  const meanX = data.reduce((s, d) => s + d.x, 0) / n;
  const meanY = data.reduce((s, d) => s + d.y, 0) / n;
  const num = data.reduce((s, d) => s + (d.x - meanX) * (d.y - meanY), 0);
  const den = data.reduce((s, d) => s + (d.x - meanX) ** 2, 0);
  if (den === 0) return null;
  const slope = num / den;
  const intercept = meanY - slope * meanX;
  const ssTot = data.reduce((s, d) => s + (d.y - meanY) ** 2, 0);
  const ssRes = data.reduce((s, d) => s + (d.y - (slope * d.x + intercept)) ** 2, 0);
  const r2 = ssTot > 0 ? 1 - ssRes / ssTot : 0;
  return { slope, intercept, r2 };
}

type AxisMap = Record<string, { scale?: (v: number) => number }>;

interface ScatterPoint {
  x: number;
  y: number;
  system: string;
}

interface CustomDotProps {
  cx?: number;
  cy?: number;
  payload?: { ram: number; fill?: string };
}

function CustomDot(props: CustomDotProps) {
  const { cx, cy, payload } = props;
  if (!payload) return null;
  const r = Math.max(4, Math.min(16, 3 + Math.sqrt(payload.ram) * 0.8));
  return (
    <circle
      cx={cx} cy={cy} r={r}
      fill={payload.fill || '#6b7280'}
      opacity={0.78}
      stroke={payload.fill || '#6b7280'}
      strokeWidth={0.5}
    />
  );
}

interface ParetoOverlayProps {
  xAxisMap?: AxisMap;
  yAxisMap?: AxisMap;
  pareto: ScatterPoint[];
  top2: ScatterPoint[];
}

function ParetoOverlay(props: ParetoOverlayProps) {
  const { xAxisMap, yAxisMap, pareto, top2 } = props;
  const xScale = Object.values(xAxisMap || {})[0]?.scale;
  const yScale = Object.values(yAxisMap || {})[0]?.scale;
  if (!xScale || !yScale || pareto.length < 2) return null;

  const pts = pareto.map(p => `${xScale(p.x)},${yScale(p.y)}`).join(' ');

  return (
    <g>
      <polyline
        points={pts}
        stroke="#fbbf24"
        strokeWidth={2}
        strokeDasharray="6 3"
        fill="none"
        opacity={0.9}
      />
      {top2.map((pt, i) => {
        const cx = xScale(pt.x);
        const cy = yScale(pt.y);
        const label = truncate(pt.system, 20);
        return (
          <g key={i}>
            <circle cx={cx} cy={cy} r={6} fill="#fbbf24" stroke="#030712" strokeWidth={1.5} />
            <text
              x={cx + 10}
              y={cy}
              fill="#f9fafb"
              fontSize={10}
              fontWeight="700"
              dominantBaseline="middle"
              stroke="#030712"
              strokeWidth={2.5}
              paintOrder="stroke"
            >
              #{i + 1} {label}
            </text>
          </g>
        );
      })}
    </g>
  );
}

interface Regression {
  slope: number;
  intercept: number;
  r2: number;
}

interface BwTrendOverlayProps {
  xAxisMap?: AxisMap;
  yAxisMap?: AxisMap;
  reg: Regression | null;
  xMin: number;
  xMax: number;
}

function BwTrendOverlay(props: BwTrendOverlayProps) {
  const { xAxisMap, yAxisMap, reg, xMin, xMax } = props;
  const xScale = Object.values(xAxisMap || {})[0]?.scale;
  const yScale = Object.values(yAxisMap || {})[0]?.scale;
  if (!xScale || !yScale || !reg) return null;

  const x1 = xScale(xMin);
  const y1 = yScale(reg.slope * xMin + reg.intercept);
  const x2 = xScale(xMax);
  const y2 = yScale(reg.slope * xMax + reg.intercept);

  return (
    <line
      x1={x1} y1={y1} x2={x2} y2={y2}
      stroke="#f59e0b"
      strokeWidth={2}
      strokeDasharray="6 3"
      opacity={0.85}
    />
  );
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

  // Best performer by t/s
  const best = benchmarks.reduce<Benchmark | null>(
    (a, b) => Number(b.tokens_per_second) > Number(a?.tokens_per_second ?? 0) ? b : a,
    null
  );

  // Best HEI
  const bestHei = benchmarks.reduce((max, b) => Math.max(max, b.hei ?? 0), 0) || null;

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

  // Pareto frontier (sorted ascending by t/s, each point must have higher MMLU than all prior)
  const sorted = [...scatterData].sort((a, b) => a.x - b.x);
  const pareto: typeof sorted = [];
  let maxY = -Infinity;
  for (const pt of sorted) {
    if (pt.y > maxY) { pareto.push(pt); maxY = pt.y; }
  }
  // Top 2 are the rightmost Pareto points (highest t/s)
  const paretoTop2 = pareto.length >= 2
    ? [pareto[pareto.length - 1], pareto[pareto.length - 2]]
    : pareto.slice(-1);

  // Bandwidth vs t/s correlation
  const bwData = benchmarks
    .filter(b => b.memory_bandwidth_gbs)
    .map(b => ({
      bandwidth: Number(b.memory_bandwidth_gbs),
      tps: Number(b.tokens_per_second),
      system: b.system_type || 'Unknown',
    }))
    .sort((a, b) => a.bandwidth - b.bandwidth);

  const reg = linearRegression(bwData.map(d => ({ x: d.bandwidth, y: d.tps })));
  const bwXMin = bwData.length > 0 ? bwData[0].bandwidth : 0;
  const bwXMax = bwData.length > 0 ? bwData[bwData.length - 1].bandwidth : 0;

  const systems = [...new Set(benchmarks.map(b => b.system_type).filter(Boolean))];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">MiniBench</h1>
        <p className="text-gray-400 mt-1">
          {best
            ? `${best.system_type} leads at ${Number(best.tokens_per_second).toFixed(1)} t/s — ${stats?.total_submissions ?? 0} runs across ${stats?.unique_systems ?? 0} systems.`
            : 'Crowdsourced LLM inference benchmarks.'}
        </p>
      </div>

      {/* Hero stat strip */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="col-span-2 bg-gray-900 border border-cyan-900/50 rounded-xl p-5">
            <div className="text-xs text-gray-500 uppercase tracking-widest mb-1.5">Top Performer</div>
            <div className="text-xl font-bold text-white truncate">{best?.system_type ?? '—'}</div>
            <div className="flex items-baseline gap-1.5 mt-1">
              <span className="text-4xl font-mono font-bold text-cyan-400">
                {best ? Number(best.tokens_per_second).toFixed(1) : '—'}
              </span>
              <span className="text-base text-cyan-600">t/s</span>
            </div>
            <div className="text-xs text-gray-500 mt-2">
              {best ? `${truncate(best.model_name, 28)} · ${best.quantization}` : ''}
            </div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="text-xs text-gray-500 uppercase tracking-widest mb-1.5">Submissions</div>
            <div className="text-3xl font-bold text-white">{stats.total_submissions}</div>
            <div className="text-xs text-gray-500 mt-2">
              {stats.unique_systems} systems · {stats.unique_models} models
            </div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="text-xs text-gray-500 uppercase tracking-widest mb-1.5">Best HEI</div>
            <div className="text-3xl font-bold text-cyan-400">
              {bestHei ? bestHei.toFixed(2) : '—'}
            </div>
            <div className="text-xs text-gray-500 mt-2">efficiency · value · speed</div>
          </div>
        </div>
      )}

      {/* Efficiency Frontier */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-start justify-between mb-1">
          <h2 className="text-lg font-semibold text-white">Efficiency Frontier</h2>
          <span className="text-xs text-gray-500 mt-1">dot size = RAM (GB)</span>
        </div>
        <p className="text-sm text-gray-400 mb-4">
          Speed (t/s) vs. quality (MMLU). Gold dashed line connects Pareto-optimal systems — best quality at each speed tier.
        </p>
        <ResponsiveContainer width="100%" height={420}>
          <ScatterChart margin={{ top: 20, right: 40, bottom: 40, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="x"
              name="Tokens/sec"
              type="number"
              stroke="#6b7280"
              label={{ value: 'Tokens/sec', position: 'insideBottom', offset: -20, fill: '#9ca3af', fontSize: 12 }}
              tick={{ fill: '#6b7280', fontSize: 11 }}
            />
            <YAxis
              dataKey="y"
              name="MMLU Score"
              type="number"
              stroke="#6b7280"
              label={{ value: 'MMLU Score', angle: -90, position: 'insideLeft', offset: 15, fill: '#9ca3af', fontSize: 12 }}
              tick={{ fill: '#6b7280', fontSize: 11 }}
            />
            <Tooltip
              cursor={{ stroke: '#4b5563', strokeWidth: 1, strokeDasharray: '4 4' }}
              content={({ payload }) => {
                if (!payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm shadow-xl">
                    <div className="font-semibold text-white">{d.system}</div>
                    <div className="text-gray-300">{d.model} ({d.quant})</div>
                    <div className="text-cyan-400">{d.x} t/s</div>
                    <div className="text-gray-400">MMLU: {d.y}</div>
                    <div className={bandwidthColor(d.bw)}>BW: {d.bw} GB/s</div>
                    <div className="text-gray-400">RAM: {d.ram} GB</div>
                  </div>
                );
              }}
            />
            <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '12px' }} />
            {systems.map(sys => (
              <Scatter
                key={sys}
                name={sys!}
                data={scatterData.filter(d => d.system === sys)}
                fill={getColor(sys!)}
                shape={CustomDot}
              />
            ))}
            <Customized component={(chartProps: { xAxisMap?: AxisMap; yAxisMap?: AxisMap }) => (
              <ParetoOverlay {...chartProps} pareto={pareto} top2={paretoTop2} />
            )} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Bandwidth vs Throughput */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-start justify-between mb-1">
          <h2 className="text-lg font-semibold text-white">Memory Bandwidth vs Throughput</h2>
          {reg && (
            <span className="text-xs font-mono text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded mt-0.5">
              R² = {reg.r2.toFixed(3)}
            </span>
          )}
        </div>
        <p className="text-sm text-gray-400 mb-4">
          Near-linear correlation confirms memory bandwidth as the dominant bottleneck.
          {reg && ` Trend: ${reg.slope.toFixed(2)} t/s per GB/s (amber dashed line).`}
        </p>
        <ResponsiveContainer width="100%" height={320}>
          <ScatterChart margin={{ top: 10, right: 40, bottom: 40, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis
              dataKey="bandwidth"
              name="Bandwidth (GB/s)"
              type="number"
              stroke="#6b7280"
              label={{ value: 'Memory Bandwidth (GB/s)', position: 'insideBottom', offset: -20, fill: '#9ca3af', fontSize: 12 }}
              tick={{ fill: '#6b7280', fontSize: 11 }}
            />
            <YAxis
              dataKey="tps"
              name="Tokens/sec"
              type="number"
              stroke="#6b7280"
              label={{ value: 'Tokens/sec', angle: -90, position: 'insideLeft', offset: 15, fill: '#9ca3af', fontSize: 12 }}
              tick={{ fill: '#6b7280', fontSize: 11 }}
            />
            <Tooltip
              cursor={{ stroke: '#4b5563', strokeWidth: 1, strokeDasharray: '4 4' }}
              content={({ payload }) => {
                if (!payload?.length) return null;
                const d = payload[0].payload;
                return (
                  <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm shadow-xl">
                    <div className="font-semibold text-white">{d.system}</div>
                    <div className="text-amber-400">{d.bandwidth} GB/s</div>
                    <div className="text-cyan-400">{d.tps} t/s</div>
                  </div>
                );
              }}
            />
            <Scatter name="Benchmarks" data={bwData} fill="#22d3ee" opacity={0.85} />
            <Customized component={(chartProps: { xAxisMap?: AxisMap; yAxisMap?: AxisMap }) => (
              <BwTrendOverlay {...chartProps} reg={reg} xMin={bwXMin} xMax={bwXMax} />
            )} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Recent Submissions */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Recent Submissions</h2>
          <Link to="/leaderboard" className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors">
            Full leaderboard →
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-gray-400 border-b border-gray-700">
              <tr>
                <th className="pb-2.5 pr-4 font-medium">System</th>
                <th className="pb-2.5 pr-4 font-medium">Model</th>
                <th className="pb-2.5 pr-4 font-medium">Quant</th>
                <th className="pb-2.5 pr-4 font-medium">t/s</th>
                <th className="pb-2.5 pr-4 font-medium">Bandwidth</th>
                <th className="pb-2.5 pr-4 font-medium">RAM</th>
                <th className="pb-2.5 pr-4 font-medium">When</th>
                <th className="pb-2.5 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {benchmarks.slice(0, 10).map((b, idx) => (
                <tr
                  key={b.id}
                  className={`border-b border-gray-800/50 hover:bg-gray-800/40 transition-colors ${idx % 2 === 1 ? 'bg-gray-800/20' : ''}`}
                >
                  <td className="py-2.5 pr-4 text-white font-medium whitespace-nowrap">{b.system_type || '—'}</td>
                  <td className="py-2.5 pr-4 text-gray-300" title={b.model_name}>
                    {truncate(b.model_name, 22)}
                  </td>
                  <td className="py-2.5 pr-4 text-gray-500 font-mono text-xs">{b.quantization}</td>
                  <td className="py-2.5 pr-4 text-cyan-400 font-semibold font-mono">
                    {Number(b.tokens_per_second).toFixed(1)}
                  </td>
                  <td className="py-2.5 pr-4">
                    <BandwidthBadge gbs={b.memory_bandwidth_gbs ? Number(b.memory_bandwidth_gbs) : null} />
                  </td>
                  <td className="py-2.5 pr-4 text-gray-400 text-xs whitespace-nowrap">
                    {Number(b.total_ram_gb)} GB
                  </td>
                  <td className="py-2.5 pr-4 text-gray-500 text-xs whitespace-nowrap">
                    {relativeTime(b.submitted_at)}
                  </td>
                  <td className="py-2.5">
                    <Link
                      to="/leaderboard"
                      className="text-xs text-gray-500 hover:text-cyan-400 transition-colors whitespace-nowrap"
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
