// Heatmap score scale + composite for the model leaderboard.
//
// Pure functions (no React) so node --test can cover the band edges and the
// composite math directly. Bands follow the leaderboard-heatmap pattern from
// docs/research-woaibench.md §"Heatmap" (continuous glanceable scale, text
// always overlaid), tuned to MiniBench's light "precision instrument" theme:
// soft background tints that keep ink text readable in every band.

/** @typedef {{ name: string, bg: string, text: string }} HeatBand */

const BANDS = [
  { min: 85, name: 'excellent', bg: 'rgba(52, 168, 83, 0.16)', text: '#1e7d3f' },
  { min: 70, name: 'strong', bg: 'rgba(52, 168, 83, 0.09)', text: '#3c8a52' },
  { min: 55, name: 'mixed', bg: 'rgba(244, 180, 0, 0.14)', text: '#8a6d1a' },
  { min: 40, name: 'weak', bg: 'rgba(230, 124, 35, 0.14)', text: '#9c5a1d' },
  { min: 0, name: 'failing', bg: 'rgba(217, 83, 79, 0.13)', text: '#a63d3a' },
];

/**
 * Map a 0–100 score to its heat band. Returns null for null/undefined/NaN —
 * missing data gets no tint, never a fake color.
 * @param {number | null | undefined} pct
 * @returns {HeatBand | null}
 */
export function heatBand(pct) {
  if (pct == null || Number.isNaN(Number(pct))) return null;
  const v = Math.max(0, Math.min(100, Number(pct)));
  return BANDS.find((b) => v >= b.min) ?? BANDS[BANDS.length - 1];
}

/**
 * Equal-weight mean of per-category pass rates (the anti-specialization
 * composite: every category counts the same regardless of task count).
 * Returns null when there are no category scores.
 * @param {Record<string, number | null | undefined>} categoryPassRates
 * @returns {number | null}
 */
export function compositeScore(categoryPassRates) {
  const vals = Object.values(categoryPassRates ?? {}).filter(
    (v) => v != null && !Number.isNaN(Number(v)),
  );
  if (vals.length === 0) return null;
  const mean = vals.reduce((a, v) => a + Number(v), 0) / vals.length;
  return Math.round(mean * 10) / 10;
}
