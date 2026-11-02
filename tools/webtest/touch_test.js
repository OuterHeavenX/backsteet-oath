// Touch UX test on an emulated device (default iPad landscape). Real CDP multi-touch.
// Usage: node touch_test.js <url> <outdir> "<Playwright device name>"
const { chromium, devices } = require('playwright');
(async () => {
  const url = process.argv[2];
  const out = process.argv[3] || '.';
  const devName = process.argv[4] || 'iPad Pro 11 landscape';
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const ctx = await browser.newContext({ ...devices[devName] });
  const page = await ctx.newPage();
  const logs = [];
  page.on('console', m => logs.push(m.text()));
  page.on('pageerror', e => logs.push('pageerror: ' + e.message));
  const wait = ms => page.waitForTimeout(ms);
  const cdp = await ctx.newCDPSession(page);
  const vp = page.viewportSize();
  const scale = Math.min(vp.width / 640, vp.height / 360);
  const gw = vp.width / scale, gh = vp.height / scale;          // game (viewport) size with stretch=expand
  const G = (x, y) => [x * scale, y * scale];
  const touch = async (type, pts) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: pts.map((p, i) => ({ x: p[0], y: p[1], id: p[2] ?? i })) });
  const tap = async (gx, gy) => { const p = G(gx, gy); await touch('touchStart', [p]); await wait(70); await touch('touchEnd', []); await wait(300); };
  const shot = async n => page.screenshot({ path: `${out}/${n}.png` });
  await page.goto(url);
  const t0 = Date.now();
  while (Date.now() - t0 < 60000 && !logs.some(l => l.includes('Godot Engine'))) await wait(250);
  await wait(4000);
  console.log('device', devName, 'viewport', JSON.stringify(vp), 'game', Math.round(gw) + 'x' + Math.round(gh));
  await shot('t01_title');
  await tap(gw / 2, gh / 2); await wait(1200);
  await shot('t02_menu');
  await tap(gw / 2, gh - 176 + 8); await wait(1200);           // New Game (first button)
  await tap(gw / 2, gh / 2 - 26); await wait(7000);            // Slot 1
  await shot('t03_intro_dialogue');
  for (let i = 0; i < 4; i++) await tap(gw / 2, 200);          // tap the street to advance dialogue
  await shot('t04_dialogue_tapped');
  await wait(400);
  // SKIP button: bottom-right of the dialogue panel (panel is 600 wide, centered, bottom of the 360-high playfield)
  const pfTop = (gh - 360 >= 72) ? 0 : Math.floor((gh - 360) / 2);
  await tap(gw / 2 + 300 - 26, pfTop + 360 - 18); await wait(1500);
  await shot('t05_after_skip');
  // fight a little with multi-touch: stick right + punch
  const docked = gh - 360 >= 72;
  const deckCy = 360 + (gh - 360) / 2;
  const stick = docked ? [Math.max(64, gw * 0.11), deckCy] : [70, pfTop + 360 - 74];
  const bx = docked ? gw - Math.max(44, gw * 0.07) : gw - 60;
  const punch = docked ? [bx - 62, deckCy + 29] : [bx - 62, pfTop + 360 - 60];
  const S = G(stick[0], stick[1]), P = G(punch[0], punch[1]);
  await touch('touchStart', [[S[0], S[1], 0]]);
  for (let i = 0; i < 10; i++) {
    await touch('touchMove', [[S[0] + 40 * scale, S[1], 0]]);
    await touch('touchStart', [[S[0] + 40 * scale, S[1], 0], [P[0], P[1], 1]]);
    await wait(80);
    await touch('touchEnd', [[S[0] + 40 * scale, S[1], 0]]);
    await wait(180);
  }
  await shot('t06_fight');
  await touch('touchEnd', []);
  await wait(800);
  // open the BAG (status) from the deck / corner, then press Back
  const bag = docked ? [gw / 2 - 30, deckCy] : [gw - 58, pfTop + 22];
  await tap(bag[0], bag[1]); await wait(1200);
  await shot('t07_status');
  await tap(gw / 2 + 280 - 34, gh / 2 - 150 + 14); await wait(1200);   // "< Back" at the right of the tab row
  await shot('t08_back');
  console.log(logs.filter(l => l.includes('BO_PERF')).slice(-2).join('\n'));
  console.log(logs.filter(l => l.includes('rror')).join('\n'));
  await browser.close();
})();
