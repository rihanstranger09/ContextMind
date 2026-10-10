import hashlib
import json
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from pathlib import Path
from fastapi import FastAPI,HTTPException,Header,Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel,Field
from graph.store import Store
from graph.tools import Tools
from agents.company_brain import Agent

@asynccontextmanager
async def lifespan(app):
    app.state.store=Store()
    yield
VERSION = '1.0.0-mvp'
FRONTEND = Path(__file__).resolve().parents[1] / 'frontend'
app=FastAPI(title='ContextMind',version=VERSION,lifespan=lifespan)
def store(): return app.state.store
def require_entity(id):
    n=store().get(id)
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
def health():
    metadata = dict(version=VERSION, graph_mode=store().backend,
                    sample_data='NovaPay', backend=store().backend, company='NovaPay',
                    fictional_data=True, synthesis='deterministic graph evidence')
    try:
        if not store().get('sys_database'):
            raise RuntimeError('Seed data unavailable')
    except Exception:
        return JSONResponse(status_code=503, content=dict(status='unhealthy', **metadata))
    return dict(status='healthy', **metadata)

@app.get('/dashboard', include_in_schema=False)
@app.get('/dashboard/', include_in_schema=False)
def dashboard():
    return FileResponse(FRONTEND / 'index.html')
@app.get('/api/entities')
def entities(q:str='',type:str|None=None): return store().search(q,type)
@app.get('/api/entities/{id}')
def entity(id:str): return require_entity(id)
@app.post('/api/chat')
def chat(body:Question): return Agent(store()).ask(body.question)
@app.post('/api/impact')
def impact(body:Impact):
    n=require_entity(body.system_id)
    if n['type']!='System': raise HTTPException(422,'Expected a System')
    return Agent(store()).ask('What is at risk if '+n['name']+' is unavailable, and who should respond?')
@app.get('/api/experts/{id}')
def experts(id:str): require_entity(id); return Tools(store()).find_experts(id)
@app.get('/api/decisions/{id}/trace')
def decision(id:str): require_entity(id); return Tools(store()).explain_decision(id)
@app.get('/api/graph/subgraph')
def subgraph(entity_id:str='sys_database',depth:int=Query(2,ge=0,le=3)):
    require_entity(entity_id); return store().subgraph(entity_id,depth)
@app.get('/api/risks')
def risks(): return Tools(store()).knowledge_gaps()
@app.post('/api/ingest/{kind}')
def ingest(kind:str,body:Record,authorization:str=Header(default='')):
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
app.mount('/',StaticFiles(directory=Path(__file__).resolve().parents[1]/'frontend',html=True),name='frontend')
