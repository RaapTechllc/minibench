import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import type { HardwareSpec, ReferenceProfile } from '../api';
import BandwidthBadge from '../components/BandwidthBadge';
import { PageHeader, Card, Skeleton, ErrorState } from '../components/ui';

function ProfileCard({ p }: { p: ReferenceProfile }) {
  const pins: [string, string | number | null][] = [
    ['Engine', p.engine ?? 'provider-served'],
    ['Quant', p.quantization ?? 'provider-served'],
    ['Context', p.context_length],
    ['Temp', p.temperature],
    ['Max tokens', p.max_tokens],
  ];
  return (
    <Card className="p-5">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-ink font-semibold">{p.display_name}</h3>
        <code className="tnum text-xs text-accent">{p.profile_key}</code>
      </div>
      {p.representative_system && (
        <p className="text-xs text-ink-3 mt-0.5">Reference rig: {p.representative_system}</p>
      )}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 mt-3 text-sm">
        {pins.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-2">
            <dt className="text-ink-3">{label}</dt>
            <dd className="tnum text-ink">{value ?? '—'}</dd>
          </div>
        ))}
      </dl>
      {p.description && <p className="text-xs text-ink-2 mt-3">{p.description}</p>}
    </Card>
  );
}

export default function Hardware() {
  const [specs, setSpecs] = useState<HardwareSpec[]>([]);
  const [profiles, setProfiles] = useState<ReferenceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(false);
    Promise.all([
      api.getHardware().then(setSpecs),
      api.getReferenceProfiles().then(setProfiles).catch(() => setProfiles([])),
    ])
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Reference rigs" title="Test Rigs & Profiles" />
        <Skeleton rows={8} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Reference rigs" title="Test Rigs & Profiles" />
        <ErrorState onRetry={load}>Hardware specs couldn't be fetched. Check your connection and try again.</ErrorState>
      </div>
    );
  }

  return (
    <div className="space-y-6">
        <PageHeader eyebrow="Reference rigs" title="Test Rigs & Profiles">
        How models are run on pinned configurations. Hardware documents the rig; capability scores live on Models.
      </PageHeader>

      {profiles.length > 0 && (
        <div className="animate-rise rise-1">
          <h2 className="text-lg font-semibold text-ink mb-1">How we run models</h2>
          <p className="text-sm text-ink-2 mb-3">One official, pinned configuration per profile. A benchmark result always names the profile it ran on.</p>
          <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {profiles.map(p => <ProfileCard key={p.id} p={p} />)}
          </div>
        </div>
      )}

      <Card className="overflow-x-auto animate-rise rise-1">
        <table className="w-full text-sm text-left">
          <thead className="text-ink-2 border-b border-line bg-surface">
            <tr>
              <th className="p-3 font-medium">System</th>
              <th className="p-3 font-medium">CPU</th>
              <th className="p-3 font-medium">GPU / iGPU</th>
              <th className="p-3 font-medium">System RAM</th>
              <th className="p-3 font-medium">VRAM</th>
              <th className="p-3 font-medium">Memory Type</th>
              <th className="p-3 font-medium text-frontier">Bandwidth</th>
              <th className="p-3 font-medium">TDP</th>
              <th className="p-3 font-medium">MSRP</th>
              <th className="p-3 font-medium">Year</th>
              <th className="p-3 font-medium">Form Factor</th>
            </tr>
          </thead>
          <tbody>
            {specs.map((s, idx) => (
              <tr key={s.id} className={`border-b border-line hover:bg-surface-2 transition-colors ${idx % 2 === 1 ? 'bg-surface-2' : ''}`}>
                <td className="p-3 text-ink font-medium">{s.system_name}</td>
                <td className="p-3 text-ink-2 text-xs">{s.cpu_model || '—'}</td>
                <td className="p-3 text-ink-2 text-xs">
                  {s.gpu_model && <div className="text-pass">{s.gpu_model}</div>}
                  {s.igpu_model && <div className="text-ink-2">{s.igpu_model}</div>}
                  {!s.gpu_model && !s.igpu_model && '—'}
                </td>
                <td className="p-3 text-ink">{s.system_ram_gb ? <><span className="tnum">{s.system_ram_gb}</span> GB</> : '—'}</td>
                <td className="p-3">{s.vram_gb ? <span className="text-accent"><span className="tnum">{s.vram_gb}</span> GB</span> : <span className="text-ink-3">None</span>}</td>
                <td className="p-3 text-ink-2">{s.memory_type || '—'}</td>
                <td className="p-3"><BandwidthBadge gbs={s.memory_bandwidth_gbs ? Number(s.memory_bandwidth_gbs) : null} /></td>
                <td className="p-3 text-ink-2 tnum">{s.tdp_watts ? `${s.tdp_watts}W` : '—'}</td>
                <td className="p-3 text-ink tnum">{s.msrp_usd ? `$${Number(s.msrp_usd).toLocaleString()}` : '—'}</td>
                <td className="p-3 text-ink-2 tnum">{s.release_year || '—'}</td>
                <td className="p-3 text-ink-2 capitalize">{s.form_factor?.replace('_', ' ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card className="p-6">
        <h2 className="text-lg font-semibold text-ink mb-2">Memory Bandwidth Color Guide</h2>
        <div className="flex flex-wrap gap-6 text-sm font-semibold">
          <span className="text-fail">{'<'} 50 GB/s</span>
          <span className="text-amber-600">50-100 GB/s</span>
          <span className="text-pass">100-200 GB/s</span>
          <span className="text-frontier">200+ GB/s</span>
        </div>
        <p className="text-xs text-ink-3 mt-2">Memory bandwidth is the primary bottleneck for local LLM inference. Higher bandwidth = more tokens/second.</p>
      </Card>
    </div>
  );
}
