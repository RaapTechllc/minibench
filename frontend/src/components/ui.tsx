/* Shared UI primitives — the design system in one place so pages compose it
   instead of re-implementing table/header/badge markup. Precision-instrument
   language: hairline rules, tabular-mono numbers, one blue accent. */
import type { ReactNode, SelectHTMLAttributes } from 'react';

/* ── Page header ─────────────────────────────────────────────────────────── */
export function PageHeader({
  eyebrow, title, children,
}: { eyebrow?: string; title: string; children?: ReactNode }) {
  return (
    <header className="animate-rise">
      {eyebrow && (
        <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-accent mb-2">
          {eyebrow}
        </div>
      )}
      <h1 className="text-4xl font-semibold tracking-tight text-ink">{title}</h1>
      {children && <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-ink-2">{children}</p>}
    </header>
  );
}

/* ── Card ────────────────────────────────────────────────────────────────── */
export function Card({ className = '', children }: { className?: string; children: ReactNode }) {
  return (
    <div className={`rounded-xl bg-surface border border-line shadow-card ${className}`}>
      {children}
    </div>
  );
}

export function CardHeader({ title, sub, right }: { title: string; sub?: string; right?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 px-5 pt-5 pb-3">
      <div>
        <h2 className="text-[15px] font-semibold text-ink">{title}</h2>
        {sub && <p className="text-[13px] text-ink-2 mt-0.5">{sub}</p>}
      </div>
      {right}
    </div>
  );
}

/* ── Stat tile ───────────────────────────────────────────────────────────── */
export function Stat({
  label, value, sub, accent = false,
}: { label: string; value: ReactNode; sub?: ReactNode; accent?: boolean }) {
  return (
    <Card className="px-5 py-4">
      <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3">{label}</div>
      <div className={`tnum mt-1.5 text-3xl font-semibold tracking-tight ${accent ? 'text-accent' : 'text-ink'}`}>
        {value}
      </div>
      {sub && <div className="text-[13px] text-ink-2 mt-1">{sub}</div>}
    </Card>
  );
}

/* ── Badges ──────────────────────────────────────────────────────────────── */
type Tone = 'neutral' | 'accent' | 'pass' | 'fail' | 'frontier';
const TONE: Record<Tone, string> = {
  neutral: 'bg-surface-2 text-ink-2 border-line',
  accent: 'bg-accent-soft text-accent-strong border-transparent',
  pass: 'bg-pass-soft text-pass border-transparent',
  fail: 'bg-fail-soft text-fail border-transparent',
  frontier: 'bg-frontier-soft text-frontier border-transparent',
};
export function Badge({
  tone = 'neutral', children, title,
}: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span title={title}
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${TONE[tone]}`}>
      {children}
    </span>
  );
}

/* Official (private split) vs Dev-slice (public, contamination-prone). This
   validity signal is unique to minibench's rigor — surface it prominently. */
export function ValidityBadge({ isPrivate }: { isPrivate: boolean | null }) {
  if (isPrivate === null || isPrivate === undefined) return null;
  return isPrivate
    ? <Badge tone="accent" title="Scored on a private held-out split — the official, contamination-resistant number.">● Official</Badge>
    : <Badge tone="neutral" title="Scored on the public dev slice — a reference number, contamination-prone.">○ Dev slice</Badge>;
}

/* ── Select ──────────────────────────────────────────────────────────────── */
export function Select({
  label, className = '', ...props
}: { label: string } & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <label className="flex items-center gap-2 text-[13px] text-ink-2">
      <span className="sr-only sm:not-sr-only">{label}</span>
      <select
        aria-label={label}
        className={`rounded-lg border border-line-strong bg-surface px-3 py-1.5 text-[13px] text-ink
          hover:border-ink-3 focus:border-accent transition-colors ${className}`}
        {...props}
      />
    </label>
  );
}

/* ── States ──────────────────────────────────────────────────────────────── */
export function Skeleton({ rows = 6 }: { rows?: number }) {
  return (
    <Card className="p-5">
      <div className="animate-pulse space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-9 rounded-lg bg-surface-2" style={{ opacity: 1 - i * 0.08 }} />
        ))}
      </div>
    </Card>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <Card className="px-6 py-14 text-center">
      <div className="text-[15px] font-medium text-ink">{title}</div>
      {children && <div className="mt-2 text-[13px] text-ink-2 max-w-md mx-auto">{children}</div>}
    </Card>
  );
}

export function ErrorState({ onRetry, children }: { onRetry?: () => void; children: ReactNode }) {
  return (
    <Card className="px-6 py-12 text-center">
      <div className="text-[15px] font-medium text-fail">Couldn't load this</div>
      <div className="mt-2 text-[13px] text-ink-2">{children}</div>
      {onRetry && (
        <button onClick={onRetry}
          className="mt-4 rounded-lg bg-accent px-4 py-1.5 text-[13px] font-medium text-white hover:bg-accent-strong transition-colors">
          Try again
        </button>
      )}
    </Card>
  );
}

/* ── Confidence-interval range bar — the instrument signature. Renders a 95%
   CI as a hairline track with a filled point, so a reader sees the estimate
   AND its uncertainty at a glance. ─────────────────────────────────────────── */
/* Clickable table header for client-side sort. */
export function SortableTh({
  label, active, dir, onClick, className = '', title,
}: {
  label: string;
  active: boolean;
  dir: 'asc' | 'desc';
  onClick: () => void;
  className?: string;
  title?: string;
}) {
  const arrow = active ? (dir === 'asc' ? ' ↑' : ' ↓') : '';
  return (
    <th className={className}>
      <button
        type="button"
        title={title}
        onClick={onClick}
        className={`inline-flex items-center gap-0.5 font-semibold capitalize transition-colors hover:text-ink ${
          active ? 'text-accent' : 'text-ink-3'
        }`}
      >
        {label}
        <span className="tnum text-[10px]">{arrow}</span>
      </button>
    </th>
  );
}

export function CIBar({ lo, hi, value }: { lo: number | null; hi: number | null; value: number }) {
  const pct = (x: number) => `${Math.max(0, Math.min(100, x))}%`;
  const hasCI = lo !== null && hi !== null;
  return (
    <div className="flex items-center gap-2">
      <span className="tnum text-[13px] font-semibold text-ink w-12 text-right">{value.toFixed(1)}</span>
      <div className="relative h-1.5 flex-1 rounded-full bg-line min-w-[64px]">
        {hasCI && (
          <div className="absolute inset-y-0 rounded-full bg-accent-soft"
            style={{ left: pct(lo!), right: pct(100 - hi!) }} />
        )}
        <div className="absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent ring-2 ring-surface"
          style={{ left: pct(value) }} />
      </div>
    </div>
  );
}
