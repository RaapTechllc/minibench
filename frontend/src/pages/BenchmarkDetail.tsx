import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { api } from '../api';
import type { Benchmark } from '../api';
import BandwidthBadge from '../components/BandwidthBadge';
import MemoryLabel from '../components/MemoryLabel';
import { Card, Skeleton, EmptyState } from '../components/ui';

function num(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
}

function fmtDate(value: string): string {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

function BackLink() {
  return (
    <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-accent hover:text-accent-strong transition-colors">
      <ArrowLeft className="w-4 h-4" /> Back to overview
    </Link>
  );
}

function Field({ label, value, accent }: { label: string; value: ReactNode; accent?: boolean }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 border-b border-line last:border-0">
      <span className="text-ink-2 text-sm shrink-0">{label}</span>
      <span className={`text-sm text-right ${accent ? 'tnum text-accent font-semibold' : 'text-ink'}`}>
        {value ?? '—'}
      </span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card className="p-5">
      <h2 className="text-xs font-semibold text-ink-3 uppercase tracking-widest mb-3">{title}</h2>
      <div>{children}</div>
    </Card>
  );
}

export default function BenchmarkDetail() {
  const { id } = useParams<{ id: string }>();
  const numericId = id ? Number(id) : NaN;
  const invalidId = Number.isNaN(numericId);
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (invalidId) return;
    let active = true;
    // Reset to the loading state when the route id changes so a stale benchmark
    // isn't shown while the new one loads.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    api
      .getBenchmark(numericId)
      .then((b) => {
        if (active) {
          setBenchmark(b);
          setNotFound(false);
        }
      })
      .catch(() => {
        if (active) setNotFound(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [numericId, invalidId]);

  if (invalidId) {
    return (
      <div className="space-y-4">
        <BackLink />
        <EmptyState title="Invalid benchmark id">
          <span className="tnum text-ink">{id}</span> is not a valid benchmark id.
        </EmptyState>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <BackLink />
        <Skeleton rows={8} />
      </div>
    );
  }

  if (notFound || !benchmark) {
    return (
      <div className="space-y-4">
        <BackLink />
        <EmptyState title="Benchmark not found">
          No benchmark with id <span className="tnum text-ink">{id}</span> exists.
        </EmptyState>
      </div>
    );
  }

  const b = benchmark;
  const params = num(b.model_params_b);
  const ttft = num(b.time_to_first_token);
  const power = num(b.total_power_watts);
  const wattsPerTok = num(b.watts_per_token);
  const quality = num(b.model_quality_score);
  const price = num(b.hardware_price_usd);
  const ambient = num(b.ambient_temp_c);

  return (
    <div className="space-y-6">
      <BackLink />

      {/* Header */}
      <Card className="p-6 animate-rise rise-1">
        <div className="text-[11px] text-ink-3 uppercase tracking-[0.14em] mb-1">Benchmark #{b.id}</div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{b.system_type || b.cpu_model}</h1>
        <div className="text-ink-2 mt-1 text-sm">
          {b.model_name} · {b.quantization} · {b.inference_engine}
        </div>
        <div className="flex flex-wrap items-end gap-x-8 gap-y-3 mt-4">
          <div>
            <div className="flex items-baseline gap-1.5">
              <span className="tnum text-4xl font-semibold text-ink">{Number(b.tokens_per_second).toFixed(1)}</span>
              <span className="text-base text-accent">t/s</span>
            </div>
            <div className="text-xs text-ink-3 mt-0.5">throughput</div>
          </div>
          <div>
            <div className="tnum text-2xl font-semibold text-ink">{b.hei?.toFixed(2) ?? '—'}</div>
            <div className="text-xs text-ink-3 mt-0.5">HEI (value)</div>
          </div>
          <div>
            <BandwidthBadge gbs={num(b.memory_bandwidth_gbs)} />
            <div className="text-xs text-ink-3 mt-1">memory bandwidth</div>
          </div>
        </div>
      </Card>

      <div className="grid md:grid-cols-2 gap-6">
        <Section title="Performance">
          <Field label="Tokens / sec" value={<span className="tnum">{Number(b.tokens_per_second).toFixed(2)}</span>} accent />
          <Field label="Time to first token" value={ttft != null ? <span className="tnum">{ttft.toFixed(3)} s</span> : '—'} />
          <Field label="Prompt tokens" value={<span className="tnum">{b.prompt_tokens}</span>} />
          <Field label="Completion tokens" value={<span className="tnum">{b.completion_tokens}</span>} />
          <Field label="Test duration" value={<span className="tnum">{Number(b.test_duration_secs).toFixed(1)} s</span>} />
          <Field label="Total power" value={power != null ? <span className="tnum">{power.toFixed(1)} W</span> : '—'} />
          <Field label="Watts / token" value={wattsPerTok != null ? <span className="tnum">{wattsPerTok.toFixed(4)}</span> : '—'} />
        </Section>

        <Section title="Quality & Value">
          <Field label="Model quality (MMLU)" value={quality != null ? <span className="tnum">{quality.toFixed(1)}</span> : '—'} />
          <Field label="Quality source" value={b.quality_source ?? '—'} />
          <Field label="Hardware Efficiency Index" value={b.hei?.toFixed(4) ?? '—'} accent />
          <Field label="Hardware price" value={price != null ? <span className="tnum">${price.toLocaleString()}</span> : '—'} />
        </Section>

        <Section title="Hardware">
          <Field label="System" value={b.system_type ?? '—'} />
          <Field label="CPU" value={b.cpu_model} />
          <Field label="Cores / threads" value={<span className="tnum">{`${b.cpu_cores ?? '?'} / ${b.cpu_threads ?? '?'}`}</span>} />
          <Field label="Discrete GPU" value={b.gpu_model ?? 'None'} />
          <Field label="Integrated GPU" value={b.igpu_model ?? 'None'} />
          <Field
            label="Memory"
            value={<MemoryLabel ramGb={num(b.total_ram_gb)} vramGb={num(b.vram_gb)} memType={b.memory_type} />}
          />
          <Field label="Bandwidth" value={<BandwidthBadge gbs={num(b.memory_bandwidth_gbs)} />} />
        </Section>

        <Section title="Software & Run">
          <Field label="Operating system" value={b.os} />
          <Field label="Inference engine" value={`${b.inference_engine}${b.engine_version ? ` (${b.engine_version})` : ''}`} />
          <Field label="Model" value={`${b.model_name}${params != null ? ` · ${params}B` : ''}`} />
          <Field label="Quantization" value={b.quantization} />
          <Field label="Thermal setting" value={b.thermal_setting ?? '—'} />
          <Field label="Ambient temp" value={ambient != null ? <span className="tnum">{ambient.toFixed(1)} °C</span> : '—'} />
          <Field label="Submitted" value={fmtDate(b.submitted_at)} />
          <Field label="Fingerprint" value={<span className="tnum text-xs">{b.fingerprint ?? '—'}</span>} />
        </Section>
      </div>
    </div>
  );
}
