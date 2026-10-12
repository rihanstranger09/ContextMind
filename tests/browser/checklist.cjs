/* Real Chromium smoke tests against an already running app. No browser security bypass. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const packagedChromium = require('@sparticuz/chromium').default;

const base = new URL(process.env.BASE_URL || 'http://127.0.0.1:8000');
const output = path.resolve(__dirname, '../../.runtime/browser-results');
const report = {testedAt: new Date().toISOString(), base: base.origin, browser: 'Chromium', storage: null, checks: [], consoleErrors: [], pageErrors: [], failedRequests: [], httpErrors: [], apiRequests: []};
function passed(check, workspace) { report.checks.push({check, workspace, status: 'passed'}); console.log(`PASS ${workspace || 'global'}: ${check}`); }
function url(route) { return new URL(route, base).href; }

(async () => {
  fs.mkdirSync(output, { recursive: true });
  if (process.env.CHROMIUM_BUNDLED_LIBS === '1') {
    const module = require('@sparticuz/chromium');
    const libs = await module.inflate(path.resolve(path.dirname(require.resolve('@sparticuz/chromium')), '../bin/al2023.tar.br'));
    module.setupLambdaEnvironment(path.join(libs, 'lib'));
  }
  const browser = await chromium.launch({
    executablePath: process.env.BROWSER_EXECUTABLE || await packagedChromium.executablePath(),
    // Do not disable CORS/web security: detecting blocked API calls is part of this checklist.
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
    headless: true,
  });
  report.browserVersion = browser.version();
  const context = await browser.newContext({ viewport: {width: 1440, height: 1000} });
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  page.on('console', message => { if (message.type() === 'error') report.consoleErrors.push(message.text()); });
  page.on('pageerror', error => report.pageErrors.push(error.message));
  page.on('requestfailed', request => report.failedRequests.push({url: request.url(), error: request.failure()?.errorText}));
  page.on('response', response => { if (response.status() >= 400) report.httpErrors.push({url: response.url(), status: response.status()}); });
  page.on('request', request => { if (new URL(request.url()).pathname.startsWith('/api/')) report.apiRequests.push(request.url()); });

  async function ready(workspace) {
    await page.waitForFunction(() => document.querySelector('#entity-count')?.textContent !== '—');
    await page.locator('#graph .graph-node').first().waitFor({state: 'visible'});
    await page.waitForFunction(() => !document.querySelector('#backend').textContent.includes('Connecting'));
    assert.equal(await page.locator('#workspace-select').inputValue(), workspace);
    assert(await page.locator('#graph line').count() > 0, 'Graph must have edges, not only nodes');
    assert.equal(await page.locator('dialog[open]').count(), 0, 'Unexpected startup error dialog');
  }
  async function answer(workspace, trigger, expectedQuestion, expectEvidence = true) {
    const responsePromise = page.waitForResponse(response => new URL(response.url()).pathname === '/api/chat' && response.request().method() === 'POST');
    await trigger();
    const response = await responsePromise;
    assert.equal(response.status(), 200);
    assert.equal(response.request().postDataJSON().question, expectedQuestion);
    assert.equal(new URL(response.url()).searchParams.get('workspace'), workspace);
    await page.locator('#conversation .answer-title').waitFor({state: 'visible'});
    await page.waitForFunction(() => !document.querySelector('#send').disabled);
    if (expectEvidence) assert(await page.locator('#conversation .fact').count() > 0);
    else {
      assert.equal(await page.locator('#conversation .fact').count(), 0);
      assert((await page.locator('#conversation .answer-title').innerText()).includes('not in the collected snapshot'));
    }
    assert.equal(await page.locator('#conversation .error').count(), 0);
    return response.json();
  }
  try {
    for (const workspace of ['novapay', 'falkordb']) {
      const health = await context.request.get(url('/api/health?workspace=' + workspace));
      assert.equal(health.status(), 200);
      const info = await health.json(); assert.equal(info.status, 'healthy'); report.storage = info.graph_mode;
      passed('Backend readiness', workspace);
    }
    await page.goto(url('/dashboard?workspace=novapay'), {waitUntil: 'networkidle'});
    await ready('novapay');
    passed('Frontend and graph load', 'novapay');
    // Exercise both the button/modal links and the native header selector.
    await page.locator('#workspace').click();
    await page.locator('#modal a[href="/dashboard?workspace=falkordb"]').click();
    await page.waitForURL('**/dashboard?workspace=falkordb'); await ready('falkordb');
    await page.locator('#workspace').click();
    await page.locator('#modal a[href="/dashboard?workspace=novapay"]').click();
    await page.waitForURL('**/dashboard?workspace=novapay'); await ready('novapay');
    passed('Both workspace button links navigate');

    for (const workspace of ['novapay', 'falkordb']) {
      await page.locator('#workspace-select').selectOption(workspace);
      if (new URL(page.url()).searchParams.get('workspace') !== workspace) await page.waitForURL('**/dashboard?workspace=' + workspace);
      await ready(workspace);
      passed('Header workspace selector', workspace);
      const question = workspace === 'novapay' ? 'Who owns Database Cluster?' : 'How do I use FalkorDB with LangChain?';
      await page.locator('#question').click();
      assert(await page.locator('#question').evaluate(el => el === document.activeElement));
      await page.locator('#question').pressSequentially(question);
      assert.equal(await page.locator('#question').inputValue(), question);
      passed('Input focus and typing', workspace);
      await answer(workspace, () => page.locator('#send').click(), question);
      passed('Send button submits typed query and renders answer', workspace);
      assert(await page.locator('.source-card').count() > 0);
      await page.locator('.source-card').first().click();
      await page.locator('#modal[open]').waitFor({state: 'visible'});
      assert((await page.locator('#modal-content').innerText()).includes('Source ID:'));
      if (workspace === 'falkordb') assert((await page.locator('#modal-content a').first().getAttribute('href')).startsWith('https://github.com/'));
      await page.locator('#close-modal').click();
      await page.locator('#conversation summary').click();
      assert(await page.locator('#conversation details[open] li').count() > 0);
      await page.locator('[data-trace]').first().click();
      assert((await page.locator('#modal-content pre').innerText()).includes('source'));
      await page.locator('#close-modal').click();
      passed('Sources and expandable/clickable graph trace', workspace);
      await page.screenshot({path: path.join(output, workspace + '-desktop.png'), fullPage: true});

      await page.locator('#new-chat').click();
      const count = await page.locator('.suggestions [data-question]').count();
      assert(count > 0);
      for (let i = 0; i < count; i++) {
        const button = page.locator('.suggestions [data-question]').nth(i);
        const text = await button.getAttribute('data-question');
        await answer(workspace, () => button.click(), text);
        await page.locator('#new-chat').click();
      }
      passed(`All ${count} dashboard demo questions clickable`, workspace);
      await page.locator('#question').fill(question);
      await answer(workspace, () => page.locator('#question').press('Enter'), question);
      passed('Enter submits', workspace);

      for (let i = 0; i < 5; i++) {
        await page.goto(url('/demo.html?workspace=' + workspace), {waitUntil: 'networkidle'});
        await page.waitForFunction(() => document.querySelector('#health').textContent.startsWith('Healthy'));
        const demoLink = page.locator('#questions a').nth(i);
        const demoQuestion = await demoLink.innerText();
        await demoLink.click();
        await ready(workspace);
        assert.equal(await page.locator('#question').inputValue(), demoQuestion);
        const expectEvidence = !(workspace === 'falkordb' && i === 4);
        await answer(workspace, () => page.locator('#send').click(), demoQuestion, expectEvidence);
      }
      passed('All 5 demo guide links prefill and submit (including negative control)', workspace);
    }
    // Actual narrow viewport: header switcher, text entry, send and SVG rendering remain usable.
    await page.setViewportSize({width: 390, height: 844});
    await page.locator('#workspace-select').selectOption('novapay');
    await page.waitForURL('**/dashboard?workspace=novapay'); await ready('novapay');
    await page.locator('#question').fill('Who owns Database Cluster?');
    await answer('novapay', () => page.locator('#send').click(), 'Who owns Database Cluster?');
    assert(await page.locator('#graph .graph-node').count() > 0);
    await page.screenshot({path: path.join(output, 'mobile.png'), fullPage: true});
    passed('Mobile viewport switcher, chat and graph');
    await page.waitForLoadState('networkidle');
    assert(report.apiRequests.length > 0);
    assert(report.apiRequests.every(request => new URL(request).origin === base.origin), 'API calls must stay on the page origin');
    passed('Same-origin API requests with browser web security enabled');
    assert.deepEqual(report.failedRequests, [], 'No failed network requests');
    assert.deepEqual(report.httpErrors, [], 'No HTTP 4xx/5xx responses');
    passed('Frontend/API resources return without HTTP errors');
    assert.deepEqual(report.pageErrors, [], 'No uncaught JavaScript errors');
    assert.deepEqual(report.consoleErrors, [], 'No red browser-console messages');
    passed('Browser console and JavaScript error-free');
    report.status = 'passed';
  } catch (error) {
    report.status = 'failed'; report.failure = error.stack;
    await page.screenshot({path: path.join(output, 'failure.png'), fullPage: true}).catch(() => {});
    throw error;
  } finally {
    fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2));
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
