import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.BASE_URL || 'http://127.0.0.1:8080';
const output = process.env.EVIDENCE_DIR || join(dirname(fileURLToPath(import.meta.url)), 'evidence');
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, ignoreHTTPSErrors: true });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(base + '/login', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Регистрация', exact: true }).click();
  const email = `browser-${Date.now()}@example.org`;
  await page.getByLabel('Имя', { exact: true }).fill('Лабораторный студент');
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Пароль', { exact: true }).fill('Lab-password-2026');
  await page.screenshot({ path: join(output, 'registration.png'), fullPage: true });
  const [response] = await Promise.all([
    page.waitForResponse(r => r.url().endsWith('/api/auth/register') && r.request().method() === 'POST'),
    page.getByRole('button', { name: 'Зарегистрироваться', exact: true }).click(),
  ]);
  if (response.status() !== 201) throw new Error(`Registration returned ${response.status()}: ${await response.text()}`);
  const registered = await response.json();
  console.log('PASS browser registration:', email, 'user id:', registered.user.id);
  await page.waitForURL(base + '/');
  const [meResponse] = await Promise.all([
    page.waitForResponse(r => r.url().endsWith('/api/auth/me') && r.status() === 200),
    page.goto(base + '/dashboard', { waitUntil: 'networkidle' }),
  ]);
  const me = await meResponse.json();
  if (me.id !== registered.user.id || me.email !== email) throw new Error('Saved account did not survive page reload');
  console.log('PASS full page reload reads the same user from the API:', me.id, me.email);
  await page.screenshot({ path: join(output, 'after-reload.png'), fullPage: true });
  if (errors.length) throw new Error(errors.join('\n'));
  console.log('PASS no browser JavaScript errors');
} finally {
  await browser.close();
}
