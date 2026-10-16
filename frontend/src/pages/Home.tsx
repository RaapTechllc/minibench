import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Trophy, Bot, Briefcase, Activity, BookOpen } from 'lucide-react';
import { api } from '../api';
import type { AgentCabinetListItem, KnownModel, UsageBoardPayload } from '../api';
import { Card, CardHeader, PageHeader, Badge, Skeleton, ValidityBadge } from '../components/ui';
import { fmtCost } from '../components/chart';
import {
  LAST_VISIT_KEY, asOfLabel, latestTimestamp, newSince, sortNewestFirst,
} from '../lib/home.js';

const NEW_MODEL_LIMIT = 6;
const CABINET_LIMIT = 5;

function readLastVisit(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(LAST_VISIT_KEY);
}

function fmtDate(value: string | null): string {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toISOString().slice(0, 10);
}

interface SurfaceCardProps {
  to: string;
  icon: typeof Trophy;
  eyebrow: string;
  title: string;
  asOf: string;
  children: React.ReactNode;
}

function SurfaceCard({ to, icon: Icon, eyebrow, title, asOf, children }: SurfaceCardProps) {
  return (
    <Link to={to} className="group block rounded-xl focus:outline-none focus:ring-2 focus:ring-accent">
      <Card className="h-full px-5 py-4 transition-colors group-hover:border-accent/40">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-accent">
            <Icon className="h-4 w-4" strokeWidth={2} />
            {eyebrow}
          </div>
          <span className="tnum text-[11px] text-ink-3">{asOf}</span>
        </div>
        <h2 className="mt-1.5 text-[15px] font-semibold text-ink">{title}</h2>
        <p className="mt-1 text-[13px] leading-relaxed text-ink-2">{children}</p>
      </Card>
    </Link>
  );
}

