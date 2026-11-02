// Loads the web export over HTTP, checks boot, input and persistence across reloads.
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2] || 'http://127.0.0.1:8765/index.html';
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--autoplay-policy=user-gesture-required'] });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await ctx.newPage();
  const logs = [];
  page.on('console', m => logs.push(m.type() + ': ' + m.text()));
  page.on('pageerror', e => logs.push('pageerror: ' + e.message));
  for (let run = 1; run <= 2; run++) {
    await page.goto(url);
    await page.waitForFunction(() => window.__boot_ok || [...document.querySelectorAll('canvas')].length > 0, null, { timeout: 30000 });
    const t0 = Date.now();
    while (Date.now() - t0 < 30000 && !logs.some(l => l.includes('PROOF_BOOT boots=' + run))) await page.waitForTimeout(250);
    await page.mouse.click(640, 360);
    await page.keyboard.down('ArrowRight'); await page.waitForTimeout(500); await page.keyboard.up('ArrowRight');
    await page.screenshot({ path: process.argv[3] + '/proof_run' + run + '.png' });
    await page.waitForTimeout(1500); // allow IndexedDB sync
  }
  console.log(logs.filter(l => !l.includes('GPU stall')).join('\n'));
  await browser.close();
})();
