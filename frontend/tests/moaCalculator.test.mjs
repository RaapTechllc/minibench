import test from 'node:test';
import assert from 'node:assert/strict';
import {
  calculateSingleModelCost,
  calculateMoaPresetCost,
  calculateMonthlySavings,
  recommendPreset,
} from '../src/lib/moaCalculator.js';

test('calculates token-weighted single model task cost', () => {
  assert.equal(calculateSingleModelCost({ inputPerM: 5, outputPerM: 25 }, 10_000, 5_000), 0.175);
});

test('calculates MoA preset cost by summing each reference plus aggregator', () => {
  const cost = calculateMoaPresetCost({
    references: [
      { inputPerM: 0.435, outputPerM: 0.87 },
      { inputPerM: 1.25, outputPerM: 2.5 },
    ],
    aggregator: { inputPerM: 1.4, outputPerM: 4.4 },
  }, 10_000, 5_000);
  assert.equal(cost, 0.0697);
});

test('projects monthly savings versus Opus baseline', () => {
  const result = calculateMonthlySavings({ baselineCost: 0.175, candidateCost: 0.06955, tasksPerDay: 100, daysPerMonth: 30 });
  assert.equal(result.baselineMonthly, 525);
  assert.equal(result.candidateMonthly, 208.65);
  assert.equal(result.savingsMonthly, 316.35);
  assert.equal(result.percentOfBaseline, 39.74);
});

test('recommends first preset that satisfies quality and cost caps', () => {
  const presets = [
    { id: 'cheap', costPerTask: 0.018, qualityScore: 74.2 },
    { id: 'balanced', costPerTask: 0.06955, qualityScore: 81 },
  ];
  assert.equal(recommendPreset(presets, { maxCostPerTask: 0.105, minQualityScore: 76.8 }).id, 'balanced');
});
