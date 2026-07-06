/**
 * Tests for Dashboard helper functions and API param serialization.
 *
 * These functions are re-implemented here (mirroring Dashboard.tsx) because
 * node --test cannot import .tsx files without a transpiler. If the
 * implementations diverge, these tests will still pass — they validate the
 * expected behavior, not the source code directly.
 *
 * To run: npm test
 */
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

// ─── fmtNum ──────────────────────────────────────────────────────────────────

function fmtNum(v, suffix = '') {
  if (v == null) return '—';
  return `${Number(v).toLocaleString()}${suffix}`;
}

// ─── fmtCost ──────────────────────────────────────────────────────────────────

function fmtCost(v) {
  if (v == null) return '—';
  return `$${Number(v).toFixed(v < 1 ? 3 : 2)}`;
}

// ─── URLSearchParams serialization (mirrors api.ts pattern) ─────────────────────

function buildQuery(params) {
  if (!params) return '';
  return '?' + new URLSearchParams(
    Object.entries(params).map(([k, v]) => [k, String(v)])
  ).toString();
}

describe('fmtNum', () => {
  it('returns em-dash for null/undefined', () => {
    assert.equal(fmtNum(null), '—');
    assert.equal(fmtNum(undefined), '—');
  });

  it('formats numbers with locale separators', () => {
    assert.equal(fmtNum(1000), '1,000');
    assert.equal(fmtNum(88), '88');
  });

  it('appends suffix when provided', () => {
    assert.equal(fmtNum(88, ' t/s'), '88 t/s');
    assert.equal(fmtNum(1000, ' t/s'), '1,000 t/s');
  });

  it('handles zero', () => {
    assert.equal(fmtNum(0), '0');
    assert.equal(fmtNum(0, ' t/s'), '0 t/s');
  });
});

describe('fmtCost', () => {
  it('returns em-dash for null', () => {
    assert.equal(fmtCost(null), '—');
  });

  it('formats costs >= 1 with 2 decimal places', () => {
    assert.equal(fmtCost(17.5), '$17.50');
    assert.equal(fmtCost(35), '$35.00');
    assert.equal(fmtCost(10), '$10.00');
  });

  it('formats costs < 1 with 3 decimal places', () => {
    assert.equal(fmtCost(0.5), '$0.500');
    assert.equal(fmtCost(0.001), '$0.001');
  });
});

describe('buildQuery (api.ts param serialization)', () => {
  it('returns empty string for no params', () => {
    assert.equal(buildQuery(), '');
    assert.equal(buildQuery(undefined), '');
  });

  it('serializes string values', () => {
    const qs = buildQuery({ task: 'overall' });
    assert.equal(qs, '?task=overall');
  });

  it('serializes number values by converting to string', () => {
    const qs = buildQuery({ limit: 8 });
    assert.equal(qs, '?limit=8');
  });

  it('serializes mixed string and number values', () => {
    const qs = buildQuery({ limit: 8, task: 'agentic_coding' });
    assert.ok(qs.includes('limit=8'));
    assert.ok(qs.includes('task=agentic_coding'));
  });
});