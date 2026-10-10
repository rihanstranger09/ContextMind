import json
import os
from pathlib import Path
from threading import RLock

NODE_TYPES = {'Person','Team','Project','System','Document','Ticket','Message','Meeting','Decision','Skill','Incident','Policy','Event','AgentDecision'}
REL_TYPES = {'MEMBER_OF','LEADS','OWNS','WORKED_ON','HAS_SKILL','USES','DEPENDS_ON','BLOCKS','ASSIGNED_TO','ABOUT','REFERENCES','DISCUSSES','BASED_ON','IMPACTS','MADE_BY','AFFECTS','RESOLVED_BY','HAS_DOCUMENT','AUTHORED','USED_EVIDENCE'}

SEED = Path(__file__).resolve().parents[1] / 'data/sample_company.json'
class Store:
    """Shared, parameterized storage contract. No user-authored Cypher."""
    def __init__(self, backend=None, path=None):
        self.backend = backend or os.getenv('GRAPH_BACKEND', 'demo')
        self.lock = RLock()
        self.path = Path(path or '.runtime/demo.json')
        if self.backend == 'falkordb':
            from falkordb import FalkorDB
            self.db = FalkorDB(host=os.getenv('FALKOR_HOST','localhost'),port=int(os.getenv('FALKOR_PORT','6379'))).select_graph(os.getenv('FALKOR_GRAPH','contextmind'))
            if not self.db.query('MATCH (n:Entity) RETURN n.id LIMIT 1').result_set:
                self.seed()
        elif self.backend == 'demo':
            raw=json.loads((self.path if self.path.exists() else SEED).read_text())
            self.nodes={n['id']:n for n in raw['nodes']}; self.edges=raw['edges']
        else: raise ValueError('Unknown GRAPH_BACKEND')
    def seed(self):
        raw=json.loads(SEED.read_text())
        for n in raw['nodes']: self.upsert(n, [])
        for e in raw['edges']: self.add_edge(e)
    def query(self, query, **params): return self.db.query(query, params).result_set
    def get(self,id):
        if self.backend=='demo': return self.nodes.get(id)
        rows=self.query('MATCH (n:Entity {id:$id}) RETURN n.payload',id=id)
        return json.loads(rows[0][0]) if rows else None
    def search(self,text='',type=None):
        text=text.lower()
        if self.backend=='demo':
            return [n for n in self.nodes.values() if n['type']!='AgentDecision' and (not type or n['type']==type) and (not text or text in json.dumps([n['id'],n['name'],n.get('aliases',[])]).lower())][:100]
        rows=self.query('MATCH (n:Entity) WHERE n.kind <> "AgentDecision" AND ($kind = "" OR n.kind = $kind) AND contains(n.search,$text) RETURN n.payload LIMIT 100',kind=type or '',text=text)
        return [json.loads(r[0]) for r in rows]
    def adjacent(self,id):
        if self.backend=='demo': return [e for e in self.edges if id in (e['source'],e['target'])]
        return [dict(source=r[0],type=r[1],target=r[2]) for r in self.query('MATCH (a:Entity)-[r]->(b:Entity) WHERE a.id=$id OR b.id=$id RETURN a.id,type(r),b.id LIMIT 300',id=id)]
    def add_edge(self,e):
        if e['type'] not in REL_TYPES: raise ValueError('Unsupported relationship')
        if self.backend=='demo':
            if e not in self.edges: self.edges.append(e)
        else:
            self.query('MATCH (a:Entity {id:$a}), (b:Entity {id:$b}) MERGE (a)-[:'+e['type']+']->(b)',a=e['source'],b=e['target'])
    def upsert(self,n,edges):
        if n['type'] not in NODE_TYPES: raise ValueError('Unsupported node type')
        with self.lock:
            if self.backend=='demo': self.nodes[n['id']]=n
            else:
                self.query('MERGE (n:Entity:'+n['type']+' {id:$id}) SET n.kind=$kind,n.name=$name,n.updated_at=$updated_at,n.search=$search,n.payload=$payload',id=n['id'],kind=n['type'],name=n['name'],updated_at=n['updated_at'],search=json.dumps([n['id'],n['name'],n.get('aliases',[])]).lower(),payload=json.dumps(n))
            for e in edges: self.add_edge(e)
            if self.backend=='demo':
                self.path.parent.mkdir(parents=True,exist_ok=True)
                temp=self.path.with_suffix('.tmp'); temp.write_text(json.dumps(dict(nodes=list(self.nodes.values()),edges=self.edges))); temp.replace(self.path)
    def subgraph(self,id,depth=2):
        seen={id}; edges=[]; frontier={id}
        for _ in range(depth):
            nxt=set()
            for key in sorted(frontier):
                for e in self.adjacent(key):
                    other=e['target'] if e['source']==key else e['source']
                    if other not in seen and len(seen)>=70: continue
                    if e not in edges: edges.append(e)
                    if other not in seen: seen.add(other); nxt.add(other)
            frontier=nxt
        return dict(nodes=[n for k in sorted(seen) if (n:=self.get(k))],edges=edges)
