import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { PageHeader, Card, CardHeader, Badge, ValidityBadge } from '../components/ui';

/* Static methodology reference — every claim here traces to the repo:
   agentbench/README.md, agentbench/grading.py, agentbench/run.py,
   agentbench/stats.py, backend/app/agents_router.py, TSD.md, README.md. */

const TH = 'pb-2 pr-4 font-medium text-ink-3';
const TD = 'py-2 pr-4 align-top';

function SectionTable({ head, rows }: { head: string[]; rows: ReactRow[] }) {
  return (
    <div className="overflow-x-auto px-5 pb-5">
      <table className="w-full text-left text-[13px]">
        <thead className="border-b border-line">
          <tr>{head.map((h) => <th key={h} className={TH}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((cells, i) => (
            <tr key={i} className="border-b border-line last:border-0">
              {cells.map((c, j) => (
                <td key={j} className={`${TD} ${j === 0 ? 'font-medium text-ink whitespace-nowrap' : 'text-ink-2'}`}>
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
type ReactRow = ReactNode[];

function Mono({ children }: { children: ReactNode }) {
  return <code className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[12px] text-ink">{children}</code>;
}

const GRADERS: ReactRow[] = [
  [<Mono key="g">exact_match</Mono>, 'Normalized string equality against a gold answer. Empty gold answers are banned by the generator.'],
  [<Mono key="g">numeric_match</Mono>, 'Parses the final number from the output and compares within a tolerance.'],
  [<Mono key="g">json_fields</Mono>, 'Output must be a valid JSON object with the required field values (float tolerance supported).'],
  [<Mono key="g">unit_test</Mono>, 'Extracts the model’s code and runs a hidden pytest/unittest module against it in a subprocess sandbox; passes iff the tests pass.'],
  [<Mono key="g">regex_match</Mono>, 'Constrained generation: the answer must satisfy a required pattern — or must not match a banned one (negative constraints).'],
  [<Mono key="g">calibration</Mono>, 'The prompt states a claim with a computed truth value and asks for a confidence; graded by Brier score (p − outcome)². Lower is better; 0.25 is the always-guess-50% baseline. Excluded from the binary pass-rate pool.'],
];

const SUITES: ReactRow[] = [
  [<Mono key="s">minibench-core-v1</Mono>, '4 categories', 'The fundamentals: math reasoning, structured extraction, format adherence, code writing.'],
  [<Mono key="s">minibench-hard-v1</Mono>, '4 categories', 'Compositional variants (search, aggregation, chained transforms, a no-eval parser) to separate frontier models that saturate core.'],
  [<Mono key="s">minibench-v2</Mono>, '4 categories', 'Frontier tier: multi-step composition, adversarial distractors, stricter transforms. Featured on the Models leaderboard.'],
  [<Mono key="s">minibench-pro-v1</Mono>, '10 categories', 'Capability matrix: function-calling, date/time arithmetic, code debugging, constrained generation, counting, unit conversion, table manipulation, self-correction — plus calibration (Brier) and robustness (consistency across matched perturbed pairs).'],
  [<Mono key="s">moa-lite-v1</Mono>, '4 categories', 'MoA-native disagreement slice: doc-conflict, constraint-pack, evidence-gap, proposal-arbitrate.'],
];

const BANDS: { range: string; label: string; cls: string }[] = [
  { range: '< 50 GB/s', label: 'Red', cls: 'text-fail bg-fail-soft' },
  { range: '50–100 GB/s', label: 'Amber', cls: 'text-amber-600 bg-amber-50' },
  { range: '100–200 GB/s', label: 'Green', cls: 'text-pass bg-pass-soft' },
  { range: '200+ GB/s', label: 'Gold', cls: 'text-frontier bg-frontier-soft' },
];

const DEFENSES: ReactRow[] = [
  [
    'Canary strings',
    <>Published suite files embed per-task canary strings. A model that echoes one saw the benchmark in training: the run is flagged at grade time, quarantined as contaminated, and <span className="font-medium text-ink">publishing is refused</span> while any canary flags exist.</>,
  ],
  [
    'Infra errors',
    <>Provider failures (429/5xx/timeouts) are retried with backoff; exhausted retries are recorded as <Mono>infra_error</Mono> and <span className="font-medium text-ink">excluded from every denominator</span>, so provider luck is never scored as capability. Publishing is refused while any infra-error trials remain — the fix is a rerun, not a partial score.</>,
  ],
  [
    'Private split vs dev slice',
    <>The committed dev slice is public and contamination-prone; official scores come from a private split regenerated from an uncommitted high-entropy seed, whose gold answers never touch disk. Leaderboard rows carry the badge: <ValidityBadge isPrivate={true} /> <ValidityBadge isPrivate={false} /></>,
  ],
  [
    'Provenance',
    <>Every results file records <Mono>seed_sha256</Mono> (proves two runs shared a seed without revealing it), <Mono>generator_sha256</Mono>, <Mono>git_commit</Mono>, <Mono>is_private_split</Mono>, and the grader version — sweeps are only comparable when these match.</>,
  ],
  [
    'Pinned decoding',
    <>Temperature 0.0, top_p 1.0, max_tokens 4096 (reasoning headroom — graders still cap gradable text at 2,000 chars), no system prompt. MoA configs are rejected for <Mono>minibench-*</Mono> suites, so a pipeline can never pose as a model.</>,
  ],
  [
    'Coding-task hardening',
    'Solution code passes an AST purity check (no file/network/process/introspection access) before it touches disk, the hidden test file gets a randomized name, and the subprocess runs with a minimal environment — closing test-file peeking.',
  ],
];

export default function Methodology() {
  return (
    <div className="space-y-8">
      <PageHeader eyebrow="How the numbers are made" title="Methodology">
        Every MiniBench capability score is produced by an executable oracle — a grader that can
        fail a deliberately wrong answer. No LLM judge scores the core suites, task suites are
        procedurally generated with computed gold answers, and every published run carries a
        reproducibility fingerprint. This page explains exactly what is measured and what is refused.
      </PageHeader>

      {/* ── Hardware benchmarks ─────────────────────────────────────────── */}
      <Card className="animate-rise rise-1">
        <CardHeader
          title="Hardware benchmarks"
          sub="Crowdsourced local-inference throughput on Mini-PC-class hardware, via the MiniBench CLI."
        />
        <div className="space-y-4 px-5 pb-5 text-[14px] leading-relaxed text-ink-2">
          <p>
            The CLI runs a standardized test against a local model: 3 warmup prompts (discarded),
            then 5 fixed test prompts (~200 tokens each), reporting the median and p95
            tokens-per-second plus time-to-first-token. Memory bandwidth, price, memory type, and
            system name are resolved from a curated lookup table keyed by the detected CPU — the
            headline metric can&rsquo;t be read reliably at runtime, so it is looked up rather than
            guessed (and can be overridden explicitly).
          </p>
          <p>
            Results roll up into the <span className="font-medium text-ink">Hardware Efficiency Index</span>:
          </p>
          <div className="rounded-lg bg-surface-2 px-4 py-3 font-mono text-[13px] text-ink">
            HEI = (tokens/sec × model_quality) / price
          </div>
          <p>
            — value per dollar, where model quality comes from an MMLU / normalized-Elo lookup.
            The site&rsquo;s central hardware thesis:{' '}
            <span className="font-medium text-ink">memory bandwidth is the critical metric</span> —
            for memory-bound local inference, throughput tracks bandwidth almost linearly, which the
            bandwidth-vs-throughput chart on the{' '}
            <Link to="/" className="font-medium text-accent hover:text-accent-strong">Overview</Link>{' '}
            makes visible. Bandwidth is color-coded everywhere:
          </p>
          <div className="flex flex-wrap gap-2">
            {BANDS.map((b) => (
              <span key={b.range} className={`tnum inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${b.cls}`}>
                {b.range} · {b.label}
              </span>
            ))}
          </div>
          <div>
            <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3">
              Submission validation
            </h3>
            <ul className="list-disc space-y-1 pl-5">
              <li><Mono>tokens_per_second</Mono> must be in 0.1–500; <Mono>test_duration_secs</Mono> ≥ 10; prompt + completion tokens ≥ 100.</li>
              <li>Rate limit: 10 submissions per IP per hour.</li>
              <li>Fingerprint = SHA256 of CPU + GPU + RAM + OS + engine + model + quantization; a duplicate fingerprint within 1 hour is rejected.</li>
              <li>Client IP is hashed, never stored raw.</li>
            </ul>
          </div>
        </div>
      </Card>

      {/* ── Agent benchmarks ────────────────────────────────────────────── */}
      <Card className="animate-rise rise-1">
        <CardHeader
          title="Agent benchmarks"
          sub="Procedurally generated capability suites, all deterministically graded (no LLM judge), all cost-bounded."
        />
        <SectionTable head={['Suite', 'Size', 'What it tests']} rows={SUITES} />
        <div className="px-5 pb-2">
          <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3">
            Executable graders
          </h3>
          <p className="text-[13px] text-ink-2">
            Rule zero: every task needs an executable oracle. A grader that cannot fail a
            deliberately-bad answer does not discriminate, so each grader is designed so that a
            wrong or empty answer scores 0.
          </p>
        </div>
        <SectionTable head={['Grader', 'Pass semantics']} rows={GRADERS} />
        <div className="space-y-3 px-5 pb-5 text-[14px] leading-relaxed text-ink-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-3">
            Trials and uncertainty
          </h3>
          <p>
            Every task runs multiple trials (3 by default), and pass rates are reported with a{' '}
            <span className="font-medium text-ink">Wilson 95% confidence interval</span> — a
            binomial interval that behaves better than the normal approximation at extreme rates.
            Consistency is measured with an unbiased{' '}
            <span className="font-medium text-ink">pass^k</span> estimator (the HumanEval pass@k
            family): for a task with <Mono>n</Mono> trials of which <Mono>c</Mono> passed, the
            probability a random size-k subset is all-passing is <Mono>C(c,k)/C(n,k)</Mono>,
            averaged over tasks — rewarding models that solve a task every time, not once by luck.
          </p>
        </div>
      </Card>

      {/* ── Dual scoring ────────────────────────────────────────────────── */}
      <Card className="animate-rise rise-2">
        <CardHeader
          title="Dual scoring (grader v3)"
          sub="Capability and format are graded as separate channels, so format pedantry is never scored as intelligence."
        />
        <div className="grid gap-4 px-5 pb-5 md:grid-cols-2">
          <div className="rounded-lg border border-line bg-surface-2/40 p-4">
            <div className="mb-1 flex items-center gap-2">
              <Badge tone="accent">Capability</Badge>
              <span className="font-mono text-[12px] text-ink-3">pass_rate</span>
            </div>
            <p className="text-[13px] leading-relaxed text-ink-2">
              Does an extractable answer match gold? This is the primary signal — the number
              models are ranked by.
            </p>
          </div>
          <div className="rounded-lg border border-line bg-surface-2/40 p-4">
            <div className="mb-1 flex items-center gap-2">
              <Badge tone="neutral">Format</Badge>
              <span className="font-mono text-[12px] text-ink-3">pass_format</span>
            </div>
            <p className="text-[13px] leading-relaxed text-ink-2">
              Did the model obey the strict answer-only contract — an isolated final answer under a
              2,000-character verbosity cap? Reported separately as a diagnostic; it closes
              decoy-burying and answer-spraying without letting formatting decide the ranking.
            </p>
          </div>
        </div>
        <p className="px-5 pb-5 text-[13px] text-ink-2">
          Rows graded under earlier grader versions are not comparable to v3 and are never mixed
          into the same comparison.
        </p>
      </Card>

      {/* ── Contamination & gaming defenses ─────────────────────────────── */}
      <Card className="animate-rise rise-2">
        <CardHeader
          title="Contamination and gaming defenses"
          sub="Scores must reflect capability, not prompt-maxing or training leakage."
        />
        <SectionTable head={['Defense', 'How it works']} rows={DEFENSES} />
      </Card>

      {/* ── What the leaderboard shows ──────────────────────────────────── */}
      <Card className="animate-rise rise-2">
        <CardHeader
          title="What the leaderboard shows"
          sub="Validity-gated, model-centric, cost-aware."
        />
        <div className="px-5 pb-5 text-[14px] leading-relaxed text-ink-2">
          <ul className="list-disc space-y-2 pl-5">
            <li>
              <span className="font-medium text-ink">Validity gate.</span> Runs with canary flags
              (contamination) or infra-error trials never rank.
            </li>
            <li>
              <span className="font-medium text-ink">Best single-model run per model.</span> Only
              runs whose config touches exactly one model string qualify for the Models leaderboard,
              so a MoA pipeline never poses as a model. A private-split run always supersedes a
              dev-slice run for the same model — even a lower one — because the public dev slice
              must never shadow an official score.
            </li>
            <li>
              <span className="font-medium text-ink">Cost per task and the Pareto frontier.</span>{' '}
              Every run carries real cost accounting; the accuracy-vs-cost chart marks the frontier
              of runs no other run dominates (cost ≤ and pass rate ≥, one strictly better). Runs
              without cost data are excluded from the frontier.
            </li>
            <li>
              <span className="font-medium text-ink">Uncertainty shown, not hidden.</span> Pass
              rates render with their 95% CI, so overlapping models read as what they are:
              statistically indistinguishable.
            </li>
          </ul>
        </div>
      </Card>

      {/* ── What we don't do ────────────────────────────────────────────── */}
      <Card className="animate-rise rise-3">
        <CardHeader
          title="What we don’t do"
          sub="The refusals are the methodology."
        />
        <div className="px-5 pb-5 text-[14px] leading-relaxed text-ink-2">
          <ul className="list-disc space-y-2 pl-5">
            <li>
              <span className="font-medium text-ink">No LLM judge for core scores.</span> Every core-suite
              verdict comes from a deterministic, executable grader.
            </li>
            <li>
              <span className="font-medium text-ink">No dry-run data, ever.</span> Offline dry-run
              artifacts (stub outputs used for smoke testing) are refused unconditionally at import —
              they are not benchmark data.
            </li>
            <li>
              <span className="font-medium text-ink">No ordering claims without significance.</span>{' '}
              &ldquo;A beats B&rdquo; requires an exact McNemar test at p &lt; 0.05; everything else is
              reported as indistinguishable.
            </li>
            <li>
              <span className="font-medium text-ink">No score edits.</span> A suspected-contaminated
              outlier gets flagged — an asterisk, never a score edit — and runs are never re-graded,
              re-seeded, or selectively rerun to move one model. Items are pruned by statistical
              discrimination only; expected orderings are checked last, as a sanity signal.
            </li>
          </ul>
        </div>
      </Card>
    </div>
  );
}
