const liveLink = document.querySelector('#live-url');
if (location.protocol === 'http:' || location.protocol === 'https:') {
  liveLink.textContent = location.origin;
  liveLink.href = location.origin + '/dashboard';
}
(async () => {
  const status = document.querySelector('#health');
  try {
    const response = await fetch('/api/health?workspace='+(new URLSearchParams(location.search).get('workspace')==='falkordb'?'falkordb':'novapay'), {cache: 'no-store', signal: AbortSignal.timeout(10000)});
    const health = await response.json();
    if (!response.ok || health.status !== 'healthy') throw new Error('Unhealthy service');
    status.textContent = `Healthy · ${health.version} · Graph mode: ${health.graph_mode} · Workspace: ${health.company} · ${health.fictional_data?'Fictional data':'Public snapshot'} · Agent: ${health.synthesis}${health.synthesis==='openai_tool_calling'&&!health.llm_configured?' (key missing)':''}`;
    if (document.querySelector('#proof-readiness')) document.querySelector('#proof-readiness').textContent = health.graph_mode==='falkordb'
      ? (health.synthesis==='openai_tool_calling'&&!health.llm_configured?'NATIVE GRAPH READY · LLM KEY MISSING; not ready for a live-agent recording.':'NATIVE GRAPH READY · Verify an actual model tool call before claiming a live-agent recording.')
      : 'PREVIEW ONLY · JSON storage is active. Do not claim Cypher executed; switch to FalkorDB mode before recording native proof.';
  } catch {
    status.textContent = 'Health check failed. Serve this page through ContextMind and check /api/health before presenting the demo.';
    if (document.querySelector('#proof-readiness')) document.querySelector('#proof-readiness').textContent='NOT READY · Backend health check failed.';
  }
})();

// The public workspace is separate from the fictional NovaPay walkthrough.
if (new URLSearchParams(location.search).get('workspace') === 'falkordb') {
  document.querySelector('#graph-demo').hidden=false;
  document.querySelector('.eyebrow').textContent = 'FALKORDB · PUBLIC GITHUB SNAPSHOT';
  document.querySelector('h1').textContent = 'ContextMind × FalkorDB';
  const questions = [
    'How do I get started with FalkorDB in Python?',
    'How do I use FalkorDB with LangChain?',
    'Who maintains the Python client? Are they active?',
    'What are the latest FalkorDB releases?',
    'What is FalkorDB annual revenue?'
  ];
  const list=document.querySelector('#questions');list.replaceChildren();
  for(const question of questions){
    const li=document.createElement('li'),a=document.createElement('a');
    a.textContent=question;a.href='/dashboard?workspace=falkordb&question='+encodeURIComponent(question);li.append(a);list.append(li);
  }
  document.querySelector('.primary').href='/dashboard?workspace=falkordb';
  liveLink.href=location.origin+'/dashboard?workspace=falkordb';
  document.querySelector('.actions a[href="/api/health"]').href='/api/health?workspace=falkordb';
  document.querySelector('main>.note:last-child').textContent='Public artifact snapshot, not a live feed. No verified private financial data or internal decision rationale is collected. Contributors are public activity evidence—not a ranking or maintainer assignment. The final question is a negative control and should return insufficient context.';
}
