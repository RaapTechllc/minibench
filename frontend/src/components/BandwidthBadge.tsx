import clsx from 'clsx';

export function bandwidthColor(gbs: number | null | undefined): string {
  if (!gbs) return 'text-gray-500';
  if (gbs >= 200) return 'text-yellow-400';
  if (gbs >= 100) return 'text-green-400';
  if (gbs >= 50) return 'text-amber-400';
  return 'text-red-400';
}

export function bandwidthBg(gbs: number | null | undefined): string {
  if (!gbs) return 'bg-gray-500/10';
  if (gbs >= 200) return 'bg-yellow-400/10';
  if (gbs >= 100) return 'bg-green-400/10';
  if (gbs >= 50) return 'bg-amber-400/10';
  return 'bg-red-400/10';
}

export default function BandwidthBadge({ gbs }: { gbs: number | null | undefined }) {
  if (!gbs) return <span className="text-gray-500">—</span>;
  return (
    <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold', bandwidthBg(gbs), bandwidthColor(gbs))}>
      {gbs} GB/s
    </span>
  );
}
