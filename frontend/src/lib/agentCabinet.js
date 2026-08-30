/** Real-Work Agent Cabinet presentation helpers.
 *
 * This board is not Solo Cabinet (/models) and not Multiplayer Cabinet
 * (/agents): no Arcade tiers, no composite score, no compare UI. The default
 * scorecard is completion, raw category completion, cost per task, and
 * latency p50; everything else stays nested under the technician object.
 */

/** Default scorecard fields — the only metrics shown outside Technician mode. */
export const AGENT_CABINET_DEFAULT_FIELDS = [
  'completion',
  'category_completion',
  'cost_usd_per_task',
  'latency_p50_ms',
];

/** Full default list-item contract served by GET /api/v1/agent-cabinet/runs. */
export const AGENT_CABINET_LIST_FIELDS = [
  'run_id',
  'submitted_at',
  'suite',
  'model_route',
  'harness',
  'harness_version',
  'completion',
  'pass_rate',
  'category_completion',
  'cost_usd_per_task',
  'latency_p50_ms',
  'private_split',
];

/** Keys rendered from the nested technician object when Technician mode is on.
 *  Never flattened onto the list item. */
export const AGENT_CABINET_TECHNICIAN_FIELDS = [
  'harness',
  'harness_version',
  'model',
  'provider',
  'model_route',
  'fixture_reference',
  'fixture_digest',
  'budgets',
  'trials',
  'ci95_low',
  'ci95_high',
  'pass_hat_k',
  'regression_rate',
  'false_verification_rate',
  'termination_reasons',
];

/** Product copy — single source so the list, detail, and tests agree. */
export const AGENT_CABINET_COPY = {
  tagline:
    'Published agent-harness runs on pinned real-work fixtures — completion, ' +
    'category breakdown, cost per task, and latency, with the reproducibility ' +
    'receipts one toggle away.',
  notSoloNotMultiplayer:
    'This is not Solo Cabinet (single-model capability) and not Multiplayer ' +
    'Cabinet (MoA configs) — scores are never combined into a composite.',
  controlledVariables:
    'Within any valid pairwise comparison, the task snapshot, tools, limits, ' +
    'verification, and trials are held constant; changed variables are explicit.',
  presentationOrder:
    'Unranked published runs, newest first. Use the pairwise comparability receipt ' +
    'before interpreting completion differences.',
  emptyTitle: 'No published Real-Work Agent Cabinet runs yet.',
  emptyBody: 'Offline dry-run artifacts do not appear.',
};

/** Title-case a raw backend category key (e.g. "repository-repair" →
 *  "Repository Repair"). Deliberately does NOT map through the Arcade
 *  CATEGORY_DISPLAY_NAMES — cabinet categories are raw task-family keys. */
export function categoryTitle(rawKey) {
  return String(rawKey ?? '')
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

/** [rawKey, completion] pairs sorted by raw key for deterministic display. */
export function sortedCategoryEntries(categoryCompletion) {
  return Object.entries(categoryCompletion ?? {}).sort(([a], [b]) => a.localeCompare(b));
}

/** Controlled-variable sentence assembled from the detail payload's
 *  held_constant list and changed_variables note.
 *
 *  held_constant lists the fields that must MATCH for a valid pairwise
 *  comparison — it is a comparison requirement, not a claim that every run on
 *  the board actually held them constant (harness, for example, may differ
 *  across listed runs while still being a comparability requirement). */
export function controlledVariableSentence(detail) {
  const held = Array.isArray(detail?.held_constant)
    ? detail.held_constant.filter(Boolean)
    : [];
  const changed = typeof detail?.changed_variables === 'string'
    ? detail.changed_variables.trim()
    : '';
  const heldPart = held.length
    ? `Must match for a valid pairwise comparison: ${held.join(', ')}.`
    : '';
  return [heldPart, changed].filter(Boolean).join(' ');
}
