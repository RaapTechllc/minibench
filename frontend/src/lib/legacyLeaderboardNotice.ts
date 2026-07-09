const NOTICE_KEY = 'minibench-legacy-leaderboard-notice';

/** One-time flag set by /leaderboard redirect; Models consumes it for a banner. */
export function markLegacyLeaderboardNotice(): void {
  sessionStorage.setItem(NOTICE_KEY, '1');
}

export function consumeLegacyLeaderboardNotice(): boolean {
  if (sessionStorage.getItem(NOTICE_KEY) !== '1') return false;
  sessionStorage.removeItem(NOTICE_KEY);
  return true;
}
