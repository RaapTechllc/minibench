export const SATURATION_PASS_RATE_MIN = 81;
export const SATURATION_THRESHOLD = 0.3;
export const DEFAULT_FEATURED_SUITE = 'minibench-hard-v1';

/** @type {Readonly<Record<string, string>>} */
export const CATEGORY_DISPLAY_NAMES = {
  reasoning: 'Math & Logic',
  'tool-use': 'Data Pull',
  instruction: 'Follow Rules',
  coding: 'Write Code',
};

/** Display order for known backend category keys. */
export const CATEGORY_DISPLAY_ORDER = ['reasoning', 'tool-use', 'instruction', 'coding'];

/** @type {ReadonlyArray<{ suite: string, label: string, season: string }>} */
export const BENCHMARK_SUITE_OPTIONS = [
  { suite: 'minibench-hard-v1', label: 'Hard v1', season: 'Primary' },
  { suite: 'minibench-v2', label: 'v2', season: 'Current' },
  { suite: 'minibench-core-v1', label: 'Core v1', season: 'Regression' },
];


/**
 * @param {string} backendKey
 * @returns {string}
 */
export function categoryDisplayName(backendKey) {
  if (backendKey in CATEGORY_DISPLAY_NAMES) {
    return CATEGORY_DISPLAY_NAMES[backendKey];
  }
  return backendKey
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

/**
 * @param {string[]} backendKeys
 * @returns {string[]}
 */
export function orderCategoryKeys(backendKeys) {
  const unique = [...new Set(backendKeys)];
  const known = CATEGORY_DISPLAY_ORDER.filter((k) => unique.includes(k));
  const rest = unique.filter((k) => !CATEGORY_DISPLAY_ORDER.includes(k)).sort();
  return [...known, ...rest];
}

/**
 * @param {string} suite
 * @returns {{ label: string, season: string } | null}
 */
export function suiteMetadata(suite) {
  return BENCHMARK_SUITE_OPTIONS.find((candidate) => candidate.suite === suite) ?? null;
}

/**
 * @param {Array<{ pass_rate?: number | string | null }>} entries
 * @param {number} [threshold]
 * @returns {'ok' | 'promote'}
 */
export function evaluateSaturation(entries, threshold = SATURATION_THRESHOLD) {
  if (!entries.length) return 'ok';
  const highPerforming = entries.filter((e) => Number(e.pass_rate) >= SATURATION_PASS_RATE_MIN).length;
  return highPerforming / entries.length > threshold ? 'promote' : 'ok';
}
