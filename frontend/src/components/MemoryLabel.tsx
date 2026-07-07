/**
 * Clearly distinguishes System RAM vs VRAM in all views.
 */
export default function MemoryLabel({
  ramGb,
  vramGb,
  memType,
}: {
  ramGb: number | null;
  vramGb: number | null;
  memType: string | null;
}) {
  return (
    <div className="flex flex-col text-xs">
      <span className="text-ink-2">
        <span className="text-ink-3">System RAM:</span>{' '}
        <span className="tnum text-ink">{ramGb ?? '?'}</span> GB
        {memType && <span className="text-ink-3 ml-1">({memType})</span>}
      </span>
      {vramGb != null && vramGb > 0 ? (
        <span className="text-accent">
          <span className="text-accent">VRAM:</span>{' '}
          <span className="tnum">{vramGb}</span> GB
        </span>
      ) : (
        <span className="text-ink-3 text-[10px]">No dedicated VRAM</span>
      )}
    </div>
  );
}
