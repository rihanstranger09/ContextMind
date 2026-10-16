/* Capture silent, real-browser native FalkorDB footage for editing/narration.
 * Refuses to record a JSON preview or an unhealthy database.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const packagedChromium = require('@sparticuz/chromium').default;
const base = new URL(process.env.BASE_URL || 'http://127.0.0.1:8000');
const output = path.resolve(__dirname, '../../.runtime/showcase');
const hold = ms => new Promise(resolve => setTimeout(resolve, ms));

(async () => {
  fs.mkdirSync(output, { recursive: true });
  if (process.env.CHROMIUM_BUNDLED_LIBS === '1') {
    const module = require('@sparticuz/chromium');
    const libs = await module.inflate(path.resolve(path.dirname(require.resolve('@sparticuz/chromium')), '../bin/al2023.tar.br'));
    module.setupLambdaEnvironment(path.join(libs, 'lib'));
  }
  const browser = await chromium.launch({
    executablePath: process.env.BROWSER_EXECUTABLE || await packagedChromium.executablePath(),
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
    headless: true,
  });
  try {
    const checkContext = await browser.newContext();
    const health = await checkContext.request.get(new URL('/api/health?workspace=falkordb', base).href);
    const proof = await checkContext.request.get(new URL('/api/graph/showcase?workspace=falkordb', base).href);
    assert.equal(health.status(), 200, 'Public workspace must be healthy');
    assert.equal(proof.status(), 200, 'Graph proof must succeed');
    assert.equal((await health.json()).graph_mode, 'falkordb', 'Refusing to film JSON demo mode');
    const evidence = await proof.json();
    assert.equal(evidence.native_cypher_executed, true, 'Refusing to film a non-native proof');
    assert(evidence.paths.length > 0, 'No graph paths to film');
    await checkContext.close();

    const context = await browser.newContext({viewport: {width: 1440, height: 900}, recordVideo: {dir: output, size: {width: 1440, height: 900}}});
    const page = await context.newPage();
    page.setDefaultTimeout(20000);
    await page.goto(new URL('/demo.html?workspace=falkordb', base).href, {waitUntil: 'networkidle'});
    await page.waitForFunction(() => document.querySelector('#proof-readiness')?.textContent.includes('READY FOR NATIVE RECORDING'));
    await hold(7000);
    await page.goto(new URL('/dashboard?workspace=falkordb', base).href, {waitUntil: 'networkidle'});
    await page.waitForFunction(() => document.querySelector('#backend')?.textContent.includes('FalkorDB storage'));
    await hold(8000);
    await page.locator('#graph-proof').click();
    await page.locator('#modal .proof-state.native').waitFor();
    await hold(22000);
    await page.locator('#close-modal').click();

    async function ask(question) {
      const reply = page.waitForResponse(r => new URL(r.url()).pathname === '/api/chat' && r.status() === 200);
      await page.locator('#question').fill(question);
      await page.locator('#send').click();
      await reply;
      await page.locator('.answer-title').waitFor();
    }
    await ask('How do I use FalkorDB with LangChain?');
    await hold(17000);
    await page.locator('.source-card').first().click();
    await page.locator('#modal[open]').waitFor();
    await hold(8000);
    await page.locator('#close-modal').click();
    await page.locator('#conversation details:not(.tool-steps) summary').click();
    await hold(10000);
    await page.locator('#new-chat').click();
    await ask('What is FalkorDB annual revenue?');
    assert((await page.locator('.answer-title').innerText()).includes('not in the collected snapshot'));
    await hold(21000);
    const video = page.video();
    await context.close();
    const file = path.resolve(__dirname, '../../deliverables/native-falkordb-showcase.webm');
    fs.mkdirSync(path.dirname(file), {recursive: true});
    fs.renameSync(await video.path(), file);
    console.log(`Silent native recording: ${file}\nAdd narration and captions before submission; see docs/presenter-runbook.md.`);
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error); process.exitCode = 1});
