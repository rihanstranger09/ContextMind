const $=s=>document.querySelector(s), esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const workspace=new URLSearchParams(location.search).get('workspace')==='falkordb'?'falkordb':'novapay';
const isPublic=workspace==='falkordb', rootEntity=isPublic?'org_falkordb':'sys_database';
const publicQuestions=[
  ['Build with Python','How do I get started with FalkorDB in Python?'],
  ['Explore an integration','Can I use FalkorDB with LangChain for building an AI agent?'],
  ['Inspect public activity','Who maintains the Python client? Are they active?'],
  ['Read release evidence','What are the latest FalkorDB releases?']
];
if(isPublic){
  $('#workspace').innerHTML='<span class="company-icon">F</span><span>FalkorDB<small>Public GitHub snapshot</small></span><span class="chevron">⌄</span>';
  $('.header-company').textContent='FalkorDB public brain';
  $('h1').textContent='A graph database. Its own company brain.';
  $('.heading p').textContent='Explore public code, documentation, releases, and contributor evidence.';
  $('.welcome h2').innerHTML='Real sources.<br>Inspectable connections.';
  $('.welcome p').textContent='A bounded public snapshot, not internal company knowledge or a live feed.';
  $('.suggestions').innerHTML=publicQuestions.map(([title,q])=>`<button data-question="${esc(q)}"><span class="suggestion-icon violet">⌘</span><div>${esc(title)}<small>${esc(q)}</small></div><span>↗</span></button>`).join('');
  $('.bottom-strip strong').textContent='Know what is collected. Know what is missing.';
  $('.bottom-strip div>span').textContent='Source provenance, collection dates, and explicit coverage limits.';
  $('.bottom-strip button').removeAttribute('data-question');
  $('.bottom-strip button').textContent='View coverage →';
  $('.bottom-strip button').onclick=showCoverage;
  $('footer>span').textContent='FalkorDB · Public artifacts · Snapshot, not live';
  $('.nav[data-page="risks"]').innerHTML='<span>◈</span> Data coverage';
  // No hand-verified public decisions exist in this snapshot; do not imply otherwise.
  $('.nav[data-page="decisions"]').remove();
  $('.graph-toolbar>span').textContent='Public snapshot explorer';
  $('.legend').innerHTML='<span><i style="background:#997acb"></i>Repository</span><span><i style="background:#7a9bd3"></i>Topic</span><span><i style="background:#d0a264"></i>Contributor</span><span><i style="background:#73ad9d"></i>Evidence</span>';
  $('.metrics>div:nth-child(2) div>span').textContent='Visible graph relationships';
  $('.input-hint>span').textContent='Source excerpts, not inferred company decisions.';
  $('.demo-badge').href='/demo.html?workspace=falkordb';
  $('#graph-proof').hidden=false;
}
if(!isPublic)$('#graph-proof').textContent='◈ DECISION CYPHER';
$('#workspace-select').value=workspace;
$('#workspace-select').onchange=e=>{location.href='/dashboard?workspace='+e.target.value};
let entities=[],current=rootEntity,graphData=null,zoom=1,busy=false; const welcome=$('#conversation').innerHTML;
async function api(path,body){path+=(path.includes('?')?'&':'?')+'workspace='+workspace;const r=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});if(!r.ok){let e=await r.json().catch(()=>({detail:'Request failed'}));throw new Error(typeof e.detail==='string'?e.detail:e.graph_error?'Graph backend unavailable ('+e.graph_error+'). '+(e.graph_error_hint||''):'Please check your request.')}return r.json()}
function modal(title,html){$('#modal-title').textContent=title;$('#modal-content').innerHTML=html;$('#modal').showModal()}
$('#close-modal').onclick=()=>$('#modal').close();$('#modal').onclick=e=>{if(e.target===$('#modal'))$('#modal').close()};
const schemaNodes=isPublic
  ? [['Organization',85,80],['Repository',320,80],['Version',555,80],['Contributor',85,255],['Guide',555,255]]
  : [['Person',85,80],['Team',320,80],['System',555,80],['Ticket / chat',85,255],['Decision',320,255],['Project',555,255]];
const schemaLinks=isPublic
  ? [[0,1,'OWNS'],[1,2,'VERSION'],[3,1,'CONTRIBUTES_TO'],[4,1,'ABOUT']]
  : [[0,1,'MEMBER_OF'],[1,2,'OWNS'],[4,3,'BASED_ON'],[4,5,'IMPACTS']];
