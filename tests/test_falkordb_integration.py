"""Actual FalkorDB integration; opt in with FALKOR_INTEGRATION=1 and a running database."""
import os
from uuid import uuid4
import pytest
from graph.store import Store, PUBLIC_SEED
from graph.ingestion import replay
from agents.public_brain import PublicAgent
from graph.showcase import graph_showcase, company_showcase

pytestmark=pytest.mark.skipif(os.getenv('FALKOR_INTEGRATION')!='1',reason='Requires a real FalkorDB service')

def test_native_graph_provenance_replay_and_privacy(monkeypatch):
    monkeypatch.setenv('FALKOR_GRAPH','contextmind_test_'+uuid4().hex)
    s=Store('falkordb',workspace='falkordb')
    c=Store('falkordb',workspace='novapay')
    try:
        decision_proof=company_showcase(c)
        assert decision_proof['native_cypher_executed']
        assert {n['type'] for n in decision_proof['evidence']}=={'Ticket','Message','Meeting','Document'}
        assert s.query('MATCH (o:Organization)-[:OWNS]->(r:Repository) RETURN count(r)')[0][0]>100
        proof=graph_showcase(s)
        assert proof['backend']=='falkordb' and proof['native_cypher_executed']
        assert proof['entity_count']>=332 and proof['relationship_count']>=378
        assert len(proof['paths'])==3
        assert all(p['nodes'][1]['name']=='FalkorDB/falkordb-py' for p in proof['paths'])
        r=PublicAgent(s).ask('How do I use FalkorDB with LangChain?')
        assert r['facts'] and r['sources']
        assert r['resolved_entities'][0]['id'] in {n['id'] for n in r['graph']['nodes']}
        assert all(e.get('content_hash') for p in r['graph_trace'] for e in p['edges'])
        reopened=Store('falkordb',workspace='falkordb')
        assert reopened.get('org_falkordb')['name']=='FalkorDB'
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
        c.db.delete()
