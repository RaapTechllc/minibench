import { test, expect } from '@playwright/test';
import { snap, waitForAppReady, withErrorCapture, gotoAndWaitForApi } from './helpers';

test.describe('Agent configurations page', () => {
  test('loads quick picks, sort control, and run drill-down', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop interactions');

    const { failedRequests, pageErrors } = await withErrorCapture(page, async () => {
      await gotoAndWaitForApi(page, '/agents', '/api/v1/agents/leaderboard');
      await snap(page, 'agents-default');

      await expect(page.locator('h1').first()).toContainText(/Agent and MoA evidence/i);

      const table = page.locator('table').last();
      await expect(table).toBeVisible({ timeout: 20_000 });

      // Quick picks
      const quickPick = page.getByRole('link', { name: /Top score|Fastest|Cheapest|Best value/i }).first();
      if (await quickPick.isVisible().catch(() => false)) {
        await expect(page.getByText('Top score')).toBeVisible();
      }

      const sort = page.getByLabel('Sort');
      await expect(sort).toBeVisible();
      for (const value of ['pass_hat_k', 'cost_usd_per_attempt', 'pass_rate']) {
        const wait = page.waitForResponse(
          (r) => r.url().includes('/api/v1/agents/leaderboard') && r.url().includes(`sort_by=${value}`) && r.ok(),
        );
        await sort.selectOption(value);
        await wait;
      }
      await snap(page, 'agents-sorted-by-cost');

      // Open first config
      await table.locator('tbody a[href*="/agents/runs/"]').first().click();
      await waitForAppReady(page);
      await expect(page).toHaveURL(/\/agents\/runs\//);
      await snap(page, 'agents-run-detail');

      // Scoring diagnostics toggle
      const showDiagnostics = page.getByRole('button', { name: /Show diagnostics/i });
      await expect(showDiagnostics).toBeVisible();
      await showDiagnostics.click();
      const hideDiagnostics = page.getByRole('button', { name: /Hide diagnostics/i });
      await expect(hideDiagnostics).toHaveAttribute('aria-pressed', 'true');
      await snap(page, 'agents-run-diagnostics');
      await hideDiagnostics.click();
      await expect(page.getByRole('button', { name: /Show diagnostics/i })).toHaveAttribute('aria-pressed', 'false');

      // Back link
      await page.getByRole('link', { name: /Back|Agents|Models/i }).first().click();
      await waitForAppReady(page);
    });

    expect(pageErrors).toEqual([]);
    expect(failedRequests).toEqual([]);
  });
});
