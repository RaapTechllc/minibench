import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Calculator, CheckCircle2, DollarSign, Gauge, Target } from 'lucide-react';
import {
  MODELS,
  calculateMonthlySavings,
  calculateSingleModelCost,
  hydratePresetCosts,
  recommendPreset,
} from '../lib/moaCalculator.js';

function currency(value: number) {
  if (value < 1) return `$${value.toFixed(5)}`;
  return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function percent(value: number) {
  return `${value.toFixed(1)}%`;
}

export default function MoaCalculator() {
  const [inputTokens, setInputTokens] = useState(10_000);
  const [outputTokens, setOutputTokens] = useState(5_000);
  const [tasksPerDay, setTasksPerDay] = useState(100);
  const [daysPerMonth, setDaysPerMonth] = useState(30);
  const [maxCostPercent, setMaxCostPercent] = useState(60);
  const [minQualityScore, setMinQualityScore] = useState(76.8);

  const baselineCost = useMemo(
    () => calculateSingleModelCost(MODELS.opus48, inputTokens, outputTokens),
    [inputTokens, outputTokens],
  );

  const presets = useMemo(
    () => hydratePresetCosts({ inputTokens, outputTokens }),
    [inputTokens, outputTokens],
  );

  const maxCostPerTask = baselineCost * (maxCostPercent / 100);
  const recommended = recommendPreset(presets, { maxCostPerTask, minQualityScore });

  const selectedForSavings = recommended ?? presets[0];
  const savings = calculateMonthlySavings({
    baselineCost,
    candidateCost: selectedForSavings.costPerTask,
    tasksPerDay,
    daysPerMonth,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-col lg:flex-row">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-2">
            <Calculator className="w-7 h-7 text-cyan-400" />
            MoA Cost Calculator
          </h1>
          <p className="text-gray-400 mt-2 max-w-3xl">
            Scale the report assumptions across token volume, task volume, quality floor, and budget cap.
            Baseline is Claude Opus 4.8 at $5/M input + $25/M output.
          </p>
        </div>
        <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl px-4 py-3 text-sm text-cyan-100 max-w-md">
          <div className="font-semibold text-cyan-300 mb-1">Decision rule</div>
          Pick the highest quality preset that clears the quality floor and stays under the selected Opus cost cap.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <InputCard label="Input tokens/task" value={inputTokens} min={1_000} max={200_000} step={1_000} onChange={setInputTokens} />
        <InputCard label="Output tokens/task" value={outputTokens} min={500} max={100_000} step={500} onChange={setOutputTokens} />
        <InputCard label="Tasks/day" value={tasksPerDay} min={1} max={2_000} step={1} onChange={setTasksPerDay} />
        <InputCard label="Days/month" value={daysPerMonth} min={1} max={31} step={1} onChange={setDaysPerMonth} />
        <InputCard label="Cost cap (% Opus)" value={maxCostPercent} min={5} max={100} step={5} onChange={setMaxCostPercent} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Metric icon={DollarSign} label="Opus baseline/task" value={currency(baselineCost)} />
        <Metric icon={Target} label="Allowed max/task" value={currency(maxCostPerTask)} />
        <Metric icon={Gauge} label="Quality floor" value={`${minQualityScore.toFixed(1)}`}>
          <input
            aria-label="Quality floor"
            type="range"
            min="70"
            max="82"
            step="0.1"
            value={minQualityScore}
            onChange={e => setMinQualityScore(Number(e.target.value))}
            className="w-full accent-cyan-400 mt-2"
          />
        </Metric>
        <Metric icon={CheckCircle2} label="Recommended" value={recommended?.id ?? 'No fit'} emphasize />
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4">Projected monthly impact</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Metric label="Baseline monthly" value={currency(savings.baselineMonthly)} />
          <Metric label="Candidate monthly" value={currency(savings.candidateMonthly)} />
          <Metric label="Monthly savings" value={currency(savings.savingsMonthly)} emphasize />
          <Metric label="Candidate / Opus" value={percent(savings.percentOfBaseline)} />
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-gray-800 bg-gray-900">
        <table className="w-full text-sm">
          <thead className="bg-gray-800/70 text-gray-300">
            <tr>
              <th className="text-left px-4 py-3">Preset</th>
              <th className="text-left px-4 py-3">References → Aggregator</th>
              <th className="text-right px-4 py-3">Cost/task</th>
              <th className="text-right px-4 py-3">% Opus</th>
              <th className="text-right px-4 py-3">Quality</th>
              <th className="text-left px-4 py-3">Fit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {presets.map(preset => {
              const withinCost = preset.costPerTask <= maxCostPerTask;
              const qualityOk = preset.qualityScore >= minQualityScore;
              const isRecommended = recommended?.id === preset.id;
              return (
                <tr key={preset.id} className={isRecommended ? 'bg-cyan-500/10' : 'hover:bg-gray-800/40'}>
                  <td className="px-4 py-4">
                    <div className="font-semibold text-white">{preset.name}</div>
                    <div className="text-xs text-gray-500">{preset.label}</div>
                  </td>
                  <td className="px-4 py-4 text-gray-300">
                    <div>{preset.references.map(model => model.name).join(' + ')}</div>
                    <div className="text-xs text-cyan-400">→ {preset.aggregator.name}</div>
                    <div className="text-xs text-gray-500 mt-1 max-w-xl">{preset.summary}</div>
                  </td>
                  <td className="px-4 py-4 text-right font-mono text-gray-200">{currency(preset.costPerTask)}</td>
                  <td className="px-4 py-4 text-right font-mono text-gray-200">{percent((preset.costPerTask / baselineCost) * 100)}</td>
                  <td className="px-4 py-4 text-right font-mono text-gray-200">{preset.qualityScore.toFixed(1)}</td>
                  <td className="px-4 py-4">
                    <div className="flex flex-wrap gap-2">
                      <Badge ok={withinCost}>{withinCost ? 'Cost ok' : 'Over cap'}</Badge>
                      <Badge ok={qualityOk}>{qualityOk ? 'Quality ok' : 'Below floor'}</Badge>
                      {isRecommended && <span className="px-2 py-1 rounded-full text-xs bg-cyan-400/20 text-cyan-200 border border-cyan-400/30">Recommended</span>}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function InputCard({ label, value, min, max, step, onChange }: { label: string; value: number; min: number; max: number; step: number; onChange: (value: number) => void }) {
  return (
    <label className="bg-gray-900 border border-gray-800 rounded-xl p-4 block">
      <span className="text-xs uppercase tracking-wide text-gray-500">{label}</span>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="mt-2 w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-white"
      />
    </label>
  );
}

function Metric({ icon: Icon, label, value, children, emphasize }: { icon?: typeof DollarSign; label: string; value: string; children?: ReactNode; emphasize?: boolean }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-gray-500">
        {Icon && <Icon className="w-4 h-4 text-cyan-400" />}
        {label}
      </div>
      <div className={emphasize ? 'text-2xl font-bold text-cyan-300 mt-2' : 'text-2xl font-bold text-white mt-2'}>{value}</div>
      {children}
    </div>
  );
}

function Badge({ ok, children }: { ok: boolean; children: ReactNode }) {
  return (
    <span className={`px-2 py-1 rounded-full text-xs border ${ok ? 'bg-emerald-400/10 text-emerald-200 border-emerald-400/30' : 'bg-red-400/10 text-red-200 border-red-400/30'}`}>
      {children}
    </span>
  );
}
