import { useMemo, useState } from 'react';
import {
  MODELS,
  calculateMonthlySavings,
  calculateSingleModelCost,
  hydratePresetCosts,
  recommendPreset,
} from '../lib/moaCalculator.js';
import { PageHeader, Card, CardHeader, Stat, Badge } from '../components/ui';

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
        <PageHeader eyebrow="Cost model" title="MoA Cost Calculator">
          Scale the report assumptions across token volume, task volume, quality floor, and budget cap.
          Baseline is Claude Opus 4.8 at $5/M input + $25/M output.
        </PageHeader>
        <div className="animate-rise bg-accent-soft border border-accent/20 rounded-xl px-4 py-3 text-[13px] text-ink-2 max-w-md">
          <div className="font-semibold text-accent-strong mb-1">Decision rule</div>
          Pick the highest quality preset that clears the quality floor and stays under the selected Opus cost cap.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <InputCard label="Input tokens/task" value={inputTokens} min={1_000} max={200_000} step={1_000} onChange={setInputTokens} first />
        <InputCard label="Output tokens/task" value={outputTokens} min={500} max={100_000} step={500} onChange={setOutputTokens} />
        <InputCard label="Tasks/day" value={tasksPerDay} min={1} max={2_000} step={1} onChange={setTasksPerDay} />
        <InputCard label="Days/month" value={daysPerMonth} min={1} max={31} step={1} onChange={setDaysPerMonth} />
        <InputCard label="Cost cap (% Opus)" value={maxCostPercent} min={5} max={100} step={5} onChange={setMaxCostPercent} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Stat label="Opus baseline/task" value={currency(baselineCost)} />
        <Stat label="Allowed max/task" value={currency(maxCostPerTask)} />
        <Stat
          label="Quality floor"
          value={minQualityScore.toFixed(1)}
          sub={
            <input
              aria-label="Quality floor"
              type="range"
              min="70"
              max="82"
              step="0.1"
              value={minQualityScore}
              onChange={e => setMinQualityScore(Number(e.target.value))}
              className="w-full mt-2"
              style={{ accentColor: 'var(--color-accent)' }}
            />
          }
        />
        <Stat label="Recommended" value={recommended?.id ?? 'No fit'} accent />
      </div>

      <Card className="p-0">
        <CardHeader title="Projected monthly impact" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 px-5 pb-5">
          <Stat label="Baseline monthly" value={currency(savings.baselineMonthly)} />
          <Stat label="Candidate monthly" value={currency(savings.candidateMonthly)} />
          <Stat label="Monthly savings" value={currency(savings.savingsMonthly)} accent />
          <Stat label="Candidate / Opus" value={percent(savings.percentOfBaseline)} />
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead className="bg-surface-2 text-ink-2 border-b border-line">
              <tr>
                <th className="text-left px-4 py-3 font-semibold">Preset</th>
                <th className="text-left px-4 py-3 font-semibold">References → Aggregator</th>
                <th className="text-right px-4 py-3 font-semibold">Cost/task</th>
                <th className="text-right px-4 py-3 font-semibold">% Opus</th>
                <th className="text-right px-4 py-3 font-semibold">Quality</th>
                <th className="text-left px-4 py-3 font-semibold">Fit</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {presets.map((preset, i) => {
                const withinCost = preset.costPerTask <= maxCostPerTask;
                const qualityOk = preset.qualityScore >= minQualityScore;
                const isRecommended = recommended?.id === preset.id;
                return (
                  <tr
                    key={preset.id}
                    className={isRecommended ? 'bg-accent-soft' : i % 2 === 1 ? 'bg-surface-2' : ''}
                  >
                    <td className="px-4 py-4">
                      <div className="font-semibold text-ink">{preset.name}</div>
                      <div className="text-xs text-ink-3">{preset.label}</div>
                    </td>
                    <td className="px-4 py-4 text-ink-2">
                      <div>{preset.references.map(model => model.name).join(' + ')}</div>
                      <div className="text-xs text-accent">→ {preset.aggregator.name}</div>
                      <div className="text-xs text-ink-3 mt-1 max-w-xl">{preset.summary}</div>
                    </td>
                    <td className="px-4 py-4 text-right tnum text-ink">{currency(preset.costPerTask)}</td>
                    <td className="px-4 py-4 text-right tnum text-ink">{percent((preset.costPerTask / baselineCost) * 100)}</td>
                    <td className="px-4 py-4 text-right tnum text-ink">{preset.qualityScore.toFixed(1)}</td>
                    <td className="px-4 py-4">
                      <div className="flex flex-wrap gap-2">
                        <Badge tone={withinCost ? 'pass' : 'fail'}>{withinCost ? 'Cost ok' : 'Over cap'}</Badge>
                        <Badge tone={qualityOk ? 'pass' : 'fail'}>{qualityOk ? 'Quality ok' : 'Below floor'}</Badge>
                        {isRecommended && <Badge tone="accent">Recommended</Badge>}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function InputCard({ label, value, min, max, step, onChange, first }: { label: string; value: number; min: number; max: number; step: number; onChange: (value: number) => void; first?: boolean }) {
  return (
    <label className={`bg-surface border border-line shadow-card rounded-xl p-4 block ${first ? 'animate-rise rise-1' : ''}`}>
      <span className="text-[11px] uppercase tracking-[0.12em] text-ink-3">{label}</span>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="mt-2 w-full tnum bg-surface border border-line-strong rounded-lg px-3 py-2 text-ink focus:border-accent transition-colors"
      />
    </label>
  );
}
