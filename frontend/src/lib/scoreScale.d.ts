export interface HeatBand {
  name: 'excellent' | 'strong' | 'mixed' | 'weak' | 'failing';
  bg: string;
  text: string;
}

export function heatBand(pct: number | null | undefined): HeatBand | null;

export function compositeScore(
  categoryPassRates: Record<string, number | null | undefined> | null | undefined,
): number | null;
