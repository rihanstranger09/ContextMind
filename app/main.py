import hashlib
import json
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from pathlib import Path
from typing import Literal
from fastapi import FastAPI,HTTPException,Header,Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel,Field
from graph.store import Store
from graph.tools import Tools
from agents.company_brain import Agent
from agents.public_brain import PublicAgent

@asynccontextmanager
async def lifespan(app):
    app.state.store=Store()
    app.state.public_store=Store(workspace="falkordb")
    yield
VERSION = '1.0.0-mvp'
FRONTEND = Path(__file__).resolve().parents[1] / 'frontend'
app=FastAPI(title='ContextMind',version=VERSION,lifespan=lifespan)
Workspace = Literal['novapay', 'falkordb']
def store(workspace='novapay'):
    return app.state.public_store if workspace=='falkordb' else app.state.store

def brain(workspace):
    return PublicAgent(store(workspace)) if workspace=='falkordb' else Agent(store(workspace))

def require_entity(id,workspace='novapay'):
    n=store(workspace).get(id)
    if not n: raise HTTPException(404,'Entity not found')
    return n
class Question(BaseModel):
    question:str=Field(min_length=2,max_length=2000)
    user_id:str|None=None
class Impact(BaseModel): system_id:str
class Record(BaseModel):
    id:str=Field(pattern=r'^[a-zA-Z0-9_-]{1,100}$')
    name:str=Field(min_length=1,max_length=200)
    content:str=Field(default='',max_length=20000)
    status:str=Field(default='OPEN',pattern='^(OPEN|IN_PROGRESS|BLOCKED|RESOLVED|CLOSED)$')
    priority:str=Field(default='MEDIUM',pattern='^(CRITICAL|HIGH|MEDIUM|LOW)$')
    updated_at:datetime
    about_id:str|None=None
    project_id:str|None=None
    assignee_id:str|None=None
@app.get('/api/health')
def health(workspace:Workspace="novapay"):
    metadata = dict(version=VERSION, graph_mode=store(workspace).backend,
                    sample_data='NovaPay' if workspace=='novapay' else None, backend=store(workspace).backend, company='NovaPay' if workspace=='novapay' else 'FalkorDB', workspace=workspace,
                    fictional_data=workspace=='novapay', synthesis='deterministic graph evidence')
    try:
        if not store(workspace).get('sys_database' if workspace=='novapay' else 'org_falkordb'):
            raise RuntimeError('Seed data unavailable')
    except Exception:
        return JSONResponse(status_code=503, content=dict(status='unhealthy', **metadata))
    return dict(status='healthy', **metadata)

@app.get('/dashboard', include_in_schema=False)
@app.get('/dashboard/', include_in_schema=False)
def dashboard():
    return FileResponse(FRONTEND / 'index.html')
@app.get('/api/entities')
def entities(q:str='',type:str|None=None,workspace:Workspace='novapay'): return store(workspace).search(q,type)
@app.get('/api/entities/{id}')
def entity(id:str,workspace:Workspace='novapay'): return require_entity(id,workspace)
@app.post('/api/chat')
def chat(body:Question,workspace:Workspace='novapay'): return brain(workspace).ask(body.question)
@app.post('/api/impact')
def impact(body:Impact,workspace:Workspace='novapay'):
    n=require_entity(body.system_id,workspace)
    if n['type']!='System': raise HTTPException(422,'Expected a System')
    return brain(workspace).ask('What is at risk if '+n['name']+' is unavailable, and who should respond?')
@app.get('/api/experts/{id}')
def experts(id:str,workspace:Workspace='novapay'):
    require_entity(id,workspace)
    if workspace=='falkordb': raise HTTPException(422,'Use public activity queries; personal expertise ranking is disabled')
    return Tools(store(workspace)).find_experts(id)
@app.get('/api/decisions/{id}/trace')
def decision(id:str,workspace:Workspace='novapay'): require_entity(id,workspace); return Tools(store(workspace)).explain_decision(id)
@app.get('/api/graph/subgraph')
def subgraph(entity_id:str|None=None,depth:int=Query(2,ge=0,le=3),workspace:Workspace='novapay'):
    entity_id=entity_id or ('org_falkordb' if workspace=='falkordb' else 'sys_database')
    require_entity(entity_id,workspace); return store(workspace).subgraph(entity_id,depth)
