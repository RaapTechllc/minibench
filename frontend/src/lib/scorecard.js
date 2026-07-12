/** @typedef {'insert-coin' | 'warm-up' | 'high-score' | 'boss-beaten' | 'credits-rolling'} TierId */

/** @type {ReadonlyArray<{ id: TierId, label: string, min: number, max: number }>} */
export const TIER_BANDS = [
  { id: 'insert-coin', label: 'Insert Coin', min: 0, max: 35 },
  { id: 'warm-up', label: 'Warm Up', min: 36, max: 50 },
  { id: 'high-score', label: 'High Score', min: 51, max: 65 },
  { id: 'boss-beaten', label: 'Boss Beaten', min: 66, max: 80 },
  { id: 'credits-rolling', label: 'Credits Rolling', min: 81, max: 100 },
];

export const CREDITS_ROLLING_MIN = 81;
export const SATURATION_THRESHOLD = 0.3;
export const DEFAULT_CABINET_SUITE = 'minibench-hard-v1';

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
export const CABINET_OPTIONS = [
  { suite: 'minibench-hard-v1', label: 'Hard Cabinet', season: 'Season 1' },
  { suite: 'minibench-v2', label: 'Season 2', season: 'Season 2' },
  { suite: 'minibench-core-v1', label: 'Classic Cabinet', season: 'Regression' },
];

/**
 * @param {number} passRate
 * @returns {TierId}
 */
export function tierIdFromPassRate(passRate) {
  const score = Math.round(Number(passRate));
  if (!Number.isFinite(score)) return 'insert-coin';
  const clamped = Math.min(100, Math.max(0, score));
  const band = TIER_BANDS.find((b) => clamped >= b.min && clamped <= b.max);
  return band?.id ?? 'insert-coin';
}

/**
 * @param {number} passRate
 * @returns {string}
 */
export function tierLabelFromPassRate(passRate) {
  const id = tierIdFromPassRate(passRate);
  return TIER_BANDS.find((b) => b.id === id)?.label ?? 'Insert Coin';
}

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
 * @param {number} passRate
 * @returns {{ tier: string, score: number, tierId: TierId }}
 */
export function formatScorecard(passRate) {
  const score = Math.round(Number(passRate));
  const safeScore = Number.isFinite(score) ? Math.min(100, Math.max(0, score)) : 0;
  const tierId = tierIdFromPassRate(safeScore);
  const tier = TIER_BANDS.find((b) => b.id === tierId)?.label ?? 'Insert Coin';
  return { tier, score: safeScore, tierId };
}

/**
 * @param {number} passRate
 * @returns {string}
 */
export function formatScorecardLabel(passRate) {
  const { tier, score } = formatScorecard(passRate);
  return `${tier} · ${score}`;
}

/**
 * @param {string} suite
 * @returns {{ label: string, season: string } | null}
 */
export function cabinetForSuite(suite) {
  return CABINET_OPTIONS.find((c) => c.suite === suite) ?? null;
}

/**
 * @param {string} tierId
 * @returns {string}
 */
export function tierChromeClass(tierId) {
  const known = TIER_BANDS.some((b) => b.id === tierId);
  const id = known ? tierId : 'insert-coin';
  return `arcade-tier-${id}`;
}

/**
 * @param {Array<{ pass_rate?: number | string | null }>} entries
 * @param {number} [threshold]
 * @returns {'ok' | 'promote'}
 */
export function evaluateSaturation(entries, threshold = SATURATION_THRESHOLD) {
  if (!entries.length) return 'ok';
  const creditsRolling = entries.filter((e) => Number(e.pass_rate) >= CREDITS_ROLLING_MIN).length;
  return creditsRolling / entries.length > threshold ? 'promote' : 'ok';
}
