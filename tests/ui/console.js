const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 820 } });
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  await page.goto('http://localhost:8790/', { waitUntil: 'networkidle' });
  const mode = await page.evaluate(() => document.body.className);
  const hidden = await page.evaluate(() => getComputedStyle(document.querySelector('.left')).display + '/' + getComputedStyle(document.querySelector('.right')).display + '/' + getComputedStyle(document.getElementById('entBtn')).display);
  const who = await page.textContent('#who');
  const how = await page.evaluate(() => document.querySelectorAll('.how div').length);
  console.log('mode:', mode, '| left/right/enterprise display:', hidden, '| how steps:', how);
  console.log('who banner:', who.trim().slice(0, 120));
  await page.screenshot({ path: '/tmp/simple_empty.png' });
  // ask the textbook question in simple mode
  await page.fill('#q', "I'm 35, no debt, $300k cash, 12 months of expenses set aside separately, stable salary. Should I put $50k into a diversified global index fund and hold it for 10+ years?");
  await page.press('#q', 'Enter');
  await page.waitForSelector('.msg.sub .next', { timeout: 20000 });
  const card = await page.textContent('.msg.sub:last-of-type');
  console.log('answer card:', card.replace(/\s+/g, ' ').slice(0, 260));
  const nextBtns = await page.$$eval('.next button', bs => bs.map(b => b.textContent));
  console.log('next strip buttons:', nextBtns);
  await page.screenshot({ path: '/tmp/simple_answer.png' });
  // close the loop from the strip
  await page.click('.next button.go');
  await page.waitForTimeout(800);
  console.log('after follow:', (await page.textContent('.next')).trim().slice(0, 90));
  // a question
  await page.fill('#q', 'Binance got hacked today. Is it something that I should be worried about?');
  await page.press('#q', 'Enter');
  await page.waitForFunction(() => document.querySelectorAll('.msg.sub').length >= 2 && document.querySelectorAll('.msg.answer').length >= 1, null, { timeout: 20000 });
  console.log('question card class:', await page.$eval('.msg.answer', e => e.className), '|', (await page.$$eval('.msg.answer .next button', bs => bs.map(b => b.textContent))).join(', '));
  // switch to advanced
  await page.click('#modeSw button[data-m="advanced"]');
  await page.waitForTimeout(300);
  const adv = await page.evaluate(() => document.body.className + ' | left:' + getComputedStyle(document.querySelector('.left')).display + ' right:' + getComputedStyle(document.querySelector('.right')).display);
  console.log('advanced:', adv, '| stored:', await page.evaluate(() => localStorage.getItem('sub-mode')));
  await page.screenshot({ path: '/tmp/advanced.png' });
  // invite flow: redeem -> intake overlay opens
  const inv = await page.evaluate(async () => (await (await fetch('/v1/invites', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ tissue: 'wealth', label: 'ui', max_uses: 2, days: 1 }) })).json()).code);
  await page.goto('http://localhost:8790/?invite=' + inv, { waitUntil: 'networkidle' });
  await page.fill('#w-name', 'Seun');
  await page.click('#wf button[type=submit]');
  await page.waitForSelector('#gf', { timeout: 8000 });
  console.log('intake overlay after invite:', await page.$eval('#ovBody h2', e => e.textContent), '| banner:', (await page.textContent('#who')).trim().slice(0, 80));
  await page.screenshot({ path: '/tmp/invite_intake.png' });
  await page.fill('#g-nw', '400000');
  const rows = await page.$$('#g-holds .hold');
  await (await rows[0].$$('input'))[0].fill('Global index fund'); await (await rows[0].$$('input'))[1].fill('150000');
  await (await rows[2].$$('input'))[0].fill('Cash'); await (await rows[2].$$('input'))[1].fill('250000');
  await page.click('#gf button[type=submit]');
  await page.waitForTimeout(1200);
  console.log('after intake banner:', (await page.textContent('#who')).trim().slice(0, 100));
  console.log('mic button visible:', await page.$eval('#micBtn', e => !e.hidden), '| mic status el:', !!(await page.$('#micStat')));
  console.log('ERRORS:', errors.length ? errors : 'none');
  await browser.close();
})().catch(e => { console.error('TEST FAILED', e); process.exit(1); });
