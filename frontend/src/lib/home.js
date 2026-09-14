// Pure helpers for the landing page's "what changed" feed. Kept free of React
// and DOM so `node --test` can exercise the freshness rules directly.

export const LAST_VISIT_KEY = 'minibench.home.lastVisit';

/** Parse an ISO-ish timestamp; null when absent or unparseable. */
export function parseTime(value) {
  if (!value) return null;
  const t = new Date(value).getTime();
  return Number.isNaN(t) ? null : t;
}

/**
 * Items whose `timeKey` field is strictly after `sinceIso`. When `sinceIso` is
 * null (first visit) nothing is "new": we never fabricate novelty.
 */
export function newSince(items, sinceIso, timeKey) {
  const since = parseTime(sinceIso);
  if (since === null) return [];
  return items.filter((item) => {
    const t = parseTime(item?.[timeKey]);
    return t !== null && t > since;
  });
}

/** Newest-first by `timeKey`; unparseable timestamps sink to the end. */
export function sortNewestFirst(items, timeKey) {
  return [...items].sort((a, b) => {
    const ta = parseTime(a?.[timeKey]);
    const tb = parseTime(b?.[timeKey]);
    if (ta === null && tb === null) return 0;
    if (ta === null) return 1;
    if (tb === null) return -1;
    return tb - ta;
  });
}

/** Latest timestamp among items, or null when none parse. */
export function latestTimestamp(items, timeKey) {
  let best = null;
  for (const item of items) {
    const t = parseTime(item?.[timeKey]);
    if (t !== null && (best === null || t > best)) best = t;
  }
  return best === null ? null : new Date(best).toISOString();
}

/** Human "as of" label: date only, or a fallback when unknown. */
export function asOfLabel(iso, fallback = 'as-of unknown') {
  const t = parseTime(iso);
  if (t === null) return fallback;
  return `as of ${new Date(t).toISOString().slice(0, 10)}`;
}
