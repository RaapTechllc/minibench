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
