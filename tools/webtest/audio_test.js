// Measures real Web Audio output of the web export (taps the graph before AudioDestinationNode).
// Usage: node tools/webtest/audio_test.js http://127.0.0.1:8765/web/index.html   -> rms > 0 after the first key press means sound is playing.
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2];
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await ctx.newPage();
  await page.addInitScript(() => {
    window.__ctxs = [];
    const conn = AudioNode.prototype.connect;
    const Orig = window.AudioContext;
    window.AudioContext = function (...a) { const c = new Orig(...a); window.__ctxs.push(c); c.__an = c.createAnalyser(); c.__an.fftSize = 2048; const g = c.createGain(); g.gain.value = 0; conn.call(c.__an, g); conn.call(g, c.destination); return c; };
    window.AudioContext.prototype = Orig.prototype;
    AudioNode.prototype.connect = function (dst, ...r) {
      const res = conn.call(this, dst, ...r);
      try { (window.__nodes = window.__nodes || []).push(this.constructor.name + '->' + (dst && dst.constructor ? dst.constructor.name : '?')); } catch (e) {}
      try { if (dst instanceof AudioDestinationNode && this.context.__an) conn.call(this, this.context.__an); } catch (e) {}
      return res;
    };
    window.__starts = [];
    const st = AudioBufferSourceNode.prototype.start;
    AudioBufferSourceNode.prototype.start = function (...a) { try { window.__starts.push({dur: this.buffer ? +this.buffer.duration.toFixed(2) : -1, ch: this.buffer ? this.buffer.numberOfChannels : 0, loop: this.loop}); } catch (e) {} return st.apply(this, a); };
    window.__gains = [];
    const cg = BaseAudioContext.prototype.createGain;
    BaseAudioContext.prototype.createGain = function () { const g = cg.call(this); window.__gains.push(g); return g; };
    window.__rms = () => window.__ctxs.map(c => { const b = new Float32Array(c.__an.fftSize); c.__an.getFloatTimeDomainData(b); let s = 0; for (const v of b) s += v * v; return { state: c.state, rate: c.sampleRate, rms: Math.sqrt(s / b.length) }; });
  });
  page.on('console', m => { const t = m.text(); if (/audio|Audio|error|ERROR/i.test(t)) console.log('console:', t.slice(0, 160)); });
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForTimeout(7000);
  console.log('before input', JSON.stringify(await page.evaluate(() => window.__rms())));
  await page.mouse.click(640, 360);
  await page.keyboard.press('Enter');
  for (let i = 0; i < 6; i++) { await page.waitForTimeout(800); console.log('after input', i, JSON.stringify(await page.evaluate(() => window.__rms()))); }
  await page.keyboard.press('ArrowDown'); await page.waitForTimeout(300);
  await page.keyboard.press('ArrowUp'); await page.waitForTimeout(300);
  console.log('after ui sfx', JSON.stringify(await page.evaluate(() => window.__rms())));
  console.log('starts', await page.evaluate(() => JSON.stringify(window.__starts)));
  console.log('gains', await page.evaluate(() => JSON.stringify(window.__gains.map(g => +g.gain.value.toFixed(4)))));
  console.log('nodes_n', await page.evaluate(() => JSON.stringify(window.__nodes || [])));
  await page.evaluate(() => { const c = window.__ctxs[0]; const o = c.createOscillator(); o.connect(c.destination); o.start(); window.__osc = o; });
  await page.waitForTimeout(500);
  console.log('with test tone', JSON.stringify(await page.evaluate(() => window.__rms())));
  await browser.close();
})();
