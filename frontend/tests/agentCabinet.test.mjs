import test from 'node:test';
import assert from 'node:assert/strict';
import {
  AGENT_CABINET_COPY,
  AGENT_CABINET_DEFAULT_FIELDS,
  AGENT_CABINET_LIST_FIELDS,
  AGENT_CABINET_TECHNICIAN_FIELDS,
  categoryTitle,
  controlledVariableSentence,
  sortedCategoryEntries,
} from '../src/lib/agentCabinet.js';

test('no composite anywhere in the cabinet field sets or copy', () => {
  for (const fields of [
    AGENT_CABINET_DEFAULT_FIELDS,
    AGENT_CABINET_LIST_FIELDS,
    AGENT_CABINET_TECHNICIAN_FIELDS,
  ]) {
    assert.equal(fields.includes('composite'), false);
  }
  for (const text of Object.values(AGENT_CABINET_COPY)) {
    assert.equal(text.toLowerCase().includes('composite score'), false);
  }
});

test('default scorecard is completion, category breakdown, cost, latency', () => {
  assert.deepEqual([...AGENT_CABINET_DEFAULT_FIELDS], [
    'completion',
    'category_completion',
    'cost_usd_per_task',
    'latency_p50_ms',
  ]);
});

test('default and technician key sets are disjoint', () => {
  const overlap = AGENT_CABINET_DEFAULT_FIELDS.filter((key) =>
    AGENT_CABINET_TECHNICIAN_FIELDS.includes(key));
  assert.deepEqual(overlap, []);
});

test('technician diagnostics never flatten onto the list item', () => {
  const technicianOnly = [
    'model',
    'provider',
    'fixture_reference',
    'fixture_digest',
    'budgets',
    'trials',
    'ci95_low',
    'ci95_high',
    'pass_hat_k',
    'regression_rate',
    'false_verification_rate',
    'termination_reasons',
  ];
  for (const key of technicianOnly) {
    assert.equal(AGENT_CABINET_LIST_FIELDS.includes(key), false, `${key} on list`);
    assert.equal(AGENT_CABINET_DEFAULT_FIELDS.includes(key), false, `${key} in default`);
    assert.equal(AGENT_CABINET_TECHNICIAN_FIELDS.includes(key), true, `${key} missing`);
  }
});

test('list contract carries the documented default item fields', () => {
  for (const key of [
    'run_id',
    'submitted_at',
    'suite',
    'model_route',
    'harness',
    'harness_version',
    'completion',
    'pass_rate',
    'category_completion',
    'cost_usd_per_task',
    'latency_p50_ms',
    'private_split',
  ]) {
    assert.equal(AGENT_CABINET_LIST_FIELDS.includes(key), true, `${key} missing`);
  }
});

test('copy constants: empty board and not-Solo-not-Multiplayer lines', () => {
  assert.equal(
    AGENT_CABINET_COPY.emptyTitle,
    'No published Real-Work Agent Cabinet runs yet.',
  );
  assert.equal(
    AGENT_CABINET_COPY.emptyBody,
    'Offline dry-run artifacts do not appear.',
  );
  assert.match(AGENT_CABINET_COPY.notSoloNotMultiplayer, /not Solo Cabinet/);
  assert.match(AGENT_CABINET_COPY.notSoloNotMultiplayer, /not Multiplayer Cabinet/);
});

test('copy constants: controlled-variable contract names what is held', () => {
  for (const term of ['task snapshot', 'tools', 'limits', 'verification', 'trials']) {
    assert.match(AGENT_CABINET_COPY.controlledVariables, new RegExp(term));
  }
  assert.match(AGENT_CABINET_COPY.controlledVariables, /changed variables are explicit/);
});

test('categoryTitle title-cases raw keys without Arcade display names', () => {
  assert.equal(categoryTitle('repository-repair'), 'Repository Repair');
  assert.equal(categoryTitle('feature-implementation'), 'Feature Implementation');
  assert.equal(categoryTitle('web_research'), 'Web Research');
  // Raw keys stay raw: no CATEGORY_DISPLAY_NAMES mapping.
  assert.equal(categoryTitle('reasoning'), 'Reasoning');
  assert.equal(categoryTitle('tool-use'), 'Tool Use');
  assert.equal(categoryTitle(''), '');
});

test('sortedCategoryEntries keeps raw keys and sorts deterministically', () => {
  assert.deepEqual(
    sortedCategoryEntries({ 'feature-implementation': 0, 'repository-repair': 100 }),
    [['feature-implementation', 0], ['repository-repair', 100]],
  );
  assert.deepEqual(sortedCategoryEntries(null), []);
  assert.deepEqual(sortedCategoryEntries(undefined), []);
});

test('controlledVariableSentence prefers payload held_constant + changed_variables', () => {
  const detail = {
    held_constant: ['task_set_sha256', 'fixture_digest', 'budgets'],
    changed_variables: 'Independent variables that may differ across listed runs are model_route and harness.',
  };
  assert.equal(
    controlledVariableSentence(detail),
    'Held constant: task_set_sha256, fixture_digest, budgets. ' +
      'Independent variables that may differ across listed runs are model_route and harness.',
  );
  assert.equal(
    controlledVariableSentence({ changed_variables: 'Changed variable: model_route.' }),
    'Changed variable: model_route.',
  );
  assert.equal(controlledVariableSentence({ held_constant: ['budgets'] }), 'Held constant: budgets.');
  assert.equal(controlledVariableSentence(null), '');
  assert.equal(controlledVariableSentence({}), '');
});
