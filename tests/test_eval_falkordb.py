"""Offline regression set: coverage/trace correctness, not an LLM quality benchmark."""
import json
import time
from pathlib import Path
import pytest
from graph.store import Store
from agents.public_brain import PublicAgent
CASES=[json.loads(line) for line in Path('data/falkordb/eval.jsonl').read_text().splitlines()]

@pytest.mark.parametrize('case',CASES,ids=[c['q'] for c in CASES])
def test_eval(case,tmp_path):
    s=Store('demo',tmp_path/'public.json',workspace='falkordb')
    started=time.monotonic()
    r=PublicAgent(s).ask(case['q'])
    # Loose guard against accidental network calls; <2 seconds is a deployment target, not asserted here.
    assert time.monotonic()-started<10
    assert r['intent']==case['intent']
    if not case['expect_evidence']:
        assert not r['facts'] and not r['sources']
        assert 'not in the collected snapshot' in r['answer']
        return
    assert r['facts'] and r['sources'] and r['graph_trace']
    assert any(case['must_cite_fragment'].lower() in n['source_url'].lower() for n in r['sources'])
    sources={n['id'] for n in r['sources']}
    for fact in r['facts']:
        assert fact['source_ids'] and set(fact['source_ids'])<=sources
        assert fact['path_indices']
        for i in fact['path_indices']:
            for e in r['graph_trace'][i]['edges']:
                assert e in s.adjacent(e['source'])
                assert e['source_url'] and e['content_hash']
