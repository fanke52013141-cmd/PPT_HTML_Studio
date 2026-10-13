"""Frozen independent semantic review service over existing snapshots and LLM."""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from html_build_snapshot import (SnapshotError, create_render_snapshot, digest,
                                 fresh_hash, json_bytes, safe_file, verify_snapshot)
from html_semantic_qa import (SemanticQAError, check_frames, evaluate_response,
                              prepare_inputs, prompts_for_beat, report_checks, seal)

ROOT = Path(__file__).resolve().parent


def project_review_dependencies(project, deps):
    """Both transports freeze the existing project text connection, never override it."""
    from dataclasses import replace
    from functools import partial
    from project_model_binding_service import freeze_project_models
    frozen = freeze_project_models(project, required=())
    return replace(deps, json_generator=partial(deps.json_generator, model_binding=frozen.text,
                                                temperature=0, max_tokens_limit=2048, request_timeout=90, strict_response=True),
                   semantic_model_identity=frozen.text.summary())


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def capture_semantic_inputs(run, root, slide, scene, capture):
    from html_storyboard_planning import load_template_catalog
    if scene.get("version") != "0.6.0":
        raise SnapshotError("SEMANTIC_SCENE_REQUIRED")
    plan = json.loads(capture.read(run / f"planning/html_visual/plan-{slide}.json", "input/semantic-plan.json"))
    contract = json.loads(capture.read(run / "planning/visual_contract.json", "input/semantic-contract.json"))
    pages = [p for p in contract["slides"] if p["slide_id"] == slide]
    if len(pages) != 1:
        raise SnapshotError("SEMANTIC_CONTRACT_REQUIRED")
    binding = json.loads(capture.read(run / f"planning/html_visual/binding-{slide}.json", "input/semantic-binding.json"))
    timeline = json.loads(capture.read(run / f"slides/{slide}/audio_timeline.json", "input/semantic-audio-timeline.json"))
    capture.read(run / f"slides/{slide}/voice.mp3", "audio/voice.mp3")
    # Model provenance is frozen as data, never credentials or an approval.
    for value in (plan, contract, binding, timeline):
        from html_build_snapshot import _no_secrets
        _no_secrets(value)
    # Record the exact catalog bytes before compiling. Snapshot creation reads
    # this source again and rejects a change between compilation and freezing.
    capture.read(root / "html_engine/visual/generated/catalog.json", "source/catalog.json")
    catalog = load_template_catalog(root)
    bound, spec = prepare_inputs(plan, pages[0], scene, binding, timeline, catalog)
    capture.add("input/semantic-frames-request.json", json_bytes(spec))
    return bound


def _inputs(snapshot):
    from html_storyboard_planning import load_template_catalog
    plan = _read(snapshot / "input/semantic-plan.json")
    contracts = _read(snapshot / "input/semantic-contract.json")
    author = _read(snapshot / "input/author-scene.json")
    binding = _read(snapshot / "input/semantic-binding.json")
    timeline = _read(snapshot / "input/semantic-audio-timeline.json")
    contract = next(p for p in contracts["slides"] if p["slide_id"] == author["id"])
    # Snapshot definitions, not mutable runtime catalog IDs, own reconstruction.
    catalog = load_template_catalog(ROOT, catalog_path=snapshot / "source/catalog.json")
    scene, spec = prepare_inputs(plan, contract, author, binding, timeline, catalog)
    if scene != _read(snapshot / "input/scene.json") or spec != _read(snapshot / "input/semantic-frames-request.json"):
        raise SemanticQAError("SEMANTIC_SNAPSHOT_INPUT_CHANGED")
    return plan, scene, spec


def _checker(root):
    names = ["html_semantic_qa.py", "html_semantic_review.py", "html_semantic_motion.py",
             "html_production_service.py", "html_narration_semantics.py", "html_object_decomposition.py",
             "html_build_snapshot.py", "html_input_manifest.py", "html_quality_report.py", "html_snapshot_review.py", "json_llm_service.py",
             "html_visual_review_service.py", "html_visual_review_routes.py", "agent_api/routes.py",
             "project_model_binding_service.py",
             "html_engine/tools/review-semantic-snapshot.cjs", "html_engine/tools/review-temporal-snapshot.cjs",
             "html_engine/tools/temporal-review.cjs", "html_engine/tools/browser-runtime.cjs"]
    return {name: fresh_hash(root / name) for name in names}


