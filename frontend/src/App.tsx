import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Cpu, BarChart3, GitCompare, Terminal, Database, Bot, Calculator } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Leaderboard from './pages/Leaderboard';
import Compare from './pages/Compare';
import Submit from './pages/Submit';
import Hardware from './pages/Hardware';
import BenchmarkDetail from './pages/BenchmarkDetail';
import Agents from './pages/Agents';
import RunDetail from './pages/RunDetail';
import MoaCalculator from './pages/MoaCalculator';

const NAV = [
  { path: '/', label: 'Dashboard', icon: BarChart3 },
  { path: '/leaderboard', label: 'Leaderboard', icon: Cpu },
  { path: '/agents', label: 'Agents', icon: Bot },
  { path: '/compare', label: 'Compare', icon: GitCompare },
  { path: '/moa-calculator', label: 'MoA Calculator', icon: Calculator },
  { path: '/hardware', label: 'Hardware', icon: Database },
  { path: '/submit', label: 'Submit', icon: Terminal },
];

export default function App() {
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <nav className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 flex items-center h-14 gap-6">
          <Link to="/" className="flex items-center gap-2 font-bold text-lg text-white shrink-0">
            <Cpu className="w-5 h-5 text-cyan-400" />
            MiniBench
          </Link>
          <div className="flex gap-1 overflow-x-auto">
            {NAV.map(({ path, label, icon: Icon }) => (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
                  pathname === path
                    ? 'bg-cyan-500/15 text-cyan-400'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            ))}
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/agents/runs/:runId" element={<RunDetail />} />
          <Route path="/benchmarks/:id" element={<BenchmarkDetail />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/moa-calculator" element={<MoaCalculator />} />
          <Route path="/hardware" element={<Hardware />} />
          <Route path="/submit" element={<Submit />} />
        </Routes>
      </main>

      <footer className="border-t border-gray-800 py-4 text-center text-sm text-gray-500">
        MiniBench by RaapTech LLC — Memory bandwidth is king.
      </footer>
    </div>
  );
}
