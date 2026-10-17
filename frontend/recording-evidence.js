/* Opt-in, response-derived filming receipt. Never pass headers or request options here. */
(function (root) {
  'use strict';
  function receipt(status, body) {
    if (!Number.isInteger(status) || status < 200 || status >= 300 || !body || !body.record) return null;
    const r = body.record, c = body.graph_counts;
    // A dedicated disposable recording ticket only. Reject unexpected values rather than printing them.
    if (!/^ticket_video_[a-z0-9]{4,32}$/.test(r.id) || !['OPEN', 'RESOLVED'].includes(r.status) ||
        typeof r.updated_at !== 'string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|\+\d\d:\d\d)$/.test(r.updated_at) ||
        !Number.isFinite(Date.parse(r.updated_at)) || !c ||
        !Number.isSafeInteger(c.nodes) || c.nodes < 0 ||
        !Number.isSafeInteger(c.relationships) || c.relationships < 0) return null;
    return Object.freeze({status, id:r.id, state:r.status, timestamp:r.updated_at,
      nodes:c.nodes, relationships:c.relationships});
  }
  function createPanel(doc) {
    const box=doc.createElement('aside');box.id='recording-evidence';box.setAttribute('aria-label','Operator API response evidence');
    box.setAttribute('aria-live','polite');box.hidden=true;doc.body.append(box);
    return function show(status, body) {
      box.replaceChildren();box.hidden=true;
      const safe=receipt(status,body);
      if (!safe) return false;
      const heading=doc.createElement('strong');heading.textContent='Fictional operator write · API response';box.append(heading);
      for (const [label,value] of Object.entries({HTTP:safe.status,'Ticket ID':safe.id,State:safe.state,
          'Updated at':safe.timestamp,'Graph nodes':safe.nodes,'Graph relationships':safe.relationships})) {
        const row=doc.createElement('div'),key=doc.createElement('span'),val=doc.createElement('b');
        key.textContent=label;val.textContent=String(value);row.append(key,val);box.append(row);
      }
      box.hidden=false;return true;
    };
  }
  if (typeof module==='object' && module.exports) module.exports={receipt,createPanel};
  if (root && root.document && new URLSearchParams(root.location.search).get('demo_evidence')==='1' &&
      new URLSearchParams(root.location.search).get('workspace')!=='falkordb') {
    root.showRecordingEvidence=createPanel(root.document);
  }
})(typeof window!=='undefined'?window:null);
