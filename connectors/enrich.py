"""Deterministic document-topic classification, explicitly marked derived/inferred."""
import re
from connectors.github import digest

def title_for(text,fallback):
    # MDX front matter is preferable to a '#' comment inside a code example.
    front=re.match(r'^---\s*\n(.*?)\n---',text,re.S)
    if front:
        title=re.search(r'^title:\s*[\"\']?(.+?)[\"\']?\s*$',front.group(1),re.M)
        if title: return title.group(1)
    without_code=re.sub(r'```.*?```','',text,flags=re.S)
    h=re.search(r'^#\s+(.+)$',without_code,re.M)
    return h.group(1) if h else fallback

def enrich(snapshot):
    nodes=snapshot['nodes']; edges=snapshot['edges']
    topics={'genai-tools/langchain.mdx':('integration_langchain','Integration','LangChain'),
            'genai-tools/llamaindex.mdx':('integration_llamaindex','Integration','LlamaIndex'),
            'genai-tools/graphrag-sdk.mdx':('integration_graphrag','Integration','GraphRAG SDK'),
            'agentic-memory/graphiti.mdx':('integration_graphiti','Integration','Graphiti'),
            'agentic-memory/cognee.mdx':('integration_cognee','Integration','Cognee'),
            'genai-tools/mcpserver/index.mdx':('integration_mcp','Integration','MCP server'),
            'cypher/index.mdx':('skill_cypher','Skill','Cypher')}
    for n in list(nodes):
        if n['type'] not in ('Document','Guide'): continue
        n['name']=title_for(n['content'],n['name'])
        n['content_hash']=digest({k:v for k,v in n.items() if k not in ('content_hash','collected_at')})
        topic=topics.get(n.get('path'))
        if not topic: continue
        id,kind,name=topic
        prov={k:n[k] for k in ('source_url','url','source_system','collected_at','visibility')}
        prov.update(method='derived',inferred=True,inferred_reason='Topic classified from the official documentation file path; no support status or compatibility inferred')
        t=dict(id=id,type=kind,name=name,updated_at=n['updated_at'],aliases=[name],
               content='Topic documented in '+n['path']+'. Consult the source for actual instructions and support constraints.',**prov)
        t['content_hash']=digest(t); nodes.append(t)
        e=dict(source=n['id'],type='DOCUMENTS',target=id,**prov)
        e['content_hash']=digest(e); edges.append(e)
    for record in nodes+edges:
        record["content_hash"]=digest({k:v for k,v in record.items() if k not in ("content_hash","collected_at")})
    return snapshot
