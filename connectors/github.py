"""Public-only, snapshot-first GitHub collection. No raw API responses or emails saved."""
import base64
import hashlib
import json
import os
import re
import subprocess
import shutil
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

ORG = 'FalkorDB'
SELECTED = ['FalkorDB', 'falkordb-py', 'node-falkordb', 'JFalkorDB', 'falkordb-go',
            'GraphRAG-SDK', 'langchain-falkordb', 'FalkorDB-MCPServer', 'QueryWeaver', 'docs']
DOC_PATHS = ['getting-started/index.mdx', 'getting-started/clients.mdx', 'references/license.mdx',
             'genai-tools/langchain.mdx', 'genai-tools/llamaindex.mdx', 'genai-tools/graphrag-sdk.mdx',
             'genai-tools/mcpserver/index.mdx', 'cypher/index.mdx',
             'integrations/langchain.mdx', 'integrations/llamaindex.mdx',
             'agentic-memory/index.mdx', 'agentic-memory/graphiti.mdx', 'agentic-memory/cognee.mdx']
EMAIL = re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}')

def clean(text):
    return EMAIL.sub('[email redacted]', str(text or ''))

def digest(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

class GitHub:
    def __init__(self, delay=1.0):
        self.delay = delay
        self.requests = 0

    def get(self, path, optional=False):
        # Paths are constructed only from discovered public repos, not arbitrary URLs.
        if not path.startswith(('orgs/FalkorDB', 'repos/FalkorDB/')):
            raise ValueError('Only FalkorDB public org endpoints are allowed')
        time.sleep(self.delay)
        self.requests += 1
        token = os.getenv('GITHUB_TOKEN')
        if token and not shutil.which("gh"):
            import httpx
            r = httpx.get('https://api.github.com/' + path, headers={
                'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
                'User-Agent': 'ContextMind-public-snapshot'}, timeout=30)
            if optional and r.status_code in (404, 409): return None
            if r.status_code in (403, 429):
                raise RuntimeError('GitHub refused collection or rate limit reached; retry later. Existing snapshot preserved.')
            r.raise_for_status()
            return r.json()
        p = subprocess.run(['gh', 'api', path], capture_output=True, text=True, timeout=45)
        if p.returncode:
            if optional and ('HTTP 404' in p.stderr or 'HTTP 409' in p.stderr): return None
            raise RuntimeError('GitHub collection failed; check gh authentication/rate limits. Existing snapshot preserved.')
        return json.loads(p.stdout)

    def pages(self, path, max_pages=20):
        for page in range(1, max_pages + 1):
            batch = self.get(path + ('&' if '?' in path else '?') + f'per_page=100&page={page}')
            yield from batch
            if len(batch) < 100: return
        raise RuntimeError('Pagination cap reached; refusing to publish an incomplete repository inventory')


def collect(client, output, selected=SELECTED):
    now = datetime.now(timezone.utc).isoformat()
    nodes, edges, missing, coverage = {}, {}, [], {}
    def provenance(url, value, **extra):
        return dict(source_url=url, url=url, source_system='github', method='api',
                    collected_at=now, content_hash=digest(value), visibility='public', inferred=False, **extra)
    def node(id, kind, name, url, **attrs):
        attrs = json.loads(clean(json.dumps(attrs, ensure_ascii=False)))
        value = dict(id=id, type=kind, name=clean(name), updated_at=attrs.pop('updated_at', now), **attrs)
        value.update(provenance(url, value))
        nodes[id] = value
        return id
    def edge(a, rel, b, url, **attrs):
        value = dict(source=a, type=rel, target=b, **attrs)
        value.update(provenance(url, value))
        edges[(a, rel, b)] = value
    org = client.get('orgs/FalkorDB')
    node('org_falkordb', 'Organization', 'FalkorDB', org['html_url'], content=org.get('description') or '', aliases=['Falkor DB', 'the sponsor'])
    repos = [r for r in client.pages('orgs/FalkorDB/repos?type=public')
             if not r.get('private') and r['owner']['login'].lower() == 'falkordb']
    by_name = {r['name'].lower(): r for r in repos}
    for r in repos:
        rid = f"repo_{r['id']}"
        aliases = [r['name']]
        if r['name'] == 'falkordb-py': aliases += ['Python client', 'Python SDK', 'Python']
        if r['name'] == 'node-falkordb': aliases += ['Node.js client', 'Node client']
        if r['name'] == 'JFalkorDB': aliases += ['Java client']
        if r['name'] == 'FalkorDB': aliases += ['core repo', 'FalkorDB core', 'database engine']
        if r['name'] == 'GraphRAG-SDK': aliases += ['GraphRAG SDK', 'GraphRAG']
        if r['name'] == 'FalkorDB-MCPServer': aliases += ['MCP server', 'MCP']
        if r['name'] == 'langchain-falkordb': aliases += ['LangChain', 'LangChain integration']
        node(rid, 'Repository', r['full_name'], r['html_url'], github_id=r['id'],
             aliases=aliases, content=r.get('description') or '', language=r.get('language'),
             stars=r['stargazers_count'], forks=r['forks_count'], archived=r['archived'],
             is_fork=r['fork'], pushed_at=r['pushed_at'], updated_at=r['updated_at'],
             open_issues=r['open_issues_count'], topics=r.get('topics', []))
        # Org ownership is explicit, not an inference that a person maintains a repo.
        edge('org_falkordb', 'OWNS', rid, r['html_url'])
    for name in selected:
        r = by_name.get(name.lower())
        if not r:
            missing.append({'source': name, 'reason': 'not found in public org inventory'})
            continue
        rid, full = f"repo_{r['id']}", r['full_name']
        base = 'repos/' + full
        branch = quote(r['default_branch'], safe='')
        commit = client.get(base + '/commits/' + branch, optional=True)
        if not commit:
            missing.append({'source': full, 'reason': 'no readable default-branch commit'})
            continue
        sha = commit['sha']
        coverage[full] = dict(commit=sha, issues_limit=10, releases_limit=5, contributors_limit=5)
        readme = client.get(base + '/readme?ref=' + sha, optional=True)
        def add_file(f, path, kind='Document'):
            if not f or f.get('encoding') != 'base64': return
            text = clean(base64.b64decode(f['content']).decode('utf-8', errors='replace'))
            url = f'https://github.com/{full}/blob/{sha}/{quote(path, safe="/")}'
            did = 'doc_' + hashlib.sha256((full + '/' + path).encode()).hexdigest()[:20]
            title = re.search(r'^#\s+(.+)$', text, re.M)
            title = title.group(1) if title else full + ' · ' + path
            node(did, kind, title, url, content=text[:16000], doc_type='README' if 'readme' in path.lower() else 'GUIDE',
                 repository_id=rid, path=path, commit_sha=sha, excerpt_truncated=len(text)>16000,
                 updated_at=commit['commit']['committer']['date'], updated_at_basis='repository commit; file modification date not verified')
            edge(did, 'ABOUT', rid, url)
            edge('org_falkordb', 'PUBLISHES', did, url)
        if readme: add_file(readme, readme['path'])
        else: missing.append({'source': full + '/README', 'reason': 'not found'})
        if name == 'docs':
            tree = client.get(base + '/git/trees/' + sha + '?recursive=1')
            if tree.get('truncated'): raise RuntimeError('Documentation tree truncated')
            paths = [f['path'] for f in tree['tree'] if f['type']=='blob' and f['path'].endswith(('.md','.mdx'))]
            candidates = [p for p in paths if re.search(r'(getting.started|langchain|llamaindex|graphrag|cypher|agentic-memory|client|license|replication|quickstart|mcpserver)',p,re.I)]
            chosen = sorted(candidates, key=lambda p:(p not in DOC_PATHS,len(p),p))[:18]
            coverage[full]['docs_paths'] = chosen
            for path in chosen:
                f = client.get(base+'/contents/'+quote(path,safe='/')+'?ref='+sha, optional=True)
                add_file(f,path,'Guide')
        since=(datetime.now(timezone.utc)-timedelta(days=730)).isoformat()
        issues=client.get(base+'/issues?state=all&sort=updated&direction=desc&per_page=10&since='+quote(since))
        for issue in issues:
            tid=f"ticket_{issue['id']}"
            node(tid,'Ticket',issue['title'],issue['html_url'],content=clean(issue.get('body'))[:8000],
                 ticket_type='pr' if 'pull_request' in issue else 'issue',status=issue['state'].upper(),
                 labels=[label['name'] for label in issue.get('labels',[])],updated_at=issue['updated_at'],
                 created_at=issue['created_at'],repository_id=rid)
            edge(tid,'IN_REPO',rid,issue['html_url'])
            # Reporters are NOT assignees. Do not infer maintenance or responsibility.
        for release in client.get(base+'/releases?per_page=5'):
            if release.get('draft'): continue
            vid=f"version_{release['id']}"
            node(vid,'Version',full+' '+release['tag_name'],release['html_url'],tag=release['tag_name'],
                 content=clean(release.get('body'))[:12000],prerelease=release['prerelease'],
                 published_at=release['published_at'],updated_at=release['published_at'],repository_id=rid)
            edge(rid,'VERSION',vid,release['html_url'])
        for contributor in client.get(base+'/contributors?per_page=5',optional=True) or []:
            if contributor.get('type')!='User': continue
            pid=f"person_github_{contributor['id']}"
            node(pid,'Person',contributor['login'],contributor['html_url'],login=contributor['login'])
            edge(pid,'CONTRIBUTES_TO',rid,f'https://github.com/{full}/graphs/contributors',
                 contributions=contributor['contributions'],count_scope='GitHub repository contributor total; not a recent-activity measure')
        for path in ['.github/CODEOWNERS','CODEOWNERS','docs/CODEOWNERS']:
            f=client.get(base+'/contents/'+path+'?ref='+sha,optional=True)
            if f:
                add_file(f,path)
                coverage[full]['codeowners_path']=path
                # Scoped CODEOWNERS rules are retained as evidence, NOT promoted to repo-wide ownership.
                break
        else: missing.append({'source':full+'/CODEOWNERS','reason':'not found in standard locations; maintainers not inferred'})
    snapshot = dict(nodes=list(nodes.values()),edges=list(edges.values()),metadata=dict(
        workspace='falkordb',collected_at=now,source='GitHub public REST API',
        repository_count=len(repos),detail_coverage=coverage,missing=missing,
        unavailable=['Website crawl (network access unavailable here)', 'YouTube (not collected)',
                     'GitHub Discussions (not collected; requires GraphQL)', 'Discord/X (no consented collection)',
                     'Partner websites (not crawled)', 'Hand-verified decisions (none yet)'],
        note='Bounded snapshot, not a live feed. Forks labeled. No personal emails or maintenance inferred from contribution counts.'))
    # Publish only a fully collected and structurally validated snapshot.
    from connectors.enrich import enrich
    from graph.ingestion import validate_snapshot
    snapshot=enrich(snapshot)
    # Keep operator suppression from the previous published snapshot on recollection.
    existing_path=Path(output)
    suppressed=set(json.loads(existing_path.read_text()).get('suppressed',[])) if existing_path.exists() else set()
    if suppressed:
        removed={n['id'] for n in snapshot['nodes'] if n['type']=='Person' and hashlib.sha256(n['id'].encode()).hexdigest() in suppressed}
        snapshot['nodes']=[n for n in snapshot['nodes'] if n['id'] not in removed]
        snapshot['edges']=[e for e in snapshot['edges'] if e['source'] not in removed and e['target'] not in removed]
        snapshot['suppressed']=sorted(suppressed)
    validate_snapshot(snapshot)
    output = Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    temp=output.with_suffix('.tmp'); temp.write_text(json.dumps(snapshot,indent=2,ensure_ascii=False)); temp.replace(output)
    return snapshot
