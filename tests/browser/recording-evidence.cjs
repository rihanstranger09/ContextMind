const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const packaged=require('@sparticuz/chromium').default;
const {receipt}=require('../../frontend/recording-evidence.js');
const base=process.env.BASE_URL||'http://127.0.0.1:6389';
const sample={record:{id:'ticket_video_abcd1234',status:'OPEN',updated_at:'2026-10-17T10:00:00Z',
  Authorization:'Bearer SHOULD_NEVER_APPEAR',password:'SECRET_FIELD',name:'VID-42'},
  graph_counts:{nodes:42,relationships:51,secret:'SECRET_FIELD'},token:'SECRET_FIELD'};
assert.deepEqual(Object.keys(receipt(200,sample)),['status','id','state','timestamp','nodes','relationships']);
assert.equal(receipt(401,sample),null);
assert.equal(receipt(200,{...sample,record:{...sample.record,id:'Bearer LEAK'}}),null);
assert.equal(receipt(200,{...sample,graph_counts:{nodes:'SECRET_FIELD',relationships:51}}),null);
(async()=>{
  if(process.env.CHROMIUM_BUNDLED_LIBS==='1'){
    const module=require('@sparticuz/chromium');
    const libs=await module.inflate(require('node:path').resolve(require('node:path').dirname(require.resolve('@sparticuz/chromium')),'../bin/al2023.tar.br'));
    module.setupLambdaEnvironment(require('node:path').join(libs,'lib'));
  }
  const browser=await chromium.launch({executablePath:process.env.BROWSER_EXECUTABLE||await packaged.executablePath(),args:['--no-sandbox','--disable-dev-shm-usage'],headless:true});
  try{
    const page=await browser.newPage();
    await page.goto(base+'/dashboard?workspace=novapay',{waitUntil:'networkidle'});
    assert.equal(await page.evaluate(()=>typeof window.showRecordingEvidence),'undefined');
    await page.goto(base+'/dashboard?workspace=falkordb&demo_evidence=1',{waitUntil:'networkidle'});
    assert.equal(await page.evaluate(()=>typeof window.showRecordingEvidence),'undefined');
    await page.goto(base+'/dashboard?workspace=novapay&demo_evidence=1',{waitUntil:'networkidle'});
    assert.equal(await page.evaluate(()=>window.showRecordingEvidence(401,{})),false);
    assert.equal(await page.locator('#recording-evidence').isVisible(),false);
    assert.equal(await page.evaluate(body=>window.showRecordingEvidence(200,body),sample),true);
    const text=await page.locator('#recording-evidence').innerText();
    assert.match(text,/HTTP\s*200/);assert.match(text,/ticket_video_abcd1234/);assert.match(text,/OPEN/);
    assert.match(text,/42/);assert.match(text,/51/);
    assert.doesNotMatch(text,/SECRET_FIELD|SHOULD_NEVER_APPEAR|Bearer|Authorization|password|token/i);
    assert.equal(await page.evaluate(body=>window.showRecordingEvidence(500,body),sample),false);
    assert.equal(await page.locator('#recording-evidence').isVisible(),false);
    console.log('PASS response-derived panel: opt-in, success, failure clears, strict allowlist');
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
