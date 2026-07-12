// One-shot sessionStorage flag: /leaderboard redirect sets it, /models
// consumes it once to show the migration banner. Lives in lib/ so the page
// files each export only a component (react-refresh constraint).
const NOTICE_KEY = 'minibench-legacy-leaderboard-notice';

export function setLegacyLeaderboardNotice(): void {
  sessionStorage.setItem(NOTICE_KEY, '1');
}

export function consumeLegacyLeaderboardNotice(): boolean {
  if (sessionStorage.getItem(NOTICE_KEY) !== '1') return false;
  sessionStorage.removeItem(NOTICE_KEY);
  return true;
}
