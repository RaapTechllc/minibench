export const LAST_VISIT_KEY: string;
export function parseTime(value: string | null | undefined): number | null;
export function newSince<T>(items: T[], sinceIso: string | null | undefined, timeKey: keyof T & string): T[];
export function sortNewestFirst<T>(items: T[], timeKey: keyof T & string): T[];
export function latestTimestamp<T>(items: T[], timeKey: keyof T & string): string | null;
export function asOfLabel(iso: string | null | undefined, fallback?: string): string;
