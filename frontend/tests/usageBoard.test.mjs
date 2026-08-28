import test from 'node:test';
import assert from 'node:assert/strict';
import {
  citation,
  formatUsdPerMillion,
  modelPageUrl,
  sortByCost,
  sortByLatency,
  sortByTask,
  taskShare,
} from '../src/lib/usageBoard.js';

const rows = [
  {
    id: 'anthropic/claude-haiku-4.5',
    blended_per_million: 3.2,
    latency_ms: 1200,
    task_shares: { code: 0.4, 'code:general_impl': 0.4 },
  },
  {
    id: 'openai/gpt-4o',
    blended_per_million: 8.125,
    latency_ms: 3200,
    task_shares: { code: 0.1 },
  },
  {
    id: 'anthropic/claude-sonnet-5',
    blended_per_million: 12,
    latency_ms: 8000,
    task_shares: { code: 0.35 },
  },
];

test('citation uses the OpenRouter CC BY 4.0 as_of form', () => {
  assert.equal(
    citation('2026-08-27T00:00:00Z'),
    'Source: OpenRouter (openrouter.ai/rankings), as of 2026-08-27T00:00:00Z. CC BY 4.0.',
  );
});

test('model page deep-links to OpenRouter', () => {
  assert.equal(modelPageUrl('openai/gpt-4o'), 'https://openrouter.ai/openai/gpt-4o');
});

test('sortByCost orders cheapest first', () => {
  assert.deepEqual(sortByCost(rows).map((r) => r.id), [
    'anthropic/claude-haiku-4.5',
    'openai/gpt-4o',
    'anthropic/claude-sonnet-5',
  ]);
});

test('taskShare matches macros and tag prefixes', () => {
  assert.equal(taskShare(rows[0], 'code'), 0.4);
  assert.equal(taskShare(rows[0], 'code:general_impl'), 0.4);
  assert.equal(taskShare(rows[1], 'reasoning'), null);
});

test('sortByTask orders by code share', () => {
  assert.equal(sortByTask(rows, 'code')[0].id, 'anthropic/claude-haiku-4.5');
  assert.equal(sortByTask(rows, 'code')[1].id, 'anthropic/claude-sonnet-5');
});

test('sortByLatency orders fastest first', () => {
  assert.deepEqual(sortByLatency(rows).map((r) => r.latency_ms), [1200, 3200, 8000]);
});

test('formats blended price', () => {
  assert.equal(formatUsdPerMillion(3.2), '$3.20/1M');
});
