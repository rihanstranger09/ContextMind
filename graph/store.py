import hashlib
import json
import os
from pathlib import Path
from threading import RLock
from graph.schema import NODE_TYPES, REL_TYPES
from graph.connection import connection_options

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / 'data/sample_company.json'
PUBLIC_SEED = ROOT / 'data/falkordb/snapshot.json'

class Store:
    """Isolated workspace storage; all graph values parameterized, identifiers allowlisted."""
    def __init__(self, backend=None, path=None, workspace='novapay', seed_path=None):
        if workspace not in ('novapay', 'falkordb'): raise ValueError('Unknown workspace')
        self.workspace = workspace
        self.backend = backend or os.getenv('GRAPH_BACKEND', 'demo')
        self.lock = RLock()
        self.batching = False
        self.seed_path = Path(seed_path or (PUBLIC_SEED if workspace=='falkordb' else SEED))
        self.path = Path(path or ('.runtime/falkordb.json' if workspace=='falkordb' else '.runtime/demo.json'))
        if self.backend == 'falkordb':
            from falkordb import FalkorDB
            graph_name = os.getenv('FALKOR_GRAPH','contextmind') + ('_public_falkordb' if workspace=='falkordb' else '')
            self.db = FalkorDB(**connection_options()).select_graph(graph_name)
            from redis.exceptions import ResponseError
            try:
                self.db.query('CREATE INDEX ON :Entity(id)')
            except ResponseError as error:
                if str(error) != "Attribute 'id' is already indexed":
                    raise
            if not self.db.query('MATCH (n:Entity) RETURN n.id LIMIT 1').result_set: self.seed()
        elif self.backend == 'demo':
            raw=json.loads((self.path if self.path.exists() else self.seed_path).read_text())
            if workspace=='falkordb' and not self.path.exists():
                from graph.ingestion import validate_snapshot
                validate_snapshot(raw)
            self.nodes={n['id']:n for n in raw['nodes']}
            self.edges=raw['edges']
            self.suppressed=set(raw.get('suppressed',[]))
            self.metadata=raw.get('metadata',{})
        else: raise ValueError('Unknown GRAPH_BACKEND')

    def seed(self):
        raw=json.loads(self.seed_path.read_text())
        if self.workspace=='falkordb':
            from graph.ingestion import validate_snapshot
            validate_snapshot(raw)
        for digest in raw.get('suppressed',[]):
            self.query('MERGE (:PrivacyTombstone {digest:$digest})',digest=digest)
        for n in raw['nodes']: self.upsert(n, [])
        for e in raw['edges']: self.add_edge(e)

    def query(self, query, **params): return self.db.query(query, params).result_set

    def counts(self):
        """Post-write graph totals for the operator recording receipt (no payloads)."""
        if self.backend == 'demo':
            return dict(nodes=len(self.nodes), relationships=len(self.edges))
        return dict(
            nodes=self.query('MATCH (n:Entity) RETURN count(n)')[0][0],
            relationships=self.query('MATCH (:Entity)-[r]->(:Entity) RETURN count(r)')[0][0],
        )

    def get(self,id):
        if self.backend=='demo': return self.nodes.get(id)
        rows=self.query('MATCH (n:Entity {id:$id}) RETURN n.payload',id=id)
        return json.loads(rows[0][0]) if rows else None

    def search(self,text='',type=None):
        text=text.lower()
        limit=2000 if self.workspace=='falkordb' else 100
        if self.backend=='demo':
            return [n for n in self.nodes.values() if n['type']!='AgentDecision' and
                    (not type or n['type']==type) and
                    (not text or text in json.dumps([n['id'],n['name'],n.get('aliases',[])]).lower())][:limit]
        rows=self.query('MATCH (n:Entity) WHERE n.kind <> "AgentDecision" AND ($kind = "" OR n.kind = $kind) AND n.search CONTAINS $text RETURN n.payload LIMIT $limit',kind=type or '',text=text,limit=limit)
        return [json.loads(r[0]) for r in rows]

    def recent_investigations(self,limit=10):
        """Persisted fictional-workspace answer memory (never public contributor history)."""
        if self.workspace!='novapay': return []
        if self.backend=='demo':
            records=[n for n in self.nodes.values() if n['type']=='AgentDecision']
            return sorted(records,key=lambda n:(n['updated_at'],n['id']),reverse=True)[:limit]
        rows=self.query('MATCH (n:Entity:AgentDecision) RETURN n.payload ORDER BY n.updated_at DESC LIMIT $limit',limit=limit)
        return [json.loads(row[0]) for row in rows]

    def adjacent(self,id):
        if self.backend=='demo': return [e for e in self.edges if id in (e['source'],e['target'])]
        rows=self.query('MATCH (a:Entity)-[r]->(b:Entity) WHERE a.id=$id OR b.id=$id RETURN a.id,type(r),b.id,r.payload LIMIT 500',id=id)
        return [json.loads(r[3]) if r[3] else dict(source=r[0],type=r[1],target=r[2]) for r in rows]

    def add_edge(self,e):
        if e['type'] not in REL_TYPES: raise ValueError('Unsupported relationship')
        if not self.get(e['source']) or not self.get(e['target']): return
        if self.backend=='demo':
            key=lambda x:(x['source'],x['type'],x['target'])
            self.edges=[old for old in self.edges if key(old)!=key(e)] + [e]
        else:
            self.query('MATCH (a:Entity {id:$a}), (b:Entity {id:$b}) MERGE (a)-[r:'+e['type']+']->(b) SET r.payload=$payload',a=e['source'],b=e['target'],payload=json.dumps(e))

    def is_suppressed(self,id):
        digest=hashlib.sha256(id.encode()).hexdigest()
        if self.backend=='demo': return digest in self.suppressed
        return bool(self.query('MATCH (t:PrivacyTombstone {digest:$digest}) RETURN t.digest',digest=digest))

    def upsert(self,n,edges):
        if n['type'] not in NODE_TYPES: raise ValueError('Unsupported node type')
        with self.lock:
            if n['type']=='Person' and self.is_suppressed(n['id']): return
            if self.backend=='demo': self.nodes[n['id']]=n
            else:
                self.query('MERGE (n:Entity:'+n['type']+' {id:$id}) SET n.kind=$kind,n.name=$name,n.updated_at=$updated_at,n.search=$search,n.payload=$payload',id=n['id'],kind=n['type'],name=n['name'],updated_at=n['updated_at'],search=json.dumps([n['id'],n['name'],n.get('aliases',[])]).lower(),payload=json.dumps(n))
            for e in edges: self.add_edge(e)
            self.flush()

    def flush(self):
        if self.backend=='demo' and not self.batching:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temp=self.path.with_suffix('.tmp')
            temp.write_text(json.dumps(dict(nodes=list(self.nodes.values()),edges=self.edges,suppressed=sorted(self.suppressed),metadata=self.metadata)))
            temp.replace(self.path)

    def forget_person(self,id):
        with self.lock:
            n=self.get(id)
            if not n or n['type']!='Person': raise ValueError('Person not found')
            digest=hashlib.sha256(id.encode()).hexdigest()
            if self.backend=='demo':
                self.suppressed.add(digest)
                # Remove historical generated traces too; they may contain copied names.
                removed={id}|{k for k,v in self.nodes.items() if v['type']=='AgentDecision'}
                self.nodes={k:v for k,v in self.nodes.items() if k not in removed}
                self.edges=[e for e in self.edges if e['source'] not in removed and e['target'] not in removed]
                self.flush()
            else:
                self.query('MERGE (:PrivacyTombstone {digest:$digest})',digest=digest)
                self.query('MATCH (n:Entity) WHERE n.id=$id OR n.kind="AgentDecision" DETACH DELETE n',id=id)

    def subgraph(self,id,depth=2):
        seen={id}; edges=[]; frontier={id}
        for _ in range(depth):
            nxt=set()
            for key in sorted(frontier):
                for e in self.adjacent(key):
                    if e['type']=='USED_EVIDENCE': continue
                    other=e['target'] if e['source']==key else e['source']
                    if other not in seen and len(seen)>=70: continue
                    if e not in edges: edges.append(e)
                    if other not in seen: seen.add(other); nxt.add(other)
            frontier=nxt
        return dict(nodes=[n for k in sorted(seen) if (n:=self.get(k))],edges=edges)
