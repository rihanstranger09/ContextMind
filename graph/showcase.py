"""Bounded, read-only graph proof for the public snapshot.

No caller-supplied Cypher, node IDs or graph names are accepted. In native mode
all metrics and path IDs come from FalkorDB queries; demo mode is labeled as a
JSON preview and never claims that Cypher ran.
"""
from time import perf_counter

ORG_ID = 'org_falkordb'
PYTHON_REPO_ID = 'repo_720742399'  # Stable GitHub repository ID in the snapshot.
CYPHER = '''MATCH (org:Entity {id: $org})-[:OWNS]->(repo:Entity {id: $repo})-[:VERSION]->(release:Entity)
RETURN org.id, repo.id, release.id
ORDER BY release.name DESC LIMIT 3'''


def graph_showcase(store):
    if store.workspace != 'falkordb':
        raise ValueError('Graph proof is limited to the public workspace')
    start = perf_counter()
    native = store.backend == 'falkordb'
    if native:
        node_count = store.query('MATCH (n:Entity) RETURN count(n)')[0][0]
        edge_count = store.query('MATCH (:Entity)-[r]->(:Entity) RETURN count(r)')[0][0]
        rows = store.query(CYPHER, org=ORG_ID, repo=PYTHON_REPO_ID)
        paths = [(org, repo, release) for org, repo, release in rows]
    else:
        node_count = len(store.nodes)
        edge_count = len(store.edges)
        owned = any(e['source'] == ORG_ID and e['target'] == PYTHON_REPO_ID
                    and e['type'] == 'OWNS' for e in store.edges)
        release_ids = [e['target'] for e in store.edges if owned and
                       e['source'] == PYTHON_REPO_ID and e['type'] == 'VERSION']
        paths = [(ORG_ID, PYTHON_REPO_ID, n['id']) for n in
                 sorted((store.get(id) for id in release_ids if store.get(id)),
                        key=lambda n: n['name'], reverse=True)[:3]]

    # Fetch values through the same store adapter, but do not expose payloads,
    # credentials, graph names, or unbounded arbitrary query results.
    results = []
    for org, repo, release in paths:
        nodes = [store.get(id) for id in (org, repo, release)]
        if not all(nodes) or [n['type'] for n in nodes] != ['Organization', 'Repository', 'Version']:
            continue
        results.append(dict(nodes=[dict(id=n['id'], name=n['name'], type=n['type'],
                                        source_url=n.get('source_url')) for n in nodes],
                            relationships=['OWNS', 'VERSION']))
    return dict(workspace='falkordb', backend=store.backend, native_cypher_executed=native,
                entity_count=node_count, relationship_count=edge_count,
                cypher=CYPHER, parameters=dict(org=ORG_ID, repo=PYTHON_REPO_ID),
                paths=results, elapsed_ms=round((perf_counter() - start) * 1000, 2),
                timing_scope='Server-side graph proof only; not a benchmark or end-to-end response time')
