/**
 * verify-runtime.mjs
 * Headless Chromium runtime check via Playwright.
 */
import { chromium } from '@playwright/test';

const args = Object.fromEntries(
  process.argv.slice(2).map(a => {
    const [k, v] = a.replace(/^--/, '').split('=');
    return [k, v ?? true];
  })
);

const PORT = args.port ?? '4173';
const TIMEOUT = parseInt(args.timeout ?? '5000', 10);
const URL = `http://localhost:${PORT}`;

const errors = [];
const warnings = [];

const browser = await chromium.launch({
  headless: true,
  args: [
    '--enable-webgl',                // Explicitly enable WebGL
    '--use-gl=angle',                // Use ANGLE as the GL abstraction layer
    '--use-angle=swiftshader',       // Route ANGLE to SwiftShader software renderer
    '--enable-unsafe-swiftshader',   // Lift Chrome's safety restriction on software GL
  ],
});
const page = await browser.newPage();

page.on('console', msg => {
  if (msg.type() === 'error') errors.push(`[console.error] ${msg.text()}`);
  if (msg.type() === 'warning') warnings.push(`[console.warn] ${msg.text()}`);
});
page.on('pageerror', err => errors.push(`[uncaught] ${err.message}`));
page.on('requestfailed', req => {
  if (!req.url().includes('favicon')) warnings.push(`[request.failed] ${req.url()}`);
});

try {
  await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: TIMEOUT });
  await page.waitForTimeout(2000);

  const webglOk = await page.evaluate(() => {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl') || c.getContext('webgl2'));
  });
  if (!webglOk) errors.push('[webgl] WebGL not supported');

  const renderText = await page.evaluate(() => {
    if (typeof window.render_game_to_text !== 'function') return null;
    try { return window.render_game_to_text(); } catch (e) { return `ERROR:${e.message}`; }
  });
  if (!renderText) {
    errors.push('[api] window.render_game_to_text() not found');
  } else if (renderText.startsWith('ERROR:')) {
    errors.push(`[api] window.render_game_to_text() threw: ${renderText}`);
  }
} catch (err) {
  errors.push(`[navigation] ${err.message}`);
} finally {
  await browser.close();
}

const result = { success: errors.length === 0, errors, warnings };
console.log(JSON.stringify(result, null, 2));
process.exit(errors.length > 0 ? 1 : 0);
