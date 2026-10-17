/* Fail-closed browser check for storyboard claims. Writes ONLY a disposable fictional ticket.
 * Requires a fresh dedicated graph, operator token in environment, native backend by default.
 * CHECK_ALLOW_DEMO=1 permits isolated JSON test runs but NEVER validates a native video.
 */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const browserRequire=require('node:module').createRequire(path.resolve(__dirname,'../tests/browser/checklist.cjs'));
const {chromium}=browserRequire('playwright');
const packaged=browserRequire('@sparticuz/chromium').default;
const base=process.env.BASE_URL||'http://127.0.0.1:8000';
const output=path.resolve(__dirname,'../.runtime/video-state-check.json');
const pause=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
  assert(process.env.VIDEO_INGEST_TOKEN,'Provide a disposable operator token in the local environment');
  if(process.env.CHROMIUM_BUNDLED_LIBS==='1'){
    const module=browserRequire('@sparticuz/chromium');
    const libs=await module.inflate(path.resolve(path.dirname(browserRequire.resolve('@sparticuz/chromium')),'../bin/al2023.tar.br'));
    module.setupLambdaEnvironment(path.join(libs,'lib'));
  }
  const browser=await chromium.launch({executablePath:process.env.BROWSER_EXECUTABLE||await packaged.executablePath(),args:['--no-sandbox','--disable-dev-shm-usage'],headless:true});
  try{
    const context=await browser.newContext({viewport:{width:1440,height:900}});
    const request=context.request;
    const get=async p=>request.get(new URL(p,base).href);
    const mode=(await (await get('/api/health?workspace=novapay')).json()).graph_mode;
    assert(mode==='falkordb'||(mode==='demo'&&process.env.CHECK_ALLOW_DEMO==='1'),'Native graph required; JSON is not native proof');
    const proof=await (await get('/api/graph/company-proof?workspace=novapay')).json();
    assert.equal(proof.evidence.length,4,'Four decision evidence records required');
    assert.equal(proof.native_cypher_executed,mode==='falkordb');
    const page=await context.newPage();page.setDefaultTimeout(20000);
    await page.goto(new URL('/dashboard?workspace=novapay&demo_evidence=1',base).href,{waitUntil:'networkidle'});
    assert.match(await page.locator('#backend').innerText(),mode==='falkordb'?/FalkorDB storage/:/JSON storage/);
    await page.locator('#graph-proof').click();
    await page.locator('.company-proof-evidence>div').first().waitFor();
    assert.equal(await page.locator('.company-proof-evidence>div').count(),4,'Four visible separate proof rows');
    await page.locator('#close-modal').click();
    async function ask(question){
      const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/chat'&&r.status()===200);
      await page.locator('#question').fill(question);await page.locator('#send').click();
      return (await response).json();
    }
    const decision=await ask('Why was Analytics Migration delayed?');
    assert(decision.tool_steps.some(s=>s.tool==='explain_decision'));
    const owner=await ask('Who owns Database Cluster?');assert(owner.tool_steps.some(s=>s.tool==='find_owner'));
    const impact=await ask('What breaks if the Database Cluster goes down?');
    const pathIndex=impact.graph_trace.findIndex(p=>p.edges.length===2 &&
      p.edges[0].source==='project_payments'&&p.edges[0].type==='USES'&&p.edges[0].target==='sys_gateway'&&
      p.edges[1].source==='sys_gateway'&&p.edges[1].type==='DEPENDS_ON'&&p.edges[1].target==='sys_database');
    assert(pathIndex>=0,'Expected Payments v2 Launch → API Gateway → Database Cluster');
    await page.locator(`[data-trace="${pathIndex}"]`).click();
    const modal=await page.locator('#modal-content').innerText();
    assert(modal.includes('Payments v2 Launch')&&modal.includes('API Gateway')&&modal.includes('Database Cluster')&&modal.includes('USES')&&modal.includes('DEPENDS_ON'),'Both edges must be readable in Path dialog');
    await page.locator('#close-modal').click();
    const shortest=await ask('What is the shortest path from Alice Johnson to Database Cluster?');
    assert.equal(shortest.tool_steps[1].tool,'shortest_evidence_path');
    await page.reload({waitUntil:'networkidle'});await page.locator('#history button').first().click();
    await page.waitForFunction(()=>document.querySelector('#modal-content')?.textContent.includes('Persisted tool and evidence trace'));
    assert.match(await page.locator('#modal-content').innerText(),/Persisted tool and evidence trace/);
    await page.locator('#close-modal').click();
    const blockers='What tickets block Analytics Migration?';
    const id='ticket_video_'+Date.now().toString(36);
    const before=await ask(blockers);assert(!before.facts.some(f=>f.text.includes('VID-42')),'Recording graph must be fresh');
    assert.equal((await get('/api/entities/'+id+'?workspace=novapay')).status(),404);
    const payload={id,name:'VID-42 · Fictional validation blocker',content:'Fictional recording-only operator update.',
      status:'OPEN',priority:'HIGH',project_id:'project_analytics',updated_at:new Date().toISOString()};
    const write=async record=>request.post(new URL('/api/ingest/tickets?workspace=novapay',base).href,{
      headers:{Authorization:'Bearer '+process.env.VIDEO_INGEST_TOKEN},data:record});
    // A denied write must never produce an onscreen receipt.
    const denied=await request.post(new URL('/api/ingest/tickets?workspace=novapay',base).href,{data:payload});
    assert.equal(denied.status(),401);assert.equal(await page.locator('#recording-evidence').isVisible(),false);
    const added=await write(payload);assert.equal(added.status(),200,'STOP: insert failed');
    const addBody=await added.json();assert.equal(addBody.record.status,'OPEN');
    assert(await page.evaluate(({status,body})=>window.showRecordingEvidence(status,body),{status:added.status(),body:addBody}));
    assert.match(await page.locator('#recording-evidence').innerText(),/OPEN/);
    const open=await ask(blockers);assert(open.facts.some(f=>f.text.includes('VID-42')));
    const done=await write({...payload,status:'RESOLVED',updated_at:new Date(Date.now()+3000).toISOString()});
    assert.equal(done.status(),200,'STOP: resolution failed');
    const doneBody=await done.json();assert.equal(doneBody.record.status,'RESOLVED');
    assert(await page.evaluate(({status,body})=>window.showRecordingEvidence(status,body),{status:done.status(),body:doneBody}));
    assert.match(await page.locator('#recording-evidence').innerText(),/RESOLVED/);
    const resolved=await ask(blockers);assert(!resolved.facts.some(f=>f.text.includes('VID-42')));
    const panel=await page.locator('#recording-evidence').innerText();
    assert(!/Bearer|Authorization|password|token/i.test(panel));
    await page.goto(new URL('/dashboard?workspace=falkordb',base).href,{waitUntil:'networkidle'});
    await page.locator('#graph-proof').click();
    const publicProof=await (await get('/api/graph/showcase?workspace=falkordb')).json();
    assert.equal(publicProof.native_cypher_executed,mode==='falkordb');assert(publicProof.paths.length>0);
    await page.goto(new URL('/architecture.html',base).href);assert.match(await page.locator('body').innerText(),/Bounded graph traversal/);
    await page.goto(new URL('/present.html',base).href);assert.match(await page.locator('body').innerText(),/Cloud deployment not verified/);
    fs.mkdirSync(path.dirname(output),{recursive:true});
    fs.writeFileSync(output,JSON.stringify({backend:mode,decision_rows:4,impact_edges:2,ticket_id:id,
      before_absent:true,after_open:true,after_resolved_absent:true,
      add_counts:addBody.graph_counts,resolve_counts:doneBody.graph_counts},null,2));
    console.log('PASS storyboard states ('+mode+'); sanitized report at .runtime/video-state-check.json');
    await context.close();
  }finally{await browser.close()}
})().catch(e=>{console.error('FAIL storyboard state check:',e.message);process.exitCode=1});
