import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, CheckCircle2, Cpu, Trophy, Vote } from 'lucide-react';
import { api } from '../api';
import type { ArenaModel, Benchmark, Stats } from '../api';

const TASKS = [
  { id: 'overall', label: 'Overall Arena', blurb: 'General-purpose frontier model preference.' },
  { id: 'agentic_coding', label: 'Agentic Coding', blurb: 'Repo edits, tool use, tests, long coding loops.' },
  { id: 'image', label: 'Image / Design', blurb: 'Generation, editing, multimodal design critique.' },
  { id: 'long_running', label: 'Long-running Tasks', blurb: 'Large context, multi-hour agent runs, reliability.' },
  { id: 'research', label: 'Research', blurb: 'Fresh web synthesis, source handling, report quality.' },
] as const;

const REFERENCES = [
  {
    name: 'LMArena / Chatbot Arena',
    url: 'https://lmarena.ai/leaderboard',
    take: 'Blind pairwise voting is the correct public preference loop. MiniBench should copy the interaction pattern, not just a static benchmark table.',
  },
  {
    name: 'Artificial Analysis',
    url: 'https://artificialanalysis.ai/',
    take: 'Market-facing model pages need quality, speed, cost, context, and provider metadata side by side.',
  },
  {
    name: 'LiveBench',
    url: 'https://livebench.ai/',
    take: 'Objective task suites matter because arena votes alone drift toward vibe and brand recognition.',
  },
  {
    name: 'SWE-bench / Terminal-Bench',
    url: 'https://swebench.com/',
    take: 'Agentic coding should be evaluated as executable work: issue resolved, tests pass, cost/latency tracked.',
  },
];

export function fmtNum(v: number | null | undefined, suffix = '') {
  if (v == null) return '—';
  return `${Number(v).toLocaleString()}${suffix}`;
}

export function fmtCost(v: number | null) {
  if (v == null) return '—';
  return `$${Number(v).toFixed(v < 1 ? 3 : 2)}`;
}

