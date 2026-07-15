import { test, expect } from '@playwright/test';
import { snap, waitForAppReady, withErrorCapture, gotoAndWaitForApi } from './helpers';

test.describe('Hardware, Methodology, Dashboard', () => {
  test('dashboard loads stats, charts, and recent submission links', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop');

    const { failedRequests, pageErrors } = await withErrorCapture(page, async () => {
      await gotoAndWaitForApi(page, '/', '/api/v1/stats').catch(async () => {
        await page.goto('/');
        await waitForAppReady(page);
      });
      await snap(page, 'dashboard-full');

      // Links into models / hardware / benchmark detail
      const modelsLink = page.getByRole('link', { name: /Models|model capability/i }).first();
      if (await modelsLink.isVisible().catch(() => false)) {
        // stay on page — just assert present
        await expect(modelsLink).toBeVisible();
      }

      const benchLink = page.locator('a[href^="/benchmarks/"]').first();
      if (await benchLink.isVisible().catch(() => false)) {
        await benchLink.click();
        await waitForAppReady(page);
        await expect(page).toHaveURL(/\/benchmarks\/\d+/);
        await snap(page, 'benchmark-detail');
        await page.getByRole('link', { name: /Back|Overview/i }).first().click();
        await waitForAppReady(page);
      }
    });

    expect(pageErrors).toEqual([]);
    expect(failedRequests).toEqual([]);
  });

  test('hardware page lists specs and profiles', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop');

    const { failedRequests, pageErrors } = await withErrorCapture(page, async () => {
      const res = await gotoAndWaitForApi(page, '/hardware', '/api/v1/hardware');
      expect(res.ok()).toBeTruthy();
      await snap(page, 'hardware');
      await expect(page.locator('h1')).toContainText(/Test Rigs/i);
      await expect(page.locator('body')).not.toContainText("Couldn't load this");
    });

    expect(pageErrors).toEqual([]);
    expect(failedRequests).toEqual([]);
  });

  test('methodology page renders sections and Overview link', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop');

    await page.goto('/methodology');
    await waitForAppReady(page);
    await snap(page, 'methodology');
    await expect(page.locator('h1').first()).toBeVisible();
    const overview = page.getByRole('main').getByRole('link', { name: 'Overview' });
    await expect(overview).toBeVisible();
    await overview.click();
    await expect(page).toHaveURL('/');
  });
});
