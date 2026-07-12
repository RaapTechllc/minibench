import { useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { setLegacyLeaderboardNotice } from '../lib/legacyNotice';

/** Sets a one-time flag so Models can show a migration banner, then redirects. */
export default function LegacyLeaderboardRedirect() {
  useEffect(() => {
    setLegacyLeaderboardNotice();
  }, []);

  return <Navigate to="/models" replace />;
}
