export type SubmitFormValues = Record<string, string>;

export interface SubmitPayload {
  cpu_model: string;
  total_ram_gb: number;
  os: string;
  inference_engine: string;
  model_name: string;
  quantization: string;
  tokens_per_second: number;
  prompt_tokens: number;
  completion_tokens: number;
  test_duration_secs: number;
  system_type?: string;
  gpu_model?: string;
  memory_type?: string;
  engine_version?: string;
  memory_bandwidth_gbs?: number;
  hardware_price_usd?: number;
  model_params_b?: number;
  time_to_first_token?: number;
}

export const REQUIRED_FIELDS: string[];
export function validateSubmitForm(values: SubmitFormValues): Record<string, string>;
export function buildSubmitPayload(values: SubmitFormValues): SubmitPayload;
