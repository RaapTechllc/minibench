export type ScenarioKind = 'spreadsheet' | 'cursor' | 'slack';

export interface ArcadeTaskResult {
  task_id: string;
  passed: boolean;
  scenario_type: string | null;
  task_description: string | null;
  passed_format: boolean | null;
}

export interface RunCabinetConfig {
  models?: string[];
  self_moa?: boolean;
}

export function cabinetPathForRun(config: RunCabinetConfig | null): '/models' | '/agents';
export function taskScenario(
  result: Pick<ArcadeTaskResult, 'scenario_type'>,
  category: string,
): { kind: ScenarioKind; fromMetadata: boolean };
export function taskDisplayName(
  result: Pick<ArcadeTaskResult, 'task_id' | 'task_description'>,
  index: number,
): string;
