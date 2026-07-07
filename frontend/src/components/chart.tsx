/* eslint-disable react-refresh/only-export-components --
   Shared chart module: co-locates the theme constants (colors, formatters,
   axis props) with the two tiny presentational chart helpers that use them.
   The fast-refresh rule is dev-HMR only and doesn't apply to this non-page
   utility module. */
/* Shared chart theme — one visual language for every recharts figure so the
   Pareto frontier, scatters, and bars all read as the same instrument. */
import type { ReactNode } from 'react';

export const CHART = {
  accent: '#0a6cff',
  frontier: '#b8860b',
  line: '#e8e8ed',
  ink3: '#9a9aa0',
  grid: '#eef0f4',
};

export const fmtPct = (n: number | string | null | undefined) =>
  n === null || n === undefined ? '—' : `${Number(n).toFixed(1)}%`;

export const fmtCost = (n: number | string | null | undefined) =>
  n === null || n === undefined ? '—' : `$${Number(n).toFixed(4)}`;

/* Frontier-aware scatter dot: gold ring for points on the cost/accuracy
   Pareto frontier, quiet blue otherwise. */
export function FrontierDot(props: {
  cx?: number; cy?: number; payload?: { on_pareto_frontier?: boolean };
}) {
  const { cx, cy, payload } = props;
  if (cx === undefined || cy === undefined) return null;
  const on = payload?.on_pareto_frontier;
  return on ? (
    <g>
      <circle cx={cx} cy={cy} r={7} fill={CHART.frontier} fillOpacity={0.16} />
      <circle cx={cx} cy={cy} r={4} fill={CHART.frontier} stroke="#fff" strokeWidth={1.5} />
    </g>
  ) : (
    <circle cx={cx} cy={cy} r={4} fill={CHART.accent} fillOpacity={0.85} stroke="#fff" strokeWidth={1.5} />
  );
}

/* Styled tooltip container — matches the card surface, never the recharts default. */
export function TooltipCard({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg border border-line bg-surface px-3 py-2 text-[12px] shadow-pop">
      {children}
    </div>
  );
}

/* Common axis props to keep every chart's grid/ticks consistent. */
export const axisProps = {
  tick: { fontSize: 11, fill: CHART.ink3 },
  stroke: CHART.line,
  tickLine: false,
} as const;
