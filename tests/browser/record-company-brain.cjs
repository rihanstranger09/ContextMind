/* Guarded native company-brain screen capture. Only fictional data is written.
 * Supply VIDEO_INGEST_TOKEN matching the local server; never show it on screen.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const packagedChromium = require('@sparticuz/chromium').default;
const base = new URL(process.env.BASE_URL || 'http://127.0.0.1:8000');
const output = path.resolve(__dirname, '../../.runtime/company-recording');
const deliverables = path.resolve(__dirname, '../../deliverables');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const route = p => new URL(p, base).href;

(async () => {
  assert(process.env.VIDEO_INGEST_TOKEN, 'Set VIDEO_INGEST_TOKEN for a disposable local instance');
  fs.mkdirSync(output, {recursive:true}); fs.mkdirSync(deliverables, {recursive:true});
  if (process.env.CHROMIUM_BUNDLED_LIBS === '1') {
    const module = require('@sparticuz/chromium');
    const libs = await module.inflate(path.resolve(path.dirname(require.resolve('@sparticuz/chromium')), '../bin/al2023.tar.br'));
    module.setupLambdaEnvironment(path.join(libs, 'lib'));
  }
  const browser = await chromium.launch({executablePath:process.env.BROWSER_EXECUTABLE || await packagedChromium.executablePath(),
    args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader'],headless:true});
  try {
    const context = await browser.newContext({viewport:{width:1440,height:900},recordVideo:{dir:output,size:{width:1440,height:900}}});
    for(const workspace of ['novapay','falkordb']) {
      const health=await context.request.get(route('/api/health?workspace='+workspace));
      assert.equal(health.status(),200,'Both workspaces must be healthy');
      assert.equal((await health.json()).graph_mode,'falkordb','Never record JSON mode as native');
    }
    for(const endpoint of ['/api/graph/company-proof?workspace=novapay','/api/graph/showcase?workspace=falkordb']) {
      const proof=await context.request.get(route(endpoint));
      assert.equal(proof.status(),200); const result=await proof.json();
      assert(result.native_cypher_executed && (result.evidence?.length || result.paths?.length),'Native proof must have real paths');
    }
    const page=await context.newPage(); page.setDefaultTimeout(20000);
    const started=Date.now(), timeline={}; const mark=name=>timeline[name]=(Date.now()-started)/1000;
    async function ask(question){
      const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/chat' && r.status()===200);
      await page.locator('#question').fill(question); await page.locator('#send').click();
      const r=await (await response).json(); await page.locator('.answer-title').waitFor(); return r;
    }
    await page.goto(route('/dashboard?workspace=novapay'),{waitUntil:'networkidle'});
    await page.waitForFunction(()=>document.querySelector('#backend')?.textContent.includes('FalkorDB storage'));
    mark('intro'); await pause(7500);

    await page.locator('#graph-model').click(); await page.locator('#modal[open]').waitFor();
    mark('model'); await pause(9000); await page.locator('#close-modal').click();
    await page.locator('#graph-proof').click(); await page.locator('.proof-state.native').waitFor();
    mark('decision_proof'); await pause(14000); await page.locator('#close-modal').click();

    const decision=await ask('Why was Analytics Migration delayed?');
    assert(decision.tool_steps.length>=2 && decision.graph_trace.length>0 && decision.sources.length>0);
    await page.locator('.tool-steps summary').click();
    await page.locator('#conversation details:not(.tool-steps) summary').click();
    mark('decision_answer'); await pause(14000);
    await page.locator('.source-card').first().click(); await page.locator('#modal[open]').waitFor();
    await pause(4500); await page.locator('#close-modal').click();

    const owner=await ask('Who owns Database Cluster?');
    assert(owner.facts.some(f=>f.text.includes('David Brown')));
    mark('ownership'); await pause(12000);
    const pathResult=await ask('What is the shortest path from Alice Johnson to Database Cluster?');
    assert.equal(pathResult.intent,'connection');
    assert.deepEqual(pathResult.graph_trace[0].edges.map(e=>e.type),['WORKED_ON','DEPENDS_ON']);
    await page.locator('.tool-steps summary').click();
    await page.locator('#conversation details:not(.tool-steps) summary').click();
    mark('shortest_path'); await pause(11500);
    await page.reload({waitUntil:'networkidle'});
    await page.locator('#history button').first().waitFor(); await page.locator('#history button').first().click();
    await page.waitForFunction(()=>document.querySelector('#modal-content')?.textContent.includes('Persisted tool and evidence trace'));
    mark('memory'); await pause(9500); await page.locator('#close-modal').click();

    const blockers='What tickets block Analytics Migration?';
    await ask(blockers); mark('before_sync'); await pause(5500);
    const id='ticket_video_'+Date.now().toString(36);
    const payload={id,name:'VID-42 · Fresh validation blocker',content:'Fictional recording-only ticket from the authenticated operator ingest.',status:'OPEN',priority:'HIGH',project_id:'project_analytics',updated_at:new Date().toISOString()};
    const write=async record=>{
      const response=await context.request.post(route('/api/ingest/tickets?workspace=novapay'),{
        headers:{Authorization:'Bearer '+process.env.VIDEO_INGEST_TOKEN},data:record});
      assert.equal(response.status(),200,'Operator ingest failed');
    };
    await write(payload);
    const fresh=await ask(blockers); assert(fresh.facts.some(f=>f.text.includes('VID-42')));
    mark('after_sync'); await pause(11500);
    await write({...payload,status:'RESOLVED',updated_at:new Date(Date.now()+1000).toISOString()});
    const resolved=await ask(blockers); assert(!resolved.facts.some(f=>f.text.includes('VID-42')));
    mark('resolved'); await pause(7500);

    await page.locator('#workspace-select').selectOption('falkordb');
    await page.waitForURL('**/dashboard?workspace=falkordb');
    await page.waitForFunction(()=>document.querySelector('#backend')?.textContent.includes('FalkorDB storage'));
    await page.locator('#graph-proof').click(); await page.locator('.proof-state.native').waitFor();
    mark('public_proof'); await pause(8500); await page.locator('#close-modal').click();
    const activity=await ask('Who maintains the Python client? Are they active?');
    assert(activity.facts.length>0 && activity.notices.some(s=>s.includes('CODEOWNERS')));
    mark('public_activity'); await pause(9000);
    await page.goto(route('/present.html'),{waitUntil:'networkidle'});
    mark('close'); await pause(10500);
    const video=page.video(); await context.close();
    const file=path.join(deliverables,'native-company-brain.webm');
    fs.renameSync(await video.path(),file);
    fs.writeFileSync(path.join(deliverables,'native-company-brain-timeline.json'),JSON.stringify(timeline,null,2));
    console.log('Recorded native company-brain footage. Review timeline and render with narration.');
  }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
