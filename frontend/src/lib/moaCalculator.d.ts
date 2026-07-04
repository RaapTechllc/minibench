export interface PricingModel {
  id?: string;
  name?: string;
  inputPerM: number;
  outputPerM: number;
  qualityScore?: number;
}

export interface MoaPreset {
  id: string;
  name: string;
  label: string;
  references: PricingModel[];
  aggregator: PricingModel;
  qualityScore: number;
  summary: string;
  costPerTask?: number;
}

export const MODELS: Record<string, PricingModel>;
export const MOA_PRESETS: MoaPreset[];
export function calculateSingleModelCost(model: PricingModel, inputTokens: number, outputTokens: number): number;
export function calculateMoaPresetCost(preset: Pick<MoaPreset, 'references' | 'aggregator'>, inputTokens: number, outputTokens: number): number;
export function calculateMonthlySavings(args: { baselineCost: number; candidateCost: number; tasksPerDay: number; daysPerMonth: number }): {
  baselineMonthly: number;
  candidateMonthly: number;
  savingsMonthly: number;
  percentOfBaseline: number;
};
export function recommendPreset<T extends { costPerTask: number; qualityScore: number }>(presets: T[], args: { maxCostPerTask: number; minQualityScore: number }): T | null;
export function hydratePresetCosts(args: { inputTokens: number; outputTokens: number }): Array<MoaPreset & { costPerTask: number }>;
