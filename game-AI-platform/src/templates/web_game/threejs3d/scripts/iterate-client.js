/**
 * iterate-client.js — Action replay + screenshot for Three.js game.
 */
const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const args = Object.fromEntries(
  process.argv.slice(2).map(a => {
    const [k, v] = a.replace(/^--/, '').split('=');
    return [k, v ?? true];
  })
);

const PORT = args.port ?? '4173';
const ACTIONS_FILE = args.actions ?? path.join(__dirname, 'example-actions.json');
const URL = `http://localhost:${PORT}`;

async function run() {
  const actions = JSON.parse(fs.readFileSync(ACTIONS_FILE, 'utf-8'));
  const browser = await chromium.launch({
    headless: true,
    args: [
      '--enable-webgl',
      '--use-gl=angle',
      '--use-angle=swiftshader',
      '--enable-unsafe-swiftshader',
    ],
  });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 800, height: 600 });
  await page.goto(URL, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);

  const results = [];
  for (const action of actions) {
    const { type, key, x, y, duration = 100, wait = 500, description } = action;
    try {
      if (type === 'keydown') await page.keyboard.press(key);
      else if (type === 'click') await page.mouse.click(x, y);
      else if (type === 'hold') {
        await page.keyboard.down(key);
        await page.waitForTimeout(duration);
        await page.keyboard.up(key);
      }
      await page.waitForTimeout(wait);
      const stateJson = await page.evaluate(() => {
        if (typeof window.render_game_to_text === 'function') return window.render_game_to_text();
        return null;
      });
      const screenshot = await page.screenshot({ encoding: 'base64', type: 'png' }).catch(() => null);
      results.push({ action: description ?? type, ok: true, state: stateJson ? JSON.parse(stateJson) : null, screenshot });
    } catch (err) {
      results.push({ action: description ?? type, ok: false, error: err.message });
    }
  }
  await browser.close();
  console.log(JSON.stringify(results, null, 2));
}

run().catch(err => { console.error(err); process.exit(1); });
