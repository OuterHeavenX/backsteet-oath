// Browser test for the exported web build over HTTP (no special headers, like itch.io).
// Usage: node game_test.js <url> <outdir> [mobile]
const { chromium, devices } = require('playwright');
(async () => {
  const url = process.argv[2] || 'http://127.0.0.1:8765/web/index.html?bo_debug=1';
  const out = process.argv[3] || '.';
  const mobile = process.argv[4] === 'mobile';
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const ctx = mobile
    ? await browser.newContext({ ...devices['Pixel 7 landscape'], hasTouch: true })
    : await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await ctx.newPage();
  const logs = [];
  page.on('console', m => logs.push(m.type() + ': ' + m.text()));
  page.on('pageerror', e => logs.push('pageerror: ' + e.message));
  const wait = ms => page.waitForTimeout(ms);
  const key = async (k, hold = 60) => { await page.keyboard.down(k); await wait(hold); await page.keyboard.up(k); };
  const t0 = Date.now();
  await page.goto(url);
  while (Date.now() - t0 < 60000 && !logs.some(l => l.includes('Godot Engine'))) await wait(250);
  await wait(4000);
  console.log('boot_ms', Date.now() - t0);
  await page.screenshot({ path: out + '/web_01_title.png' });
  if (mobile) {
    await page.touchscreen.tap(400, 200); await wait(1500);
    await page.screenshot({ path: out + '/web_m02_menu.png' });
  } else {
    await key('Enter'); await wait(1500);
    await page.screenshot({ path: out + '/web_02_menu.png' });
    await key('Enter'); await wait(1200);            // New Game (first button on a fresh profile)
    await page.screenshot({ path: out + '/web_03_slots.png' });
    await key('Enter'); await wait(7000);            // slot 1 -> world
    await page.screenshot({ path: out + '/web_04_intro.png' });
    await key('Escape'); await wait(2500);           // skip intro dialogue
    await page.keyboard.down('d'); await wait(900); await page.keyboard.up('d');
    for (let i = 0; i < 12; i++) { await key('j', 40); await wait(150); }
    await page.screenshot({ path: out + '/web_05_fight.png' });
    for (let i = 0; i < 20; i++) { await key(i % 4 == 3 ? 'k' : 'j', 40); await wait(180); }
    await wait(6000);
    await page.screenshot({ path: out + '/web_06_after.png' });
    await key('Tab'); await wait(800);
    await page.screenshot({ path: out + '/web_07_status.png' });
    await key('Escape'); await wait(500);
    // reload: save must persist (Continue appears on the title)
    await page.reload();
    const t1 = Date.now();
    while (Date.now() - t1 < 60000 && logs.filter(l => l.includes('Godot Engine')).length < 2) await wait(250);
    await wait(4000);
    await key('Enter'); await wait(1500);
    await page.screenshot({ path: out + '/web_08_reload_menu.png' });
  }
  console.log(logs.filter(l => !l.includes('GPU stall') && !l.includes('WebGL: INVALID')).join('\n'));
  await browser.close();
})();
