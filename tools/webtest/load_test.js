// Cold-load measurement for the exported web build: what is transferred, how long until the title screen, and how
// long from confirming New Game until the player has control. Headless Chromium only (software WebGL).
//
// Usage: node tools/webtest/load_test.js <url> [profile] [out.json]
//   url      e.g. http://127.0.0.1:8765/index.html   (the script adds ?bo_debug=1 for the timing markers)
//   profile  unthrottled (default) | cable-50mbit | dsl-10mbit | fast-4g   (applied with CDP
//            Network.emulateNetworkConditions; the numbers are in PROFILES below)
// Serve the build first: python3 tools/webtest/serve.py build/web 8765 [--gzip]
//
// What is measured (wall clock in the test process, milliseconds from the start of navigation):
//   engine_start_ms   first "Godot Engine" console line (wasm compiled and started)
//   title_ms          BO_MARK title_ready: the title screen has drawn its first frames
//   new_game_control_ms   from the key press that confirms save slot 1 until BO_MARK control (the intro dialogue is
//                     skipped as soon as it appears; accuracy about +/-0.6 s because of the key-press polling)
//   warm_title_ms     the same page reloaded in the same browser context (HTTP cache warm)
// Transfer sizes come from CDP Network.loadingFinished (encodedDataLength, bytes on the wire incl. headers) and
// Network.dataReceived (decoded bytes).
const { chromium } = require('playwright');
const fs = require('fs');

const PROFILES = {
  'unthrottled': null,
  'cable-50mbit': { down_mbit: 50, up_mbit: 10, latency_ms: 20 },
  'dsl-10mbit': { down_mbit: 10, up_mbit: 1, latency_ms: 40 },
  'fast-4g': { down_mbit: 9, up_mbit: 1.5, latency_ms: 60 },
};

