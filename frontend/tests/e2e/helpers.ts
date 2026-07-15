import { expect, type Page, type Response } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

export const ARTIFACTS = path.resolve('artifacts/e2e');

export function ensureArtifactsDir() {
  fs.mkdirSync(ARTIFACTS, { recursive: true });
}

export async function snap(page: Page, name: string) {
  ensureArtifactsDir();
  const file = path.join(ARTIFACTS, `${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

/** Collect console + page errors for the duration of a callback. */
export async function withErrorCapture<T>(
  page: Page,
  fn: () => Promise<T>,
): Promise<{ result: T; consoleErrors: string[]; pageErrors: string[]; failedRequests: string[] }> {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const failedRequests: string[] = [];

  const onConsole = (msg: { type: () => string; text: () => string }) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  };
  const onPageError = (err: Error) => pageErrors.push(err.message);
  const onResponse = (res: Response) => {
    const status = res.status();
    const url = res.url();
    if (status >= 400 && (url.includes('/api/') || url.includes('/health'))) {
      failedRequests.push(`${status} ${res.request().method()} ${url}`);
    }
  };

  page.on('console', onConsole);
  page.on('pageerror', onPageError);
  page.on('response', onResponse);
  try {
    const result = await fn();
    return { result, consoleErrors, pageErrors, failedRequests };
  } finally {
    page.off('console', onConsole);
    page.off('pageerror', onPageError);
    page.off('response', onResponse);
  }
}

export async function waitForAppReady(page: Page) {
  await page.waitForLoadState('domcontentloaded');
  await expect(page.getByRole('link', { name: 'MiniBench' }).first()).toBeVisible();
}

/** Goto + wait for a matching API response without missing the race. */
export async function gotoAndWaitForApi(
  page: Page,
  path: string,
  urlPart: string,
) {
  const responsePromise = page.waitForResponse(
    (r) => r.url().includes(urlPart) && r.request().method() === 'GET',
    { timeout: 30_000 },
  );
  await page.goto(path);
  const res = await responsePromise;
  await waitForAppReady(page);
  return res;
}

export async function dismissLegacyNoticeIfPresent(page: Page) {
  const dismiss = page.getByRole('button', { name: 'Dismiss' });
  if (await dismiss.isVisible().catch(() => false)) {
    await dismiss.click();
  }
}

export async function clickAllVisibleButtons(page: Page, opts?: { exclude?: RegExp[] }) {
  const exclude = opts?.exclude ?? [];
  const buttons = page.locator('button:visible, a[href]:visible');
  const count = await buttons.count();
  const clicked: string[] = [];

  for (let i = 0; i < count; i++) {
    const btn = buttons.nth(i);
    if (!(await btn.isVisible().catch(() => false))) continue;
    const label =
      (await btn.getAttribute('aria-label')) ||
      (await btn.innerText().catch(() => '')).trim().replace(/\s+/g, ' ') ||
      (await btn.getAttribute('href')) ||
      `button-${i}`;

    if (exclude.some((re) => re.test(label))) continue;
    // Skip external / destructive / submit-without-form-fill
    if (/submit benchmark/i.test(label)) continue;
    if (/^#/.test(label)) continue;

    try {
      await btn.click({ timeout: 3000 });
      clicked.push(label.slice(0, 80));
      await page.waitForTimeout(150);
    } catch {
      // Element may have unmounted after prior navigation — continue sweep.
    }
  }
  return clicked;
}
