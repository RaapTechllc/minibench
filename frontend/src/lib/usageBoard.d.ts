export const CITE_TEMPLATE: string;
export function citation(asOf: string): string;
export function modelPageUrl(id: string): string;
export function taskShare(row: { task_shares?: Record<string, number> }, task: string): number | null;
export function sortByCost<T extends { id: string; blended_per_million?: number | null }>(rows: T[]): T[];
export function sortByLatency<T extends { id: string; latency_ms?: number | null }>(rows: T[]): T[];
export function sortByTask<T extends { id: string; blended_per_million?: number | null; task_shares?: Record<string, number> }>(rows: T[], task: string): T[];
export function formatUsdPerMillion(value: number | null | undefined): string;
export function formatTokens(value: number | null | undefined): string;
