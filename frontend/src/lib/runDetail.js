const CATEGORY_SCENARIO_FALLBACK = {
  reasoning: 'spreadsheet',
  'tool-use': 'spreadsheet',
  instruction: 'slack',
  coding: 'cursor',
};

const SCENARIO_TYPES = new Set(['spreadsheet', 'cursor', 'slack']);

export function cabinetPathForModels(models) {
  return models.length > 1 ? '/agents' : '/models';
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
  if (description) return description;
  if (/canary|seed/i.test(result.task_id)) return `Task ${index + 1}`;
  const cleaned = result.task_id
    .replace(/[-_]/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
    .trim();
  return cleaned || `Task ${index + 1}`;
}

export function summarizeTaskVerdicts(results) {
  const capabilityPercent = results.length
    ? Math.round((results.filter((result) => result.passed).length / results.length) * 1000) / 10
    : null;
  const formatResults = results.filter((result) => result.passed_format !== null);
  const formatPercent = formatResults.length
    ? Math.round((formatResults.filter((result) => result.passed_format).length / formatResults.length) * 1000) / 10
    : null;
  return { capabilityPercent, formatPercent, formatCount: formatResults.length };
}
