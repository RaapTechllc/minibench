export type TierId =
  | 'insert-coin'
  | 'warm-up'
  | 'high-score'
  | 'boss-beaten'
  | 'credits-rolling';

export interface TierBand {
  id: TierId;
  label: string;
  min: number;
  max: number;
}

export interface CabinetOption {
  suite: string;
  label: string;
  season: string;
}

export interface Scorecard {
  tier: string;
  score: number;
  tierId: TierId;
}

export type SaturationState = 'ok' | 'promote';

export const TIER_BANDS: readonly TierBand[];
export const CREDITS_ROLLING_MIN: number;
export const SATURATION_THRESHOLD: number;
export const DEFAULT_CABINET_SUITE: string;
export const CATEGORY_DISPLAY_NAMES: Readonly<Record<string, string>>;
export const CATEGORY_DISPLAY_ORDER: readonly string[];
export const CABINET_OPTIONS: readonly CabinetOption[];

export function tierIdFromPassRate(passRate: number): TierId;
export function tierLabelFromPassRate(passRate: number): string;
export function categoryDisplayName(backendKey: string): string;
export function orderCategoryKeys(backendKeys: string[]): string[];
export function formatScorecard(passRate: number): Scorecard;
export function formatScorecardLabel(passRate: number): string;
export function cabinetForSuite(suite: string): CabinetOption | null;
export function tierChromeClass(tierId: string): string;
export function evaluateSaturation(
  entries: Array<{ pass_rate?: number | string | null }>,
  threshold?: number,
): SaturationState;
