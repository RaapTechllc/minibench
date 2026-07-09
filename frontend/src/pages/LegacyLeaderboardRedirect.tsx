import { useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { markLegacyLeaderboardNotice } from '../lib/legacyLeaderboardNotice';

/** Sets a one-time flag so Models can show a migration banner, then redirects. */
export default function LegacyLeaderboardRedirect() {
  useEffect(() => {
    markLegacyLeaderboardNotice();
  }, []);

  return <Navigate to="/models" replace />;
}