$('#graph-model').onclick=()=>{
  const links=schemaLinks.map(([a,b,label])=>{const [x1,y1]=schemaNodes[a].slice(1),[x2,y2]=schemaNodes[b].slice(1),dx=x2-x1,dy=y2-y1,d=Math.hypot(dx,dy);return `<line x1="${x1+dx*76/d}" y1="${y1+dy*20/d}" x2="${x2-dx*76/d}" y2="${y2-dy*20/d}" marker-end="url(#model-arrow)"/><text x="${(x1+x2)/2}" y="${(y1+y2)/2-11}" text-anchor="middle">${esc(label)}</text>`}).join('');
  const nodes=schemaNodes.map(([name,x,y])=>`<g><rect x="${x-74}" y="${y-24}" width="148" height="48" rx="13"/><text x="${x}" y="${y+5}" text-anchor="middle">${esc(name)}</text></g>`).join('');
  modal('Graph model · '+(isPublic?'public artifact snapshot':'fictional company brain'),
    `<p>${isPublic?'Captured GitHub artifacts; no inferred human maintainer or internal decisions.':'NovaPay is fictional. Decisions also link to Meeting and Document evidence; saved investigations link to sources via USED_EVIDENCE.'}</p><svg class="model-svg" viewBox="0 0 640 340" role="img" aria-label="${isPublic?'Public artifact':'Fictional company'} graph node and relationship diagram"><defs><marker id="model-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10" fill="#9980ba"/></marker></defs>${links}${nodes}</svg><p>Native FalkorDB stores typed nodes and relationships. Read the exact query and traversal definitions in docs/graph-model-and-queries.md.</p>`);
};
// This is a fixed, read-only query. Never accept Cypher or graph names from the browser.
$('#graph-proof').onclick=async()=>{
  if(!isPublic)return showCompanyProof();
  modal('FalkorDB · the graph is the engine','<p>Reading the graph…</p>');
  try{
    const proof=await api('/api/graph/showcase');
    const native=proof.native_cypher_executed;
    const sourceLink=n=>{
      try{const url=new URL(n.source_url);if(url.protocol==='https:'&&url.hostname==='github.com')return `<a href="${esc(url.href)}" target="_blank" rel="noopener noreferrer">View release source ↗</a>`}catch{}
      return 'Source URL not available';
    };
    const trails=proof.paths.map(p=>`<div class="proof-path"><strong>${esc(p.nodes[0].name)}</strong><span>─ ${esc(p.relationships[0])} →</span><strong>${esc(p.nodes[1].name)}</strong><span>─ ${esc(p.relationships[1])} →</span><strong>${esc(p.nodes[2].name)}</strong><small>${sourceLink(p.nodes[2])}</small></div>`).join('');
    $('#modal-content').innerHTML=`<div class="proof-state ${native?'native':'preview'}">${native?'● NATIVE FALKORDB · CYPHER EXECUTED':'○ JSON PREVIEW · CYPHER NOT EXECUTED'}</div>
      <p>${native?'These results were read from the FalkorDB graph with native Cypher.':'These results came from the bundled JSON snapshot. Start with GRAPH_BACKEND=falkordb to run the Cypher below against a real database.'}</p>
      <div class="proof-metrics"><div><strong>${Number(proof.entity_count).toLocaleString()}</strong><span>Stored entities</span></div><div><strong>${Number(proof.relationship_count).toLocaleString()}</strong><span>Stored relationships</span></div></div>
      <h3>Two-hop graph traversal · organization → Python client → releases</h3>
      <pre class="proof-query">${esc(proof.cypher)}</pre><p class="proof-params">Parameters: ${esc(JSON.stringify(proof.parameters))}</p>
      <h3>Paths with public release evidence</h3>${trails||'<p>No matching release paths in this snapshot.</p>'}
      <p class="proof-foot">${native?'Server-side proof: '+esc(proof.elapsed_ms)+' ms. This is not a benchmark.':'The Cypher above is illustrative until native mode is enabled.'} Public GitHub snapshot; not a live feed.</p>`;
  }catch(e){$('#modal-content').innerHTML='<p class="error">Graph proof unavailable: '+esc(e.message)+'</p>'}
};
async function showCompanyProof(){
  modal('Decision provenance · graph proof','<p>Reading the decision graph…</p>');
  try{const p=await api('/api/graph/company-proof');
    $('#modal-content').innerHTML=`<div class="proof-state ${p.native_cypher_executed?'native':'preview'}">${p.native_cypher_executed?'● NATIVE FALKORDB · SECOND CYPHER QUERY EXECUTED':'○ JSON PREVIEW · CYPHER NOT EXECUTED'}</div>
      <p><strong>${esc(p.decision)}</strong> impacts ${esc(p.project)}. The rationale is backed by four linked records across tickets, chat, meeting and documentation. NovaPay and its data are fictional.</p>
      <h3>Decision → evidence and impacted project</h3><pre class="proof-query">${esc(p.cypher)}</pre>
      <div class="proof-path company-proof-evidence">${p.evidence.map(e=>`<div>BASED_ON → <strong>${esc(e.name)}</strong> · ${esc(e.type)}${e.status?' · '+esc(e.status):''}</div>`).join('')}</div>
      <p class="proof-foot">This is a fixed read-only query. Inspect the answer trace for more relationship context; no unsupported public FalkorDB decisions are inferred.</p>`;
  }catch(e){$('#modal-content').innerHTML='<p class="error">Decision proof unavailable: '+esc(e.message)+'</p>'}
}
const colors={Repository:'#997acb',Organization:'#b28ccc',Version:'#73ad9d',Guide:'#73ad9d',Integration:'#7a9bd3',System:'#997acb',Project:'#7a9bd3',Person:'#d0a264',Team:'#d0a264',Document:'#73ad9d',Ticket:'#73ad9d',Message:'#73ad9d',Meeting:'#73ad9d',Decision:'#b28ccc',Incident:'#c9a170'};
function draw(data){graphData=data;const nodes=data.nodes.filter(n=>n&&n.type!=='AgentDecision');let visible=nodes.filter(n=>n.id===current||['System','Project','Person','Team','Repository','Organization','Integration'].includes(n.type));if(visible.length<6)visible=nodes;visible=visible.slice(0,17);if(!visible.some(n=>n.id===current)&&nodes.some(n=>n.id===current))visible=[nodes.find(n=>n.id===current),...visible.slice(0,16)];
const center=visible.find(n=>n.id===current)||visible[0];const outer=visible.filter(n=>n!==center);const pos={};if(center)pos[center.id]=[310,207];outer.forEach((n,i)=>{let a=-Math.PI/2+i*2*Math.PI/outer.length;pos[n.id]=[310+Math.cos(a)*(i%2?234:192),207+Math.sin(a)*(i%2?153:150)]});
let svg='<defs><marker id="arrow" viewBox="0 0 10 10" refX="24" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#c7bbd8"/></marker></defs><g id="graph-inner" transform="translate(310 210) scale('+zoom+') translate(-310 -210)">';
for(const e of data.edges){if(!pos[e.source]||!pos[e.target])continue;let [x,y]=pos[e.source],[x2,y2]=pos[e.target];svg+=`<line x1="${x}" y1="${y}" x2="${x2}" y2="${y2}" stroke="#d9cfe6" stroke-width="1.1" marker-end="url(#arrow)"/><text x="${(x+x2)/2}" y="${(y+y2)/2-5}" text-anchor="middle" fill="#c0b0ce" font-size="6" style="paint-order:stroke;stroke:white;stroke-width:3px">${esc(e.type.replaceAll('_',' '))}</text>`}
for(const n of visible){let [x,y]=pos[n.id],color=colors[n.type]||'#aaa',r=n===center?29:19;let icon={System:'▧',Project:'◇',Person:'♙',Team:'♧',Document:'▤',Ticket:'≡',Decision:'◷'}[n.type]||'◈';svg+=`<g class="graph-node" tabindex="0" role="button" aria-label="Explore ${esc(n.name)}" data-node="${esc(n.id)}"><circle cx="${x}" cy="${y}" r="${r+7}" fill="${color}" opacity=".06"/><circle cx="${x}" cy="${y}" r="${r}" fill="white" stroke="${color}" stroke-opacity=".55" stroke-width="1.2"/><circle cx="${x}" cy="${y}" r="${r-3}" fill="${color}" opacity=".1"/><text x="${x}" y="${y+7}" text-anchor="middle" fill="${color}" font-size="${n===center?26:20}">${icon}</text><text x="${x}" y="${y+r+16}" text-anchor="middle" fill="${n===center?'#8260a6':'#9f8eae'}" font-size="${n===center?11:8}" font-weight="${n===center?600:400}">${esc(n.name.length>29?n.name.slice(0,27)+'…':n.name)}</text></g>`}$('#graph').innerHTML=svg+'</g>';
$('#graph').querySelectorAll('[data-node]').forEach(el=>{el.onclick=()=>selectNode(el.dataset.node);el.onkeydown=e=>{if(e.key==='Enter')selectNode(el.dataset.node)}})}
function drawPath(data,edges,startId){
  graphData=data;
  const nodes=new Map(data.nodes.map(n=>[n.id,n]));let ids=[startId],key=startId;
  for(const e of edges){key=e.source===key?e.target:e.source;ids.push(key)}
  const x=i=>620*(i+1)/(ids.length+1),y=210;
  let svg='<defs><marker id="path-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10" fill="#9978c2"/></marker></defs>';
  edges.forEach((e,i)=>{const forward=e.source===ids[i],left=x(i)+35,right=x(i+1)-35;svg+=`<line x1="${forward?left:right}" y1="${y}" x2="${forward?right:left}" y2="${y}" stroke="#9978c2" stroke-width="2" marker-end="url(#path-arrow)"/><text x="${(x(i)+x(i+1))/2}" y="${y-14}" text-anchor="middle" font-size="12" fill="#674a8a">${esc(e.type)}</text>`});
  ids.forEach((id,i)=>{const n=nodes.get(id);if(!n)return;svg+=`<g class="graph-node" tabindex="0" role="button" aria-label="Explore ${esc(n.name)}" data-node="${esc(id)}"><circle cx="${x(i)}" cy="${y}" r="28" fill="#faf7fe" stroke="#9978c2" stroke-width="2"/><text x="${x(i)}" y="${y+7}" text-anchor="middle" font-size="22" fill="#8b67ae">${n.type==='Person'?'♙':'▧'}</text><text x="${x(i)}" y="${y+49}" text-anchor="middle" font-size="12" font-weight="600" fill="#674a8a">${esc(n.name)}</text></g>`});
  $('#graph').innerHTML=svg;
  $('#graph').querySelectorAll('[data-node]').forEach(el=>{el.onclick=()=>selectNode(el.dataset.node);el.onkeydown=e=>{if(e.key==='Enter')selectNode(el.dataset.node)}});
}
async function selectNode(id,refresh=true){try{const n=await api('/api/entities/'+encodeURIComponent(id));current=id;$('#graph-focus').textContent=n.name+' ⌄';$('#entity-detail').innerHTML=`<div class="detail-kicker">IN FOCUS <span>${esc(n.type)}</span></div><h3><span class="node-square">▧</span>${esc(n.name)} ${n.criticality?`<span class="critical">${esc(n.criticality)}</span>`:''}</h3><p>${esc((n.content||n.rationale||n.title||n.status||'Explore ownership, dependencies, and connected evidence.').slice(0,400))}</p><div class="detail-footer"><span>${isPublic?'Captured '+esc(n.collected_at?.slice(0,10)):'Updated '+esc(n.updated_at?.slice(0,10))}</span><button id="investigate">Investigate →</button></div>`;$('#investigate').onclick=()=>ask(isPublic?'Find docs about '+n.name:n.type==='Decision'?'Why '+n.name+'?':n.type==='Project'?'What tickets block '+n.name+'?':n.type==='System'?'Who owns '+n.name+'?':'Find docs about '+n.name);if(refresh)draw(await api('/api/graph/subgraph?entity_id='+encodeURIComponent(id)+'&depth=2'))}catch(e){modal('Unable to load entity',esc(e.message))}}
$('#investigate').onclick=()=>ask(isPublic?publicQuestions[0][1]:'Who owns Database Cluster?');$('#zoom-in').onclick=()=>{zoom=Math.min(1.8,zoom+.15);draw(graphData)};$('#zoom-out').onclick=()=>{zoom=Math.max(.6,zoom-.15);draw(graphData)};$('#reset-graph').onclick=()=>{zoom=1;selectNode(rootEntity)};
$('#graph-focus').onclick=()=>{modal('Explore an entity',`<input id="entity-search" placeholder="Search systems, people, projects…" style="width:100%;padding:12px;border:1px solid #ddd1e8;border-radius:7px;margin-bottom:12px"><div id="entity-results"></div>`);const render=q=>{$('#entity-results').innerHTML=entities.filter(n=>n.name.toLowerCase().includes(q.toLowerCase())&&n.type!=='AgentDecision').map(n=>`<button class="modal-record" style="display:block;width:100%;text-align:left" data-select="${esc(n.id)}">${esc(n.name)} <small>· ${esc(n.type)}</small></button>`).join('');$('#entity-results').querySelectorAll('button').forEach(b=>b.onclick=()=>{$('#modal').close();selectNode(b.dataset.select)})};render('');$('#entity-search').oninput=e=>render(e.target.value)};
async function ask(question){if(busy||!question.trim())return;busy=true;$('#send').disabled=true;$('#question').value='';$('#conversation').innerHTML=`<div class="question-bubble">${esc(question)}</div><div class="loading">✧ Traversing company relationships and collecting evidence…</div>`;
try{const r=await api('/api/chat',{question});let html=`<div class="question-bubble">${esc(question)}</div><div class="answer-header"><span class="assistant-symbol">✧</span>ContextMind <span class="citation">${esc((r.agent_mode||'').endsWith('tool_calling')?'LIVE LLM AGENT · '+r.model:'DETERMINISTIC · '+r.intent)}</span></div><div class="answer-title">${esc(r.answer)}</div>`;
html+=r.facts.map(f=>`<div class="fact">${esc(f.text)} ${f.path_indices.map(i=>`<button class="citation" data-trace="${i}">Path ${i+1} ↗</button>`).join('')}${(f.source_ids||[]).map(id=>`<button class="citation" data-source="${r.sources.findIndex(s=>s.id===id)}">Source ↗</button>`).join('')}${f.entity_id?`<button class="citation" data-inspect="${esc(f.entity_id)}">Graph record ↗</button>`:''}</div>`).join('');
if(r.notices?.length)html+=`<div class="public-notice">${r.notices.map(n=>`<p>${esc(n)}</p>`).join('')}</div>`;
if(r.recommended_actions.length)html+=`<div class="answer-section-title">RECOMMENDED ACTION</div><p class="fact">${esc(r.recommended_actions.join(' '))}</p>`;
if(r.sources.length)html+=`<div class="answer-section-title">CONNECTED SOURCES · ${r.sources.length}</div><div class="source-grid">${r.sources.map((s,i)=>`<button class="source-card" data-source="${i}"><span style="color:#9b80bc">▤</span> ${esc(s.name)}<small>${esc(s.type)} · ${esc(s.updated_at?.slice(0,10))}${s.method?' · '+esc(s.method):''}${s.inferred?' · INFERRED':''}${r.freshness.stale_sources.includes(s.id)?' · STALE':''}</small></button>`).join('')}</div>`;
if(r.graph_trace.length)html+=`<details><summary>Why this answer? · ${r.graph_trace.length} graph paths</summary><ol>${r.graph_trace.map(p=>`<li>${esc(p.label)}</li>`).join('')}</ol></details>`;
if(r.tool_steps?.length)html+=`<details class="tool-steps"><summary>Tools used · ${r.tool_steps.length} recorded steps</summary><ol>${r.tool_steps.map(s=>`<li><strong>${esc(s.tool)}</strong>${s.focus?' · '+esc(s.focus):''} · ${esc(s.results)} results</li>`).join('')}</ol><p>${(r.agent_mode||'').endsWith('tool_calling')?'Model-requested tool calls executed by the server against bounded graph reads; not hidden model reasoning.':'Rule-based tool routing, not autonomous planning or hidden model reasoning.'}</p></details>`;
html+=`<p style="font-size:8px;color:#afa0bb;line-height:1.7">${isPublic?'Public GitHub snapshot · No private data · No personal performance ranking.':'Fictional NovaPay data · Graph-derived answer · Verify operational availability before acting.'}</p>`;$('#conversation').innerHTML=html;
$('#conversation').querySelectorAll('[data-trace]').forEach(b=>b.onclick=()=>{let t=r.graph_trace[+b.dataset.trace];modal('Evidence path',`<p>${esc(t.label)}</p><p>These stored graph relationships support this claim. This is an auditable retrieval trace, not hidden model reasoning.</p><pre>${esc(JSON.stringify(t.edges,null,2))}</pre>`)});
$('#conversation').querySelectorAll('[data-inspect]').forEach(b=>b.onclick=()=>selectNode(b.dataset.inspect));$('#conversation').querySelectorAll('[data-source]').forEach(b=>b.onclick=()=>showSource(r.sources[+b.dataset.source]));
if(r.graph.nodes.length){
  const route=r.tool_steps?.find(s=>['shortest_evidence_path','shortest_path'].includes(s.tool));
  current=(route&&r.graph_trace[0]?.edges[0]?.source)||route?.focus?.split(' → ')[0]||r.resolved_entities[0]?.id||r.graph.nodes[0].id;
  await selectNode(current,false);
  if(route&&r.graph_trace.length)drawPath(r.graph,r.graph_trace[0].edges,current);
  else draw(r.graph);
  $('#graph-focus').textContent='Answer evidence ⌄'
}
if(!isPublic)await loadHistory();
}catch(e){$('#conversation').innerHTML+=`<div class="error">${esc(e.message)}. Please try again.</div>`;$('.loading')?.remove()}finally{busy=false;$('#send').disabled=false}}
async function loadHistory(){
  if(isPublic){$('.recent-label')?.remove();$('#history')?.remove();return}
  const records=await api('/api/investigations?limit=8');
  $('#history').replaceChildren();
  if(!records.length){$('#history').innerHTML='<p class="muted history-empty">No saved investigations yet.</p>';return}
  for(const item of records){
    const button=document.createElement('button');button.textContent='◷ '+item.question;
    button.title='Saved '+item.updated_at.slice(0,16)+' · Click to inspect stored graph memory';
    button.onclick=async()=>{
      try{const n=await api('/api/entities/'+encodeURIComponent(item.id));
        modal('Stored investigation',`<p><strong>${esc(n.question)}</strong> · ${esc(n.updated_at.slice(0,16))}</p><p>${esc(n.answer)}</p><ol>${(n.facts||[]).map(f=>`<li>${esc(f.text)}</li>`).join('')}</ol><h3>Persisted tool and evidence trace</h3><pre>${esc((n.tool_steps||[]).map(s=>s.tool+' → '+s.results+' results').join('\n'))}</pre><ol>${(n.graph_trace||[]).map(p=>`<li>${esc(p.label)}</li>`).join('')}</ol><p>Saved to this workspace graph. Re-run the question to see current data.</p>`)
      }catch(e){modal('Memory unavailable',esc(e.message))}
    };
    $('#history').append(button)
  }
}
function sourceLink(url){try{const u=new URL(url);return u.protocol==='https:'&&u.hostname==='github.com'?`<a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer">Open original source ↗</a>`:''}catch{return ''}}
function showSource(s){modal(s.name,`<span class="citation">${esc(s.type)} · Updated ${esc(s.updated_at?.slice(0,10))}</span><pre>${esc(s.content||s.rationale||'Public activity record; see its source link.')}</pre>${isPublic?`${sourceLink(s.source_url||s.url)} ${s.activity_source_url?sourceLink(s.activity_source_url):''}<p>Source system: ${esc(s.source_system)} · Method: ${esc(s.method)}<br>Collected: ${esc(s.collected_at)}<br>Inferred: ${esc(s.inferred)} ${esc(s.inferred_reason||'')}<br>${esc(s.updated_at_basis||'')}</p><p style="overflow-wrap:anywhere">${esc(s.content_hash)}</p>`:s.url?`<p>Original source (fictional demo URL):<br><code>${esc(s.url)}</code></p>`:''}<p>Source ID: ${esc(s.id)}</p>`)}
async function showCoverage(){try{const data=await api('/api/coverage');modal('FalkorDB · Data coverage',`<p>This is the shipped public snapshot. Source cards report their own capture dates. A missing source means it was not collected—not necessarily that it is private or does not exist.</p><pre>${esc(JSON.stringify(data,null,2))}</pre><p>No automated watcher is started with the app. See the repository’s public-data guide for opt-in refresh and deletion instructions.</p>`)}catch(e){modal('Coverage unavailable',esc(e.message))}}
$('#chat-form').onsubmit=e=>{e.preventDefault();ask($('#question').value)};$('#question').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask($('#question').value)}};document.addEventListener('click',e=>{const b=e.target.closest('[data-question]');if(b)ask(b.dataset.question)});document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key==='k'){e.preventDefault();$('#question').focus()}});
$('#new-chat').onclick=()=>{if(busy)return;$('#conversation').innerHTML=welcome;$('#question').focus();selectNode(rootEntity)};
$('#help').onclick=()=>modal('A company brain you can inspect','<p>ContextMind connects people, systems, projects, documents, tickets, chats, and decisions. Ask a question to follow graph relationships and inspect the evidence behind the answer.</p><p>With LLM_PROVIDER=openai, NovaPay uses live model-selected, bounded read-only graph tools; disabled mode uses a deterministic router. Check the sidebar mode before presenting. NovaPay and all source URLs are fictional. Local demo mode uses JSON storage; the Docker deployment uses FalkorDB. External connectors, authentication, and per-user access control are not implemented.</p><p>Keyboard shortcut: Ctrl / ⌘ K to ask a question.</p>');$('#workspace').onclick=()=>modal('Choose a workspace','<p><a href="/dashboard?workspace=novapay">NovaPay — fictional sandbox</a></p><p><a href="/dashboard?workspace=falkordb">FalkorDB — public GitHub snapshot</a></p><p>Separate graphs and runtime storage. Switching never merges company data.</p>');
$('.sidebar nav').onclick=async e=>{let b=e.target.closest('[data-page]');if(!b)return;document.querySelectorAll('.nav').forEach(x=>x.classList.toggle('active',x===b));const page=b.dataset.page;try{if(page==='ask'){$('#question').focus();return}if(page==='graph'){await selectNode(rootEntity);$('.context').scrollIntoView({behavior:'smooth'});return}if(page==='decisions'){ask(isPublic?'Why did FalkorDB choose Cypher?':'Why was Analytics Migration delayed?');return}if(page==='sources'){let records=await api('/api/entities');records=records.filter(n=>['Document','Guide','Version','Ticket','Message','Meeting','Incident'].includes(n.type));modal('Source library',records.map((s,i)=>`<button class="modal-record" style="text-align:left;width:100%" data-library="${i}"><h3>${esc(s.name)}</h3><span>${esc(s.type)} · ${esc(s.updated_at.slice(0,10))}</span></button>`).join(''));document.querySelectorAll('[data-library]').forEach(el=>el.onclick=()=>showSource(records[+el.dataset.library]));return}if(page==='risks'){if(isPublic)await showCoverage();else ask('Which critical systems have no active owner?')}}catch(e){modal('Something went wrong',esc(e.message))}};
(async()=>{try{
  const health=await api('/api/health');
  $('#backend').textContent=(health.backend==='demo'?'JSON storage':'FalkorDB storage')+(isPublic?' · Public snapshot':health.synthesis.endsWith('tool_calling')?' · LIVE LLM AGENT'+(health.llm_configured?'':' · KEY MISSING'):' · Deterministic · Fictional demo');
  entities=await api('/api/entities');$('#entity-count').textContent=entities.length;
  const g=await api('/api/graph/subgraph?entity_id='+rootEntity+'&depth=2');
  $('#link-count').textContent=g.edges.length;draw(g);await selectNode(rootEntity,false);await loadHistory();
}catch(e){$('#backend').textContent='Graph connection unavailable';modal('Connection error',esc(e.message))}})();
if(isPublic)$('#help').onclick=()=>modal('FalkorDB public brain','<p>Explore a bounded snapshot of public FalkorDB GitHub repositories, selected docs, releases, issues, and contributors. It is not a live feed and contains no internal company context.</p><p>Source excerpts are attributed, not independently verified. Contribution counts are not maintainer status. No private data, financial claims, invented rationale, or compatibility promises.</p><p>Use Data coverage to inspect collection limits. Storage mode is shown separately from workspace identity.</p>');

// Demo links prefill a question; sending remains an explicit user action.
const demoQuestion=new URLSearchParams(location.search).get('question');
if(demoQuestion){$('#question').value=demoQuestion.slice(0,2000);$('#question').focus()}
