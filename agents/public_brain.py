"""Conservative public-artifact retrieval. Quotes are source evidence, not inferred decisions."""
import re
from datetime import datetime, timezone
from uuid import uuid4
from graph.tools import normalize

STOP={'how','do','i','a','the','is','with','for','and','of','to','in','it','what','which','can','use','using','falkordb','me','show','about','are','has','any','on','does','get','find','from','you','should','we','an'}

def tokens(text):
    return {t for t in normalize(text).split() if len(t)>2 and t not in STOP}

class PublicAgent:
    def __init__(self, store): self.s=store

    def ask(self, question):
        q=normalize(question); facts=[]; paths=[]; sources={}; notices=[]
        repos=self.s.search(type='Repository')
        matches=[]
        for n in repos:
            names=[n['id'],n['name'],*n.get('aliases',[])]
            if n['name']=='FalkorDB/FalkorDB': names=[a for a in names if normalize(a)!='falkordb']
            score=max((len(normalize(a)) for a in names if f' {normalize(a)} ' in f' {q} '),default=0)
            if score: matches.append((score,n))
        matches.sort(key=lambda x:(-x[0],x[1]['id']))
        selected=matches[0][1] if matches else None
        # A bare FalkorDB reference does not select its core repository when discussing the whole org.
        if selected and selected['name'].lower()=='falkordb/falkordb' and 'core' not in q:
            selected=None
        intent='public_search'

        def related_path(n):
            es=self.s.adjacent(n['id'])
            primary=next(([e] for e in es if e['type'] in ('ABOUT','IN_REPO','VERSION','OWNS','PUBLISHES')),[])
            topic=next(([e] for e in es if e['type']=='DOCUMENTS' and tokens(self.s.get(e['target'])['name']) & tokens(q)),[])
            return topic+primary

        def add(text, source, path=None):
            path=path if path is not None else related_path(source)
            if not path or not source.get('source_url'): return
            if path not in paths: paths.append(path)
            sources[source['id']]=source
            facts.append(dict(text=text,source_ids=[source['id']],path_indices=[paths.index(path)]))

        missing='I do not have enough connected public context to answer confidently. This information is not in the collected snapshot; that does not prove it is unavailable elsewhere.'
        if re.search(r'\b(revenue|salary|salaries|private|internal strategy|funding forecast|password|annual income)\b',q):
            intent='insufficient_context'
        elif any(t in q for t in ['why','rationale','decision','roadmap','compatib','supports falkordb v','support falkordb v','supported version','breaking changes','between v','from v1']):
            intent='insufficient_context'
            notices.append('No hand-verified rationale, version-compatibility matrix, or version-diff extraction is available. Raw release notes are not promoted to decisions.')
        elif any(t in q for t in ['maintain','contributor','contributes','expert','who owns']):
            intent='public_activity'
            if selected:
                owners=[e for e in self.s.adjacent(selected['id']) if e['type']=='OWNS' and e['target']==selected['id']]
                if owners: add(f"GitHub organization FalkorDB owns {selected['name']}. This does not identify its human maintainers.",selected,owners[:1])
                contributions=[e for e in self.s.adjacent(selected['id']) if e['type']=='CONTRIBUTES_TO' and e['target']==selected['id']]
                for e in sorted(contributions,key=lambda e:self.s.get(e['source'])['name'].lower()):
                    person=self.s.get(e['source'])
                    source=dict(person,activity_source_url=e['source_url'])
                    add(f"{person['name']}: {e['contributions']} contributions recorded by GitHub for {selected['name']}. Repository total, not recent activity or a maintainer designation.",source,[e])
                notices.append('Contributor sample is bounded to five API entries, displayed alphabetically. No personal performance ranking. CODEOWNERS, if collected, is source text with path-scoped rules, not proof of repository-wide maintenance.')
            else:
                # Org-wide activity is repository metadata, never a ranking of real people.
                for r in sorted(repos,key=lambda n:n.get('pushed_at') or '',reverse=True)[:6]:
                    add(f"{r['name']} — GitHub pushed_at {r.get('pushed_at')}; archived: {r['archived']}; fork: {r['is_fork']}. Push timestamps are not commit-frequency or support guarantees.",r)
        elif any(t in q for t in ['release','version','what changed','newest','latest']):
            intent='public_releases'
            versions=self.s.search(type='Version')
            if selected: versions=[n for n in versions if n.get('repository_id')==selected['id']]
            else:
                core=next((n for n in repos if n['name']=='FalkorDB/FalkorDB'),None)
                versions=[n for n in versions if core and n.get('repository_id')==core['id']]
            for v in sorted(versions,key=lambda n:n.get('published_at') or '',reverse=True)[:3]:
                add(f"{v['name']} — published {v['published_at']}; prerelease: {v['prerelease']}. Release-note excerpt: {v['content'][:1200]}",v)
            notices.append('These are the most recent releases in this bounded snapshot, not a guarantee of the latest live release. No compatibility inferred from tag numbers.')
        elif any(t in q for t in ['issue','bug','ticket','need help','contribute']):
            intent='public_issues'
            issues=self.s.search(type='Ticket')
            if selected: issues=[n for n in issues if n.get('repository_id')==selected['id']]
            elif 'performance' in q or 'large graphs' in q:
                core=next((r for r in repos if r['name']=='FalkorDB/FalkorDB'),None)
                issues=[n for n in issues if core and n.get('repository_id')==core['id']]
            if 'open' in q or 'need help' in q: issues=[n for n in issues if n['status']=='OPEN']
            if 'need help' in q: issues=[n for n in issues if any(label.lower() in ('help wanted','good first issue') for label in n['labels'])]
            terms=tokens(q)-{'open','issues','issue','reported','anyone','help','need','tickets','contribute'}
            if terms and not selected:
                issues=[n for n in issues if tokens(n['name']+' '+n['content']+' '+' '.join(n['labels'])) & terms]
            for n in sorted(issues,key=lambda n:n['updated_at'],reverse=True)[:5]:
                add(f"{n['name']} — {n['ticket_type']}, {n['status'].lower()}, updated {n['updated_at']}. Reported text (not independently verified): {n['content'][:700]}",n)
            notices.append('At most ten recently updated issues/PRs per selected repository were collected. Missing issues are not evidence that a problem does not exist.')
        else:
            docs=self.s.search(type='Document')+self.s.search(type='Guide')
            terms=tokens(q)
            # Scope documents to a resolved repository plus matching official documentation pages.
            scored=[]
            for n in docs:
                text=n.get('content',''); title_tokens=tokens(n['name']+' '+n.get('path',''))
                overlap=len(terms & tokens(text))
                own=bool(selected and n.get('repository_id')==selected['id'])
                score=overlap+3*len(terms & title_tokens)+(6 if own else 0)
                if score and (overlap or own): scored.append((score,n))
            for _,n in sorted(scored,key=lambda x:(-x[0],x[1]['id']))[:4]:
                body=re.sub(r'^---\s*\n.*?\n---\s*', '', n['content'], count=1, flags=re.S)
                parts=[p.strip() for p in re.split(r'\n\s*\n',body) if p.strip() and not p.strip().startswith(('[![','<img','<a href'))]
                relevant=sorted(enumerate(parts),key=lambda x:(-len(tokens(x[1]) & terms),x[0]))[:2]
                excerpts='\n\n'.join(p for _,p in sorted(relevant))[:1600]
                add(f"{n['name']} — source excerpt:\n{excerpts}",n)
            if facts:
                notices.append('These are attributed source excerpts, not independently tested instructions or a claim of official support. Review the linked source before using example code.')
                if 'neo4j' in q or 'benchmark' in q: notices.append('Comparison claims are publisher-authored, not an independent benchmark. Conditions and versions matter.')
        graph_edges=[]
        for path in paths:
            for e in path:
                if e not in graph_edges: graph_edges.append(e)
        ids={e[k] for e in graph_edges for k in ('source','target')}
        now=datetime.now(timezone.utc)
        stale=[]
        for n in sources.values():
            date=n.get('pushed_at') if n['type']=='Repository' else n.get('updated_at')
            threshold=180 if n['type'] in ('Guide','Document') else 30 if n['type']=='Ticket' and n.get('status')=='OPEN' else 90
            if date and (now-datetime.fromisoformat(date.replace('Z','+00:00'))).days>threshold: stale.append(n['id'])
        return dict(id='public_trace_'+uuid4().hex,question=question,intent=intent,
                    answer='Here is the evidence in the collected public FalkorDB graph.' if facts else missing,
                    facts=facts,sources=list(sources.values()),graph_trace=[dict(edges=p,label=' · '.join(
                        f"{self.s.get(e['source'])['name']} → {e['type']} → {self.s.get(e['target'])['name']}" for e in p)) for p in paths],
                    recommended_actions=[],notices=notices,resolved_entities=[selected] if selected else [],
                    graph=dict(nodes=[self.s.get(id) for id in sorted(ids)],edges=graph_edges),
                    freshness=dict(stale_sources=stale,latest_source_at=max((n['collected_at'] for n in sources.values()),default=None)))