export default function Home() {
  // Captured once at mount so the feed compares against the *previous* visit,
  // then the visit marker is advanced for next time.
  const [lastVisit] = useState<string | null>(readLastVisit);
  const [models, setModels] = useState<KnownModel[]>([]);
  const [cabinet, setCabinet] = useState<AgentCabinetListItem[]>([]);
  const [usage, setUsage] = useState<UsageBoardPayload | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([
      api.getNewModels(),
      api.getAgentCabinetRuns(),
      api.getOpenRouterBoard(),
    ]).then(([m, c, u]) => {
      if (cancelled) return;
      if (m.status === 'fulfilled') setModels(m.value);
      if (c.status === 'fulfilled') setCabinet(c.value);
      if (u.status === 'fulfilled') setUsage(u.value);
      setLoading(false);
      window.localStorage.setItem(LAST_VISIT_KEY, new Date().toISOString());
    });
    return () => { cancelled = true; };
  }, []);

  const newModels = sortNewestFirst(newSince(models, lastVisit, 'first_seen'), 'first_seen');
  const recentModels = sortNewestFirst(models, 'first_seen').slice(0, NEW_MODEL_LIMIT);
  const recentCabinet = sortNewestFirst(cabinet, 'submitted_at').slice(0, CABINET_LIMIT);
  const newCabinet = newSince(cabinet, lastVisit, 'submitted_at');

  const catalogAsOf = asOfLabel(latestTimestamp(models, 'first_seen'));
  const cabinetAsOf = asOfLabel(latestTimestamp(cabinet, 'submitted_at'));
  const usageAsOf = asOfLabel(usage?.meta.as_of);
  const usageLive = usage?.meta.live === true;

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="MiniBench" title="Which model-plus-harness finishes real work, at what cost and speed">
        Every number here carries its source and date. Solo and Multiplayer screen models cheaply;
        the Agent Cabinet measures stateful real work with receipts; the Usage Board shows what the
        market actually runs. No composite score, ever.
      </PageHeader>

      {loading ? (
        <Skeleton rows={5} />
      ) : (
        <Card className="animate-rise rise-1">
          <CardHeader
            title="What changed"
            sub={lastVisit
              ? `Since your last visit (${fmtDate(lastVisit)}). New items are marked.`
              : 'First visit: showing the most recent items. Return later to see what is new.'}
            right={
              <Badge tone={usageLive ? 'accent' : 'neutral'}>
                Usage Board · {usageLive ? 'Live poll' : 'Fixture / cache'}
              </Badge>
            }
          />
          <div className="grid gap-6 px-5 pb-5 md:grid-cols-2">
            <section>
              <div className="flex items-center justify-between">
                <h3 className="text-[13px] font-semibold text-ink">Models in the catalog, not yet benchmarked</h3>
                <span className="text-[11px] text-ink-3">{catalogAsOf}</span>
              </div>
              {recentModels.length === 0 ? (
                <p className="mt-2 text-[13px] text-ink-3">Catalog is empty or every tracked model has a published run.</p>
              ) : (
                <ul className="mt-2 divide-y divide-line/70">
                  {recentModels.map((m) => {
                    const isNew = newModels.some((n) => n.id === m.id);
                    return (
                      <li key={m.id} className="flex items-center justify-between gap-3 py-2 text-[13px]">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="truncate font-medium text-ink">{m.display_name ?? m.model_id}</span>
                            {isNew && <Badge tone="accent">new</Badge>}
                            {m.license === 'open' && <Badge tone="pass">open</Badge>}
                          </div>
                          <div className="truncate text-[11px] text-ink-3">{m.model_id}</div>
                        </div>
                        <span className="tnum shrink-0 text-[11px] text-ink-3">{fmtDate(m.first_seen)}</span>
                      </li>
                    );
                  })}
                </ul>
              )}
              <Link to="/models" className="mt-2 inline-block text-[12px] font-medium text-accent hover:text-accent-strong">
                Solo Cabinet →
              </Link>
            </section>

            <section>
              <div className="flex items-center justify-between">
                <h3 className="text-[13px] font-semibold text-ink">Newest Agent Cabinet runs</h3>
                <span className="text-[11px] text-ink-3">{cabinetAsOf}</span>
              </div>
              {recentCabinet.length === 0 ? (
                <p className="mt-2 text-[13px] text-ink-3">No published runs yet. Unranked, newest first when they land.</p>
              ) : (
                <ul className="mt-2 divide-y divide-line/70">
                  {recentCabinet.map((r) => {
                    const isNew = newCabinet.some((n) => n.run_id === r.run_id);
                    return (
                      <li key={r.run_id} className="flex items-center justify-between gap-3 py-2 text-[13px]">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <Link to={`/agent-cabinet/runs/${r.run_id}`} className="truncate font-medium text-ink hover:text-accent">
                              {r.model_route ?? 'unknown route'}
                            </Link>
                            {isNew && <Badge tone="accent">new</Badge>}
                            <ValidityBadge isPrivate={r.private_split} />
                          </div>
                          <div className="truncate text-[11px] text-ink-3">
                            {r.harness ?? '—'}{r.harness_version ? ` ${r.harness_version}` : ''} · {r.suite ?? '—'}
                          </div>
                        </div>
                        <div className="shrink-0 text-right">
                          <div className="tnum text-[13px] font-semibold text-ink">{Number(r.completion).toFixed(0)}% done</div>
                          <div className="tnum text-[11px] text-ink-3">{fmtCost(r.cost_usd_per_task)}/task · {fmtDate(r.submitted_at)}</div>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
              <Link to="/agent-cabinet" className="mt-2 inline-block text-[12px] font-medium text-accent hover:text-accent-strong">
                Agent Cabinet →
              </Link>
            </section>
          </div>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 animate-rise rise-2">
        <SurfaceCard to="/agent-cabinet" icon={Briefcase} eyebrow="Agent Cabinet" title="Real work, held constant" asOf={cabinetAsOf}>
          Stateful tasks with hidden checks. Model and harness recorded separately; runs are unranked
          and every comparison carries a receipt.
        </SurfaceCard>
        <SurfaceCard to="/models" icon={Trophy} eyebrow="Solo Cabinet" title="Single-model screening" asOf={catalogAsOf}>
          Pinned decoding, executable graders, 95% CI bars. Cheap first pass before spending on agent runs.
        </SurfaceCard>
        <SurfaceCard to="/agents" icon={Bot} eyebrow="Multiplayer Cabinet" title="Mixture-of-agents configs" asOf={cabinetAsOf}>
          MoA stacks measured with cost per task. Combine compute instead of picking one model.
        </SurfaceCard>
        <SurfaceCard to="/usage/cost" icon={Activity} eyebrow="Usage Board" title="What the market runs" asOf={usageAsOf}>
          OpenRouter usage, price, and official evals, republished with citation. Not a MiniBench score.
        </SurfaceCard>
      </div>

      <p className="flex items-center gap-2 text-[13px] text-ink-3">
        <BookOpen className="h-4 w-4" strokeWidth={2} />
        How numbers are produced, graded, and cited:{' '}
        <Link to="/methodology" className="font-medium text-accent hover:text-accent-strong">Methodology</Link>
      </p>
    </div>
  );
}
