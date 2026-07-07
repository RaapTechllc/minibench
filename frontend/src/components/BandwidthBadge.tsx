import clsx from 'clsx';

/* Light-palette bandwidth tiers. Thresholds are identical to lib/bandwidth.ts;
   only the classes are swapped to the daylight tokens. Kept inline (not in the
   shared lib) so this shared badge renders in the light design without touching
   other consumers of the lib. */
function tierClasses(gbs: number): string {
  if (gbs >= 200) return 'text-frontier bg-frontier-soft';
  if (gbs >= 100) return 'text-pass bg-pass-soft';
  if (gbs >= 50) return 'text-amber-600 bg-amber-50';
  return 'text-fail bg-fail-soft';
}

export default function BandwidthBadge({ gbs }: { gbs: number | null | undefined }) {
  if (!gbs) return <span className="text-ink-3">—</span>;
  return (
    <span
      className={clsx(
        'tnum inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold',
        tierClasses(gbs),
      )}
    >
      {gbs} GB/s
    </span>
  );
}
