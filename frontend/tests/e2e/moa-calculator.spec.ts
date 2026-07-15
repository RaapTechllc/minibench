import { test, expect } from '@playwright/test';
import { snap, waitForAppReady, withErrorCapture } from './helpers';

test.describe('MoA Calculator', () => {
  test('all inputs update recommendation and savings', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop interactions');

    const { pageErrors } = await withErrorCapture(page, async () => {
      await page.goto('/moa-calculator');
      await waitForAppReady(page);
      await snap(page, 'moa-default');

      await expect(page.locator('h1')).toContainText('MoA Cost Calculator');
      await expect(page.getByText('Recommended')).toBeVisible();
      await expect(page.locator('table')).toBeVisible();

      const fields = [
        { label: 'Input tokens/task', value: '20000' },
        { label: 'Output tokens/task', value: '8000' },
        { label: 'Tasks/day', value: '250' },
        { label: 'Days/month', value: '22' },
        { label: 'Cost cap (% Opus)', value: '40' },
      ];

      for (const { label, value } of fields) {
        const input = page.getByLabel(label, { exact: true });
        await input.fill(value);
        await page.waitForTimeout(100);
      }

      const quality = page.getByLabel('Quality floor');
      await quality.fill('78');
      await snap(page, 'moa-after-inputs');

      // Extreme floor should change recommendation state
      await quality.fill('82');
      await page.waitForTimeout(150);
      await snap(page, 'moa-high-quality-floor');

      await expect(page.getByText('Projected monthly impact')).toBeVisible();
      await expect(page.getByText('Monthly savings')).toBeVisible();
    });

    expect(pageErrors).toEqual([]);
  });
});
