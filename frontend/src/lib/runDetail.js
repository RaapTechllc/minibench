const CATEGORY_SCENARIO_FALLBACK = {
  reasoning: 'spreadsheet',
  'tool-use': 'spreadsheet',
  instruction: 'slack',
  coding: 'cursor',
};

const SCENARIO_TYPES = new Set(['spreadsheet', 'cursor', 'slack']);

export function cabinetPathForRun(config) {
  return config?.self_moa || (config?.models?.length ?? 0) > 1 ? '/agents' : '/models';
}

export function taskScenario(result, category) {
  const scenarioType = result.scenario_type?.trim().toLowerCase();
  if (scenarioType && SCENARIO_TYPES.has(scenarioType)) {
    return { kind: scenarioType, fromMetadata: true };
  }
  return {
    kind: CATEGORY_SCENARIO_FALLBACK[category] ?? 'spreadsheet',
    fromMetadata: false,
  };
}

export function taskDisplayName(result, index) {
  const description = result.task_description?.trim();
  if (/canary|seed/i.test(result.task_id) || (description && /canary|seed/i.test(description))) {
    return `Task ${index + 1}`;
  }
  if (description) return description;
  const cleaned = result.task_id
    .replace(/[-_]/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
    .trim();
  return cleaned || `Task ${index + 1}`;
}
