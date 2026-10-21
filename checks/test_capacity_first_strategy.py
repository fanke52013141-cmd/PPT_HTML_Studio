"""capacity_first deterministic repair against the real capacity QA (browser CI)."""
import copy

import html_capacity_repair as capacity
import html_visual_store as store
from checks.test_html_candidate_agent import draft  # noqa: F401  (pytest fixture)


def test_capacity_first_repairs_overflow_without_any_model_call(draft):
    run, scene = draft
    original = copy.deepcopy(scene)
    store.save_scene(run, scene["id"], scene, 0)
    result = capacity.repair_capacity(
        run, scene["id"], {"expected_revision": 1, "scope": ["headline"]},
    )
    assert result["status"] == "candidate", result
    assert result["review"]["passed"]
    assert result["provider_calls"] == 0 and result["author_unchanged"] is True
    assert store.load_scene(run, scene["id"]) == original
    operations = result["request"]["operations"]
    assert operations
    kinds = {operation["kind"] for operation in operations}
    assert kinds <= {"set_presentation", "set_text_style"}
    fonts = [operation["values"]["fontSizePx"] for operation in operations
             if operation["kind"] == "set_text_style"]
    assert all(font >= capacity.MIN_READABLE_PX for font in fonts)
    assert result["candidate"]["scene"] != original
    assert result["attempts"] and result["attempts"][-1]["passed"]


def test_capacity_first_stops_with_explicit_no_fit_without_model(draft):
    run, scene = draft
    headline = next(node for node in scene["nodes"] if node["id"] == "headline")
    headline["runs"] = [{"text": "字" * 400, "emphasis": False}]
    store.save_scene(run, scene["id"], scene, 0)
    original = store.load_scene(run, scene["id"])
    result = capacity.repair_capacity(
        run, scene["id"], {"expected_revision": 1, "scope": ["headline"]},
    )
    assert result["status"] == "needs_revision"
    assert result["reason"] == "NO_DETERMINISTIC_CAPACITY_FIT"
    assert result["provider_calls"] == 0 and result["author_unchanged"] is True
    assert store.load_scene(run, scene["id"]) == original
    assert result["attempts"]
