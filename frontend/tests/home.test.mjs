import test from 'node:test';
import assert from 'node:assert/strict';
import {
  asOfLabel, latestTimestamp, newSince, parseTime, sortNewestFirst,
} from '../src/lib/home.js';

const items = [
  { id: 'a', first_seen: '2026-09-01T00:00:00Z' },
  { id: 'b', first_seen: '2026-09-10T12:00:00Z' },
  { id: 'c', first_seen: 'not a date' },
  { id: 'd', first_seen: null },
];

test('parseTime returns null for empty or garbage input', () => {
  assert.equal(parseTime(null), null);
  assert.equal(parseTime(''), null);
  assert.equal(parseTime('nope'), null);
  assert.equal(parseTime('2026-09-14T00:00:00Z'), Date.parse('2026-09-14T00:00:00Z'));
});

test('newSince returns nothing on a first visit (no fabricated novelty)', () => {
  assert.deepEqual(newSince(items, null, 'first_seen'), []);
  assert.deepEqual(newSince(items, 'garbage', 'first_seen'), []);
});

test('newSince is strictly after the cutoff and skips unparseable rows', () => {
  const out = newSince(items, '2026-09-01T00:00:00Z', 'first_seen');
  assert.deepEqual(out.map((i) => i.id), ['b']);
});

test('sortNewestFirst orders by time and sinks unparseable rows', () => {
  const out = sortNewestFirst(items, 'first_seen');
  assert.deepEqual(out.map((i) => i.id), ['b', 'a', 'c', 'd']);
});

test('latestTimestamp picks the max and is null when nothing parses', () => {
  assert.equal(latestTimestamp(items, 'first_seen'), '2026-09-10T12:00:00.000Z');
  assert.equal(latestTimestamp([{ x: 'bad' }], 'x'), null);
});

test('asOfLabel shows a date or an honest fallback', () => {
  assert.equal(asOfLabel('2026-09-10T12:00:00Z'), 'as of 2026-09-10');
  assert.equal(asOfLabel(null), 'as-of unknown');
  assert.equal(asOfLabel(undefined, 'n/a'), 'n/a');
});
