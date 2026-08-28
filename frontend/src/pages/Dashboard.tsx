import { useEffect, useState } from 'react';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Customized,
} from 'recharts';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { Benchmark, Stats } from '../api';
import BandwidthBadge from '../components/BandwidthBadge';
import {
  Card, CardHeader, Stat, Badge, Skeleton, ErrorState,
} from '../components/ui';
import { CHART, TooltipCard, axisProps } from '../components/chart';

/* Categorical identity colours per system — kept as a quiet signal (a swatch in
   the tooltip), never as chart-wide colour: the figures speak in one blue. */
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
  if (!system) return CHART.ink3;
  return SYSTEM_COLORS[system] || CHART.ink3;
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
  payload?: { ram: number };
}

/* Dot size encodes RAM; every dot is the single accent blue. */
function CustomDot(props: CustomDotProps) {
  const { cx, cy, payload } = props;
  if (!payload) return null;
  const r = Math.max(4, Math.min(16, 3 + Math.sqrt(payload.ram) * 0.8));
  return (
    <circle
      cx={cx} cy={cy} r={r}
      fill={CHART.accent}
      fillOpacity={0.7}
      stroke="#fff"
      strokeWidth={1}
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
        stroke={CHART.frontier}
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
            <circle cx={cx} cy={cy} r={6} fill={CHART.frontier} stroke="#fff" strokeWidth={1.5} />
            <text
              x={cx + 10}
              y={cy}
              fill={CHART.ink3}
              fontSize={10}
              fontWeight="700"
              dominantBaseline="middle"
              stroke="#fff"
              strokeWidth={3}
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
      stroke={CHART.accent}
      strokeWidth={2}
      strokeDasharray="6 3"
      opacity={0.85}
    />
  );
}

const axisLabel = { fill: CHART.ink3, fontSize: 12 } as const;

