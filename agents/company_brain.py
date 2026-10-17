from datetime import datetime,timezone
from uuid import uuid4
from graph.tools import Tools,normalize

class Agent:
    def __init__(self,store): self.s=store; self.t=Tools(store)
    def ask(self,question):
        q=question.lower(); paths=[]; facts=[]; actions=[]; tool_steps=[]
        def run(name, fn, *args):
            result=fn(*args)
            focus=' → '.join(args[:2]) if name=='shortest_evidence_path' else (args[0] if args and isinstance(args[0],str) else None)
            tool_steps.append(dict(tool=name, focus=focus, results=len(result)))
            return result
        entities=run('resolve_entity',self.t.resolve_entity,question)
        intent='knowledge'
        def add(text,ps):
            paths.extend(p for p in ps if p not in paths)
            facts.append(dict(text=text,path_indices=[paths.index(p) for p in ps]))
        if any(w in q for w in ['gap','no active owner','no owner','without owner']):
            intent='risk'
            for gap in run('knowledge_gaps',self.t.knowledge_gaps):
                facts.append(dict(text=f"{gap['entity']['name']}: {', '.join(gap['missing'])}. This is missing graph data, not proof of no real-world owner.",path_indices=[],entity_id=gap['entity']['id']))
        elif ('shortest path' in normalize(q) or 'how is' in normalize(q) and 'connected to' in normalize(q)) and len(entities)>=2:
            intent='connection'
            words=normalize(q)
            pair=sorted(entities[:3],key=lambda n:(words.find(normalize(n['name'])) if normalize(n['name']) in words else 10**6,n['id']))[:2]
            start,end=pair
            path=run('shortest_evidence_path',self.t.shortest_evidence_path,start['id'],end['id'])
            if path:
                add(f"A shortest recorded path from {start['name']} to {end['name']} uses {len(path)} graph relationships. This is a bounded search of stored evidence, not proof of a current assignment.",[path])
        elif entities:
            entity=entities[0]; id=entity['id']; name=entity['name']
            if any(w in q for w in ['why','decision','delayed']):
                intent='decision'
                decision_targets=[id]
                if entity['type']=='System':
                    decision_targets += sorted({p[0]['source'] for p in run('analyze_system_impact',self.t.analyze_system_impact,id) if self.s.get(p[0]['source'])['type']=='Project'})
                for item in [item for target in decision_targets for item in run('explain_decision',self.t.explain_decision,target)]:
                    add(f"{item['decision']['name']}: {item['decision']['rationale']}",item['paths'])
            if any(w in q for w in ['risk','break','down','outage','unavailable','affected','fails','impact']):
                intent='impact'
                for p in run('analyze_system_impact',self.t.analyze_system_impact,id): add(f"{self.s.get(p[0]['source'])['name']} depends on {name} {'indirectly' if len(p)>1 else 'directly'}.",[p])
            if any(w in q for w in ['owner','owns','respond','should','outage','unavailable']):
                if intent=='knowledge': intent='ownership'
                for p in run('find_owner',self.t.find_owner,id): add(f"{self.s.get(p[0]['source'])['name']} {'leads the owning team for' if len(p)>1 else 'owns'} {name}.",[p])
            if any(w in q for w in ['expert','knows','experience','respond','should','unavailable']):
                if intent=='knowledge': intent='expert'
                experts=run('find_experts',self.t.find_experts,id)
                for rank,expert in enumerate(experts[:3],1):
                    person=expert['person']; add(f"{rank}. {person['name']} — evidence score {expert['score']}; {person.get('availability','availability unknown').lower()}{'; on call' if person.get('on_call') else ''}.",expert['paths'])
                if experts: actions.append('Confirm current availability with the owning team before paging the highest-ranked responder. Expert scores reflect recorded graph relationships, not certainty.')
            if any(w in q for w in ['block','ticket','status']):
                intent='blockers'
                for p in run('find_project_blockers',self.t.find_project_blockers,id):
                    ticket=self.s.get(p[0]['source']); add(f"{ticket['name']} is {ticket['status'].lower().replace('_',' ')} and blocks {name}.",[p])
            if intent=='knowledge':
                for e in self.s.adjacent(id):
                    other=e['source'] if e['target']==id else e['target']; n=self.s.get(other)
                    if n['type']=='Document': add(n.get('content',n['name']),[[e]])
        ids={e[k] for p in paths for e in p for k in ['source','target']}
        ids.update(f['entity_id'] for f in facts if 'entity_id' in f)
        sources=run('get_evidence_sources',self.t.get_evidence_sources,ids)
        trace=[dict(edges=p,label=' · '.join(f"{self.s.get(e['source'])['name']} → {e['type']} → {self.s.get(e['target'])['name']}" for e in p)) for p in paths]
        now=datetime.now(timezone.utc)
        stale=[n['id'] for n in sources if (now-datetime.fromisoformat(n['updated_at'].replace('Z','+00:00'))).days>90]
        answer='I do not have enough connected company context to answer confidently.' if not facts else {'impact':'Here’s the blast radius in your company graph.','ownership':'Here’s who owns it.','expert':'The strongest matches in your company graph.','decision':'The decision, connected to its evidence.','blockers':'These open tickets are blocking progress.','risk':'These critical systems have knowledge gaps.','connection':'Here’s the shortest recorded connection.','knowledge':'Here’s the connected context.'}[intent]
        result=dict(id='trace_'+uuid4().hex,question=question,answer=answer,intent=intent,facts=facts,sources=sources,graph_trace=trace,tool_steps=tool_steps,recommended_actions=actions,resolved_entities=entities[:3],freshness=dict(stale_sources=stale,latest_source_at=max((n['updated_at'] for n in sources),default=None)),graph=dict(nodes=[self.s.get(id) for id in sorted(ids)],edges=[e for i,p in enumerate(paths) for e in p if e not in [x for earlier in paths[:i] for x in earlier]]))
        self.s.upsert(dict(id=result['id'],type='AgentDecision',name=question,question=question,answer=answer,intent=intent,facts=facts,graph_trace=trace,tool_steps=tool_steps,source_ids=[n['id'] for n in sources],updated_at=now.isoformat()),[dict(source=result['id'],type='USED_EVIDENCE',target=n['id']) for n in sources])
        return result
