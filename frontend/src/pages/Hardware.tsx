import { useEffect, useState } from 'react';
import { api } from '../api';
import type { HardwareSpec, ReferenceProfile } from '../api';
import BandwidthBadge from '../components/BandwidthBadge';

function ProfileCard({ p }: { p: ReferenceProfile }) {
  const pins: [string, string | number | null][] = [
    ['Engine', p.engine ?? 'provider-served'],
    ['Quant', p.quantization ?? 'provider-served'],
    ['Context', p.context_length],
    ['Temp', p.temperature],
    ['Max tokens', p.max_tokens],
  ];
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-white font-semibold">{p.display_name}</h3>
        <code className="text-xs text-cyan-400">{p.profile_key}</code>
      </div>
      {p.representative_system && (
        <p className="text-xs text-gray-500 mt-0.5">Reference rig: {p.representative_system}</p>
      )}
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 mt-3 text-sm">
        {pins.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-2">
            <dt className="text-gray-500">{label}</dt>
            <dd className="text-gray-200">{value ?? '—'}</dd>
          </div>
        ))}
      </dl>
      {p.description && <p className="text-xs text-gray-400 mt-3">{p.description}</p>}
    </div>
  );
}

export default function Hardware() {
  const [specs, setSpecs] = useState<HardwareSpec[]>([]);
  const [profiles, setProfiles] = useState<ReferenceProfile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getHardware().then(setSpecs),
      api.getReferenceProfiles().then(setProfiles).catch(() => setProfiles([])),
    ]).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-gray-400">Loading...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Hardware &amp; Reference Profiles</h1>
        <p className="text-gray-400 mt-1">Hardware is the test rig, not the competition: models are benchmarked on a fixed reference profile so capability numbers are comparable.</p>
      </div>

      {profiles.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-white mb-1">How we run models</h2>
          <p className="text-sm text-gray-400 mb-3">One official, pinned configuration per profile. A benchmark result always names the profile it ran on.</p>
          <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {profiles.map(p => <ProfileCard key={p.id} p={p} />)}
          </div>
        </div>
      )}

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-gray-400 border-b border-gray-800 bg-gray-900/50">
            <tr>
              <th className="p-3">System</th>
              <th className="p-3">CPU</th>
              <th className="p-3">GPU / iGPU</th>
              <th className="p-3">System RAM</th>
              <th className="p-3">VRAM</th>
              <th className="p-3">Memory Type</th>
              <th className="p-3 font-semibold text-yellow-400">Bandwidth</th>
              <th className="p-3">TDP</th>
              <th className="p-3">MSRP</th>
              <th className="p-3">Year</th>
              <th className="p-3">Form Factor</th>
            </tr>
          </thead>
          <tbody>
            {specs.map(s => (
              <tr key={s.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="p-3 text-white font-medium">{s.system_name}</td>
                <td className="p-3 text-gray-300 text-xs">{s.cpu_model || '—'}</td>
                <td className="p-3 text-gray-300 text-xs">
                  {s.gpu_model && <div className="text-green-400">{s.gpu_model}</div>}
                  {s.igpu_model && <div className="text-gray-400">{s.igpu_model}</div>}
                  {!s.gpu_model && !s.igpu_model && '—'}
                </td>
                <td className="p-3">{s.system_ram_gb ? `${s.system_ram_gb} GB` : '—'}</td>
                <td className="p-3">{s.vram_gb ? <span className="text-purple-400">{s.vram_gb} GB</span> : <span className="text-gray-600">None</span>}</td>
                <td className="p-3 text-gray-400">{s.memory_type || '—'}</td>
                <td className="p-3"><BandwidthBadge gbs={s.memory_bandwidth_gbs ? Number(s.memory_bandwidth_gbs) : null} /></td>
                <td className="p-3 text-gray-400">{s.tdp_watts ? `${s.tdp_watts}W` : '—'}</td>
                <td className="p-3 text-gray-300">{s.msrp_usd ? `$${Number(s.msrp_usd).toLocaleString()}` : '—'}</td>
                <td className="p-3 text-gray-400">{s.release_year || '—'}</td>
                <td className="p-3 text-gray-400 capitalize">{s.form_factor?.replace('_', ' ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-2">Memory Bandwidth Color Guide</h2>
        <div className="flex gap-6 text-sm">
          <span className="text-red-400">{'<'} 50 GB/s</span>
          <span className="text-amber-400">50-100 GB/s</span>
          <span className="text-green-400">100-200 GB/s</span>
          <span className="text-yellow-400">200+ GB/s</span>
        </div>
        <p className="text-xs text-gray-500 mt-2">Memory bandwidth is the primary bottleneck for local LLM inference. Higher bandwidth = more tokens/second.</p>
      </div>
    </div>
  );
}
