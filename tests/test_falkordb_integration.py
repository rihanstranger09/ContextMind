"""Actual FalkorDB integration; opt in with FALKOR_INTEGRATION=1 and a running database."""
import os
from uuid import uuid4
import pytest
from graph.store import Store, PUBLIC_SEED
from graph.ingestion import replay
from agents.public_brain import PublicAgent

pytestmark=pytest.mark.skipif(os.getenv('FALKOR_INTEGRATION')!='1',reason='Requires a real FalkorDB service')

def test_native_graph_provenance_replay_and_privacy(monkeypatch):
    monkeypatch.setenv('FALKOR_GRAPH','contextmind_test_'+uuid4().hex)
    s=Store('falkordb',workspace='falkordb')
    try:
        assert s.query('MATCH (o:Organization)-[:OWNS]->(r:Repository) RETURN count(r)')[0][0]>100
        r=PublicAgent(s).ask('How do I use FalkorDB with LangChain?')
        assert r['facts'] and r['sources']
        assert all(e.get('content_hash') for p in r['graph_trace'] for e in p['edges'])
        before=s.query('MATCH (n:Entity) RETURN count(n)')[0][0]
        replay(s,PUBLIC_SEED)
        assert s.query('MATCH (n:Entity) RETURN count(n)')[0][0]==before
        person=s.search(type='Person')[0]
        s.forget_person(person['id'])
        replay(s,PUBLIC_SEED)
        assert s.get(person['id']) is None
        assert s.is_suppressed(person['id'])
    finally:
        s.db.delete()
