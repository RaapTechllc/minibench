import { useEffect } from 'react';
import { Navigate } from 'react-router-dom';

const NOTICE_KEY = 'minibench-legacy-leaderboard-notice';

/** Sets a one-time flag so Models can show a migration banner, then redirects. */
export default function LegacyLeaderboardRedirect() {
  useEffect(() => {
    sessionStorage.setItem(NOTICE_KEY, '1');
  }, []);

  return <Navigate to="/models" replace />;
}

export function consumeLegacyLeaderboardNotice(): boolean {
  if (sessionStorage.getItem(NOTICE_KEY) !== '1') return false;
  sessionStorage.removeItem(NOTICE_KEY);
  return true;
}
