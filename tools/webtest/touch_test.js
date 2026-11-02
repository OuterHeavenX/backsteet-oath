// Mobile landscape touch test: emulated Pixel 7 landscape with real multi-touch via CDP.
// Verifies on-screen controls appear, movement + attack work simultaneously, and no page scroll.
const { chromium, devices } = require('playwright');
(async () => {
  const url = process.argv[2];
  const out = process.argv[3] || '.';
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const ctx = await browser.newContext({ ...devices['Pixel 7 landscape'] });
  const page = await ctx.newPage();
  const logs = [];
  page.on('console', m => logs.push(m.text()));
  page.on('pageerror', e => logs.push('pageerror: ' + e.message));
  const wait = ms => page.waitForTimeout(ms);
  const cdp = await ctx.newCDPSession(page);
  const vp = page.viewportSize();
  const touch = async (type, points) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: points.map((p, i) => ({ x: p[0], y: p[1], id: p[2] ?? i })) });
  const tap = async (x, y) => { await touch('touchStart', [[x, y]]); await wait(80); await touch('touchEnd', []); await wait(250); };
  await page.goto(url);
  const t0 = Date.now();
  while (Date.now() - t0 < 60000 && !logs.some(l => l.includes('Godot Engine'))) await wait(250);
  await wait(4000);
  console.log('viewport', JSON.stringify(vp));
  await tap(vp.width / 2, vp.height / 2);        // press-any-button
  await wait(1200);
  await page.screenshot({ path: out + '/touch_01_menu.png' });
  // menu buttons are centered; New Game is the first button on a fresh profile
  const scale = vp.height / 360;
  const btnY = (y) => y * scale;
  await tap(vp.width / 2, btnY(360 - 176 + 6));  // first button
  await wait(1200);
  await page.screenshot({ path: out + '/touch_02_slots.png' });
  // slot menu: first slot button roughly in the upper middle of the centered panel
  const sx = vp.width / 2, sy = vp.height / 2 - 30 * scale;
  await tap(sx, sy);
  await wait(7000);
  await page.screenshot({ path: out + '/touch_03_world.png' });
  // skip intro dialogue: tap the dialogue panel repeatedly
  for (let i = 0; i < 14; i++) await tap(vp.width / 2, vp.height - 40 * scale);
  await wait(2500);
  const before = logs.filter(l => l.includes('BO_PERF')).slice(-1)[0] || '';
  // multi-touch: finger 0 holds the stick to the right, finger 1 hammers PUNCH at the same time
  const stick = [70 * scale, vp.height - 74 * scale];
  const punch = [vp.width - 122 * scale, vp.height - 60 * scale];
  await touch('touchStart', [[stick[0], stick[1], 0]]);
  for (let i = 0; i < 8; i++) {
    await touch('touchMove', [[stick[0] + 40 * scale, stick[1], 0]]);
    await touch('touchStart', [[stick[0] + 40 * scale, stick[1], 0], [punch[0], punch[1], 1]]);
    await wait(90);
    await touch('touchEnd', [[stick[0] + 40 * scale, stick[1], 0]]);
    await wait(200);
  }
  await page.screenshot({ path: out + '/touch_04_multitouch.png' });
  await touch('touchEnd', []);
  await wait(5500);
  const after = logs.filter(l => l.includes('BO_PERF')).slice(-1)[0] || '';
  const scrollY = await page.evaluate(() => window.scrollY + document.scrollingElement.scrollTop);
  console.log('before:', before);
  console.log('after: ', after);
  console.log('page scroll offset:', scrollY);
  console.log(logs.filter(l => l.includes('rror')).join('\n'));
  await browser.close();
})();
