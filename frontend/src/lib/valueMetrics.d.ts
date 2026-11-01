export interface ValueModel {
  id?: string | number;
  passRate: number;
  costPerAttempt: number;
  latencyMs: number;
}

export interface ValueScenario {
  tasksPerMonth?: number;
  failureCostUsd?: number;
  hourlyValueUsd?: number;
}

export interface ModelEconomics {
  passRate: number;
  costPerAttempt: number;
  latencyMs: number;
  costPerSuccess: number;
  expectedLatencyPerSuccessMs: number;
  successfulTasksPerDollar: number;
  monthlyApiCost: number;
  expectedSuccessfulTasks: number;
  expectedFailureLoss: number;
  latencyCost: number;
  expectedEconomicCost: number;
  expectedEconomicCostPerSuccess: number;
}

export interface PremiumVerdict {
  worthIt: boolean;
  conditionalWorthIt: boolean;
  reason:
    | 'no-measured-quality-uplift'
    | 'quality-evidence-unavailable'
    | 'quality-uplift-not-demonstrated'
    | 'premium-justified'
    | 'premium-not-justified';
  qualityDelta: number;
  costDelta?: number;
  attemptCostDeltaUsd: number;
  economicCostDeltaUsd: number;
  latencyDeltaMs?: number;
  breakEvenFailureCost: number | null;
  breakEvenFailureCostUsd: number | null;
}

export function costPerSuccess(costPerAttempt: number, passRate: number): number;
export function evaluateModel(model: ValueModel, scenario?: ValueScenario): ModelEconomics;
export function breakEvenFailureCost(baseline: ValueModel, premium: ValueModel, hourlyValueUsd?: number): number | null;
export type EvidenceStatus = 'unavailable' | 'challenger-higher' | 'baseline-higher' | 'indistinguishable';

export function premiumVerdict(
  baseline: ValueModel,
  premium: ValueModel,
  scenario: ValueScenario,
  evidence: EvidenceStatus,
): PremiumVerdict;
export function evidenceStatus(
  baselineInterval: [number, number] | null,
  challengerInterval: [number, number] | null,
): EvidenceStatus;
export function paretoFrontier<T extends ValueModel>(models: T[]): T[];
export function rankByEconomicValue<T extends ValueModel>(
  models: T[],
  scenario?: ValueScenario,
): Array<T & { economics: ModelEconomics }>;
