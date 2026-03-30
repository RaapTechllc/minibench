import { useEffect, useState } from 'react';
import { api } from '../api';
import type { HardwareSpec } from '../api';
import BandwidthBadge from '../components/BandwidthBadge';

export default function Hardware() {
  const [specs, setSpecs] = useState<HardwareSpec[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getHardware().then(setSpecs).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-gray-400">Loading...</div>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Hardware Database</h1>
        <p className="text-gray-400 mt-1">Known hardware specs sorted by memory bandwidth (the critical metric for LLM inference).</p>
      </div>

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
