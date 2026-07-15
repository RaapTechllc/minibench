import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import {
  ARTIFACTS,
  dismissLegacyNoticeIfPresent,
  ensureArtifactsDir,
  snap,
  waitForAppReady,
  withErrorCapture,
} from './helpers';

/**
 * Exhaustive click sweep: every route, every visible control that is safe to
 * activate, with screenshots + a machine-readable findings JSON for the health report.
 */
test.describe('Full interactive sweep', () => {
  test('visit every route, exercise controls, record health findings', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium-desktop', 'full sweep on desktop');
    ensureArtifactsDir();

    const findings: {
      route: string;
      status: 'ok' | 'warn' | 'fail';
      notes: string[];
      consoleErrors: string[];
      pageErrors: string[];
      failedRequests: string[];
      screenshot?: string;
    }[] = [];

    const routes = [
      '/',
      '/models',
      '/agents',
      '/moa-calculator',
      '/hardware',
      '/methodology',
      '/submit',
      '/compare',
      '/leaderboard',
      '/agents/runs/00000000-0000-0000-0000-000000000000', // not-found path
      '/benchmarks/999999', // not-found path
    ];

    for (const route of routes) {
      const capture = await withErrorCapture(page, async () => {
        await page.goto(route);
        await waitForAppReady(page);
        await dismissLegacyNoticeIfPresent(page);

        // Wait briefly for network settle on data pages
        await page.waitForLoadState('networkidle').catch(() => null);

        const notes: string[] = [];

        // Exercise selects
        const selects = page.locator('select:visible');
        const selectCount = await selects.count();
        for (let i = 0; i < selectCount; i++) {
          const sel = selects.nth(i);
          const values = await sel.locator('option').evaluateAll((opts) =>
            opts.map((o) => (o as HTMLOptionElement).value),
          );
          if (values.length > 1) {
            await sel.selectOption(values[Math.min(1, values.length - 1)]);
            notes.push(`select[${i}] -> ${values[Math.min(1, values.length - 1)] || '(empty)'}`);
            await page.waitForTimeout(200);
          }
        }

        // Exercise non-submit buttons (sorts, toggles, dismiss, retry, menu)
        const buttons = page.locator('button:visible');
        const btnCount = await buttons.count();
        for (let i = 0; i < btnCount; i++) {
          const btn = buttons.nth(i);
          const label =
            ((await btn.getAttribute('aria-label')) || (await btn.innerText()).trim()).replace(/\s+/g, ' ');
          if (!label) continue;
          if (/submit benchmark/i.test(label)) continue;
          if (/close menu|open menu/i.test(label)) continue;
          try {
            await btn.click({ timeout: 2500 });
            notes.push(`clicked button: ${label.slice(0, 60)}`);
            await page.waitForTimeout(150);
          } catch {
            notes.push(`skip button: ${label.slice(0, 60)}`);
          }
        }

        // Number / range inputs — nudge values
        const ranges = page.locator('input[type="range"]:visible, input[type="number"]:visible');
        const rCount = await ranges.count();
        for (let i = 0; i < Math.min(rCount, 8); i++) {
          const input = ranges.nth(i);
          const type = await input.getAttribute('type');
          if (type === 'range') {
            await input.fill('75');
            notes.push(`range[${i}] -> 75`);
          } else {
            const current = await input.inputValue();
            const next = String(Math.max(1, Number(current) || 1));
            await input.fill(next);
            notes.push(`number[${i}] -> ${next}`);
          }
        }

        const shot = await snap(page, `sweep-${route.replace(/\W+/g, '_') || 'home'}`);
        return { notes, shot };
      });

      const hasHard =
        capture.pageErrors.length > 0 ||
        capture.failedRequests.some((r) => !r.includes('/agents/runs/00000000') && !r.includes('/benchmarks/999999'));

      // Expected 404 API for synthetic not-found routes
      const expectedFail =
        route.includes('00000000') || route.includes('999999');

      findings.push({
        route,
        status: hasHard && !expectedFail ? 'fail' : capture.consoleErrors.length ? 'warn' : 'ok',
        notes: capture.result.notes,
        consoleErrors: capture.consoleErrors,
        pageErrors: capture.pageErrors,
        failedRequests: capture.failedRequests,
        screenshot: capture.result.shot,
      });
    }

    // Error-state retry button: force by visiting with API blocked briefly
    await page.route('**/api/v1/hardware', (route) => route.abort());
    await page.goto('/hardware');
    await waitForAppReady(page);
    const retry = page.getByRole('button', { name: /Try again/i });
    if (await retry.isVisible({ timeout: 5000 }).catch(() => false)) {
      await snap(page, 'hardware-error-state');
      await page.unroute('**/api/v1/hardware');
      await retry.click();
      await page.waitForResponse((r) => r.url().includes('/api/v1/hardware') && r.ok());
      await snap(page, 'hardware-error-recovered');
      findings.push({
        route: '/hardware (error+retry)',
        status: 'ok',
        notes: ['ErrorState retry works'],
        consoleErrors: [],
        pageErrors: [],
        failedRequests: [],
      });
    } else {
      await page.unroute('**/api/v1/hardware');
      findings.push({
        route: '/hardware (error+retry)',
        status: 'warn',
        notes: ['Could not trigger ErrorState'],
        consoleErrors: [],
        pageErrors: [],
        failedRequests: [],
      });
    }

    const out = path.join(ARTIFACTS, 'findings.json');
    fs.writeFileSync(out, JSON.stringify({ generatedAt: new Date().toISOString(), findings }, null, 2));

    const fails = findings.filter((f) => f.status === 'fail');
    expect(fails, JSON.stringify(fails, null, 2)).toEqual([]);
  });
});
