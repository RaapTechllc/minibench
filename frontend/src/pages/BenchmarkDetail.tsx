import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { api } from '../api';
import type { Benchmark } from '../api';
import BandwidthBadge from '../components/BandwidthBadge';
import MemoryLabel from '../components/MemoryLabel';

function num(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
}

function fmtDate(value: string): string {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

function Field({ label, value, accent }: { label: string; value: ReactNode; accent?: boolean }) {
  return (
    <div className="flex justify-between gap-4 py-1.5 border-b border-gray-800/40 last:border-0">
      <span className="text-gray-400 text-sm shrink-0">{label}</span>
      <span className={`text-sm text-right ${accent ? 'text-cyan-400 font-semibold' : 'text-gray-200'}`}>
        {value ?? '—'}
      </span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">{title}</h2>
      <div>{children}</div>
    </div>
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
        <Link to="/leaderboard" className="inline-flex items-center gap-1.5 text-sm text-cyan-400 hover:text-cyan-300">
          <ArrowLeft className="w-4 h-4" /> Back to leaderboard
        </Link>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center">
          <div className="text-lg font-semibold text-white">Invalid benchmark id</div>
          <p className="text-gray-400 mt-1 text-sm">
            <span className="font-mono text-gray-300">{id}</span> is not a valid benchmark id.
          </p>
        </div>
      </div>
    );
  }

  if (loading) return <div className="text-center py-20 text-gray-400">Loading...</div>;

  if (notFound || !benchmark) {
    return (
      <div className="space-y-4">
        <Link to="/leaderboard" className="inline-flex items-center gap-1.5 text-sm text-cyan-400 hover:text-cyan-300">
          <ArrowLeft className="w-4 h-4" /> Back to leaderboard
        </Link>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center">
          <div className="text-lg font-semibold text-white">Benchmark not found</div>
          <p className="text-gray-400 mt-1 text-sm">
            No benchmark with id <span className="font-mono text-gray-300">{id}</span> exists.
          </p>
        </div>
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
      <Link to="/leaderboard" className="inline-flex items-center gap-1.5 text-sm text-cyan-400 hover:text-cyan-300">
        <ArrowLeft className="w-4 h-4" /> Back to leaderboard
      </Link>

      {/* Header */}
      <div className="bg-gray-900 border border-cyan-900/50 rounded-xl p-6">
        <div className="text-xs text-gray-500 uppercase tracking-widest mb-1">Benchmark #{b.id}</div>
        <h1 className="text-2xl font-bold text-white">{b.system_type || b.cpu_model}</h1>
        <div className="text-gray-400 mt-1 text-sm">
          {b.model_name} · {b.quantization} · {b.inference_engine}
        </div>
        <div className="flex flex-wrap items-end gap-x-8 gap-y-3 mt-4">
          <div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-4xl font-mono font-bold text-cyan-400">{Number(b.tokens_per_second).toFixed(1)}</span>
              <span className="text-base text-cyan-600">t/s</span>
            </div>
            <div className="text-xs text-gray-500 mt-0.5">throughput</div>
          </div>
          <div>
            <div className="text-2xl font-mono font-bold text-white">{b.hei?.toFixed(2) ?? '—'}</div>
            <div className="text-xs text-gray-500 mt-0.5">HEI (value)</div>
          </div>
          <div>
            <BandwidthBadge gbs={num(b.memory_bandwidth_gbs)} />
            <div className="text-xs text-gray-500 mt-1">memory bandwidth</div>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Section title="Performance">
          <Field label="Tokens / sec" value={`${Number(b.tokens_per_second).toFixed(2)}`} accent />
          <Field label="Time to first token" value={ttft != null ? `${ttft.toFixed(3)} s` : '—'} />
          <Field label="Prompt tokens" value={b.prompt_tokens} />
          <Field label="Completion tokens" value={b.completion_tokens} />
          <Field label="Test duration" value={`${Number(b.test_duration_secs).toFixed(1)} s`} />
          <Field label="Total power" value={power != null ? `${power.toFixed(1)} W` : '—'} />
          <Field label="Watts / token" value={wattsPerTok != null ? wattsPerTok.toFixed(4) : '—'} />
        </Section>

        <Section title="Quality & Value">
          <Field label="Model quality (MMLU)" value={quality != null ? quality.toFixed(1) : '—'} />
          <Field label="Quality source" value={b.quality_source ?? '—'} />
          <Field label="Hardware Efficiency Index" value={b.hei?.toFixed(4) ?? '—'} accent />
          <Field label="Hardware price" value={price != null ? `$${price.toLocaleString()}` : '—'} />
        </Section>

        <Section title="Hardware">
          <Field label="System" value={b.system_type ?? '—'} />
          <Field label="CPU" value={b.cpu_model} />
          <Field label="Cores / threads" value={`${b.cpu_cores ?? '?'} / ${b.cpu_threads ?? '?'}`} />
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
          <Field label="Ambient temp" value={ambient != null ? `${ambient.toFixed(1)} °C` : '—'} />
          <Field label="Submitted" value={fmtDate(b.submitted_at)} />
          <Field label="Fingerprint" value={<span className="font-mono text-xs">{b.fingerprint ?? '—'}</span>} />
        </Section>
      </div>

      <div className="text-sm">
        <Link to={`/compare`} className="text-cyan-400 hover:text-cyan-300">Compare with another system →</Link>
      </div>
    </div>
  );
}
