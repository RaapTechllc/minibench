import { test, expect } from '@playwright/test';
import { snap, waitForAppReady, withErrorCapture } from './helpers';

const NAV_ROUTES = [
  { path: '/', title: /Choose the model that earns its keep/i },
  { path: '/models', title: /Model evidence|Hard v1|v2/i },
  { path: '/agents', title: /Agent and MoA evidence/i },
  { path: '/compare', title: /stronger model worth the premium/i },
  { path: '/moa-calculator', title: /MoA Cost Calculator/i },
  { path: '/hardware', title: /Hardware is context/i },
  { path: '/methodology', title: /Methodology/i },
] as const;

const LEGACY_ROUTES = [
  { path: '/submit', title: /Submit throughput/i },
  { path: '/legacy-overview', title: /Overview|Dashboard|Efficiency|frontier|bandwidth/i },
  { path: '/leaderboard', expectRedirect: '/models' },
] as const;

test.describe('Navigation & routes', () => {
  test('desktop nav links reach every primary page', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop nav only');

    const { consoleErrors, pageErrors, failedRequests } = await withErrorCapture(page, async () => {
      await page.goto('/');
      await waitForAppReady(page);
      await snap(page, '00-dashboard');

      for (const route of NAV_ROUTES) {
        // Prefer direct goto for reliability, then verify nav aria-current
        await page.goto(route.path);
        await waitForAppReady(page);
        await expect(page.locator('h1').first()).toBeVisible();
        await snap(page, `nav-${route.path.replace(/\W+/g, '_') || 'home'}`);
      }

      // Click each desktop nav link in order
      await page.goto('/');
      await waitForAppReady(page);
      const labels = ['Value', 'Models', 'Configurations', 'Compare', 'Cost planner', 'Deployment', 'Evidence'];
      const desktopNav = page.locator('header nav').first();
      for (const label of labels) {
        await desktopNav.getByRole('link', { name: label }).click();
        await waitForAppReady(page);
        await expect(desktopNav.getByRole('link', { name: label })).toHaveAttribute('aria-current', 'page');
      }
    });

    expect(pageErrors, `page errors: ${pageErrors.join('\n')}`).toEqual([]);
    expect(failedRequests, `API failures: ${failedRequests.join('\n')}`).toEqual([]);
    // Filter noisy Vite HMR / extension noise if any
    const realConsole = consoleErrors.filter((e) => !/favicon|Download the React DevTools/i.test(e));
    expect(realConsole, `console errors: ${realConsole.join('\n')}`).toEqual([]);
  });

  test('legacy routes render or redirect', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop only');

    for (const route of LEGACY_ROUTES) {
      await page.goto(route.path);
      await waitForAppReady(page);
      if ('expectRedirect' in route && route.expectRedirect) {
        await expect(page).toHaveURL(new RegExp(route.expectRedirect));
        await snap(page, 'legacy-leaderboard-redirect');
      } else if ('title' in route && route.title) {
        await expect(page.locator('h1').first()).toContainText(route.title);
        await snap(page, `legacy-${route.path.replace(/\W+/g, '_')}`);
      }
    }
  });

  test('brand link returns home', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'desktop only');
    await page.goto('/methodology');
    await waitForAppReady(page);
    await page.getByRole('link', { name: 'MiniBench' }).first().click();
    await expect(page).toHaveURL('/');
  });
});
