import { test, expect } from '@playwright/test';
import { snap, waitForAppReady, withErrorCapture, gotoAndWaitForApi } from './helpers';

const VALID_SUBMIT = {
  cpu_model: 'Apple M4 Pro',
  system_type: 'Mac Mini M4 Pro',
  gpu_model: '',
  total_ram_gb: '48',
  memory_type: 'LPDDR5x',
  memory_bandwidth_gbs: '273',
  hardware_price_usd: '1599',
  os: 'macOS 15.2',
  inference_engine: 'llama.cpp',
  engine_version: '0.5.4',
  model_name: `E2E-Test-Model-${Date.now()}`,
  model_params_b: '8',
  quantization: 'Q4_K_M',
  tokens_per_second: '42.5',
  time_to_first_token: '0.4',
  prompt_tokens: '200',
  completion_tokens: '300',
  test_duration_secs: '15',
};

test.describe('Submit & Compare (legacy)', () => {
  test('submit form validates required fields then accepts a valid run', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop');

    const { failedRequests, pageErrors } = await withErrorCapture(page, async () => {
      await page.goto('/submit');
      await waitForAppReady(page);
      await snap(page, 'submit-empty');

      await page.getByRole('button', { name: 'Submit benchmark' }).click();
      // Client-side validation should surface without API call
      await expect(page.locator('[aria-invalid="true"]').first()).toBeVisible();
      await snap(page, 'submit-validation-errors');

      const fillByLabel = async (label: string | RegExp, value: string) => {
        await page.getByLabel(label, { exact: typeof label === 'string' }).fill(value);
      };

      await fillByLabel(/^CPU model/, VALID_SUBMIT.cpu_model);
      await fillByLabel(/^System/, VALID_SUBMIT.system_type);
      await fillByLabel(/^RAM \(GB\)/, VALID_SUBMIT.total_ram_gb);
      await fillByLabel(/^Memory type/, VALID_SUBMIT.memory_type);
      await fillByLabel(/^Memory bandwidth \(GB\/s\)/, VALID_SUBMIT.memory_bandwidth_gbs);
      await fillByLabel(/^Price \(USD\)/, VALID_SUBMIT.hardware_price_usd);
      await fillByLabel(/^OS/, VALID_SUBMIT.os);
      await fillByLabel(/^Inference engine/, VALID_SUBMIT.inference_engine);
      await fillByLabel(/^Engine version/, VALID_SUBMIT.engine_version);
      await fillByLabel(/^Model/, `E2E-Test-Model-${Date.now()}`);
      await fillByLabel(/^Params \(B\)/, VALID_SUBMIT.model_params_b);
      await fillByLabel(/^Quantization/, VALID_SUBMIT.quantization);
      await fillByLabel(/^Tokens\/sec/, VALID_SUBMIT.tokens_per_second);
      await fillByLabel(/^TTFT \(s\)/, VALID_SUBMIT.time_to_first_token);
      await fillByLabel(/^Prompt tokens/, VALID_SUBMIT.prompt_tokens);
      await fillByLabel(/^Completion tokens/, VALID_SUBMIT.completion_tokens);
      await fillByLabel(/^Test duration \(s\)/, VALID_SUBMIT.test_duration_secs);

      await snap(page, 'submit-filled');

      const [resp] = await Promise.all([
        page.waitForResponse((r) => r.url().includes('/api/v1/submit') && r.request().method() === 'POST'),
        page.getByRole('button', { name: 'Submit benchmark' }).click(),
      ]);

      expect(resp.ok(), `submit status ${resp.status()} body ${await resp.text()}`).toBeTruthy();
      await expect(page.getByText('Benchmark submitted')).toBeVisible();
      await snap(page, 'submit-success');

      await page.getByRole('link', { name: /View submission/i }).click();
      await waitForAppReady(page);
      await expect(page).toHaveURL(/\/benchmarks\/\d+/);
      await snap(page, 'submit-view-submission');
    });

    expect(pageErrors).toEqual([]);
    // Allow rate-limit or validation only if unexpected — empty preferred
    const hardFails = failedRequests.filter((r) => !r.startsWith('422'));
    expect(hardFails).toEqual([]);
  });

  test('compare page selects two benchmarks', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop');

    const { failedRequests, pageErrors } = await withErrorCapture(page, async () => {
      await gotoAndWaitForApi(page, '/compare', '/api/v1/benchmarks');
      await snap(page, 'compare-default');

      const selectA = page.getByLabel('A');
      const selectB = page.getByLabel('B');
      await expect(selectA).toBeVisible();
      await expect(selectB).toBeVisible();

      const aOpts = await selectA.locator('option').evaluateAll((opts) =>
        opts.map((o) => (o as HTMLOptionElement).value),
      );
      if (aOpts.length >= 2) {
        // Page auto-loads compare for first two; force a different pairing.
        const wait = page.waitForResponse((r) => r.url().includes('/api/v1/compare') && r.ok());
        await selectA.selectOption(aOpts[aOpts.length - 1]);
        await selectB.selectOption(aOpts[0]);
        await wait;
        await expect(page.getByText('Metric comparison')).toBeVisible();
        await snap(page, 'compare-side-by-side');
      } else {
        await expect(page.getByText(/Pick two systems|Metric comparison/i)).toBeVisible();
      }

      // Cross-links
      await page.getByRole('link', { name: 'Models' }).first().click();
      await expect(page).toHaveURL(/\/models/);
    });

    expect(pageErrors).toEqual([]);
    expect(failedRequests).toEqual([]);
  });
});
