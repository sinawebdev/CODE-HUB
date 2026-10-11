// End-to-end smoke test: real frontend + real FastAPI backend + PostgreSQL, driven in headless Edge.
// Usage: node e2e.js <baseUrl> <serverLogPath> <adminEmail> <adminPassword> <screenshotDir>
const fs = require('fs');
const path = require('path');
const { chromium } = require("C:/Users/HPLAPT~1/AppData/Local/Temp/claude/c--Users-HP-LAPTOP-Downloads-koforlink/696e98c8-2ba6-4753-9bcc-7e024a0265e0/scratchpad/tools/node/node_modules/playwright-core");

const [BASE, LOG, ADMIN_EMAIL, ADMIN_PASSWORD, SHOTS] = process.argv.slice(2);
const API = BASE + '/api/v1';
const PNG = Buffer.from('89504e470d0a1a0a0000000d4948445200000001000000010806000000' +
  '1f15c4890000000d49444154789c6360f8cfc0f01f0005000201e2e3a5a10000000049454e44ae426082', 'hex');
const PDF = Buffer.from('%PDF-1.4\n%e2e test cv\n' + '0'.repeat(64));
const results = [];
const consoleErrors = [];
const badResponses = [];

function codeFromLog(email) {
  const log=fs.readFileSync(LOG);
  const text=log.subarray(0,2).equals(Buffer.from([0xff,0xfe]))
    ? log.subarray(2).toString('utf16le') : log.toString('utf8');
  const start=text.lastIndexOf('to='+email+' ');
  const block=text.slice(start,start+600);
  const match=block.match(/code is (\d{6})/);
  if(start<0 || !match)throw new Error('No code in server log for '+email);
  return match[1];
}
async function api(method, url, token, body) {
  const res = await fetch(API + url, {
    method, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`${method} ${url} -> ${res.status} ${JSON.stringify(json)}`);
  return json.data;
}
async function step(name, fn) {
  const started = Date.now();
  try {
    await fn();
    results.push({ name, ok: true, ms: Date.now() - started });
    console.log('  ok  ', name);
  } catch (e) {
    results.push({ name, ok: false, error: e.message.split('\n')[0] });
    console.log('  FAIL', name, '-', e.message.split('\n')[0]);
    if (global.page) await global.page.screenshot({ path: path.join(SHOTS, name.replace(/\W+/g, '_') + '.png'), fullPage: true }).catch(() => {});
  }
}
const toastText = async page => (await page.locator('#toasts .toast').last().textContent({ timeout: 8000 })).trim();
async function goto(page, hash) { await page.evaluate(h => { location.hash = h; }, hash); await page.waitForTimeout(400); }

(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const context = await browser.newContext({ viewport: { width: 1360, height: 900 } });
  const page = await context.newPage();
  global.page = page;
  page.setDefaultTimeout(10000);
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => consoleErrors.push('pageerror: ' + e.message));
  page.on('response', r => { if (r.url().includes('/api/v1/') && r.status() >= 500) badResponses.push(r.status() + ' ' + r.url()); });

  const stamp = Date.now().toString(36);
  const me = { first: 'Esi', last: 'Tester', email: `esi.${stamp}@example.com`, password: 'e2e-password-1' };
  let ama, amaToken;

  await step('landing page renders', async () => {
    await page.goto(BASE + '/', { waitUntil: 'load' });
    await page.locator('#landing').waitFor({ state: 'visible', timeout: 15000 });
    if (await page.locator('#bootScreen').count()) throw new Error('boot screen still present');
  });

  await step('register a new account', async () => {
    await page.locator('#landing a[href="#/register"]').first().click();
    const f = page.locator('#regForm');
    await f.waitFor();
    await f.locator('[name=firstName]').fill(me.first);
    await f.locator('[name=lastName]').fill(me.last);
    await f.locator('[name=email]').fill(me.email);
    await f.locator('[name=professionalTitle]').fill('QA Engineer');
    await f.locator('[name=role]').selectOption('Employer');
    await f.locator('[name=password]').fill(me.password);
    await f.locator('[name=confirmPassword]').fill(me.password);
    await page.locator('#regBtn').click();
    await page.locator('#otpWrap .otp-input').first().waitFor({ timeout: 15000 });
  });

  await step('wrong code is rejected, correct code verifies email', async () => {
    const code = codeFromLog(me.email);
    const wrong = code === '000000' ? '111111' : '000000';
    const inputs = page.locator('#otpWrap .otp-input');
    for (let i = 0; i < 6; i++) await inputs.nth(i).fill(wrong[i]);
    await page.locator('#verifyBtn').click();
    await page.locator('#otpError:not(.hidden)').waitFor({ timeout: 8000 });
    for (let i = 0; i < 6; i++) await inputs.nth(i).fill(code[i]);
    await page.locator('#verifyBtn').click();
    await page.locator('#composeTrigger').waitFor({ timeout: 15000 });
  });

  await step('home shows stories bar, composer and seeded feed', async () => {
    await page.locator('#storiesScroll .story-item').first().waitFor({ timeout: 10000 });
    await page.locator('#feed article.post').first().waitFor({ timeout: 10000 });
    const names = await page.locator('.sidebar .user-chip-name').textContent();
    if (!names.includes(`${me.first} ${me.last}`)) throw new Error('sidebar name wrong: ' + names);
  });

  await step('composer card buttons do not double-open the composer', async () => {
    await page.locator('#composeTrigger .composer-tools [data-new-post]').click();
    await page.waitForTimeout(400);
    const modals = await page.locator('#modalRoot .overlay').count();
    if (modals !== 1) throw new Error('expected 1 composer modal, got ' + modals);
  });

  await step('create a post with an image', async () => {
    await page.locator('#composerText').fill('Hello from the E2E test ' + stamp);
    await page.locator('#composerFile').setInputFiles({ name: 'pixel.png', mimeType: 'image/png', buffer: PNG });
    await page.locator('#composerMedia img').waitFor({ timeout: 10000 });
    await page.locator('#composerPost').click();
    await page.locator(`#feed article.post:has-text("${stamp}") .post-media img`).waitFor({ timeout: 10000 });
    const src = await page.locator(`#feed article.post:has-text("${stamp}") .post-media img`).getAttribute('src');
    const img = await page.request.get(new URL(src, BASE).toString());
    if (img.status() !== 200) throw new Error('uploaded image not served: ' + img.status());
  });

  await step('like and comment on my post', async () => {
    const post = page.locator(`#feed article.post:has-text("${stamp}")`).first();
    await post.locator('[data-like]').click();
    await post.locator('.post-stats:has-text("1 like")').waitFor({ timeout: 8000 });
    await post.locator('[data-comment-toggle]').click();
    await post.locator('[data-comment-input]').fill('First comment!');
    await post.locator('[data-comment-submit]').click();
    await post.locator('.comment:has-text("First comment!")').waitFor({ timeout: 8000 });
  });

  await step('edit my profile', async () => {
    await goto(page, '#/profile');
    await page.locator('#editProfileBtn').click();
    await page.locator('#epHeadline').fill('Breaking things on purpose');
    await page.locator('#epSave').click();
    await page.locator('#main :text("Breaking things on purpose")').first().waitFor({ timeout: 10000 });
  });

  await step('connect with a demo member who accepts', async () => {
    const login = await api('POST', '/auth/login', null, { email: 'ama.mensah@demo.koforlink', password: 'Demo@1234' });
    amaToken = login.accessToken; ama = login.user;
    await goto(page, '#/user/' + ama.UserID);
    await page.locator('#connBtn').click();
    await page.locator('#connBtn:has-text("Pending")').waitFor({ timeout: 8000 });
    const reqs = await api('GET', '/network/requests', amaToken);
    const mine = reqs.incoming.find(r => r.name.includes(me.first));
    if (!mine) throw new Error('Ama did not receive the request');
    await api('POST', `/network/connections/${mine.connectionId}/respond`, amaToken, { action: 'accept' });
  });

  await step('notifications show the acceptance', async () => {
    await goto(page, '#/notifications');
    await page.locator('#notifList .notif:has-text("Connection accepted")').waitFor({ timeout: 8000 });
  });

  await step('message the new connection', async () => {
    await goto(page, '#/messages');
    await page.locator('#newChatBtn').click();
    await page.locator('[data-new-chat]').first().click();
    await page.locator('#chatInput').waitFor({ timeout: 10000 });
    await page.locator('#chatInput').fill('Hi Ama, thanks for connecting!');
    await page.locator('#chatSendBtn').click();
    await page.locator('#chatScroll .msg.mine:has-text("thanks for connecting")').waitFor({ timeout: 8000 });
    const convs = await api('GET', '/messaging/conversations', amaToken);
    if (!convs.some(c => c.unread > 0)) throw new Error('Ama has no unread message');
  });

  await step('apply to a seeded job with a CV', async () => {
    await goto(page, '#/jobs');
    await page.locator('#jobsList .job-card').first().click();
    await page.locator('#applyBtn').click();
    await page.locator('#applyLetter').fill('I would love to join.');
    await page.locator('#applyCV').setInputFiles({ name: 'cv.pdf', mimeType: 'application/pdf', buffer: PDF });
    await page.waitForTimeout(1500);
    await page.locator('#applySubmit').click();
    await page.locator('#main button:has-text("Applied")').waitFor({ timeout: 10000 });
  });

  await step('create a company and add a workplace', async () => {
    await goto(page, '#/companies');
    await page.locator('#createCompanyBtn').click();
    await page.locator('#cfName').fill('E2E Widgets ' + stamp);
    await page.locator('#cfSubmit').click();
    await page.locator(`#main h1:has-text("E2E Widgets ${stamp}")`).waitFor({ timeout: 10000 });
    await page.locator('#addLocationBtn').click();
    await page.locator('#lfName').fill('Main Workshop');
    await page.locator('#lfSubmit').click();
    await page.locator('[data-co-tab="locations"]').click();
    await page.locator('.loc-card:has-text("Main Workshop")').waitFor({ timeout: 10000 });
  });

  await step('create an event and attend it', async () => {
    await goto(page, '#/events');
    await page.locator('#newEventBtn').click();
    await page.locator('#evTitle').fill('E2E Meetup ' + stamp);
    await page.locator('#evDate').fill('2099-03-01');
    await page.locator('#evSubmit').click();
    const card = page.locator(`.card:has-text("E2E Meetup ${stamp}")`);
    await card.waitFor({ timeout: 10000 });
    await card.locator('[data-attend]').click();
    await page.locator(`.card:has-text("E2E Meetup ${stamp}"):has-text("1 attending")`).waitFor({ timeout: 10000 });
  });

  await step('search finds people, jobs and posts', async () => {
    await goto(page, '#/search');
    await page.locator('#globalSearch').fill('Eastern');
    await page.locator('#searchResults h3').first().waitFor({ timeout: 10000 });
  });

  await step('sign out and sign in as admin', async () => {
    await page.locator('#logoutBtn').click();
    await page.locator('#loginForm').waitFor({ timeout: 15000 });
    await page.locator('#loginForm [name=email]').fill(ADMIN_EMAIL);
    await page.locator('#loginForm [name=password]').fill(ADMIN_PASSWORD);
    await page.locator('#loginBtn').click();
    await page.locator('.sidebar a[href="#/admin"]').waitFor({ timeout: 15000 });
  });

  await step('admin centre: stats, user list, manage modal pre-selects current values', async () => {
    await goto(page, '#/admin');
    await page.locator('#adminStats .stat-card .stat-value').first().waitFor({ timeout: 10000 });
    await page.locator('[data-admin-tab="users"]').click();
    const row = page.locator(`#adminListBody tr:has-text("${me.email}")`);
    await row.locator('[data-admin-user]').click();
    const role = await page.locator('#auRole').inputValue();
    const status = await page.locator('#auStatus').inputValue();
    if (role !== 'Employer' || status !== 'Active') throw new Error(`modal shows ${role}/${status}, expected Employer/Active`);
    await page.locator('#modalRoot [data-close]').first().click();
  });

  await step('forgot password: code flow', async () => {
    await page.locator('#logoutBtn').click();
    await page.locator('#loginForm').waitFor({ timeout: 15000 });
    await page.locator('#forgotLink').click();
    await page.locator('#resetEmail').fill(me.email);
    await page.locator('#resetBtn').click();
    await page.waitForTimeout(1500);
    const code = codeFromLog(me.email);
    if (!code) throw new Error('no reset code in log');
    const codeInput = page.locator('#modalRoot input[inputmode="numeric"], #modalRoot #resetCode').first();
    await codeInput.fill(code);
    await page.locator('#modalRoot input[type="password"]').first().fill('reset-password-2');
    await page.locator('#modalRoot .modal-foot .btn-primary').click();
    await page.waitForTimeout(1500);
    await api('POST', '/auth/login', null, { email: me.email, password: 'reset-password-2' });
  });

  await context.close();
  await browser.close();
  fs.writeFileSync(path.join(SHOTS,'..','e2e-results.json'),JSON.stringify({results,consoleErrors,badResponses},null,2));
  const failed = results.filter(r => !r.ok);
  console.log(`\n${results.length - failed.length}/${results.length} steps passed`);
  console.log('console errors:', consoleErrors.length ? '\n  ' + [...new Set(consoleErrors)].join('\n  ') : 'none');
  console.log('5xx API responses:', badResponses.length ? '\n  ' + badResponses.join('\n  ') : 'none');
  process.exit(failed.length || badResponses.length ? 1 : 0);
})().catch(e => { console.error('E2E crashed:', e); process.exit(2); });
