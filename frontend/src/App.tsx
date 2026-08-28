import { useState } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Gauge, BarChart3, Database, Bot, Briefcase, Calculator, Trophy, BookOpen, Activity, Menu, X } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Compare from './pages/Compare';
import Submit from './pages/Submit';
import Hardware from './pages/Hardware';
import LegacyLeaderboardRedirect from './pages/LegacyLeaderboardRedirect';
import BenchmarkDetail from './pages/BenchmarkDetail';
import Agents from './pages/Agents';
import AgentCabinet from './pages/AgentCabinet';
import AgentCabinetRun from './pages/AgentCabinetRun';
import RunDetail from './pages/RunDetail';
import MoaCalculator from './pages/MoaCalculator';
import Models from './pages/Models';
import Methodology from './pages/Methodology';
import UsageBoard from './pages/UsageBoard';

const NAV = [
  { path: '/', label: 'Overview', icon: BarChart3 },
  { path: '/models', label: 'Models', icon: Trophy },
  { path: '/usage/cost', label: 'Usage', icon: Activity },
  { path: '/agents', label: 'Agents', icon: Bot },
  { path: '/agent-cabinet', label: 'Agent Cabinet', icon: Briefcase },
  { path: '/moa-calculator', label: 'MoA Calculator', icon: Calculator },
  { path: '/hardware', label: 'Test Rigs', icon: Database },
  { path: '/methodology', label: 'Methodology', icon: BookOpen },
];

function NavLinks({ pathname, onNavigate }: { pathname: string; onNavigate?: () => void }) {
  return (
    <>
      {NAV.map(({ path, label, icon: Icon }) => {
        const active = pathname === path
          || (path === '/usage/cost' && pathname.startsWith('/usage'))
          || (path === '/agent-cabinet' && pathname.startsWith('/agent-cabinet'));
        return (
          <Link
            key={path}
            to={path}
            onClick={onNavigate}
            aria-current={active ? 'page' : undefined}
            className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors ${
              active ? 'bg-accent-soft text-accent-strong' : 'text-ink-2 hover:text-ink hover:bg-surface-2'
            }`}
          >
            <Icon className="h-4 w-4" strokeWidth={2} />
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
      <header className="sticky top-0 z-50 border-b border-line bg-paper/85 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 lg:px-6">
          <Link to="/" className="flex shrink-0 items-center gap-2 font-semibold tracking-tight text-ink">
            <span className="grid h-7 w-7 place-items-center rounded-lg bg-accent text-white">
              <Gauge className="h-4 w-4" strokeWidth={2.5} />
            </span>
            MiniBench
          </Link>
          <nav className="ml-2 hidden items-center gap-0.5 lg:flex">
            <NavLinks pathname={pathname} />
          </nav>
          <button
            className="ml-auto grid h-9 w-9 place-items-center rounded-lg text-ink-2 hover:bg-surface-2 lg:hidden"
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
        {open && (
          <nav className="border-t border-line bg-surface px-3 py-2 lg:hidden">
            <div className="flex flex-col gap-0.5">
              <NavLinks pathname={pathname} onNavigate={() => setOpen(false)} />
            </div>
          </nav>
        )}
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 lg:px-6 lg:py-10">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/models" element={<Models />} />
          <Route path="/usage" element={<UsageBoard />} />
          <Route path="/usage/cost" element={<UsageBoard />} />
          <Route path="/usage/task" element={<UsageBoard />} />
          <Route path="/usage/latency" element={<UsageBoard />} />
          <Route path="/leaderboard" element={<LegacyLeaderboardRedirect />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/agents/runs/:runId" element={<RunDetail />} />
          <Route path="/agent-cabinet" element={<AgentCabinet />} />
          <Route path="/agent-cabinet/runs/:runId" element={<AgentCabinetRun />} />
          <Route path="/benchmarks/:id" element={<BenchmarkDetail />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/moa-calculator" element={<MoaCalculator />} />
          <Route path="/hardware" element={<Hardware />} />
          <Route path="/submit" element={<Submit />} />
          <Route path="/methodology" element={<Methodology />} />
        </Routes>
      </main>

      <footer className="mx-auto max-w-7xl px-4 py-8 lg:px-6">
        <div className="border-t border-line pt-6 text-[13px] text-ink-3">
          MiniBench by RaapTech LLC — deterministic, contamination-resistant model evaluation.
        </div>
      </footer>
    </div>
  );
}
