const roundCurrency = value => Number(value.toFixed(5));
const roundMoney = value => Number(value.toFixed(2));
const roundPercent = value => Number(value.toFixed(2));

export function calculateSingleModelCost(model, inputTokens, outputTokens) {
  return roundCurrency(rawSingleModelCost(model, inputTokens, outputTokens));
}

function rawSingleModelCost(model, inputTokens, outputTokens) {
  return (inputTokens / 1_000_000) * model.inputPerM + (outputTokens / 1_000_000) * model.outputPerM;
}

export function calculateMoaPresetCost(preset, inputTokens, outputTokens) {
  const referencesCost = preset.references.reduce(
    (sum, model) => sum + rawSingleModelCost(model, inputTokens, outputTokens),
    0,
  );
  const aggregatorCost = rawSingleModelCost(preset.aggregator, inputTokens, outputTokens);
  return roundCurrency(referencesCost + aggregatorCost);
}

export function calculateMonthlySavings({ baselineCost, candidateCost, tasksPerDay, daysPerMonth }) {
  const baselineMonthly = baselineCost * tasksPerDay * daysPerMonth;
  const candidateMonthly = candidateCost * tasksPerDay * daysPerMonth;
  const savingsMonthly = baselineMonthly - candidateMonthly;
  return {
    baselineMonthly: roundMoney(baselineMonthly),
    candidateMonthly: roundMoney(candidateMonthly),
    savingsMonthly: roundMoney(savingsMonthly),
    percentOfBaseline: roundPercent((candidateCost / baselineCost) * 100),
  };
}

export function recommendPreset(presets, { maxCostPerTask, minQualityScore }) {
  return [...presets]
    .filter(preset => preset.costPerTask <= maxCostPerTask && preset.qualityScore >= minQualityScore)
    .sort((a, b) => {
      const qualityDelta = b.qualityScore - a.qualityScore;
      if (Math.abs(qualityDelta) > 0.1) return qualityDelta;
      return a.costPerTask - b.costPerTask;
    })[0] ?? null;
}

export const MODELS = {
  opus48: { id: 'opus48', name: 'Claude Opus 4.8', inputPerM: 5, outputPerM: 25, qualityScore: 76.4 },
  glm52: { id: 'glm52', name: 'GLM-5.2', inputPerM: 1.4, outputPerM: 4.4, qualityScore: 81 },
  kimi27: { id: 'kimi27', name: 'Kimi K2.7 Code', inputPerM: 0.95, outputPerM: 4, qualityScore: 81.1 },
  minimaxM3: { id: 'minimaxM3', name: 'MiniMax M3', inputPerM: 0.6, outputPerM: 2.4, qualityScore: 74.2 },
  grok43: { id: 'grok43', name: 'Grok 4.3', inputPerM: 1.25, outputPerM: 2.5, qualityScore: 73.6 },
  deepseekV4Pro: { id: 'deepseekV4Pro', name: 'DeepSeek V4 Pro', inputPerM: 0.435, outputPerM: 0.87, qualityScore: 73.6 },
  deepseekV4Flash: { id: 'deepseekV4Flash', name: 'DeepSeek V4 Flash', inputPerM: 0.14, outputPerM: 0.28, qualityScore: 70 },
  mimoFlash: { id: 'mimoFlash', name: 'MiMo-V2.5 Flash', inputPerM: 0.1, outputPerM: 0.3, qualityScore: 68 },
};

export const MOA_PRESETS = [
  {
    id: 'glm-tool-moa',
    name: 'GLM Tool MoA',
    label: 'Primary',
    references: [MODELS.deepseekV4Pro, MODELS.grok43],
    aggregator: MODELS.glm52,
    qualityScore: 81,
    summary: 'Best daily driver: strong Terminal-Bench, 1M context, 2-family proposer diversity.',
  },
  {
    id: 'kimi-tool-moa',
    name: 'Kimi Tool MoA',
    label: 'Secondary',
    references: [MODELS.deepseekV4Pro, MODELS.grok43],
    aggregator: MODELS.kimi27,
    qualityScore: 81.1,
    summary: 'Best MCP signal: Kimi K2.7 Code MCP Mark 81.1 with lower aggregator cost.',
  },
  {
    id: 'glm-flash-moa',
    name: 'GLM Flash MoA',
    label: 'Budget GLM',
    references: [MODELS.mimoFlash, MODELS.deepseekV4Flash],
    aggregator: MODELS.glm52,
    qualityScore: 79,
    summary: 'GLM aggregator with cheap references for high-volume work.',
  },
  {
    id: 'm3-experimental',
    name: 'MiniMax M3 Experimental',
    label: 'Experimental',
    references: [MODELS.deepseekV4Pro, MODELS.grok43],
    aggregator: MODELS.minimaxM3,
    qualityScore: 74.2,
    summary: 'Lowest cost 1M-context experiment; weaker complex-agent closeout than GLM/Kimi.',
  },
  {
    id: 'mimo-kimi-budget',
    name: 'MiMo Flash → Kimi',
    label: 'Cheapest tool-use',
    references: [MODELS.mimoFlash],
    aggregator: MODELS.kimi27,
    qualityScore: 78,
    summary: 'Lowest API spend with a strong Kimi aggregator for lightweight tool-use tasks.',
  },
];

export function hydratePresetCosts({ inputTokens, outputTokens }) {
  return MOA_PRESETS.map(preset => ({
    ...preset,
    costPerTask: calculateMoaPresetCost(preset, inputTokens, outputTokens),
  }));
}
