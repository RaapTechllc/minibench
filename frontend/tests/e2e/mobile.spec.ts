import { test, expect } from '@playwright/test';
import { snap, waitForAppReady, withErrorCapture } from './helpers';

test.describe('Mobile navigation', () => {
  test('hamburger opens, navigates, and closes', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-mobile', 'mobile viewport only');

    const { pageErrors } = await withErrorCapture(page, async () => {
      await page.goto('/');
      await waitForAppReady(page);
      await snap(page, 'mobile-home');

      const menuBtn = page.getByRole('button', { name: /Open menu/i });
      await expect(menuBtn).toBeVisible();
      await menuBtn.click();
      await expect(page.getByRole('button', { name: /Close menu/i })).toBeVisible();
      await snap(page, 'mobile-menu-open');

      const mobileNav = page.locator('header nav').filter({ hasText: 'Methodology' });
      await mobileNav.getByRole('link', { name: 'Models' }).click();
      await waitForAppReady(page);
      await expect(page).toHaveURL(/\/models/);
      // Menu should close after navigate
      await expect(page.getByRole('button', { name: /Open menu/i })).toBeVisible();
      await snap(page, 'mobile-models');

      await page.getByRole('button', { name: /Open menu/i }).click();
      await mobileNav.getByRole('link', { name: 'Agents' }).click();
      await expect(page).toHaveURL(/\/agents/);

      await page.getByRole('button', { name: /Open menu/i }).click();
      await mobileNav.getByRole('link', { name: 'MoA Calculator' }).click();
      await expect(page).toHaveURL(/\/moa-calculator/);

      await page.getByRole('button', { name: /Open menu/i }).click();
      await mobileNav.getByRole('link', { name: 'Test Rigs' }).click();
      await expect(page).toHaveURL(/\/hardware/);

      await page.getByRole('button', { name: /Open menu/i }).click();
      await mobileNav.getByRole('link', { name: 'Methodology' }).click();
      await expect(page).toHaveURL(/\/methodology/);

      await page.getByRole('button', { name: /Open menu/i }).click();
      await mobileNav.getByRole('link', { name: 'Overview' }).click();
      await expect(page).toHaveURL('/');
      await snap(page, 'mobile-back-home');
    });

    expect(pageErrors).toEqual([]);
  });
});
