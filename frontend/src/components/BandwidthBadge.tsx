import clsx from 'clsx';
import { bandwidthColor, bandwidthBg } from '../lib/bandwidth';

export default function BandwidthBadge({ gbs }: { gbs: number | null | undefined }) {
  if (!gbs) return <span className="text-gray-500">—</span>;
  return (
    <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold', bandwidthBg(gbs), bandwidthColor(gbs))}>
      {gbs} GB/s
    </span>
  );
}
