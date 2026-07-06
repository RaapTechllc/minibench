// Pure validation + payload building for the manual submit form.
// Mirrors the server-side rules in backend/app/schemas.py (BenchmarkSubmit)
// and backend/app/main.py (POST /api/v1/submit) so users get feedback
// before the request is sent.

export const REQUIRED_FIELDS = [
  'cpu_model',
  'total_ram_gb',
  'os',
  'inference_engine',
  'model_name',
  'quantization',
  'tokens_per_second',
  'prompt_tokens',
  'completion_tokens',
  'test_duration_secs',
];

const FLOAT_FIELDS = [
  'total_ram_gb',
  'memory_bandwidth_gbs',
  'hardware_price_usd',
  'model_params_b',
  'tokens_per_second',
  'time_to_first_token',
  'test_duration_secs',
];

const INT_FIELDS = ['prompt_tokens', 'completion_tokens'];

const STRING_FIELDS = [
  'cpu_model',
  'system_type',
  'gpu_model',
  'memory_type',
  'os',
  'inference_engine',
  'engine_version',
  'model_name',
  'quantization',
];

function isBlank(value) {
  return value === undefined || value === null || String(value).trim() === '';
}

function asNumber(value) {
  const n = Number(String(value).trim());
  return Number.isFinite(n) ? n : null;
}

/**
 * Validate raw form values (all strings). Returns an object mapping field
 * name -> error message; empty object means the form is valid.
 */
export function validateSubmitForm(values) {
  const errors = {};

  for (const field of REQUIRED_FIELDS) {
    if (isBlank(values[field])) errors[field] = 'Required';
  }

  for (const field of [...FLOAT_FIELDS, ...INT_FIELDS]) {
    if (isBlank(values[field]) || errors[field]) continue;
    const n = asNumber(values[field]);
    if (n === null) {
      errors[field] = 'Must be a number';
    } else if (INT_FIELDS.includes(field) && !Number.isInteger(n)) {
      errors[field] = 'Must be a whole number';
    }
  }

  const tps = asNumber(values.tokens_per_second);
  if (!errors.tokens_per_second && tps !== null && (tps < 0.1 || tps > 500)) {
    errors.tokens_per_second = 'Must be between 0.1 and 500';
  }

  const duration = asNumber(values.test_duration_secs);
  if (!errors.test_duration_secs && duration !== null && duration < 10) {
    errors.test_duration_secs = 'Must be at least 10 seconds';
  }

  const ram = asNumber(values.total_ram_gb);
  if (!errors.total_ram_gb && ram !== null && ram < 0.1) {
    errors.total_ram_gb = 'Must be at least 0.1 GB';
  }

  const prompt = asNumber(values.prompt_tokens);
  const completion = asNumber(values.completion_tokens);
  if (!errors.prompt_tokens && prompt !== null && prompt < 1) {
    errors.prompt_tokens = 'Must be at least 1';
  }
  if (!errors.completion_tokens && completion !== null && completion < 1) {
    errors.completion_tokens = 'Must be at least 1';
  }
  if (
    !errors.prompt_tokens && !errors.completion_tokens &&
    prompt !== null && completion !== null && prompt + completion < 100
  ) {
    errors.completion_tokens = 'Prompt + completion tokens must total at least 100';
  }

  return errors;
}

/**
 * Convert raw form values into the POST /api/v1/submit JSON payload.
 * Numbers are coerced; blank optional fields are omitted entirely.
 * Assumes validateSubmitForm(values) returned no errors.
 */
export function buildSubmitPayload(values) {
  const payload = {};
  for (const field of STRING_FIELDS) {
    if (!isBlank(values[field])) payload[field] = String(values[field]).trim();
  }
  for (const field of FLOAT_FIELDS) {
    if (!isBlank(values[field])) payload[field] = asNumber(values[field]);
  }
  for (const field of INT_FIELDS) {
    if (!isBlank(values[field])) payload[field] = asNumber(values[field]);
  }
  return payload;
}