export default function Dashboard() {
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  function load() {
    setLoading(true);
    setError(false);
    Promise.all([api.getBenchmarks(), api.getStats()])
      .then(([b, s]) => { setBenchmarks(b); setStats(s); })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  if (loading) {
    return (
      <div className="space-y-10">
        <div className="animate-rise space-y-4">
          <div className="h-10 w-2/3 rounded-lg bg-surface-2 animate-pulse" />
          <div className="h-5 w-1/2 rounded-lg bg-surface-2 animate-pulse" />
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 rounded-xl bg-surface-2 animate-pulse" />
          ))}
        </div>
        <Skeleton rows={8} />
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState onRetry={load}>
        We couldn't reach the benchmark API. Check your connection and try again.
      </ErrorState>
    );
  }

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

  return (
    <div className="space-y-12">
      {/* Hero — a thesis, not a tile */}
      <section className="animate-rise max-w-3xl pt-2">
        <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent mb-3">
          Model capability, measured
        </div>
        <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight text-ink leading-[1.05]">
          Deterministic minibenchmarks for frontier and open-weight models.
        </h1>
        <p className="mt-4 text-[17px] leading-relaxed text-ink-2">
          Controlled suites with executable oracles — pass rates, cost per task, and confidence
          intervals on pinned reference profiles.{' '}
          <Link to="/models" className="text-accent hover:text-accent-strong font-medium">
            See model rankings →
          </Link>
        </p>
        <p className="mt-3 text-[15px] leading-relaxed text-ink-2">
          Agent harnesses scored on pinned real-work fixtures — never mixed with Solo or
          Multiplayer scores — live in the{' '}
          <Link to="/agent-cabinet" className="text-accent hover:text-accent-strong font-medium">
            Real-Work Agent Cabinet →
          </Link>
        </p>
      </section>

      {/* Stat strip */}
      {stats && (
        <div className="animate-rise rise-1 grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat
            label="Legacy top t/s"
            accent
            value={<>{best ? Number(best.tokens_per_second).toFixed(1) : '—'}<span className="text-lg text-ink-3 font-normal"> t/s</span></>}
            sub={best ? `${truncate(best.system_type ?? '—', 20)} · ${best.quantization}` : undefined}
          />
          <Stat
            label="Legacy submissions"
            value={stats.total_submissions}
            sub={`${stats.unique_systems} systems · ${stats.unique_models} models`}
          />
          <Stat
            label="Legacy best HEI"
            accent
            value={bestHei ? bestHei.toFixed(2) : '—'}
            sub="uncontrolled matrix"
          />
          <Stat
            label="Peak throughput"
            value={stats.max_tokens_per_second != null ? Number(stats.max_tokens_per_second).toFixed(0) : '—'}
            sub={stats.avg_tokens_per_second != null ? `${Number(stats.avg_tokens_per_second).toFixed(1)} t/s average` : undefined}
          />
        </div>
      )}

      {/* Efficiency Frontier */}
      {/* Legacy community throughput — retained for reference, not ranked */}
      <Card className="animate-rise rise-2">
        <CardHeader
          title="Efficiency Frontier"
          sub="Legacy community submissions — uncontrolled matrix of hardware × engine × model. Not comparable across rows; see Models for official capability scores."
          right={<span className="text-[11px] text-ink-3">dot size = RAM (GB)</span>}
        />
        <div className="px-2 pb-4">
          <ResponsiveContainer width="100%" height={420}>
            <ScatterChart margin={{ top: 20, right: 40, bottom: 40, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
              <XAxis
                dataKey="x"
                name="Tokens/sec"
                type="number"
                {...axisProps}
                label={{ value: 'Tokens/sec', position: 'insideBottom', offset: -20, ...axisLabel }}
              />
              <YAxis
                dataKey="y"
                name="MMLU Score"
                type="number"
                {...axisProps}
                label={{ value: 'MMLU Score', angle: -90, position: 'insideLeft', offset: 15, ...axisLabel }}
              />
              <Tooltip
                cursor={{ stroke: CHART.line, strokeWidth: 1, strokeDasharray: '4 4' }}
                content={({ payload }) => {
                  if (!payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <TooltipCard>
                      <div className="flex items-center gap-1.5 font-semibold text-ink">
                        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: d.fill }} />
                        {d.system}
                      </div>
                      <div className="text-ink-2">{d.model} ({d.quant})</div>
                      <div className="tnum text-accent mt-1">{d.x} t/s</div>
                      <div className="tnum text-ink-2">MMLU {d.y}</div>
                      <div className="tnum text-frontier">{d.bw} GB/s</div>
                      <div className="tnum text-ink-3">{d.ram} GB RAM</div>
                    </TooltipCard>
                  );
                }}
              />
              <Scatter name="Benchmarks" data={scatterData} fill={CHART.accent} shape={CustomDot} />
              <Customized component={(chartProps: { xAxisMap?: AxisMap; yAxisMap?: AxisMap }) => (
                <ParetoOverlay {...chartProps} pareto={pareto} top2={paretoTop2} />
              )} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Bandwidth vs Throughput */}
      <Card className="animate-rise rise-2">
        <CardHeader
          title="Memory Bandwidth vs Throughput"
          sub={
            reg
              ? `Near-linear correlation confirms bandwidth as the dominant bottleneck. Trend: ${reg.slope.toFixed(2)} t/s per GB/s (blue line).`
              : 'Near-linear correlation confirms memory bandwidth as the dominant bottleneck.'
          }
          right={reg ? <Badge tone="frontier"><span className="tnum">R² = {reg.r2.toFixed(3)}</span></Badge> : undefined}
        />
        <div className="px-2 pb-4">
          <ResponsiveContainer width="100%" height={320}>
            <ScatterChart margin={{ top: 10, right: 40, bottom: 40, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} />
              <XAxis
                dataKey="bandwidth"
                name="Bandwidth (GB/s)"
                type="number"
                {...axisProps}
                label={{ value: 'Memory Bandwidth (GB/s)', position: 'insideBottom', offset: -20, ...axisLabel }}
              />
              <YAxis
                dataKey="tps"
                name="Tokens/sec"
                type="number"
                {...axisProps}
                label={{ value: 'Tokens/sec', angle: -90, position: 'insideLeft', offset: 15, ...axisLabel }}
              />
              <Tooltip
                cursor={{ stroke: CHART.line, strokeWidth: 1, strokeDasharray: '4 4' }}
                content={({ payload }) => {
                  if (!payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <TooltipCard>
                      <div className="font-semibold text-ink">{d.system}</div>
                      <div className="tnum text-frontier mt-1">{d.bandwidth} GB/s</div>
                      <div className="tnum text-accent">{d.tps} t/s</div>
                    </TooltipCard>
                  );
                }}
              />
              <Scatter name="Benchmarks" data={bwData} fill={CHART.accent} fillOpacity={0.8} />
              <Customized component={(chartProps: { xAxisMap?: AxisMap; yAxisMap?: AxisMap }) => (
                <BwTrendOverlay {...chartProps} reg={reg} xMin={bwXMin} xMax={bwXMax} />
              )} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Recent Submissions */}
      <Card className="animate-rise rise-2">
        <CardHeader
          title="Recent submissions"
          sub="Legacy crowdsourced throughput data — each row mixes different hardware, engines, and quantizations."
          right={
            <Link to="/hardware" className="text-[13px] font-medium text-accent hover:text-accent-strong transition-colors">
              Test rig profiles →
            </Link>
          }
        />
        <div className="overflow-x-auto px-5 pb-5">
          <table className="w-full text-[13px] text-left">
            <thead className="text-ink-3 border-b border-line">
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
                  className={`border-b border-line hover:bg-surface-2 transition-colors ${idx % 2 === 1 ? 'bg-surface-2/40' : ''}`}
                >
                  <td className="py-2.5 pr-4 text-ink font-medium whitespace-nowrap">{b.system_type || '—'}</td>
                  <td className="py-2.5 pr-4 text-ink-2" title={b.model_name}>
                    {truncate(b.model_name, 22)}
                  </td>
                  <td className="py-2.5 pr-4 tnum text-ink-3 text-xs">{b.quantization}</td>
                  <td className="py-2.5 pr-4 tnum text-accent font-semibold">
                    {Number(b.tokens_per_second).toFixed(1)}
                  </td>
                  <td className="py-2.5 pr-4">
                    <BandwidthBadge gbs={b.memory_bandwidth_gbs ? Number(b.memory_bandwidth_gbs) : null} />
                  </td>
                  <td className="py-2.5 pr-4 tnum text-ink-2 text-xs whitespace-nowrap">
                    {Number(b.total_ram_gb)} GB
                  </td>
                  <td className="py-2.5 pr-4 text-ink-3 text-xs whitespace-nowrap">
                    {relativeTime(b.submitted_at)}
                  </td>
                  <td className="py-2.5">
                    <Link
                      to={`/benchmarks/${b.id}`}
                      className="text-xs text-ink-3 hover:text-accent transition-colors whitespace-nowrap"
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
