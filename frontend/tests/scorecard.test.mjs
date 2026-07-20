import test from 'node:test';
import assert from 'node:assert/strict';
import {
  tierIdFromPassRate,
  tierLabelFromPassRate,
  categoryDisplayName,
  orderCategoryKeys,
  formatScorecard,
  formatScorecardLabel,
  evaluateSaturation,
  tierChromeClass,
  CREDITS_ROLLING_MIN,
  DEFAULT_CABINET_SUITE,
} from '../src/lib/scorecard.js';
import {
  cabinetPathForRun,
  taskDisplayName,
  taskScenario,
} from '../src/lib/runDetail.js';

test('tier bands at boundaries', () => {
  assert.equal(tierIdFromPassRate(35), 'insert-coin');
  assert.equal(tierIdFromPassRate(36), 'warm-up');
  assert.equal(tierIdFromPassRate(50), 'warm-up');
  assert.equal(tierIdFromPassRate(51), 'high-score');
  assert.equal(tierIdFromPassRate(65), 'high-score');
  assert.equal(tierIdFromPassRate(66), 'boss-beaten');
  assert.equal(tierIdFromPassRate(80), 'boss-beaten');
  assert.equal(tierIdFromPassRate(81), 'credits-rolling');
  assert.equal(tierIdFromPassRate(100), 'credits-rolling');
});

test('tier labels match ids', () => {
  assert.equal(tierLabelFromPassRate(68), 'Boss Beaten');
  assert.equal(tierLabelFromPassRate(58), 'High Score');
});

test('category display names for known backend keys', () => {
  assert.equal(categoryDisplayName('reasoning'), 'Math & Logic');
  assert.equal(categoryDisplayName('tool-use'), 'Data Pull');
  assert.equal(categoryDisplayName('instruction'), 'Follow Rules');
  assert.equal(categoryDisplayName('coding'), 'Write Code');
});

test('category display name fallback title-cases unknown keys', () => {
  assert.equal(categoryDisplayName('self-correct'), 'Self Correct');
});

test('orderCategoryKeys preserves display order then sorts unknowns', () => {
  assert.deepEqual(
    orderCategoryKeys(['coding', 'reasoning', 'self-correct', 'tool-use']),
    ['reasoning', 'tool-use', 'coding', 'self-correct'],
  );
});

test('formatScorecard returns tier, score, and tierId', () => {
  assert.deepEqual(formatScorecard(68), {
    tier: 'Boss Beaten',
    score: 68,
    tierId: 'boss-beaten',
  });
});

test('formatScorecardLabel renders arcade headline', () => {
  assert.equal(formatScorecardLabel(68), 'Boss Beaten · 68');
});

test('evaluateSaturation promotes when more than 30% are Credits Rolling', () => {
  const entries = [
    { pass_rate: 90 },
    { pass_rate: 85 },
    { pass_rate: 40 },
    { pass_rate: 82 },
  ];
  assert.equal(evaluateSaturation(entries), 'promote');
  assert.equal(evaluateSaturation([{ pass_rate: 90 }, { pass_rate: 40 }, { pass_rate: 35 }, { pass_rate: 50 }]), 'ok');
});

test('evaluateSaturation uses CREDITS_ROLLING_MIN threshold', () => {
  assert.equal(CREDITS_ROLLING_MIN, 81);
  const belowThreshold = [{ pass_rate: 80 }, { pass_rate: 80 }, { pass_rate: 80 }, { pass_rate: 81 }];
  assert.equal(evaluateSaturation(belowThreshold), 'ok');
});

test('default cabinet suite is hard-v1', () => {
  assert.equal(DEFAULT_CABINET_SUITE, 'minibench-hard-v1');
});

test('tierChromeClass maps each tier id to a stable CSS class', () => {
  assert.equal(tierChromeClass('insert-coin'), 'arcade-tier-insert-coin');
  assert.equal(tierChromeClass('warm-up'), 'arcade-tier-warm-up');
  assert.equal(tierChromeClass('high-score'), 'arcade-tier-high-score');
  assert.equal(tierChromeClass('boss-beaten'), 'arcade-tier-boss-beaten');
  assert.equal(tierChromeClass('credits-rolling'), 'arcade-tier-credits-rolling');
});

test('tierChromeClass falls back for unknown ids', () => {
  assert.equal(tierChromeClass('unknown'), 'arcade-tier-insert-coin');
  assert.equal(tierChromeClass(''), 'arcade-tier-insert-coin');
});

test('run detail returns to the cabinet implied by model count', () => {
  assert.equal(cabinetPathForRun({ models: ['openrouter/example/model'] }), '/models');
  assert.equal(cabinetPathForRun({ models: ['openrouter/example/a', 'openrouter/example/b'] }), '/agents');
  assert.equal(cabinetPathForRun({ models: ['openrouter/example/model'], self_moa: true }), '/agents');
  assert.equal(cabinetPathForRun(null), '/models');
});

test('run detail uses typed metadata and preserves historical fallbacks', () => {
  const current = {
    task_id: 'mb2-code-01',
    scenario_type: 'cursor',
    task_description: 'Fix the failing parser.',
  };
  assert.deepEqual(taskScenario(current, 'coding'), { kind: 'cursor', fromMetadata: true });
  assert.equal(taskDisplayName(current, 0), 'Fix the failing parser.');

  const historical = { task_id: 'mbh-reason-01' };
  assert.deepEqual(taskScenario(historical, 'reasoning'), {
    kind: 'spreadsheet',
    fromMetadata: false,
  });
  assert.equal(taskDisplayName(historical, 0), 'Mbh Reason 01');
  assert.equal(taskDisplayName({ task_id: 'seed-canary-01' }, 2), 'Task 3');
  assert.equal(
    taskDisplayName({ task_id: 'ordinary-task', task_description: 'Inspect the seed identifier.' }, 3),
    'Task 4',
  );
});