@app.get('/api/risks')
def risks(workspace:Workspace='novapay'):
    return Tools(store(workspace)).knowledge_gaps() if workspace=='novapay' else []
@app.post('/api/ingest/{kind}')
def ingest(kind:str,body:Record,authorization:str=Header(default=''),workspace:Workspace='novapay'):
    if workspace=='falkordb': raise HTTPException(403,'Public workspace requires provenance-validated snapshot ingestion')
    token=os.getenv('INGEST_TOKEN')
    if not token: raise HTTPException(403,'Ingestion disabled. Configure INGEST_TOKEN.')
    if not secrets.compare_digest(authorization,'Bearer '+token): raise HTTPException(401,'Invalid ingestion token')
    types={'documents':'Document','tickets':'Ticket','messages':'Message'}
    if kind not in types: raise HTTPException(404,'Unsupported record type')
    current=store().get(body.id)
    if current and current['type']!=types[kind]: raise HTTPException(409,'ID belongs to another entity type')
    if body.updated_at.tzinfo is None: raise HTTPException(422,'updated_at must include a timezone')
    if current and datetime.fromisoformat(current['updated_at'].replace('Z','+00:00'))>body.updated_at: raise HTTPException(409,'Older than current record')
    edges=[]
    for key,rel,typ in [('about_id','ABOUT','System'),('project_id','BLOCKS' if kind=='tickets' else 'REFERENCES','Project'),('assignee_id','ASSIGNED_TO','Person')]:
        target=getattr(body,key)
        if target:
            if require_entity(target)['type']!=typ: raise HTTPException(422,'Invalid relationship target')
            edges.append(dict(source=body.id,type=rel,target=target))
    # Relationship changes require explicit support; never leave an old assignee/blocker silently attached.
    for rel in ['ABOUT','BLOCKS','REFERENCES','ASSIGNED_TO']:
        existing={e['target'] for e in store().adjacent(body.id) if e['source']==body.id and e['type']==rel} if current else set()
        desired={e['target'] for e in edges if e['type']==rel}
        if existing and existing!=desired: raise HTTPException(409,'Relationship replacement is not supported in this MVP; preserve existing targets')
    n=body.model_dump(mode='json'); n.update(type=types[kind],source='manual',last_synced_at=datetime.now(timezone.utc).isoformat(),content_hash=hashlib.sha256(json.dumps(n,sort_keys=True).encode()).hexdigest())
    store().upsert(n,edges)
    return dict(record=n,created=current is None)
@app.get('/api/workspaces')
def workspaces():
    return [dict(id='novapay',name='NovaPay',mode='fictional sandbox'),
            dict(id='falkordb',name='FalkorDB',mode='public GitHub snapshot')]

@app.get('/api/coverage')
def coverage(workspace:Workspace='novapay'):
    if workspace=='novapay': return dict(workspace=workspace,fictional=True)
    import json
    from graph.store import PUBLIC_SEED
    # Describes the shipped snapshot; runtime source cards carry their own collection dates.
    return dict(shipped_snapshot=json.loads(PUBLIC_SEED.read_text())['metadata'],
                runtime_org_collected_at=store(workspace).get('org_falkordb')['collected_at'])

@app.delete('/api/people/{id}')
def forget_person(id:str,workspace:Workspace='falkordb',authorization:str=Header(default='')):
    token=os.getenv('INGEST_TOKEN')
    if not token: raise HTTPException(403,'Deletion disabled; configure INGEST_TOKEN for an operator')
    if not secrets.compare_digest(authorization,'Bearer '+token): raise HTTPException(401,'Invalid token')
    n=require_entity(id,workspace)
    if n['type']!='Person': raise HTTPException(422,'Only Person deletion is supported')
    store(workspace).forget_person(id)
    return dict(deleted=True,suppressed_on_replay=True,
                scope='Active workspace Person node, incident relationships, generated traces. Public source text and version-controlled snapshots require separate review and removal.')

app.mount('/',StaticFiles(directory=Path(__file__).resolve().parents[1]/'frontend',html=True),name='frontend')
