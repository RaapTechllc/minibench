import test from 'node:test';
import assert from 'node:assert/strict';
import { validateSubmitForm, buildSubmitPayload } from '../src/lib/submitForm.js';

const valid = {
  cpu_model: 'Apple M4 Pro',
  total_ram_gb: '24',
  os: 'macOS 15.2',
  inference_engine: 'MLX',
  model_name: 'Llama-3-8B-Instruct',
  quantization: 'Q4_K_M',
  tokens_per_second: '45.2',
  prompt_tokens: '200',
  completion_tokens: '300',
  test_duration_secs: '15',
};

test('valid form has no errors', () => {
  assert.deepEqual(validateSubmitForm(valid), {});
});

test('missing required fields are flagged', () => {
  const errors = validateSubmitForm({ ...valid, cpu_model: '  ', quantization: '' });
  assert.equal(errors.cpu_model, 'Required');
  assert.equal(errors.quantization, 'Required');
});

test('non-numeric input is rejected', () => {
  const errors = validateSubmitForm({ ...valid, tokens_per_second: 'fast' });
  assert.equal(errors.tokens_per_second, 'Must be a number');
});

test('mirrors API range rules', () => {
  assert.match(validateSubmitForm({ ...valid, tokens_per_second: '999' }).tokens_per_second, /0\.1 and 500/);
  assert.match(validateSubmitForm({ ...valid, test_duration_secs: '3' }).test_duration_secs, /at least 10/);
  const tokenErrors = validateSubmitForm({ ...valid, prompt_tokens: '40', completion_tokens: '50' });
  assert.match(tokenErrors.completion_tokens, /at least 100/);
});

test('token counts must be whole numbers', () => {
  const errors = validateSubmitForm({ ...valid, prompt_tokens: '1.5' });
  assert.equal(errors.prompt_tokens, 'Must be a whole number');
});

test('payload coerces numbers and trims strings', () => {
  const payload = buildSubmitPayload({ ...valid, cpu_model: ' Apple M4 Pro ' });
  assert.equal(payload.cpu_model, 'Apple M4 Pro');
  assert.equal(payload.total_ram_gb, 24);
  assert.equal(payload.tokens_per_second, 45.2);
  assert.equal(payload.prompt_tokens, 200);
});

test('payload omits blank optional fields', () => {
  const payload = buildSubmitPayload({ ...valid, gpu_model: '', memory_bandwidth_gbs: '  ' });
  assert.ok(!('gpu_model' in payload));
  assert.ok(!('memory_bandwidth_gbs' in payload));
});

test('payload includes provided optional fields as numbers', () => {
  const payload = buildSubmitPayload({ ...valid, memory_bandwidth_gbs: '273', hardware_price_usd: '1399' });
  assert.equal(payload.memory_bandwidth_gbs, 273);
  assert.equal(payload.hardware_price_usd, 1399);
});
