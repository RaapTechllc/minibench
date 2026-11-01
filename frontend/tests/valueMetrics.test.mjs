import test from 'node:test';
import assert from 'node:assert/strict';

import {
  breakEvenFailureCost,
  costPerSuccess,
  evaluateModel,
  evidenceStatus,
  paretoFrontier,
  premiumVerdict,
  rankByEconomicValue,
} from '../src/lib/valueMetrics.js';

test('cost per success charges failed attempts instead of hiding them', () => {
  assert.equal(costPerSuccess(0.02, 0.8), 0.025);
  assert.equal(costPerSuccess(0.02, 0), Infinity);
});

test('economic evaluation keeps measured and projected values explicit', () => {
  const result = evaluateModel(
    { passRate: 0.8, costPerAttempt: 0.02, latencyMs: 3_600 },
    { tasksPerMonth: 1_000, failureCostUsd: 2, hourlyValueUsd: 50 },
  );

  assert.equal(result.costPerSuccess, 0.025);
  assert.equal(result.monthlyApiCost, 20);
  assert.equal(result.expectedFailureLoss, 0.4);
  assert.equal(result.latencyCost, 0.05);
  assert.equal(result.expectedEconomicCost, 0.47);
  assert.equal(result.expectedEconomicCostPerSuccess, 0.5875);
  assert.equal(result.successfulTasksPerDollar, 40);
  assert.equal(result.expectedLatencyPerSuccessMs, 4_500);
});

test('premium break-even is the incremental cost per added success probability', () => {
  const baseline = { passRate: 0.9, costPerAttempt: 0.001, latencyMs: 1_000 };
  const premium = { passRate: 0.95, costPerAttempt: 0.003, latencyMs: 1_000 };

  assert.ok(Math.abs(breakEvenFailureCost(baseline, premium) - 0.04) < 1e-12);
  const justified = premiumVerdict(
    baseline,
    premium,
    { failureCostUsd: 0.1, hourlyValueUsd: 0 },
    'challenger-higher',
  );
  assert.equal(justified.worthIt, true);
  assert.equal(justified.attemptCostDeltaUsd, 0.002);
  assert.equal(justified.economicCostDeltaUsd, -0.003);
  assert.equal(justified.breakEvenFailureCostUsd, 0.04);
  assert.equal(premiumVerdict(
    baseline,
    premium,
    { failureCostUsd: 0.01, hourlyValueUsd: 0 },
    'challenger-higher',
  ).worthIt, false);
});

test('slower premium includes the economic cost of incremental latency', () => {
  const baseline = { passRate: 0.9, costPerAttempt: 0.001, latencyMs: 1_000 };
  const premium = { passRate: 0.95, costPerAttempt: 0.003, latencyMs: 4_600 };

  assert.ok(Math.abs(breakEvenFailureCost(baseline, premium, 50) - 1.04) < 1e-12);
});

test('premium verdict refuses to justify a model with no quality uplift', () => {
  const verdict = premiumVerdict(
    { passRate: 0.9, costPerAttempt: 0.001, latencyMs: 1_000 },
    { passRate: 0.9, costPerAttempt: 0.003, latencyMs: 900 },
    { failureCostUsd: 50, hourlyValueUsd: 0 },
  );

  assert.equal(verdict.worthIt, false);
  assert.equal(verdict.reason, 'no-measured-quality-uplift');
  assert.equal(verdict.breakEvenFailureCost, null);
});

test('confidence intervals prevent unsupported winner language', () => {
  assert.equal(evidenceStatus([0.82, 0.91], [0.88, 0.96]), 'indistinguishable');
  assert.equal(evidenceStatus([0.82, 0.87], [0.9, 0.96]), 'challenger-higher');
  assert.equal(evidenceStatus(null, [0.9, 0.96]), 'unavailable');
});

test('overlapping confidence intervals keep an economic threshold conditional', () => {
  const verdict = premiumVerdict(
    { passRate: 0.9, costPerAttempt: 0.001, latencyMs: 1_000 },
    { passRate: 0.95, costPerAttempt: 0.003, latencyMs: 1_000 },
    { failureCostUsd: 0.1, hourlyValueUsd: 0 },
    'indistinguishable',
  );

  assert.equal(verdict.worthIt, false);
  assert.equal(verdict.conditionalWorthIt, true);
  assert.equal(verdict.reason, 'quality-uplift-not-demonstrated');
  assert.equal(verdict.breakEvenFailureCostUsd, 0.04);
});

test('pareto frontier removes options worse on quality, cost, and latency', () => {
  const models = [
    { id: 'budget', passRate: 0.9, costPerAttempt: 0.01, latencyMs: 1_000 },
    { id: 'premium', passRate: 0.95, costPerAttempt: 0.02, latencyMs: 1_000 },
    { id: 'dominated', passRate: 0.85, costPerAttempt: 0.03, latencyMs: 2_000 },
  ];

  assert.deepEqual(paretoFrontier(models).map(model => model.id), ['budget', 'premium']);
});

test('economic ranking uses the declared scenario rather than a magic score', () => {
  const models = [
    { id: 'cheap', passRate: 0.8, costPerAttempt: 0.001, latencyMs: 1_000 },
    { id: 'accurate', passRate: 0.98, costPerAttempt: 0.02, latencyMs: 1_000 },
  ];

  assert.equal(rankByEconomicValue(models, { failureCostUsd: 0.01, hourlyValueUsd: 0 })[0].id, 'cheap');
  assert.equal(rankByEconomicValue(models, { failureCostUsd: 1, hourlyValueUsd: 0 })[0].id, 'accurate');
});
