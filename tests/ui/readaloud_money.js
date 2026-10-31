const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch(); const page = await browser.newPage();
  await page.addInitScript(() => {
    window.__sp = [];
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: { getVoices: () => [{ name: 'Samantha', lang: 'en-US', localService: true }], cancel: () => {}, speak: (u) => window.__sp.push(u.text) } });
    window.SpeechSynthesisUtterance = function(t){ this.text = t; };
    localStorage.setItem('sub-speak', '1');
  });
  await page.goto('http://localhost:8790/', { waitUntil: 'networkidle' });
  await page.fill('#q', 'Should I borrow $150k against the flat to buy more MOONX?');
  await page.press('#q', 'Enter');
  await page.waitForSelector('.msg.sub .next', { timeout: 20000 }); await page.waitForTimeout(300);
  const sp = await page.evaluate(() => window.__sp);
  console.log('spoken headline:', sp[0]); console.log('money sentences:', sp.filter(t => /dollars/.test(t)).slice(0, 3));
  console.log('card intact:', (await page.textContent('.msg.sub')).includes('Do not'));
  await browser.close();
})();
