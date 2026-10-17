/* Guarded v4 native capture. Aborts on any failed proof/write; never films credentials.
 * Draft video is NOT published automatically. Use a disposable graph and separate
 * operator environment variable. RECORD_ALLOW_DEMO=1 is rehearsal ONLY.
 */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const browserRequire=require('node:module').createRequire(path.resolve(__dirname,'../tests/browser/checklist.cjs'));
const {chromium}=browserRequire('playwright');
const packaged=browserRequire('@sparticuz/chromium').default;
const base=process.env.BASE_URL||'http://127.0.0.1:8000';
const url=p=>new URL(p,base).href;
const output=path.resolve(__dirname,'../deliverables');
const scratch=path.resolve(__dirname,'../.runtime/company-v4');
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{
  assert(process.env.VIDEO_INGEST_TOKEN,'Recording requires a disposable operator credential in the local environment');
  if(process.env.CHROMIUM_BUNDLED_LIBS==='1'){
    const module=browserRequire('@sparticuz/chromium');
    const libs=await module.inflate(path.resolve(path.dirname(browserRequire.resolve('@sparticuz/chromium')),'../bin/al2023.tar.br'));
    module.setupLambdaEnvironment(path.join(libs,'lib'));
  }
  fs.mkdirSync(scratch,{recursive:true});
  const browser=await chromium.launch({executablePath:process.env.BROWSER_EXECUTABLE||await packaged.executablePath(),args:['--no-sandbox','--disable-dev-shm-usage'],headless:true});
  try{
    const context=await browser.newContext({viewport:{width:1440,height:900},recordVideo:{dir:scratch,size:{width:1440,height:900}}});
    const request=context.request;
    for(const workspace of ['novapay','falkordb']){
      const health=await request.get(url('/api/health?workspace='+workspace));assert.equal(health.status(),200);
      const mode=(await health.json()).graph_mode;
      assert(mode==='falkordb'||(process.env.RECORD_ALLOW_DEMO==='1'&&mode==='demo'),'Native graph required');
    }
    const native=(await (await request.get(url('/api/health?workspace=novapay'))).json()).graph_mode==='falkordb';
    for(const path of ['/api/graph/company-proof?workspace=novapay','/api/graph/showcase?workspace=falkordb']){
      const proof=await request.get(url(path));assert.equal(proof.status(),200);
      const data=await proof.json();assert.equal(data.native_cypher_executed,native);
      assert(data.evidence?.length===4||data.paths?.length>0);
    }
    const page=await context.newPage();page.setDefaultTimeout(20000);
    await page.goto(url('/dashboard?workspace=novapay&demo_evidence=1'),{waitUntil:'networkidle'});
    const start=Date.now(), timeline={};
    const mark=key=>timeline[key]=(Date.now()-start)/1000;
    const until=async seconds=>{const wait=seconds*1000-(Date.now()-start);
      if(wait < -3500)throw Error('Scene fell behind script by more than 3.5s; re-time/re-record');
      if(wait>0)await pause(wait);
    };
    const ask=async q=>{
      const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/chat'&&r.status()===200);
      await page.locator('#question').fill(q);await page.locator('#send').click();
      const answer=await(await response).json();await page.locator('.answer-title').waitFor();return answer;
    };
    const blockers='What tickets block Analytics Migration?';
    const id='ticket_video_'+Date.now().toString(36);
    const record={id,name:'VID-42 · Fictional validation blocker',content:'Fictional recording-only operator update.',status:'OPEN',
      priority:'HIGH',project_id:'project_analytics',updated_at:new Date().toISOString()};
    const write=async body=>{
      const response=await request.post(url('/api/ingest/tickets?workspace=novapay'),{
        headers:{Authorization:'Bearer '+process.env.VIDEO_INGEST_TOKEN},data:body});
      assert.equal(response.status(),200,'STOP: operator write failed');
      const data=await response.json();assert.equal(data.record.status,body.status);
      assert(await page.evaluate(({status,data})=>window.showRecordingEvidence(status,data),{status:response.status(),data}));
      const label=await page.locator('#recording-evidence').innerText();
      assert(!/Bearer|Authorization|token|password/i.test(label));return data;
    };
    mark('intro');await until(6);
    await page.locator('#graph-model').click();mark('model');await until(14);await page.locator('#close-modal').click();
    await page.locator('#graph-proof').click();await page.locator('.company-proof-evidence>div').first().waitFor();
    assert.equal(await page.locator('.company-proof-evidence>div').count(),4);mark('decision_proof');await until(26);await page.locator('#close-modal').click();
    const decision=await ask('Why was Analytics Migration delayed?');assert(decision.tool_steps.some(s=>s.tool==='explain_decision'));
    await page.locator('.tool-steps summary').click();await page.locator('#conversation details:not(.tool-steps) summary').click();
    mark('decision_answer');await until(39);
    const owner=await ask('Who owns Database Cluster?');assert(owner.facts.some(f=>f.text.includes('Platform Engineering')));
    mark('ownership');await until(45);
    const impact=await ask('What breaks if the Database Cluster goes down?');
    const i=impact.graph_trace.findIndex(p=>p.edges.length===2&&p.edges[0].source==='project_payments'&&p.edges[0].type==='USES'&&p.edges[1].target==='sys_database'&&p.edges[1].type==='DEPENDS_ON');
    assert(i>=0);await page.locator(`[data-trace="${i}"]`).click();
    const visible=await page.locator('#modal-content').innerText();assert(visible.includes('Payments v2 Launch')&&visible.includes('API Gateway')&&visible.includes('Database Cluster'));
    mark('impact');await until(64);await page.locator('#close-modal').click();
    const shortest=await ask('What is the shortest path from Alice Johnson to Database Cluster?');
    assert.equal(shortest.tool_steps[1].tool,'shortest_evidence_path');
    await page.locator('.tool-steps summary').click();mark('shortest');await until(74);
    await page.reload({waitUntil:'networkidle'});await page.locator('#history button').first().click();
    await page.waitForFunction(()=>document.querySelector('#modal-content')?.textContent.includes('Persisted tool and evidence trace'));
    mark('memory');await until(81);await page.locator('#close-modal').click();
    const before=await ask(blockers);assert(!before.facts.some(f=>f.text.includes('VID-42')));
    mark('before');await until(84);
    await write(record);mark('insert');await until(87);
    const fresh=await ask(blockers);assert(fresh.facts.some(f=>f.text.includes('VID-42')));
    mark('open');await until(91);
    await write({...record,status:'RESOLVED',updated_at:new Date(Date.now()+3000).toISOString()});mark('resolve');await until(94);
    const after=await ask(blockers);assert(!after.facts.some(f=>f.text.includes('VID-42')));
    mark('resolved');await until(97);
    await page.locator('#workspace-select').selectOption('falkordb');await page.waitForURL('**/dashboard?workspace=falkordb');
    await page.locator('#graph-proof').click();await page.locator('.proof-state').waitFor();mark('public_proof');await until(105);
    await page.goto(url('/architecture.html'),{waitUntil:'networkidle'});mark('architecture');await until(113);
    await page.goto(url('/present.html'),{waitUntil:'networkidle'});mark('close');await until(120);
    const video=page.video();await context.close();
    const target=native?output:scratch;fs.mkdirSync(target,{recursive:true});
    fs.renameSync(await video.path(),path.join(target,native?'native-company-v4.webm':'demo-rehearsal-v4.webm'));
    fs.writeFileSync(path.join(target,native?'native-company-v4-timeline.json':'demo-rehearsal-v4-timeline.json'),JSON.stringify(timeline,null,2));
    console.log(native?'Guarded native v4 footage recorded; narration/render still required.':'JSON REHEARSAL ONLY; not a native demo or submission video.');
  }finally{await browser.close()}
})().catch(e=>{console.error('STOP recording:',e.message);process.exitCode=1});
