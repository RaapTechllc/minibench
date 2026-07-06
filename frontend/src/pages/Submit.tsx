import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Terminal, Download, Upload, Cpu, ClipboardList, CheckCircle2, AlertCircle } from 'lucide-react';
import { api, type Benchmark } from '../api';
import { validateSubmitForm, buildSubmitPayload } from '../lib/submitForm';

interface FieldDef {
  name: string;
  label: string;
  placeholder: string;
  required?: boolean;
}

const HARDWARE_FIELDS: FieldDef[] = [
  { name: 'cpu_model', label: 'CPU model', placeholder: 'Apple M4 Pro', required: true },
  { name: 'system_type', label: 'System', placeholder: 'Mac Mini M4 Pro' },
  { name: 'gpu_model', label: 'GPU model', placeholder: 'RTX 4060 (blank if iGPU only)' },
  { name: 'total_ram_gb', label: 'RAM (GB)', placeholder: '24', required: true },
  { name: 'memory_type', label: 'Memory type', placeholder: 'LPDDR5x / Unified' },
  { name: 'memory_bandwidth_gbs', label: 'Memory bandwidth (GB/s)', placeholder: '273' },
  { name: 'hardware_price_usd', label: 'Price (USD)', placeholder: '1399 — needed for HEI' },
];

const SOFTWARE_FIELDS: FieldDef[] = [
  { name: 'os', label: 'OS', placeholder: 'macOS 15.2', required: true },
  { name: 'inference_engine', label: 'Inference engine', placeholder: 'llama.cpp / MLX / ollama', required: true },
  { name: 'engine_version', label: 'Engine version', placeholder: '0.5.4' },
  { name: 'model_name', label: 'Model', placeholder: 'Llama-3-8B-Instruct', required: true },
  { name: 'model_params_b', label: 'Params (B)', placeholder: '8' },
  { name: 'quantization', label: 'Quantization', placeholder: 'Q4_K_M', required: true },
];

const PERFORMANCE_FIELDS: FieldDef[] = [
  { name: 'tokens_per_second', label: 'Tokens/sec', placeholder: '45.2', required: true },
  { name: 'time_to_first_token', label: 'TTFT (s)', placeholder: '0.42' },
  { name: 'prompt_tokens', label: 'Prompt tokens', placeholder: '200', required: true },
  { name: 'completion_tokens', label: 'Completion tokens', placeholder: '300', required: true },
  { name: 'test_duration_secs', label: 'Test duration (s)', placeholder: '15', required: true },
];

function FieldGroup({
  title, fields, values, errors, onChange,
}: {
  title: string;
  fields: FieldDef[];
  values: Record<string, string>;
  errors: Record<string, string>;
  onChange: (name: string, value: string) => void;
}) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">{title}</h3>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {fields.map(f => (
          <label key={f.name} className="block">
            <span className="text-sm text-gray-300">
              {f.label}
              {f.required && <span className="text-cyan-400 ml-0.5">*</span>}
            </span>
            <input
              type="text"
              value={values[f.name] ?? ''}
              onChange={e => onChange(f.name, e.target.value)}
              placeholder={f.placeholder}
              aria-invalid={!!errors[f.name]}
              className={`mt-1 w-full bg-gray-800 border rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-cyan-500 ${
                errors[f.name] ? 'border-red-500' : 'border-gray-700'
              }`}
            />
            {errors[f.name] && <span className="text-xs text-red-400 mt-1 block">{errors[f.name]}</span>}
          </label>
        ))}
      </div>
    </div>
  );
}

function ManualSubmitForm() {
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [result, setResult] = useState<Benchmark | null>(null);

  const onChange = (name: string, value: string) => {
    setValues(v => ({ ...v, [name]: value }));
    if (errors[name]) setErrors(e => ({ ...e, [name]: '' }));
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);
    const validation = validateSubmitForm(values);
    setErrors(validation);
    if (Object.keys(validation).length > 0) return;

    setSubmitting(true);
    try {
      setResult(await api.submitBenchmark(buildSubmitPayload(values)));
    } catch (err) {
      setServerError(err instanceof Error ? err.message : 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-center gap-2 text-green-400 mb-3">
          <CheckCircle2 className="w-5 h-5" />
          <h2 className="text-lg font-semibold">Benchmark submitted</h2>
        </div>
        <p className="text-sm text-gray-300">
          {result.system_type || result.cpu_model} — {result.model_name} ({result.quantization}) at{' '}
          <span className="text-cyan-400 font-semibold">{Number(result.tokens_per_second)} t/s</span>
          {result.hei != null && <> · HEI {Number(result.hei).toFixed(4)}</>}
        </p>
        <div className="mt-4 flex gap-4 text-sm">
          <Link to={`/benchmarks/${result.id}`} className="text-cyan-400 hover:underline">
            View submission →
          </Link>
          <button
            onClick={() => { setResult(null); setValues({}); }}
            className="text-gray-400 hover:text-gray-200"
          >
            Submit another
          </button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-6" noValidate>
      <div className="flex items-center gap-2 text-cyan-400">
        <ClipboardList className="w-5 h-5" />
        <h2 className="text-lg font-semibold">Manual Submission</h2>
      </div>
      <p className="text-sm text-gray-400 -mt-3">
        Ran your benchmark another way? Enter the results directly. Fields marked
        <span className="text-cyan-400"> *</span> are required; the same validation rules as the CLI apply.
      </p>

      <FieldGroup title="Hardware" fields={HARDWARE_FIELDS} values={values} errors={errors} onChange={onChange} />
      <FieldGroup title="Software" fields={SOFTWARE_FIELDS} values={values} errors={errors} onChange={onChange} />
      <FieldGroup title="Performance" fields={PERFORMANCE_FIELDS} values={values} errors={errors} onChange={onChange} />

      {serverError && (
        <div className="flex items-start gap-2 p-3 bg-red-400/10 border border-red-400/20 rounded-lg text-sm text-red-400">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{serverError}</span>
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed text-gray-950 font-semibold text-sm rounded-lg px-5 py-2.5"
      >
        {submitting ? 'Submitting…' : 'Submit benchmark'}
      </button>
    </form>
  );
}

export default function Submit() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Submit Benchmarks</h1>
        <p className="text-gray-400 mt-1">Use the MiniBench CLI to benchmark your hardware and submit results — or enter them manually below.</p>
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

      <ManualSubmitForm />

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
