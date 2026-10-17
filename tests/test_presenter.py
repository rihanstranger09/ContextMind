"""The video recipe is inspectable and fails closed when footage is missing."""
import importlib.util
from pathlib import Path
import pytest


def recipe():
    path = Path(__file__).resolve().parents[1] / 'tests/browser/render-showcase.py'
    spec = importlib.util.spec_from_file_location('render_showcase', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_narration_timing_and_caption_coverage():
    m = recipe()
    assert len(m.CLIPS) == len(m.STARTS) == 5
    assert m.STARTS == (0, 16, 39, 57, 75)
    assert m.CUES[0][0] == 0 and m.CUES[-1][1] == 95
    assert all(a < b and (i == 0 or a >= m.CUES[i - 1][1])
               for i, (a, b, _) in enumerate(m.CUES))
    assert m.stamp(75) == '00:01:15,000'
    assert 'Cypher' in ' '.join(text for _, _, text in m.CUES)


def test_renderer_requires_real_recording(tmp_path, monkeypatch):
    m = recipe()
    monkeypatch.setattr(m, 'VIDEO', tmp_path / 'missing.webm')
    with pytest.raises(SystemExit, match='Missing media:'):
        m.render()


def test_company_video_recipe_guards_media_and_scene_order(tmp_path, monkeypatch):
    import importlib.util
    path=Path(__file__).resolve().parents[1]/'tests/browser/render-company-brain.py'
    spec=importlib.util.spec_from_file_location('company_render',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    assert len(m.CLIPS)==len(m.STARTS)==11
    assert '06-shortest-path' in m.NAMES
    assert m.STARTS[5] == 62.6
    assert m.CUES[-1][1]==139.5
    assert 'Company Brain' in m.CUES[-1][2]
    monkeypatch.setattr(m,'VIDEO',tmp_path/'missing.webm')
    with pytest.raises(SystemExit,match='Missing media'):
        m.render()
