export interface BenchmarkSuiteOption {
  suite: string;
  label: string;
  season: string;
}

export type SaturationState = 'ok' | 'promote';

export const SATURATION_PASS_RATE_MIN: number;
export const SATURATION_THRESHOLD: number;
export const DEFAULT_FEATURED_SUITE: string;
export const CATEGORY_DISPLAY_NAMES: Readonly<Record<string, string>>;
export const CATEGORY_DISPLAY_ORDER: readonly string[];
export const BENCHMARK_SUITE_OPTIONS: readonly BenchmarkSuiteOption[];

export function categoryDisplayName(backendKey: string): string;
export function orderCategoryKeys(backendKeys: string[]): string[];
export function suiteMetadata(suite: string): BenchmarkSuiteOption | null;
export function evaluateSaturation(
  entries: Array<{ pass_rate?: number | string | null }>,
  threshold?: number,
): SaturationState;
