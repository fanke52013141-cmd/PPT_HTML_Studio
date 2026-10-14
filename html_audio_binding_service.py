"""Adapt the existing TTS completion boundary to HTML's derived audio clock."""
import json
from pathlib import Path
from html_visual_store import load_scene
from html_audio_binder import bind_scene_to_audio
from html_scene_editing import _validate_binding


def validate_course_audio_bindings(run_dir):
    run = Path(run_dir)
    read = lambda path: json.loads(path.read_text(encoding="utf-8"))
    contract = read(run/"planning/visual_contract.json")
    results = []
    for slide in contract["slides"]:
        sid = slide["slide_id"]
        scene = load_scene(run, sid)
        binding = read(run/f"planning/html_visual/binding-{sid}.json")
        timeline = read(run/f"slides/{sid}/audio_timeline.json")
        _validate_binding(binding, scene, slide["narration_beats"])
        if scene.get("version") in ("0.6.0", "0.7.0"):
            from html_semantic_qa import prepare
            plan = read(run/f"planning/html_visual/plan-{sid}.json")
            bound = prepare(scene, plan, binding, slide, timeline)["bound_scene"]
        else:
            bound = bind_scene_to_audio(scene, timeline, binding)
        results.append({"slide_id": sid, "duration_ms": bound["durationMs"], "clock": "audio_timeline"})
    if not results:
        raise ValueError("HTML course has no pages")
    # Author files stay at author time. A04 and export consume this same pure binding.
    return {"passed": True, "pages": results, "author_written": False}