def _derive(snapshot, folder):
    from html_quality_report import validate_quality_report
    plan, scene, spec = _inputs(snapshot)
    raw = _read(folder / "semantic-frames.json")
    check_frames(scene, plan, spec, raw)
    engineering = _read(folder / "engineering.json")
    status = validate_quality_report(engineering, snapshot, evidence_dir=folder / "engineering")
    if not status["valid"]:
        raise SemanticQAError("SEMANTIC_ENGINEERING_EVIDENCE_INVALID")
    evaluations = []
    for index, beat in enumerate(plan["beats"]):
        request = _read(folder / f"request-{index}.json")
        if request != prompts_for_beat(plan, scene, raw, index):
            raise SemanticQAError("SEMANTIC_REQUEST_CHANGED")
        response = _read(folder / f"response-{index}.json")
        frames = [f for f in raw["frames"] if f["beatId"] == beat["id"]]
        try:
            evaluations.append(evaluate_response(response, beat, frames))
        except SemanticQAError as error:
            evaluations.append({"beatId": beat["id"], "status": "pending_review", "error": str(error)})
    return report_checks(status["engineering"], evaluations), evaluations


def review_semantic_scene(scene, *, run_dir, deps, evidence_dir=None, review_id=None):
    from html_visual_store import load_scene_with_revision
    from html_snapshot_review import review_snapshot
    run, root = Path(run_dir).resolve(), Path(deps.repo_root).resolve()
    document = load_scene_with_revision(run, scene["id"])
    if document is None or document["scene"] != scene:
        raise SemanticQAError("SEMANTIC_SAVED_SCENE_REQUIRED")
    from html_input_manifest import resolved_scene_inputs
    input_digest = resolved_scene_inputs(scene, run, root)["digest"]
    captured = create_render_snapshot(run, scene["id"], repo_root=root,
                                      expected_revision=document["revision"], target="semantic_review")
    snapshot = Path(captured["path"])
    checker = _checker(root)
    plan, bound, spec = _inputs(snapshot)
    base = run / "planning/html_visual/semantic-review"
    base.mkdir(parents=True, exist_ok=True)
    if evidence_dir is None:
        folder = Path(tempfile.mkdtemp(prefix="review-", dir=base))
    else:
        folder = safe_file(run, str(evidence_dir))
        if not folder.is_relative_to(base.resolve()):
            raise SemanticQAError("SEMANTIC_EVIDENCE_PATH_INVALID")
        folder.mkdir(parents=True, exist_ok=True)
    stable_review_id = str(review_id or folder.name)
    engineering = review_snapshot(snapshot, repo_root=root, output_dir=folder / "engineering-work",
                                  temporal={"sampling_mode": "output_frames", "fps": 30, "overlap_policy": "registered"})
    shutil.copytree(Path(engineering["report_path"]).parent, folder / "engineering")
    (folder / "engineering.json").write_bytes(json_bytes(engineering["report"]))
    if not engineering["validation"]["valid"] or engineering["report"]["checks"]["engineering"] != "passed":
        raise SemanticQAError("SEMANTIC_ENGINEERING_FAILED")
    request = snapshot / "input/semantic-frames-request.json"
    env = dict(os.environ)
    env.pop("HPS_HTML_RESOURCES", None)
    result = deps.run_subprocess_bounded([deps.node_bin, str(root / "html_engine/tools/review-semantic-snapshot.cjs"),
                                         str(snapshot), str(request), str(folder)], cwd=str(root),
                                         env=env, capture_output=True, timeout_sec=deps.stage_timeout_sec)
    if result.returncode:
        raise SemanticQAError("SEMANTIC_FRAMES_FAILED")
    raw = _read(folder / "semantic-frames.json")
    check_frames(bound, plan, spec, raw)
    for index, beat in enumerate(plan["beats"]):
        prompts = prompts_for_beat(plan, bound, raw, index)
        (folder / f"request-{index}.json").write_bytes(json_bytes(prompts))
        frames = [f for f in raw["frames"] if f["beatId"] == beat["id"]]
        try:
            response = deps.json_generator(**prompts, run_dir=str(run), artifact_prefix=f"semantic-{scene['id']}-{stable_review_id}-{index}",
                                          image_paths=[str(safe_file(folder, f["file"])) for f in frames])
            json_bytes(response)
        except Exception as error:
            if type(error).__name__ == "HtmlTaskError":
                # The persistent course job must reconcile the original
                # provider request before it can continue this review.
                raise
            # Provider/config errors are pending, never evidence of semantic pass.
            response = {"unavailable": True, "error_type": type(error).__name__}
        (folder / f"response-{index}.json").write_bytes(json_bytes(response))
    checks, evaluations = _derive(snapshot, folder)
    if verify_snapshot(snapshot)["snapshot_id"] != captured["snapshot_id"] or _checker(root) != checker:
        raise SemanticQAError("SEMANTIC_SOURCE_CHANGED_DURING_REVIEW")
    if resolved_scene_inputs(scene, run, root)["digest"] != input_digest:
        raise SemanticQAError("SEMANTIC_SOURCE_CHANGED_DURING_REVIEW")
    report = seal({"format": "hps.html.semantic_quality_report", "version": "0.1.0",
                   "scene_sha256": hashlib.sha256(json.dumps(scene, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                   "snapshot_id": captured["snapshot_id"], "source_revision": document["revision"],
                   "input_digest": input_digest,
                   "snapshot_path": str(snapshot.relative_to(run)).replace("\\", "/"),
                   "evidence_path": str(folder.relative_to(run)).replace("\\", "/"),
                   "checker": checker, "checks": checks, "evaluations": evaluations,
                   "model_identity": deps.semantic_model_identity or {"source": "injected"},
                   "passed": checks["engineering"] == checks["semantic"] == "passed", "approval_granted": False,
                   "evidence": [{"path": str(p.relative_to(folder)).replace("\\", "/"), "sha256": fresh_hash(p)}
                                for p in sorted(folder.rglob("*")) if p.is_file() and "engineering-work" not in p.parts]})
    (folder / "semantic-report.json").write_bytes(json_bytes(report))
    if document != load_scene_with_revision(run, scene["id"]):
        raise SemanticQAError("SEMANTIC_SOURCE_CHANGED_DURING_REVIEW")
    screenshot = run / "planning/html_visual/review" / f"review-{scene['id']}.png"
    screenshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(safe_file(folder, raw["frames"][-1]["file"]), screenshot)
    from pipeline_lifecycle import write_json_atomic
    write_json_atomic(base / f"current-{scene['id']}.json", report)
    return report


def semantic_status(scene, run_dir, repo_root=ROOT):
    """Recompute report/evidence/source validity; never trust a stored passed flag."""
    from html_input_manifest import resolved_scene_inputs
    try:
        run, root = Path(run_dir).resolve(), Path(repo_root).resolve()
        report = _read(run / f"planning/html_visual/semantic-review/current-{scene['id']}.json")
        original = dict(report)
        identity = original.pop("report_digest")
        if (digest(json_bytes(original)) != identity or report["format"] != "hps.html.semantic_quality_report"
            or report["version"] != "0.1.0" or report["approval_granted"] is not False or report["checker"] != _checker(root)
            or report["input_digest"] != resolved_scene_inputs(scene, run, root)["digest"]):
            raise SemanticQAError("SEMANTIC_REPORT_STALE")
        folder = safe_file(run, report["evidence_path"])
        snapshot = safe_file(run, report["snapshot_path"])
        if report != _read(folder / "semantic-report.json"):
            raise SemanticQAError("SEMANTIC_REPORT_RECEIPT_CHANGED")
        manifest = verify_snapshot(snapshot)
        if manifest["snapshot_id"] != report["snapshot_id"] or manifest["target"] != "semantic_review":
            raise SemanticQAError("SEMANTIC_SNAPSHOT_CHANGED")
        plan, bound, spec = _inputs(snapshot)
        del plan, bound, spec
        if scene != _read(snapshot / "input/author-scene.json"):
            raise SemanticQAError("SEMANTIC_SCENE_CHANGED")
        entries = report["evidence"]
        names = [e["path"] for e in entries]
        frames = _read(folder / "semantic-frames.json")["frames"]
        required = {"semantic-frames.json", "engineering.json", *[f["file"] for f in frames]}
        beats = _read(snapshot / "input/semantic-plan.json")["beats"]
        required |= {f"{kind}-{i}.json" for i in range(len(beats)) for kind in ("request", "response")}
        if len(set(names)) != len(names) or not required.issubset(names):
            raise SemanticQAError("SEMANTIC_EVIDENCE_MISSING")
        for entry in entries:
            if fresh_hash(safe_file(folder, entry["path"])) != entry["sha256"]:
                raise SemanticQAError("SEMANTIC_EVIDENCE_CHANGED")
        checks, evaluations = _derive(snapshot, folder)
        passed = checks["engineering"] == checks["semantic"] == "passed"
        if checks != report["checks"] or evaluations != report["evaluations"] or passed != report["passed"]:
            raise SemanticQAError("SEMANTIC_REPORT_OUTCOME_CHANGED")
        return {"valid": True, "passed": passed, "report": report, "checks": checks, "report_digest": identity}
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        return {"valid": False, "passed": False, "reason": "semantic_review_missing_or_stale"}


def semantic_frame_path(run_dir, slide_id, beat_index, frame_index, *, repo_root=ROOT):
    from html_visual_store import load_scene, validate_slide_id
    scene = load_scene(run_dir, validate_slide_id(slide_id))
    if type(beat_index) is not int or type(frame_index) is not int or beat_index < 0 or frame_index not in (0, 1, 2) or scene is None:
        raise SemanticQAError("SEMANTIC_FRAME_REFERENCE_INVALID")
    status = semantic_status(scene, run_dir, repo_root)
    if not status["valid"] or beat_index >= len(status["report"]["evaluations"]):
        raise SemanticQAError("SEMANTIC_FRAME_EVIDENCE_STALE")
    folder = safe_file(run_dir, status["report"]["evidence_path"])
    return safe_file(folder, f"beat-{beat_index}-{frame_index}.png")
