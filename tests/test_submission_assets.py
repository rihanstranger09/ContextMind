"""Guard the draft screenplay, captions and fail-closed seed entry point."""
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]

def load(name,relative):
    spec=importlib.util.spec_from_file_location(name,ROOT/relative)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v4_caption_text_exactly_matches_script():
    caps=load('v4captions','scripts/generate_v4_captions.py')
    rows=caps.cues()
    assert len(rows)==16 and rows[0][0]==0 and rows[-1][1]==120
    saved=(ROOT/'presentation/ContextMind-v4-draft.srt').read_text()
    assert saved==caps.render(rows)
    assert 'No LLM is wired in' in saved
    assert 'VID-42' in saved


def test_v4_captions_reject_overlaps_and_missing_audio_timing(tmp_path):
    caps=load('v4captions2','scripts/generate_v4_captions.py')
    timing=tmp_path/'times.json';timing.write_text('{"2":[0,10]}')
    with pytest.raises(ValueError,match='Overlapping'):
        caps.cues(timings=timing)


def test_seed_refuses_non_native_mode(monkeypatch,tmp_path):
    seed=load('seedv4','scripts/seed_demo_graph.py')
    monkeypatch.setenv('GRAPH_BACKEND','demo')
    with pytest.raises(SystemExit,match='falkordb'):
        seed.seed(tmp_path/'name.env')
    assert not (tmp_path/'name.env').exists()


def test_readme_scope_and_query_docs():
    readme=(ROOT/'README.md').read_text()
    model=(ROOT/'docs/graph-model-and-queries.md').read_text()
    for expected in ('Company Brain','docker compose up --build','```mermaid','Provenance and build timeline',
                     'AI assistance disclosure','complete local setup','No LLM'):
        assert expected.lower() in readme.lower()
    for expected in ('BASED_ON','IMPACTS','Store.counts()', 'shortest_evidence_path',
                     'application-side', 'MATCH (n:Entity)', 'USED_EVIDENCE'):
        assert expected in model
