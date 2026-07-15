import { test, expect } from '@playwright/test';
import { snap, waitForAppReady, withErrorCapture } from './helpers';

test.describe('Agents page (Multiplayer Cabinet)', () => {
  test('loads quick picks, sort control, and run drill-down', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop interactions');

    const { failedRequests, pageErrors } = await withErrorCapture(page, async () => {
      await page.goto('/agents');
      await waitForAppReady(page);
      await page.waitForResponse((r) => r.url().includes('/api/v1/agents/leaderboard') && r.ok());
      await snap(page, 'agents-default');

      await expect(page.locator('h1').first()).toContainText(/MoA scorecards|frontier/i);

      const table = page.locator('table.arcade-highscore-table');
      await expect(table).toBeVisible({ timeout: 20_000 });

      // Quick picks
      const quickPick = page.getByRole('link', { name: /Top score|Fastest|Cheapest|Best value/i }).first();
      if (await quickPick.isVisible().catch(() => false)) {
        await expect(page.getByText('Top score')).toBeVisible();
      }

      const sort = page.getByLabel('Sort');
      await expect(sort).toBeVisible();
      for (const value of ['pass_rate', 'pass_hat_k', 'cost_usd_per_task']) {
        await sort.selectOption(value);
        await page.waitForResponse((r) => r.url().includes('/api/v1/agents/leaderboard') && r.ok());
      }
      await snap(page, 'agents-sorted-by-cost');

      // Open first config
      await table.locator('tbody a[href*="/agents/runs/"]').first().click();
      await waitForAppReady(page);
      await expect(page).toHaveURL(/\/agents\/runs\//);
      await snap(page, 'agents-run-detail');

      // Technician mode toggle
      const tech = page.getByRole('button', { name: /Technician mode/i });
      await expect(tech).toBeVisible();
      await tech.click();
      await expect(tech).toHaveAttribute('aria-pressed', 'true');
      await snap(page, 'agents-run-technician');
      await tech.click();
      await expect(tech).toHaveAttribute('aria-pressed', 'false');

      // Back link
      await page.getByRole('link', { name: /Back|Agents|Models/i }).first().click();
      await waitForAppReady(page);
    });

    expect(pageErrors).toEqual([]);
    expect(failedRequests).toEqual([]);
  });
});
