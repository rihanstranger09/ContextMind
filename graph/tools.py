import re
from collections import deque

def normalize(text): return re.sub(r'[^a-z0-9]+',' ',text.lower()).strip()
class Tools:
    def __init__(self,store): self.s=store
    def resolve_entity(self,text):
        q=normalize(text); matches=[]
        for n in self.s.search():
            names=[n['name'], n['id'], *n.get('aliases',[])]
            score=max((len(normalize(a)) for a in names if f' {normalize(a)} ' in f' {q} '),default=0)
            if score: matches.append((score,n))
        return [n for _,n in sorted(matches,key=lambda x:-x[0])]
    def links(self,id,kind=None,incoming=False):
        return [e for e in self.s.adjacent(id) if e['target' if incoming else 'source']==id and (not kind or e['type']==kind)]
    def shortest_evidence_path(self,start_id,end_id,max_hops=4):
        """Bounded BFS over recorded company edges; returns a shortest path, if any.

        Edges remain in their stored direction. USED_EVIDENCE is excluded so
        previously saved answers cannot create artificial shortcuts.
        """
        allowed={'MEMBER_OF','LEADS','OWNS','WORKED_ON','USES','DEPENDS_ON',
                 'ABOUT','ASSIGNED_TO','BLOCKS','BASED_ON','IMPACTS',
                 'AUTHORED','RESOLVED_BY'}
        if start_id==end_id or not self.s.get(start_id) or not self.s.get(end_id): return []
        queue=deque([(start_id,[])]); seen={start_id}
        while queue:
            key,path=queue.popleft()
            if len(path)>=max_hops: continue
            priority={'WORKED_ON':0,'OWNS':1,'DEPENDS_ON':2,'USES':3,'MEMBER_OF':4,'LEADS':5}
            for e in sorted(self.s.adjacent(key),key=lambda e:(priority.get(e['type'],9),e['type'],e['source'],e['target'])):
                if e['type'] not in allowed: continue
                other=e['target'] if e['source']==key else e['source']
                if other in seen: continue
                node=self.s.get(other)
                if not node or node['type']=='AgentDecision': continue
                candidate=path+[e]
                if other==end_id: return candidate
                if len(seen)>=70: continue
                seen.add(other);queue.append((other,candidate))
        return []

    def find_owner(self,id):
        paths=[]
        for e in self.links(id,'OWNS',True):
            paths.append([e])
            for lead in self.links(e['source'],'LEADS',True): paths.append([lead,e])
        return paths
    def analyze_system_impact(self,id):
        queue=deque([(id,[])]); seen={id}; paths=[]
        while queue:
            key,path=queue.popleft()
            for e in self.links(key,incoming=True):
                if e['type']=='USES': paths.append([e]+path)
                if e['type']=='DEPENDS_ON' and e['source'] not in seen and len(path)<5:
                    seen.add(e['source']); p=[e]+path; paths.append(p); queue.append((e['source'],p))
        return paths
    def find_experts(self,id,limit=5):
        candidates={}
        related=[([],id)] + [(p,p[0]['source']) for p in self.analyze_system_impact(id)]
        for tail,key in related:
            for e in self.links(key,incoming=True):
                paths=[]; score=0
                if e['type'] in ['WORKED_ON','OWNS'] and self.s.get(e['source'])['type']=='Person': paths=[([e]+tail,5 if e['type']=='OWNS' else 3,e['source'])]
                if e['type'] in ['ABOUT','AFFECTS']:
                    for x in self.s.adjacent(e['source']):
                        if x['type']=='AUTHORED' and x['target']==e['source']: paths.append(([x,e]+tail,2,x['source']))
                        if x['type']=='RESOLVED_BY' and x['source']==e['source']: paths.append(([x,e]+tail,4,x['target']))
                for path,score,person in paths:
                    c=candidates.setdefault(person,dict(person=self.s.get(person),score=0,paths=[]))
                    if path not in c['paths']: c['score']+=score; c['paths'].append(path)
        for path in self.find_owner(id):
            if len(path)==2:
                person=path[0]['source']; c=candidates.setdefault(person,dict(person=self.s.get(person),score=0,paths=[])); c['score']+=5; c['paths'].append(path)
        return sorted(candidates.values(),key=lambda x:(-x['score'],x['person']['name']))[:limit]
    def explain_decision(self,id):
        node=self.s.get(id)
        decisions=[node] if node['type']=='Decision' else [self.s.get(e['source']) for e in self.links(id,'IMPACTS',True)]
        return [dict(decision=d,paths=[[e] for e in self.links(d['id'])]) for d in decisions]
    def find_project_blockers(self,id):
        return [[e] for e in self.links(id,'BLOCKS',True) if self.s.get(e['source']).get('status') in ['OPEN','IN_PROGRESS','BLOCKED']]
    def knowledge_gaps(self):
        result=[]
        for n in self.s.search(type='System'):
            if n.get('criticality')!='CRITICAL': continue
            missing=[]
            if not self.find_owner(n['id']): missing.append('no recorded owner')
            if not any(self.s.get(e['source'])['type']=='Document' for e in self.links(n['id'],'ABOUT',True)): missing.append('no linked documentation')
            if missing: result.append(dict(entity=n,missing=missing))
        return result
    def get_evidence_sources(self,ids):
        nodes={id:self.s.get(id) for id in ids}
        for id in list(ids):
            for e in self.s.adjacent(id):
                other=e['source'] if e['target']==id else e['target']; n=self.s.get(other)
                if n and n['type'] in ['Document','Ticket','Message','Meeting','Incident']: nodes[other]=n
        return [n for n in nodes.values() if n and n['type'] in ['Document','Ticket','Message','Meeting','Incident']][:12]
