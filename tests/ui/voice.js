const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = []; page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });

  // --- simulate the browser's speech engines before the page loads
  await page.addInitScript(() => {
    window.__sr = { instances: [], spoken: [] };
    class FakeSR {
      constructor(){ this.continuous=false; this.interimResults=false; this.lang=''; window.__sr.instances.push(this); }
      start(){ this.started = true; setTimeout(() => this.onstart && this.onstart(), 10); }
      stop(){ this.stopped = true; setTimeout(() => this.onend && this.onend(), 10); }
      // helpers the test calls
      say(text, final){ const res = [{ 0: { transcript: text }, isFinal: !!final, length: 1 }]; res.length = 1; this.onresult && this.onresult({ results: res }); }
      fail(code){ this.onerror && this.onerror({ error: code }); }
      end(){ this.onend && this.onend(); }
    }
    window.webkitSpeechRecognition = FakeSR; window.SpeechRecognition = FakeSR;
    // fake voices + capture every utterance
    const voices = [
      { name: 'Google US English', lang: 'en-US', localService: false },
      { name: 'Samantha', lang: 'en-US', localService: true },
      { name: 'Microsoft Aria Online (Natural) - English (United States)', lang: 'en-US', localService: false },
      { name: 'Majed', lang: 'ar-SA', localService: true },
    ];
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: { getVoices: () => voices, cancel: () => { window.__sr.cancelled = (window.__sr.cancelled||0)+1; }, speak: (u) => window.__sr.spoken.push({ text: u.text, voice: u.voice && u.voice.name, lang: u.lang, rate: u.rate }), speaking: false } });
    window.SpeechSynthesisUtterance = function(t){ this.text = t; };
    localStorage.setItem('sub-speak', '1');   // read-aloud on
  });

  await page.goto('http://localhost:8790/', { waitUntil: 'networkidle' });
  console.log('mic visible:', await page.$eval('#micBtn', e => !e.hidden), '| speaker visible:', await page.$eval('#spkBtn', e => !e.hidden), '| read-aloud pressed:', await page.$eval('#spkBtn', e => e.getAttribute('aria-pressed')));

  // ---- 1. microphone: tap, speak, pause 6s -> auto-send
  await page.click('#micBtn');
  await page.waitForTimeout(100);
  let st = await page.textContent('#micStat');
  console.log('after tap -> status:', st.trim(), '| continuous:', await page.evaluate(() => window.__sr.instances[0].continuous), '| lang:', await page.evaluate(() => window.__sr.instances[0].lang));
  await page.evaluate(() => window.__sr.instances[0].say('should I move forty thousand', false));
  console.log('interim transcript in box:', await page.inputValue('#q'));
  await page.evaluate(() => window.__sr.instances[0].say('should I move forty thousand into the global equity index fund', true));
  console.log('final transcript in box:', await page.inputValue('#q'));
  await page.waitForTimeout(6500);   // the 6-second silence timer
  await page.waitForSelector('.msg.user', { timeout: 5000 });
  console.log('auto-sent after silence:', (await page.textContent('.msg.user')).trim(), '| box cleared:', (await page.inputValue('#q')) === '');
  await page.waitForSelector('.msg.sub .next', { timeout: 20000 });

  // ---- 2. read-aloud: what was spoken for that answer
  const spoken = await page.evaluate(() => window.__sr.spoken);
  console.log('utterances:', spoken.length, '| voice:', spoken[0] && spoken[0].voice, '| first:', spoken[0] && spoken[0].text, '| rate0:', spoken[0] && spoken[0].rate);
  console.log('money read as:', spoken.map(s => s.text).filter(t => /thousand|million|dollars/.test(t)).slice(0,2));
  console.log('ledger/markdown leaked?', spoken.some(s => /\*\*|Vagus Ledger|_/.test(s.text)));

  // ---- 3. microphone: no-speech error keeps listening, not-allowed stops with a clear message
  await page.click('#micBtn');
  await page.waitForTimeout(50);
  await page.evaluate(() => window.__sr.instances[1].fail('no-speech'));
  console.log('no-speech ->', (await page.textContent('#micStat')).trim());
  await page.evaluate(() => window.__sr.instances[1].end());   // browser ends the session; we restart
  await page.waitForTimeout(50);
  console.log('restarted after end:', await page.evaluate(() => window.__sr.instances[1].started && window.__sr.instances.length === 2), '| still listening:', (await page.textContent('#micStat')).trim().length > 0);
  await page.evaluate(() => window.__sr.instances[1].fail('not-allowed'));
  await page.waitForTimeout(100);
  console.log('not-allowed -> status cleared:', (await page.textContent('#micStat')).trim() === '', '| toast:', (await page.textContent('.toast')).trim().slice(0, 70));

  // ---- 4. tap to stop and send
  await page.click('#micBtn');
  await page.waitForTimeout(50);
  await page.evaluate(() => window.__sr.instances[2].say('Binance got hacked today, should I be worried', true));
  await page.click('#micBtn');     // second tap = stop and send
  await page.waitForFunction(() => document.querySelectorAll('.msg.user').length >= 2, null, { timeout: 5000 });
  console.log('tap-to-send:', (await page.$$eval('.msg.user', es => es.map(e => e.textContent.trim())))[1]);
  await page.waitForFunction(() => document.querySelectorAll('.msg.answer').length >= 1, null, { timeout: 20000 });

  // ---- 5. Arabic goes to an Arabic voice
  await page.evaluate(() => { window.__sr.spoken.length = 0; });
  await page.fill('#q', 'أفكر في وضع ٢٠٠ ألف دولار إضافية في MOONX، فكرة جيدة أليس كذلك؟');
  await page.press('#q', 'Enter');
  await page.waitForFunction(() => document.querySelectorAll('.msg.sub').length >= 3, null, { timeout: 20000 });
  await page.waitForTimeout(300);
  const ar = await page.evaluate(() => window.__sr.spoken);
  console.log('arabic voice:', ar[0] && ar[0].voice, '| lang:', ar[0] && ar[0].lang, '| sample:', ar[0] && ar[0].text.slice(0, 40));

  // ---- 6. speaker toggle off cancels
  await page.click('#spkBtn');
  console.log('toggle off -> pressed:', await page.$eval('#spkBtn', e => e.getAttribute('aria-pressed')), '| cancelled calls:', await page.evaluate(() => window.__sr.cancelled));
  console.log('ERRORS:', errors.length ? errors : 'none');
  await browser.close();
})().catch(e => { console.error('TEST FAILED', e); process.exit(1); });
