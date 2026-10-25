import copy
from pathlib import Path
from PIL import Image

import html_review_cache as cache
from html_page_budget import page_budgeted, current_budget
from html_visual_review_service import HtmlReviewDependencies
from checks.test_html_candidate_capacity_solver import ROOT, document


def test_exact_cache_stable_screenshot_corruption_and_input_invalidation(tmp_path, monkeypatch):
    calls=[]; font=['one']
    monkeypatch.setattr(cache,'resolved_scene_inputs',lambda scene,*a:{'scene':scene,'font':font[0]})
    @cache.cached_review
    def render(scene, *, run_dir, deps, diagnostic=False, preflight_dir=None):
        calls.append(copy.deepcopy(scene))
        Image.new('RGB',(10,10),'white').save(Path(run_dir)/'shared.png')
        return {'passed':True,'screenshot':'shared.png'}
    @page_budgeted
    def task(*, run_dir,deps,checkpoint=lambda:None):
        scene=document()
        first=render(scene,run_dir=run_dir,deps=deps)
        Image.new('RGB',(10,10),'black').save(run_dir/'shared.png')
        second=render(scene,run_dir=run_dir,deps=deps)
        assert first==second and len(calls)==1
        with Image.open(run_dir/second['screenshot']) as image: assert image.getpixel((0,0))==(255,255,255)
        (run_dir/second['screenshot']).write_bytes(b'corrupt')
        render(scene,run_dir=run_dir,deps=deps)
        assert len(calls)==2
        font[0]='two'
        render(scene,run_dir=run_dir,deps=deps)
        assert len(calls)==3
        render(scene,run_dir=run_dir,deps=deps,diagnostic=True)
        render(scene,run_dir=run_dir,deps=deps,preflight_dir=run_dir/'temporal')
        assert len(calls)==5
        assert any(e['kind']=='review_cache_hit' for e in current_budget().events)
    task(run_dir=tmp_path,deps=HtmlReviewDependencies(ROOT,lambda **kw:{}))
