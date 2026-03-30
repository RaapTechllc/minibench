import { Terminal, Download, Upload, Cpu } from 'lucide-react';

export default function Submit() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Submit Benchmarks</h1>
        <p className="text-gray-400 mt-1">Use the MiniBench CLI to benchmark your hardware and submit results.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2 text-cyan-400">
            <Download className="w-5 h-5" />
            <h2 className="text-lg font-semibold">1. Install</h2>
          </div>
          <pre className="bg-gray-950 border border-gray-800 rounded-lg p-4 text-sm text-gray-300 overflow-x-auto">
{`pip install minibench

# Or from source:
git clone https://github.com/RaapTechllc/minibench
cd minibench/cli
pip install -e .`}
          </pre>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2 text-cyan-400">
            <Cpu className="w-5 h-5" />
            <h2 className="text-lg font-semibold">2. Detect Hardware</h2>
          </div>
          <pre className="bg-gray-950 border border-gray-800 rounded-lg p-4 text-sm text-gray-300 overflow-x-auto">
{`# Show detected hardware
minibench detect

# Auto-detects:
# - CPU model, cores, threads
# - System RAM (distinguished from VRAM)
# - GPU / iGPU
# - Memory bandwidth (from lookup table)
# - OS version`}
          </pre>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2 text-cyan-400">
            <Terminal className="w-5 h-5" />
            <h2 className="text-lg font-semibold">3. Run Benchmark</h2>
          </div>
          <pre className="bg-gray-950 border border-gray-800 rounded-lg p-4 text-sm text-gray-300 overflow-x-auto">
{`# Auto-detect model + run
minibench run

# Specify model
minibench run --model llama3:8b

# With hardware details
minibench run \\
  --model llama3:8b \\
  --system-type "Mac Mini M4 Pro" \\
  --bandwidth 273 \\
  --price 1399

# View local results
minibench results`}
          </pre>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2 text-cyan-400">
            <Upload className="w-5 h-5" />
            <h2 className="text-lg font-semibold">4. Upload Results</h2>
          </div>
          <pre className="bg-gray-950 border border-gray-800 rounded-lg p-4 text-sm text-gray-300 overflow-x-auto">
{`# Upload latest result
minibench upload

# Custom API endpoint
minibench upload --api-url https://api.minibench.dev`}
          </pre>
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-3">Test Methodology</h2>
        <div className="space-y-2 text-sm text-gray-300">
          <p><strong>Warmup:</strong> 3 throwaway prompts to warm caches</p>
          <p><strong>Test:</strong> 5 standardized prompts (~200 tokens each)</p>
          <p><strong>Metrics:</strong> Median t/s, p95 t/s, TTFT, total duration</p>
          <p><strong>Validation:</strong> t/s must be 0.1-500, duration must be 10s+, 100+ total tokens</p>
          <p><strong>Dedup:</strong> Same hardware+model fingerprint blocked for 1 hour</p>
        </div>
        <div className="mt-4 p-3 bg-yellow-400/10 border border-yellow-400/20 rounded-lg">
          <p className="text-sm text-yellow-400">
            Memory bandwidth is the #1 factor for local LLM performance. Always provide your system's memory bandwidth for the most useful comparison.
          </p>
        </div>
      </div>
    </div>
  );
}
