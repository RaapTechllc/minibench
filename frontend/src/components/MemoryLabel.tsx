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
      <span className="text-gray-300">
        <span className="text-gray-500">System RAM:</span> {ramGb ?? '?'} GB
        {memType && <span className="text-gray-500 ml-1">({memType})</span>}
      </span>
      {vramGb != null && vramGb > 0 ? (
        <span className="text-purple-400">
          <span className="text-purple-500">VRAM:</span> {vramGb} GB
        </span>
      ) : (
        <span className="text-gray-600 text-[10px]">No dedicated VRAM</span>
      )}
    </div>
  );
}
