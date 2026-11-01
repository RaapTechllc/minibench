import test from 'node:test';
import assert from 'node:assert/strict';
import {
  categoryDisplayName,
  orderCategoryKeys,
  evaluateSaturation,
  suiteMetadata,
  SATURATION_PASS_RATE_MIN,
  DEFAULT_FEATURED_SUITE,
} from '../src/lib/scorecard.js';

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

test('evaluateSaturation promotes when more than 30% clear the pass-rate threshold', () => {
  const entries = [
    { pass_rate: 90 },
    { pass_rate: 85 },
    { pass_rate: 40 },
    { pass_rate: 82 },
  ];
  assert.equal(evaluateSaturation(entries), 'promote');
  assert.equal(evaluateSaturation([{ pass_rate: 90 }, { pass_rate: 40 }, { pass_rate: 35 }, { pass_rate: 50 }]), 'ok');
});

test('evaluateSaturation uses the explicit pass-rate threshold', () => {
  assert.equal(SATURATION_PASS_RATE_MIN, 81);
  const belowThreshold = [{ pass_rate: 80 }, { pass_rate: 80 }, { pass_rate: 80 }, { pass_rate: 81 }];
  assert.equal(evaluateSaturation(belowThreshold), 'ok');
});

test('default featured suite is hard-v1', () => {
  assert.equal(DEFAULT_FEATURED_SUITE, 'minibench-hard-v1');
});

test('suite metadata resolves a declared benchmark lane', () => {
  assert.deepEqual(suiteMetadata('minibench-hard-v1'), {
    suite: 'minibench-hard-v1',
    label: 'Hard v1',
    season: 'Primary',
  });
  assert.equal(suiteMetadata('unknown'), null);
});
