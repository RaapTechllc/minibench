import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import type { ReferenceProfile } from '../api';
import { ErrorState, Skeleton } from '../components/ui';

function ProfileCard({ profile }: { profile: ReferenceProfile }) {
  const settings: [string, string | number | null][] = [
    ['Engine', profile.engine ?? 'Provider served'],
    ['Minimum version', profile.engine_version_min],
    ['Quantization', profile.quantization ?? 'Provider served'],
    ['Context', profile.context_length ? profile.context_length.toLocaleString() : null],
    ['Temperature', profile.temperature],
    ['Max output', profile.max_tokens ? profile.max_tokens.toLocaleString() : null],
  ];

  return (
    <article className="border border-line bg-surface p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-accent">Reference profile</div>
          <h3 className="mt-1 text-base font-semibold text-ink">{profile.display_name}</h3>
        </div>
        <span className="evidence-pill evidence-development">Configuration only</span>
      </div>
      <code className="mt-2 block text-xs text-ink-3">{profile.profile_key}</code>
      <dl className="mt-4 border-y border-line py-2 text-sm">
        {settings.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4 py-1">
            <dt className="text-ink-3">{label}</dt>
            <dd className="tnum text-right text-ink">{value ?? 'Not specified'}</dd>
          </div>
        ))}
      </dl>
      {profile.representative_system && (
        <p className="mt-3 text-xs text-ink-3">Representative system: {profile.representative_system}</p>
      )}
      {profile.description && <p className="mt-3 text-sm leading-6 text-ink-2">{profile.description}</p>}
    </article>
  );
}

export default function Hardware() {
  const [profiles, setProfiles] = useState<ReferenceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getReferenceProfiles()
      .then(list => {
        if (!cancelled) {
          setProfiles(list);
          setError(null);
          setLoading(false);
        }
      })
      .catch(reason => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : 'Deployment profiles are unavailable.');
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, []);

  const retry = () => {
    setLoading(true);
    setError(null);
    api.getReferenceProfiles()
      .then(list => { setProfiles(list); setLoading(false); })
      .catch(reason => { setError(reason instanceof Error ? reason.message : 'Deployment profiles are unavailable.'); setLoading(false); });
  };

  return (
    <div className="space-y-8">
      <header className="max-w-4xl">
        <div className="text-sm font-medium text-accent">Deployment evidence</div>
        <h1 className="mt-2 text-[30px] font-medium leading-tight tracking-[-0.02em] text-ink sm:text-[34px]">
          Hardware is context—not a crown.
        </h1>
        <p className="mt-3 max-w-3xl text-[15px] leading-6 text-ink-2">
          MiniBench no longer ranks machines from theoretical specifications or one-off local runs. A local setup becomes comparable only when a model, quantization, engine, context, and reference profile are pinned to measured task and performance evidence.
        </p>
      </header>

      <section className="decision-summary" aria-labelledby="hardware-policy-heading">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.08em] text-positive">Policy change</div>
          <h2 id="hardware-policy-heading" className="mt-2 text-xl font-semibold text-ink">No new hardware testing is required for Value Intelligence.</h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-ink-2">
            Model capability, actual cost per attempt, reliability, and latency drive the recommendation. Local hardware records remain supporting deployment evidence and are never used to infer model quality.
          </p>
        </div>
        <Link to="/" className="shrink-0 text-sm font-medium text-accent hover:text-accent-strong">Open Value desk →</Link>
      </section>

      <section aria-labelledby="lanes-heading">
        <div className="section-heading-row">
          <div>
            <h2 id="lanes-heading">Three evidence lanes</h2>
            <p>Each lane answers a different question. MiniBench does not blend them until the contracts match.</p>
          </div>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          <article className="border border-line bg-surface p-5">
            <span className="evidence-pill evidence-official">Measured</span>
            <h3 className="mt-3 font-semibold text-ink">Cloud model economics</h3>
            <p className="mt-2 text-sm leading-6 text-ink-2">Task success, charged run cost, p50/p95 latency, uncertainty, and provider/model identity. This is the current recommendation lane.</p>
          </article>
          <article className="border border-line bg-surface p-5">
            <span className="evidence-pill evidence-development">Configuration</span>
            <h3 className="mt-3 font-semibold text-ink">Local reference profiles</h3>
            <p className="mt-2 text-sm leading-6 text-ink-2">Pinned engine, quantization, context, and representative system. A profile defines how to reproduce a run; it does not prove speed or quality.</p>
          </article>
          <article className="border border-line bg-surface p-5">
            <span className="evidence-pill evidence-incomplete">Coverage gap</span>
            <h3 className="mt-3 font-semibold text-ink">Verified local setups</h3>
            <p className="mt-2 text-sm leading-6 text-ink-2">Requires an explicit model × profile link with throughput, time to first token, context, power, and run provenance. Until then, fit is unknown—not estimated.</p>
          </article>
        </div>
      </section>

      {loading && <Skeleton rows={6} />}
      {!loading && error && <ErrorState onRetry={retry}>{error}</ErrorState>}

      {!loading && !error && (
        <section aria-labelledby="profiles-heading">
          <div className="section-heading-row">
            <div>
              <h2 id="profiles-heading">Pinned run configurations</h2>
              <p>{profiles.length} profiles define reproducible lanes. They are not hardware recommendations.</p>
            </div>
            <Link to="/methodology" className="text-sm font-medium text-accent hover:text-accent-strong">Profile methodology →</Link>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {profiles.map(profile => <ProfileCard key={profile.id} profile={profile} />)}
          </div>
        </section>
      )}

      <section className="grid gap-4 lg:grid-cols-2" aria-label="Deployment interpretation">
        <article className="border border-line bg-surface p-5">
          <h2 className="text-base font-semibold text-ink">What MiniBench can say now</h2>
          <ul className="mt-3 space-y-2 text-sm leading-6 text-ink-2">
            <li>• Which hosted model is cheapest per measured successful task.</li>
            <li>• Whether a quality premium clears a declared failure-cost threshold.</li>
            <li>• Which pinned configuration produced a published local result.</li>
            <li>• Whether cost, quality, and latency evidence are comparable and current.</li>
          </ul>
        </article>
        <article className="border border-line bg-surface p-5">
          <h2 className="text-base font-semibold text-ink">What MiniBench will not invent</h2>
          <ul className="mt-3 space-y-2 text-sm leading-6 text-ink-2">
            <li>• Tokens per second from memory bandwidth alone.</li>
            <li>• Model fit from nominal RAM or VRAM without a quantized artifact size.</li>
            <li>• Total cost of ownership without utilization, energy, and amortization assumptions.</li>
            <li>• A local-versus-cloud winner when the evidence lanes do not match.</li>
          </ul>
        </article>
      </section>

      <aside className="method-note">
        <strong>Legacy hardware catalog:</strong> static machine specifications remain available through the API for historical compatibility, but the product no longer presents them as a ranked benchmark. Existing measurements can be reviewed on the <Link to="/legacy-overview" className="font-medium text-accent hover:text-accent-strong">legacy overview</Link>.
      </aside>
    </div>
  );
}