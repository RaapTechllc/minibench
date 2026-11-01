import { test, expect } from '@playwright/test';
import { snap, waitForAppReady, withErrorCapture, gotoAndWaitForApi } from './helpers';

test.describe('Value, Deployment, Methodology', () => {
  test('value desk loads scenario controls and model evidence', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop');

    const { failedRequests, pageErrors } = await withErrorCapture(page, async () => {
      await gotoAndWaitForApi(page, '/', '/api/v1/agents/models/leaderboard').catch(async () => {
        await page.goto('/');
        await waitForAppReady(page);
      });
      await snap(page, 'value-desk-full');
      await expect(page.locator('h1')).toContainText(/earns its keep/i);
      await expect(page.getByLabel('Benchmark suite')).toBeVisible();
      await expect(page.getByLabel('Tasks / month')).toBeVisible();
    });

    expect(pageErrors).toEqual([]);
    expect(failedRequests).toEqual([]);
  });

  test('hardware page lists specs and profiles', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop');

    const { failedRequests, pageErrors } = await withErrorCapture(page, async () => {
      const res = await gotoAndWaitForApi(page, '/hardware', '/api/v1/profiles');
      expect(res.ok()).toBeTruthy();
      await snap(page, 'hardware');
      await expect(page.locator('h1')).toContainText(/Hardware is context/i);
      await expect(page.locator('body')).not.toContainText("Couldn't load this");
    });

    expect(pageErrors).toEqual([]);
    expect(failedRequests).toEqual([]);
  });

  test('methodology page renders sections and Value desk link', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop');

    await page.goto('/methodology');
    await waitForAppReady(page);
    await snap(page, 'methodology');
    await expect(page.locator('h1').first()).toBeVisible();
    const valueDesk = page.getByRole('main').getByRole('link', { name: 'Value desk' }).first();
    await expect(valueDesk).toBeVisible();
    await valueDesk.click();
    await expect(page).toHaveURL('/');
  });
});