(async () => {
  let url = process.argv[2];
  const profileName = process.argv[3] || 'unthrottled';
  const outFile = process.argv[4] || '';
  if (!url || !(profileName in PROFILES)) {
    console.error('usage: node load_test.js <url> [' + Object.keys(PROFILES).join('|') + '] [out.json]');
    process.exit(2);
  }
  if (!url.includes('bo_debug')) url += (url.includes('?') ? '&' : '?') + 'bo_debug=1';
  const profile = PROFILES[profileName];
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });   // fresh context: empty cache
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  if (profile) {
    await cdp.send('Network.emulateNetworkConditions', {
      offline: false, latency: profile.latency_ms,
      downloadThroughput: profile.down_mbit * 1e6 / 8, uploadThroughput: profile.up_mbit * 1e6 / 8,
    });
  }
  let reqs = new Map();
  let phase = 'cold';
  cdp.on('Network.requestWillBeSent', e => reqs.set(e.requestId, { url: e.request.url, phase, decoded: 0, encoded: 0, status: 0, fromCache: false, encoding: '' }));
  cdp.on('Network.responseReceived', e => { const r = reqs.get(e.requestId); if (r) { r.status = e.response.status; r.fromCache = !!e.response.fromDiskCache; r.encoding = (e.response.headers['Content-Encoding'] || e.response.headers['content-encoding'] || ''); r.mime = e.response.mimeType; } });
  cdp.on('Network.dataReceived', e => { const r = reqs.get(e.requestId); if (r) r.decoded += e.dataLength; });
  cdp.on('Network.loadingFinished', e => { const r = reqs.get(e.requestId); if (r) { r.encoded = e.encodedDataLength; r.done = true; } });

  let t0 = 0;
  let marks = {};
  let logs = [];
  page.on('console', m => {
    const t = m.text();
    const now = Date.now() - t0;
    if (t.includes('Godot Engine') && marks.engine_start === undefined) marks.engine_start = now;
    const mm = /BO_MARK (\w+) ms=(\d+)/.exec(t);
    if (mm && marks[mm[1]] === undefined) marks[mm[1]] = now;
    if (/ERROR|error:/i.test(t) && !/GPU stall|WebGL: INVALID/.test(t)) logs.push(t.slice(0, 200));
  });
  page.on('pageerror', e => logs.push('pageerror: ' + e.message));
  const wait = ms => page.waitForTimeout(ms);
  const key = async (k, hold = 60) => { await page.keyboard.down(k); await wait(hold); await page.keyboard.up(k); };
  const until = async (name, timeout) => { const s = Date.now(); while (marks[name] === undefined && Date.now() - s < timeout) await wait(50); return marks[name] !== undefined; };

  // ---- cold load to the title screen
  t0 = Date.now();
  await page.goto(url, { waitUntil: 'commit' });
  const gotTitle = await until('title_ready', 600000);
  await wait(1500);   // let trailing requests finish
  const result = { url, profile: profileName, profile_settings: profile, browser: 'chromium ' + browser.version() + ' headless, WebGL via SwiftShader (software)', viewport: '1280x720' };
  result.engine_start_ms = marks.engine_start;
  result.title_ms = gotTitle ? marks.title_ready : null;
  const files = [...reqs.values()].filter(r => r.phase === 'cold').map(r => ({ file: r.url.split('/').pop().split('?')[0] || '/', status: r.status, transfer_bytes: Math.round(r.encoded), decoded_bytes: r.decoded, content_encoding: r.encoding }));
  result.files = files;
  result.transfer_bytes = files.reduce((a, f) => a + f.transfer_bytes, 0);
  result.decoded_bytes = files.reduce((a, f) => a + f.decoded_bytes, 0);

  // ---- new game: title -> main menu -> New Game -> slot 1 -> world; skip the intro dialogue when it appears
  if (gotTitle) {
    await key('Enter'); await wait(1500);
    await key('Enter'); await wait(1200);
    const base = { ...marks };
    delete marks.world_ready; delete marks.control; delete marks.dialogue;
    const tNew = Date.now() - t0;
    await key('Enter');
    const gotWorld = await until('world_ready', 120000);
    result.new_game_world_ready_ms = gotWorld ? marks.world_ready - tNew : null;
    if (gotWorld) {
      await until('dialogue', 30000);
      const s = Date.now();
      while (marks.control === undefined && Date.now() - s < 60000) { await key('Escape', 40); await wait(560); }
      result.new_game_control_ms = marks.control !== undefined ? marks.control - tNew : null;
    }
    await wait(500);
  }

  // ---- warm reload in the same context: how much is fetched again, how long to the title
  phase = 'warm';
  marks = {};
  t0 = Date.now();
  await page.reload({ waitUntil: 'commit' });
  const gotWarm = await until('title_ready', 600000);
  await wait(1000);
  const warm = [...reqs.values()].filter(r => r.phase === 'warm');
  result.warm_title_ms = gotWarm ? marks.title_ready : null;
  result.warm_transfer_bytes = Math.round(warm.reduce((a, r) => a + r.encoded, 0));
  result.warm_statuses = warm.map(r => (r.url.split('/').pop().split('?')[0] || '/') + ':' + r.status + (r.fromCache ? ':cache' : ''));
  result.errors = logs.slice(0, 20);
  await browser.close();

  const mb = b => (b / 1048576).toFixed(2) + ' MiB';
  console.log('profile ' + profileName + (profile ? ' (' + profile.down_mbit + ' Mbit/s down, ' + profile.up_mbit + ' Mbit/s up, ' + profile.latency_ms + ' ms latency)' : '') + '  ' + result.browser);
  for (const f of files) console.log('  ' + f.file.padEnd(28) + String(f.status).padEnd(5) + mb(f.transfer_bytes).padStart(12) + ' on the wire' + mb(f.decoded_bytes).padStart(12) + ' decoded  ' + (f.content_encoding || 'identity'));
  console.log('  total transfer ' + mb(result.transfer_bytes) + ', decoded ' + mb(result.decoded_bytes));
  console.log('  engine start ' + result.engine_start_ms + ' ms, title screen ' + result.title_ms + ' ms');
  console.log('  new game: world ready ' + result.new_game_world_ready_ms + ' ms, player control ' + result.new_game_control_ms + ' ms after confirming the slot');
  console.log('  warm reload: title ' + result.warm_title_ms + ' ms, transfer ' + mb(result.warm_transfer_bytes) + '  [' + result.warm_statuses.join(' ') + ']');
  if (result.errors.length) console.log('  console errors:\n    ' + result.errors.join('\n    '));
  if (outFile) fs.writeFileSync(outFile, JSON.stringify(result, null, 1));
})();
