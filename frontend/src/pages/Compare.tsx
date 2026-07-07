import { useEffect, useState } from 'react';
import { api } from '../api';
import type { Benchmark } from '../api';
import {
  PageHeader, Card, CardHeader, Select,
  Skeleton, EmptyState, ErrorState,
} from '../components/ui';

const label = (b: Benchmark) =>
  `${b.system_type || b.cpu_model} — ${b.model_name} (${b.quantization})`;

const shortLabel = (b: Benchmark) => b.system_type || b.cpu_model || 'Unknown';

export default function Compare() {
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [idA, setIdA] = useState<number | null>(null);
  const [idB, setIdB] = useState<number | null>(null);
  const [compare, setCompare] = useState<{ a: Benchmark; b: Benchmark } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function loadBenchmarks() {
    setLoading(true);
    setError(null);
    api.getBenchmarks({ limit: '50' })
      .then(b => {
        setBenchmarks(b);
        if (b.length >= 2) { setIdA(b[0].id); setIdB(b[1].id); }
      })
      .catch(() => setError('Could not load the list of systems.'))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadBenchmarks(); }, []);

  useEffect(() => {
    if (idA && idB) {
      api.getCompare(idA, idB)
        .then((d) => { setCompare(d); setError(null); })
        .catch(() => setError('Could not load the comparison for these two systems.'));
    }
  }, [idA, idB]);

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Head to head" title="Compare Hardware">
        Side-by-side comparison of two benchmark runs. Each metric is charted on
        its own scale — unlike units are never stacked on one axis.
      </PageHeader>

      {/* Pickers */}
      <div className="animate-rise rise-1 flex flex-wrap items-center gap-4">
        <Select label="A" value={idA ?? ''} onChange={e => setIdA(Number(e.target.value))}
          className="min-w-[220px] flex-1">
          {benchmarks.map(b => <option key={b.id} value={b.id}>{label(b)}</option>)}
        </Select>
        <span className="text-[13px] font-medium text-ink-3">vs</span>
        <Select label="B" value={idB ?? ''} onChange={e => setIdB(Number(e.target.value))}
          className="min-w-[220px] flex-1">
          {benchmarks.map(b => <option key={b.id} value={b.id}>{label(b)}</option>)}
        </Select>
      </div>

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton rows={9} />
          <Skeleton rows={9} />
        </div>
      ) : error ? (
        <ErrorState onRetry={loadBenchmarks}>{error}</ErrorState>
      ) : benchmarks.length < 2 ? (
        <EmptyState title="Pick two systems to compare">
          At least two benchmark runs are needed to draw a comparison.
        </EmptyState>
      ) : !compare ? (
        <EmptyState title="Pick two systems to compare">
          Choose a system for both A and B above to see them side by side.
        </EmptyState>
      ) : (
        <>
          {/* Spec cards */}
          <div className="grid gap-4 md:grid-cols-2">
            <SpecCard b={compare.a} tag="A" tone="accent" />
            <SpecCard b={compare.b} tag="B" tone="neutral" />
          </div>

          {/* Metric comparison — one scale per metric */}
          <Card className="animate-rise rise-1">
            <CardHeader title="Metric comparison"
              sub="Paired bars per metric, each normalised to its own scale." />
            <div className="flex items-center gap-5 px-5 pb-1 text-[12px] text-ink-2">
              <LegendDot className="bg-accent" /> <span className="tnum">A · {shortLabel(compare.a)}</span>
              <LegendDot className="bg-ink-3" /> <span className="tnum">B · {shortLabel(compare.b)}</span>
            </div>
            <div className="space-y-5 px-5 pb-6 pt-3">
              {metrics(compare.a, compare.b).map(m => (
                <MetricRow key={m.name} {...m} />
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

/* ── Metric model — each metric carries its own unit and never shares an axis ── */
type Metric = {
  name: string;
  unit: string;
  a: number | null;
  b: number | null;
  decimals: number;
};

function metrics(a: Benchmark, b: Benchmark): Metric[] {
  return [
    { name: 'Tokens / sec', unit: 't/s', a: num(a.tokens_per_second), b: num(b.tokens_per_second), decimals: 1 },
    { name: 'Memory bandwidth', unit: 'GB/s', a: num(a.memory_bandwidth_gbs), b: num(b.memory_bandwidth_gbs), decimals: 0 },
    { name: 'System RAM', unit: 'GB', a: num(a.total_ram_gb), b: num(b.total_ram_gb), decimals: 0 },
    { name: 'MMLU', unit: '', a: num(a.model_quality_score), b: num(b.model_quality_score), decimals: 1 },
  ];
}

function num(v: number | null | undefined): number | null {
  return v === null || v === undefined ? null : Number(v);
}

function MetricRow({ name, unit, a, b, decimals }: Metric) {
  const max = Math.max(a ?? 0, b ?? 0) || 1;
  const pct = (v: number | null) => `${((v ?? 0) / max) * 100}%`;
  const fmt = (v: number | null) => (v === null ? '—' : v.toFixed(decimals));

  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-[13px] font-medium text-ink-2">{name}</span>
        {unit && <span className="text-[11px] uppercase tracking-[0.1em] text-ink-3">{unit}</span>}
      </div>
      <Bar tone="accent" width={pct(a)} value={fmt(a)} />
      <div className="h-1.5" />
      <Bar tone="neutral" width={pct(b)} value={fmt(b)} />
    </div>
  );
}

function Bar({ tone, width, value }: { tone: 'accent' | 'neutral'; width: string; value: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="h-2.5 flex-1 rounded-full bg-surface-2">
        <div
          className={`h-full rounded-full ${tone === 'accent' ? 'bg-accent' : 'bg-ink-3'}`}
          style={{ width }}
        />
      </div>
      <span className="tnum w-16 text-right text-[13px] font-semibold text-ink">{value}</span>
    </div>
  );
}

function LegendDot({ className }: { className: string }) {
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${className}`} />;
}

/* ── Spec card ─────────────────────────────────────────────────────────────── */
function SpecCard({ b, tag, tone }: { b: Benchmark; tag: 'A' | 'B'; tone: 'accent' | 'neutral' }) {
  return (
    <Card className="animate-rise rise-1 p-5">
      <div className="mb-3 flex items-center gap-2">
        <span
          className={`inline-flex h-6 w-6 items-center justify-center rounded-lg text-[12px] font-semibold ${
            tone === 'accent' ? 'bg-accent-soft text-accent-strong' : 'bg-surface-2 text-ink-2'
          }`}
        >
          {tag}
        </span>
        <span className="text-lg font-semibold tracking-tight text-ink">{shortLabel(b)}</span>
      </div>
      <dl className="space-y-2 text-[13px]">
        <Row label="CPU" value={b.cpu_model} />
        <Row label="System RAM" value={`${Number(b.total_ram_gb)} GB ${b.memory_type || ''}`.trim()} />
        <Row label="VRAM" value={b.vram_gb ? `${Number(b.vram_gb)} GB` : 'None (system RAM only)'} accent={!!b.vram_gb} />
        <Row label="Bandwidth" value={b.memory_bandwidth_gbs ? `${Number(b.memory_bandwidth_gbs)} GB/s` : '—'} />
        <Row label="Model" value={`${b.model_name} (${b.quantization})`} />
        <Row label="Engine" value={b.inference_engine} />
        <Row label="Tokens / sec" value={Number(b.tokens_per_second).toFixed(1)} accent />
        <Row label="TTFT" value={b.time_to_first_token ? `${Number(b.time_to_first_token).toFixed(2)}s` : '—'} />
        <Row label="HEI" value={b.hei?.toFixed(2) ?? '—'} accent />
        <Row label="Price" value={b.hardware_price_usd ? `$${Number(b.hardware_price_usd).toLocaleString()}` : '—'} />
      </dl>
    </Card>
  );
}

function Row({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line pb-2 last:border-0 last:pb-0">
      <dt className="text-ink-2">{label}</dt>
      <dd className={`tnum text-right font-medium ${accent ? 'text-accent-strong' : 'text-ink'}`}>{value}</dd>
    </div>
  );
}
