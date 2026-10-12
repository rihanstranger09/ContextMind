"""Validation and replay of normalized public snapshots, without network access."""
import json
import hashlib
from datetime import datetime
from urllib.parse import urlsplit
from graph.store import NODE_TYPES, REL_TYPES

PROVENANCE=('source_url','source_system','method','collected_at','content_hash','visibility','inferred')
def validate_snapshot(snapshot):
    ids=set()
    for record in snapshot['nodes']+snapshot['edges']:
        if any(key not in record for key in PROVENANCE): raise ValueError('Missing public provenance')
        url=urlsplit(record['source_url'])
        if url.scheme!='https' or url.hostname!='github.com' or url.username or url.password:
            raise ValueError('This snapshot importer currently accepts GitHub public sources only')
        if record['visibility']!='public': raise ValueError('Non-public source rejected')
        if datetime.fromisoformat(record['collected_at'].replace('Z','+00:00')).tzinfo is None: raise ValueError('Timezone required')
        if not record['content_hash'].startswith('sha256:') or len(record['content_hash'])!=71: raise ValueError('Invalid content hash')
        expected='sha256:'+hashlib.sha256(json.dumps({k:v for k,v in record.items() if k not in ('content_hash','collected_at')},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if record['content_hash']!=expected: raise ValueError('Content hash mismatch')
    for n in snapshot['nodes']:
        if n['type'] not in NODE_TYPES or n['id'] in ids: raise ValueError('Invalid or duplicate node')
        if n['type']=='Person' and ('email' in n or not n.get('login')): raise ValueError('Public login required; email prohibited')
        ids.add(n['id'])
    for e in snapshot['edges']:
        if e['type'] not in REL_TYPES or e['source'] not in ids or e['target'] not in ids: raise ValueError('Invalid or dangling edge')

def replay(store,path):
    if store.workspace != "falkordb": raise ValueError("Public snapshots require the isolated FalkorDB workspace")
    snapshot=json.loads(open(path).read()); validate_snapshot(snapshot)
    with store.lock:
        for digest in snapshot.get('suppressed',[]):
            if store.backend=='demo': store.suppressed.add(digest)
            else: store.query('MERGE (:PrivacyTombstone {digest:$digest})',digest=digest)
        store.batching=True
        try:
            # Reconcile this source's current bounded snapshot, not an ever-growing union.
            incoming={n['id'] for n in snapshot['nodes']}
            if store.backend=='demo':
                store.nodes={k:n for k,n in store.nodes.items() if n.get('source_system')!='github' or k in incoming}
                store.edges=[e for e in store.edges if e.get('source_system')!='github']
                store.metadata=snapshot['metadata']
            else:
                store.query('MATCH (a:Entity)-[r]->(b:Entity) DELETE r')
                for n in store.search():
                    if n.get('source_system')=='github' and n['id'] not in incoming:
                        store.query('MATCH (n:Entity {id:$id}) DETACH DELETE n',id=n['id'])
            for n in store.search(type='Person'):
                if store.is_suppressed(n['id']): store.forget_person(n['id'])
            for node in snapshot['nodes']: store.upsert(node,[])
            for edge in snapshot['edges']: store.add_edge(edge)
        finally:
            store.batching=False
            store.flush()
    return snapshot['metadata']
