import test from 'node:test';
import assert from 'node:assert/strict';
import { heatBand, compositeScore } from '../src/lib/scoreScale.js';

test('band edges: 85 excellent, 70 strong, 55 mixed, 40 weak, below failing', () => {
  assert.equal(heatBand(100).name, 'excellent');
  assert.equal(heatBand(85).name, 'excellent');
  assert.equal(heatBand(84.9).name, 'strong');
  assert.equal(heatBand(70).name, 'strong');
  assert.equal(heatBand(69.9).name, 'mixed');
  assert.equal(heatBand(55).name, 'mixed');
  assert.equal(heatBand(54.9).name, 'weak');
  assert.equal(heatBand(40).name, 'weak');
  assert.equal(heatBand(39.9).name, 'failing');
  assert.equal(heatBand(0).name, 'failing');
});

test('out-of-range values clamp instead of falling off the scale', () => {
  assert.equal(heatBand(140).name, 'excellent');
  assert.equal(heatBand(-5).name, 'failing');
});

test('missing scores get no band — no fake colors for absent data', () => {
  assert.equal(heatBand(null), null);
  assert.equal(heatBand(undefined), null);
  assert.equal(heatBand(NaN), null);
});

test('every band ships a bg tint and a readable text color', () => {
  for (const v of [90, 75, 60, 45, 10]) {
    const b = heatBand(v);
    assert.match(b.bg, /^rgba\(/);
    assert.match(b.text, /^#[0-9a-f]{6}$/);
  }
});

test('composite is the equal-weight category mean, rounded to 1 decimal', () => {
  assert.equal(compositeScore({ a: 100, b: 50 }), 75);
  assert.equal(compositeScore({ a: 33.33, b: 66.67, c: 0 }), 33.3);
  // Equal weight regardless of implied task counts: one category one vote.
  assert.equal(compositeScore({ reasoning: 80, coding: 100 }), 90);
});

test('composite ignores null holes and returns null when empty', () => {
  assert.equal(compositeScore({ a: 100, b: null }), 100);
  assert.equal(compositeScore({}), null);
  assert.equal(compositeScore(null), null);
});
