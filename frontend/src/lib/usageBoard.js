/** Usage Board ranking + citation helpers. Numbers stay cited to OpenRouter. */

export const CITE_TEMPLATE = 'Source: OpenRouter (openrouter.ai/rankings), as of {as_of}. CC BY 4.0.';

export function citation(asOf) {
  return CITE_TEMPLATE.replace('{as_of}', asOf);
}

export function modelPageUrl(id) {
  return `https://openrouter.ai/${id}`;
}

export function taskShare(row, task) {
  const shares = row.task_shares || {};
  if (task in shares) return shares[task];
  const matches = Object.entries(shares)
    .filter(([key]) => key === task || key.startsWith(`${task}:`))
    .map(([, value]) => value);
  return matches.length ? Math.max(...matches) : null;
}

export function sortByCost(rows) {
  return [...rows]
    .filter((row) => row.blended_per_million != null)
    .sort((a, b) => a.blended_per_million - b.blended_per_million || a.id.localeCompare(b.id));
}

export function sortByLatency(rows) {
  return [...rows]
    .filter((row) => row.latency_ms != null)
    .sort((a, b) => a.latency_ms - b.latency_ms || a.id.localeCompare(b.id));
}

export function sortByTask(rows, task) {
  return [...rows]
    .map((row) => ({ row, share: taskShare(row, task) }))
    .filter((item) => item.share != null)
    .sort((a, b) => {
      if (b.share !== a.share) return b.share - a.share;
      const pa = a.row.blended_per_million ?? 1e9;
      const pb = b.row.blended_per_million ?? 1e9;
      if (pa !== pb) return pa - pb;
      return a.row.id.localeCompare(b.row.id);
    })
    .map((item) => item.row);
}

export function formatUsdPerMillion(value) {
  if (value == null) return '—';
  return `$${Number(value).toFixed(2)}/1M`;
}

export function formatTokens(value) {
  if (value == null) return '—';
  const n = Number(value);
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  return String(n);
}
