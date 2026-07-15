import { test, expect } from '@playwright/test';
import {
  dismissLegacyNoticeIfPresent,
  gotoAndWaitForApi,
  snap,
  waitForAppReady,
  withErrorCapture,
} from './helpers';

test.describe('Models page (Solo Cabinet)', () => {
  test('loads leaderboard, cabinet/chart selects, and sortable headers', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop interactions');

    const { failedRequests, pageErrors } = await withErrorCapture(page, async () => {
      await gotoAndWaitForApi(page, '/models', '/api/v1/agents/models/leaderboard');
      await dismissLegacyNoticeIfPresent(page);
      await snap(page, 'models-default');

      await expect(page.locator('h1').first()).toBeVisible();
      // Table or empty state should appear
      const table = page.locator('table.arcade-highscore-table');
      const empty = page.getByText(/No published runs/i);
      await expect(table.or(empty).first()).toBeVisible({ timeout: 20_000 });

      const cabinet = page.getByLabel('Cabinet');
      await expect(cabinet).toBeVisible();
      const options = await cabinet.locator('option').allTextContents();
      expect(options.length).toBeGreaterThan(1);

      // Cycle cabinet options
      for (const value of await cabinet.locator('option').evaluateAll((opts) =>
        opts.map((o) => (o as HTMLOptionElement).value),
      )) {
        await cabinet.selectOption(value);
        await page.waitForResponse((r) => r.url().includes('/api/v1/agents/models/leaderboard') && r.ok());
        await page.waitForTimeout(200);
      }
      await snap(page, 'models-after-cabinet-cycle');

      // Chart Y-axis select
      const chart = page.getByLabel('Chart Y-axis');
      if (await chart.isVisible()) {
        const chartOpts = await chart.locator('option').evaluateAll((opts) =>
          opts.map((o) => (o as HTMLOptionElement).value),
        );
        for (const value of chartOpts.slice(0, 3)) {
          await chart.selectOption(value);
          await page.waitForTimeout(150);
        }
      }

      // Sortable column headers
      if (await table.isVisible()) {
        const sortButtons = table.locator('thead button');
        const n = await sortButtons.count();
        expect(n).toBeGreaterThan(0);
        for (let i = 0; i < Math.min(n, 6); i++) {
          await sortButtons.nth(i).click();
          await page.waitForTimeout(100);
          await sortButtons.nth(i).click(); // toggle dir
          await page.waitForTimeout(100);
        }
        await snap(page, 'models-sorted');

        // Drill into first model run
        const firstRun = table.locator('tbody a[href*="/agents/runs/"]').first();
        if (await firstRun.isVisible()) {
          await firstRun.click();
          await waitForAppReady(page);
          await expect(page).toHaveURL(/\/agents\/runs\//);
          await snap(page, 'models-to-run-detail');
        }
      }
    });

    expect(pageErrors).toEqual([]);
    expect(failedRequests).toEqual([]);
  });
});
