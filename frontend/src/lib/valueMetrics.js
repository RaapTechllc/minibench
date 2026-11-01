const HOURS_TO_MS = 3_600_000;

const round = (value, digits = 6) => {
  if (!Number.isFinite(value)) return value;
  return Number(value.toFixed(digits));
};

const probability = value => Math.min(1, Math.max(0, Number(value) || 0));
const nonNegative = value => Math.max(0, Number(value) || 0);

export function costPerSuccess(costPerAttempt, passRate) {
  const p = probability(passRate);
  if (p === 0) return Infinity;
  return round(nonNegative(costPerAttempt) / p);
}

export function evaluateModel(model, scenario = {}) {
  const passRate = probability(model.passRate);
  const costPerAttempt = nonNegative(model.costPerAttempt);
  const latencyMs = nonNegative(model.latencyMs);
  const tasksPerMonth = nonNegative(scenario.tasksPerMonth ?? 1_000);
  const failureCostUsd = nonNegative(scenario.failureCostUsd);
  const hourlyValueUsd = nonNegative(scenario.hourlyValueUsd);
  const expectedFailureLoss = (1 - passRate) * failureCostUsd;
  const latencyCost = (latencyMs / HOURS_TO_MS) * hourlyValueUsd;
  const expectedEconomicCost = costPerAttempt + expectedFailureLoss + latencyCost;

  return {
    passRate,
    costPerAttempt,
    latencyMs,
    costPerSuccess: costPerSuccess(costPerAttempt, passRate),
    expectedLatencyPerSuccessMs: passRate === 0 ? Infinity : round(latencyMs / passRate),
    successfulTasksPerDollar: passRate === 0 ? 0 : costPerAttempt === 0 ? Infinity : round(passRate / costPerAttempt),
    monthlyApiCost: round(costPerAttempt * tasksPerMonth),
    expectedSuccessfulTasks: round(passRate * tasksPerMonth),
    expectedFailureLoss: round(expectedFailureLoss),
    latencyCost: round(latencyCost),
    expectedEconomicCost: round(expectedEconomicCost),
    expectedEconomicCostPerSuccess: passRate === 0
      ? Infinity
      : round(expectedEconomicCost / passRate),
  };
}

export function breakEvenFailureCost(baseline, premium, hourlyValueUsd = 0) {
  const qualityDelta = probability(premium.passRate) - probability(baseline.passRate);
  if (qualityDelta <= 0) return null;

  const costDelta = nonNegative(premium.costPerAttempt) - nonNegative(baseline.costPerAttempt);
  const latencyDeltaCost = (
    (nonNegative(premium.latencyMs) - nonNegative(baseline.latencyMs)) / HOURS_TO_MS
  ) * nonNegative(hourlyValueUsd);

  return round(Math.max(0, (costDelta + latencyDeltaCost) / qualityDelta));
}

export function premiumVerdict(baseline, premium, scenario = {}, evidence = 'unavailable') {
  const qualityDelta = probability(premium.passRate) - probability(baseline.passRate);
  const attemptCostDeltaUsd = round(nonNegative(premium.costPerAttempt) - nonNegative(baseline.costPerAttempt));
  const economicCostDeltaUsd = round(
    evaluateModel(premium, scenario).expectedEconomicCost
      - evaluateModel(baseline, scenario).expectedEconomicCost,
  );
  if (qualityDelta <= 0) {
    return {
      worthIt: false,
      conditionalWorthIt: false,
      reason: 'no-measured-quality-uplift',
      qualityDelta,
      breakEvenFailureCost: null,
      breakEvenFailureCostUsd: null,
      attemptCostDeltaUsd,
      economicCostDeltaUsd,
    };
  }

  const threshold = breakEvenFailureCost(baseline, premium, scenario.hourlyValueUsd);
  const conditionalWorthIt = nonNegative(scenario.failureCostUsd) >= threshold;

  if (evidence !== 'challenger-higher') {
    return {
      worthIt: false,
      conditionalWorthIt,
      reason: evidence === 'unavailable'
        ? 'quality-evidence-unavailable'
        : 'quality-uplift-not-demonstrated',
      qualityDelta: round(qualityDelta),
      costDelta: attemptCostDeltaUsd,
      attemptCostDeltaUsd,
      economicCostDeltaUsd,
      latencyDeltaMs: round(nonNegative(premium.latencyMs) - nonNegative(baseline.latencyMs)),
      breakEvenFailureCost: threshold,
      breakEvenFailureCostUsd: threshold,
    };
  }

  return {
    worthIt: conditionalWorthIt,
    conditionalWorthIt,
    reason: conditionalWorthIt ? 'premium-justified' : 'premium-not-justified',
    qualityDelta: round(qualityDelta),
    costDelta: attemptCostDeltaUsd,
    attemptCostDeltaUsd,
    economicCostDeltaUsd,
    latencyDeltaMs: round(nonNegative(premium.latencyMs) - nonNegative(baseline.latencyMs)),
    breakEvenFailureCost: threshold,
    breakEvenFailureCostUsd: threshold,
  };
}

export function evidenceStatus(baselineInterval, challengerInterval) {
  if (!Array.isArray(baselineInterval) || !Array.isArray(challengerInterval)) return 'unavailable';
  if (baselineInterval.length !== 2 || challengerInterval.length !== 2) return 'unavailable';

  const [baseLow, baseHigh] = baselineInterval.map(Number);
  const [challengerLow, challengerHigh] = challengerInterval.map(Number);
  if (![baseLow, baseHigh, challengerLow, challengerHigh].every(Number.isFinite)) return 'unavailable';
  if (challengerLow > baseHigh) return 'challenger-higher';
  if (baseLow > challengerHigh) return 'baseline-higher';
  return 'indistinguishable';
}

export function paretoFrontier(models) {
  return models.filter((candidate, candidateIndex) => !models.some((other, otherIndex) => {
    if (candidateIndex === otherIndex) return false;

    const noWorse = probability(other.passRate) >= probability(candidate.passRate)
      && nonNegative(other.costPerAttempt) <= nonNegative(candidate.costPerAttempt)
      && nonNegative(other.latencyMs) <= nonNegative(candidate.latencyMs);
    const strictlyBetter = probability(other.passRate) > probability(candidate.passRate)
      || nonNegative(other.costPerAttempt) < nonNegative(candidate.costPerAttempt)
      || nonNegative(other.latencyMs) < nonNegative(candidate.latencyMs);
    return noWorse && strictlyBetter;
  }));
}

export function rankByEconomicValue(models, scenario = {}) {
  return models
    .map(model => ({ ...model, economics: evaluateModel(model, scenario) }))
    .sort((a, b) => (
      a.economics.expectedEconomicCostPerSuccess - b.economics.expectedEconomicCostPerSuccess
      || probability(b.passRate) - probability(a.passRate)
      || nonNegative(a.costPerAttempt) - nonNegative(b.costPerAttempt)
    ));
}