function TaskPill({ active, children, onClick }: { active: boolean; children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-4 py-2 text-sm transition-colors ${
        active
          ? 'border-cyan-400 bg-cyan-400/15 text-cyan-200'
          : 'border-gray-800 bg-gray-900 text-gray-400 hover:border-gray-600 hover:text-gray-200'
      }`}
    >
      {children}
    </button>
  );
}

function ModelCard({ model, task, onVote }: { model: ArenaModel; task: string; onVote: (modelId: string) => void }) {
  return (
    <div className="group relative overflow-hidden rounded-2xl border border-gray-800 bg-gray-900 p-5 transition hover:border-cyan-800/80">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-cyan-400 via-purple-400 to-amber-300 opacity-70" />
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-gray-500">#{model.arena_rank ?? '—'}</span>
            <span className="rounded-full border border-gray-700 px-2 py-0.5 text-xs text-gray-400">{model.modality}</span>
          </div>
          <h3 className="mt-2 text-xl font-bold text-white">{model.display_name}</h3>
          <p className="text-sm text-gray-400">{model.provider}</p>
        </div>
        <button
          type="button"
          onClick={() => onVote(model.model_id)}
          className="flex items-center gap-1 rounded-lg border border-cyan-700/60 bg-cyan-500/10 px-3 py-2 text-sm font-semibold text-cyan-200 hover:bg-cyan-500/20"
          title={`Vote for ${model.display_name} on ${task}`}
        >
          <Vote className="h-4 w-4" /> {model.vote_count}
        </button>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-lg bg-gray-950 p-3">
          <div className="text-xs uppercase tracking-wide text-gray-500">Arena score</div>
          <div className="font-mono text-lg text-cyan-300">{fmtNum(model.arena_score)}</div>
        </div>
        <div className="rounded-lg bg-gray-950 p-3">
          <div className="text-xs uppercase tracking-wide text-gray-500">Intel index</div>
          <div className="font-mono text-lg text-purple-300">{fmtNum(model.intelligence_index)}</div>
        </div>
        <div className="rounded-lg bg-gray-950 p-3">
          <div className="text-xs uppercase tracking-wide text-gray-500">Speed</div>
          <div className="font-mono text-lg text-emerald-300">{fmtNum(model.output_speed_tps, ' t/s')}</div>
        </div>
        <div className="rounded-lg bg-gray-950 p-3">
          <div className="text-xs uppercase tracking-wide text-gray-500">Cost / 1M</div>
          <div className="font-mono text-lg text-amber-300">{fmtCost(model.cost_per_million_tokens)}</div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {model.strengths.map(s => (
          <span key={s} className="rounded-full bg-gray-800 px-2.5 py-1 text-xs text-gray-300">{s}</span>
        ))}
      </div>

      <a href={model.source_url} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-1 text-xs text-gray-500 hover:text-cyan-300">
        {model.source_name} <ArrowUpRight className="h-3 w-3" />
      </a>
    </div>
  );
}

export default function Dashboard() {
  const [arenaModels, setArenaModels] = useState<ArenaModel[]>([]);
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [task, setTask] = useState<(typeof TASKS)[number]['id']>('overall');
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.getArenaModels({ task }),
      api.getBenchmarks({ limit: '8' }),
      api.getStats(),
    ])
      .then(([models, b, s]) => { setArenaModels(models); setBenchmarks(b); setStats(s); })
      .finally(() => setLoading(false));
  }, [task]);

  const activeTask = TASKS.find(t => t.id === task)!;
  const hardwareLeader = useMemo(() => benchmarks.reduce<Benchmark | null>(
    (a, b) => Number(b.tokens_per_second) > Number(a?.tokens_per_second ?? 0) ? b : a,
    null,
  ), [benchmarks]);

  async function handleVote(modelId: string) {
    const res = await api.voteArenaModel(task, modelId);
    setArenaModels(models => models.map(m => m.model_id === modelId ? { ...m, vote_count: res.vote_count } : m));
    setNotice(res.accepted ? 'Vote counted.' : 'Already counted from this network for that model/task.');
    window.setTimeout(() => setNotice(null), 2400);
  }

  if (loading) return <div className="py-20 text-center text-gray-400">Loading MiniBench Arena...</div>;

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-3xl border border-cyan-900/50 bg-gradient-to-br from-gray-900 via-gray-950 to-cyan-950/40 p-6 md:p-8">
        <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs font-semibold text-cyan-200">
              <Trophy className="h-4 w-4" /> Arena-first dashboard
            </div>
            <h1 className="text-4xl font-black tracking-tight text-white md:text-5xl">MiniBench should rank models, not just machines.</h1>
            <p className="mt-4 max-w-3xl text-lg text-gray-300">
              The old dashboard was hardware-only. This view adds an LMArena-style model catalog, task-specific voting,
              external benchmark references, and keeps local hardware throughput as the cost/performance layer underneath.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link to="/agents" className="rounded-lg bg-cyan-400 px-4 py-2 font-semibold text-gray-950 hover:bg-cyan-300">Agent leaderboard</Link>
              <Link to="/leaderboard" className="rounded-lg border border-gray-700 px-4 py-2 font-semibold text-gray-200 hover:bg-gray-800">Hardware leaderboard</Link>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
            <div className="rounded-2xl border border-gray-800 bg-gray-950/70 p-4">
              <div className="text-sm text-gray-500">Arena models</div>
              <div className="text-3xl font-bold text-cyan-300">{arenaModels.length}</div>
            </div>
            <div className="rounded-2xl border border-gray-800 bg-gray-950/70 p-4">
              <div className="text-sm text-gray-500">Hardware runs</div>
              <div className="text-3xl font-bold text-purple-300">{stats?.total_submissions ?? 0}</div>
            </div>
            <div className="rounded-2xl border border-gray-800 bg-gray-950/70 p-4">
              <div className="text-sm text-gray-500">Fastest local run</div>
              <div className="text-xl font-bold text-white">{hardwareLeader?.system_type ?? '—'}</div>
              <div className="font-mono text-amber-300">{hardwareLeader ? Number(hardwareLeader.tokens_per_second).toFixed(1) : '—'} t/s</div>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {TASKS.map(t => <TaskPill key={t.id} active={task === t.id} onClick={() => setTask(t.id)}>{t.label}</TaskPill>)}
        </div>
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-bold text-white">{activeTask.label}</h2>
            <p className="text-gray-400">{activeTask.blurb}</p>
          </div>
          {notice && <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">{notice}</div>}
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {arenaModels.map(model => <ModelCard key={model.model_id} model={model} task={task} onVote={handleVote} />)}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-4">
        {REFERENCES.map(ref => (
          <a key={ref.name} href={ref.url} target="_blank" rel="noreferrer" className="rounded-2xl border border-gray-800 bg-gray-900 p-5 hover:border-gray-600">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-semibold text-white">{ref.name}</h3>
              <ArrowUpRight className="h-4 w-4 text-gray-500" />
            </div>
            <p className="mt-3 text-sm text-gray-400">{ref.take}</p>
          </a>
        ))}
      </section>

      <section className="rounded-2xl border border-gray-800 bg-gray-900 p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-white">Hardware is now the infrastructure layer</h2>
            <p className="text-sm text-gray-400">Still important, but secondary to model/task preference and quality.</p>
          </div>
          <Cpu className="h-6 w-6 text-gray-500" />
        </div>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          {benchmarks.slice(0, 4).map(b => (
            <Link key={b.id} to={`/benchmarks/${b.id}`} className="rounded-xl border border-gray-800 bg-gray-950 p-4 hover:border-gray-600">
              <div className="flex items-center gap-2 text-sm text-gray-500"><CheckCircle2 className="h-4 w-4" /> verified run</div>
              <div className="mt-2 font-semibold text-white">{b.system_type}</div>
              <div className="text-sm text-gray-400">{b.model_name}</div>
              <div className="mt-2 font-mono text-cyan-300">{Number(b.tokens_per_second).toFixed(1)} t/s</div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
