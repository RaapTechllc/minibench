import { useState } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Value from './pages/Value';
import Compare from './pages/Compare';
import Submit from './pages/Submit';
import Hardware from './pages/Hardware';
import LegacyLeaderboardRedirect from './pages/LegacyLeaderboardRedirect';
import BenchmarkDetail from './pages/BenchmarkDetail';
import Agents from './pages/Agents';
import RunDetail from './pages/RunDetail';
import MoaCalculator from './pages/MoaCalculator';
import Models from './pages/Models';
import Methodology from './pages/Methodology';

const NAV = [
  { path: '/', label: 'Value' },
  { path: '/models', label: 'Models' },
  { path: '/agents', label: 'Configurations' },
  { path: '/compare', label: 'Compare' },
  { path: '/moa-calculator', label: 'Cost planner' },
  { path: '/hardware', label: 'Deployment' },
  { path: '/methodology', label: 'Evidence' },
];

function NavLinks({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <>
      {NAV.map(({ path, label }) => {
        const active = pathname === path;
        return (
          <Link
            key={path}
            to={path}
            onClick={onNavigate}
            aria-current={active ? 'page' : undefined}
            className={`flex min-h-9 items-center border-b-2 px-2.5 text-[13px] font-medium transition-colors ${
              active ? 'border-accent text-ink' : 'border-transparent text-ink-2 hover:border-line-strong hover:text-ink'
            }`}
          >
            {label}
          </Link>
        );
      })}
    </>
  );
}

export default function App() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen">
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <header className="sticky top-0 z-50 border-b border-line bg-surface/95 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-4 px-4 lg:px-6">
          <Link to="/" className="flex shrink-0 items-center gap-2.5 font-semibold tracking-tight text-ink">
            <span className="grid h-7 w-7 place-items-center rounded bg-ink text-[10px] font-bold tracking-wide text-white">
              MB
            </span>
            <span>MiniBench</span>
            <span className="hidden border-l border-line pl-2.5 text-xs font-normal text-ink-3 sm:inline">Value Intelligence</span>
          </Link>
          <nav className="ml-2 hidden items-center gap-0.5 lg:flex">
            <NavLinks pathname={pathname} />
          </nav>
          <button
            className="ml-auto grid h-11 w-11 place-items-center rounded text-ink-2 hover:bg-surface-2 lg:hidden"
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
        {open && (
          <nav className="border-t border-line bg-surface px-3 py-2 lg:hidden" aria-label="Mobile navigation">
            <div className="flex flex-col gap-0.5">
              <NavLinks pathname={pathname} onNavigate={() => setOpen(false)} />
            </div>
          </nav>
        )}
      </header>

      <main id="main-content" className="mx-auto max-w-[1440px] px-4 py-7 lg:px-6 lg:py-9">
        <Routes>
          <Route path="/" element={<Value />} />
          <Route path="/legacy-overview" element={<Dashboard />} />
          <Route path="/models" element={<Models />} />
          <Route path="/leaderboard" element={<LegacyLeaderboardRedirect />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/agents/runs/:runId" element={<RunDetail />} />
          <Route path="/benchmarks/:id" element={<BenchmarkDetail />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/moa-calculator" element={<MoaCalculator />} />
          <Route path="/hardware" element={<Hardware />} />
          <Route path="/submit" element={<Submit />} />
          <Route path="/methodology" element={<Methodology />} />
        </Routes>
      </main>

      <footer className="mx-auto max-w-[1440px] px-4 py-8 lg:px-6">
        <div className="flex flex-col gap-2 border-t border-line pt-5 text-xs text-ink-3 sm:flex-row sm:items-center sm:justify-between">
          <span>MiniBench by RaapTech LLC</span>
          <span>Measured results · explicit assumptions · auditable evidence</span>
        </div>
      </footer>
    </div>
  );
}
