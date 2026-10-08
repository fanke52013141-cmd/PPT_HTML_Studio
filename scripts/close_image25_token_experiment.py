"""Offline real-asset draft closure; never creates approvals or confirmed audio."""

from __future__ import annotations

import json
import hashlib
import os
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from html_asset_sheet import HtmlAssetSheetError
from html_asset_sheet_review import _candidate, accept_candidate
from html_asset_sheet_store import persist_sheet_candidates
from html_render_runner import (
    HtmlRenderError,
    HtmlRenderRunner,
    HtmlRenderRunnerDependencies,
)
from html_visual_review_service import (
    HtmlReviewDependencies,
    approval_status,
    review_scene,
)
from html_visual_store import save_scene
from runtime_support import run_subprocess_killable


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    run = ROOT / "outputs/image25-sheet/closure-token-v1"
    if run.exists() and "--resume" not in sys.argv[1:]:
        raise SystemExit("Refusing to replace an existing closure experiment")
    previous = (
        ROOT / "outputs/image25-sheet/toapis-bulb-reference-v1/extraction-2-clean"
    )
    spec = json.loads((previous / "spec.json").read_text(encoding="utf-8"))
    candidate = persist_sheet_candidates(
        run, (previous / "source.png").read_bytes(), spec
    )
    manifest = candidate["manifest"]
    _candidate(run, manifest["sheet_id"], manifest["request_key"])
    gates = {}
    try:
        accept_candidate(
            run,
            manifest["sheet_id"],
            manifest["request_key"],
            "bulb",
            expected_revision=0,
        )
        raise AssertionError("Unreviewed candidate was accepted")
    except HtmlAssetSheetError as exc:
        assert exc.code == "SHEET_REVIEW_REQUIRED", exc
        gates["asset_acceptance"] = {
            "status": "blocked",
            "code": exc.code,
            "message": str(exc),
        }
    entry = dict(manifest["assets"][0])
    entry["file"] = candidate["directory"] + "/asset-bulb.png"
    entry["anchors"] = [{"id": "focus", "x": 994, "y": 547}]
    entry["anchor_provenance"] = (
        "Derived alpha-bounds center for draft preview only; not a reviewed semantic anchor"
    )
    resources = run / "planning/draft_preview/resources.json"
    write(resources, {"purpose": "unapproved_draft_preview_only", "assets": [entry]})
    assert not (run / "planning/html_visual/resources.json").exists()

    scene = json.loads(
        (ROOT / "html_engine/visual/scenes/condensation.json").read_text(
            encoding="utf-8"
        )
    )
    scene.update(
        id="token-closure",
        name="什么是 Token？",
        source="Manually authored Token draft using registered template; real Image2.5 candidate; no model planning claim",
    )
    nodes = {node["id"]: node for node in scene["nodes"]}
    nodes["header"].update(title="什么是 Token？")
    for key, text in {
        "headline": "模型处理文本时使用的基本单位",
        "intro": "具体切分方式取决于模型使用的分词器。",
        "anchor-label": "概念\n配图",
    }.items():
        nodes[key]["runs"] = [{"text": text, "emphasis": False}]
    for key, title, body in [
        ("card-1", "未必是一个完整的词", "可以是词的一部分、标点或其他文本片段。"),
        ("card-2", "Token 数量不等于字数", "中文、英文和符号可能采用不同切分方式。"),
        ("card-3", "上下文与用量按 Token 衡量", "许多服务按输入和输出 Token 计费。"),
    ]:
        nodes[key].update(title=title, body=body, icon="lightbulb")
    nodes["figure"]["tag"].update(text="理解文本如何被处理")
    nodes["figure"]["note"].update(icon="lightbulb", text="灯泡仅作概念配图")
    nodes["subject"]["assetRef"] = {"id": "bulb", "version": entry["version"]}
    nodes["summary"]["from"]["text"] = "文本"
    nodes["summary"]["to"]["text"] = "Token"
    nodes["summary"].update(term="分词", takeaway="具体切分由分词器决定")
    scene["beats"] = []
    revision_file = run / "planning/html_visual/revision.json"
    revision = (
        json.loads(revision_file.read_text(encoding="utf-8"))["revision"]
        if revision_file.exists()
        else 0
    )
    stored = save_scene(run, scene["id"], scene, expected_revision=revision)
    narration = [
        "Token 是模型处理文本时使用的基本单位。",
        "一个 Token 不一定对应一个完整的词。",
        "Token 数量不等于字数，具体切分由分词器决定。",
        "许多服务按输入和输出 Token 计算用量和费用。",
    ]
    write(
        run / "planning/draft_preview/narration.json",
        {
            "status": "draft_not_synthesized",
            "segments": narration,
            "timing": "scene fixture timing for visual inspection only",
        },
    )
    chrome = Path(
        os.environ.get(
            "HPS_CHROME",
            "C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe",
        )
    )
    if not chrome.is_file():
        raise SystemExit("Chromium unavailable; set HPS_CHROME")

    def draft_process(*args, **kwargs):
        env = dict(kwargs.get("env") or os.environ)
        env.update(HPS_HTML_RESOURCES=str(resources), HPS_CHROME=str(chrome))
        kwargs["env"] = env
        return run_subprocess_killable(*args, **kwargs)

    def no_model(**kwargs):
        raise AssertionError("This offline experiment does not invoke a model planner")

    deps = HtmlReviewDependencies(
        repo_root=ROOT, json_generator=no_model, run_subprocess_bounded=draft_process
    )
    report = review_scene(scene, run_dir=run, deps=deps)
    gates["scene_approval"] = approval_status(
        scene, run_dir=run, deps=deps, slide_id=scene["id"]
    )
    runner = HtmlRenderRunner(
        HtmlRenderRunnerDependencies(
            repo_root=ROOT, read_slide_ids=lambda _: [scene["id"]]
        )
    )
    try:
        runner._audio_path(run, scene["id"])
        raise AssertionError("Unexpected audio in isolated experiment")
    except HtmlRenderError as exc:
        gates["video_audio"] = {"status": "blocked", "message": str(exc)}
    times = run / "planning/draft_preview/times.json"
    write(times, [1200, 7000, 18000])
    frames = run / "draft-frames"
    frames.mkdir(exist_ok=True)
    result = draft_process(
        [
            "node",
            str(ROOT / "html_engine/tools/export-snapshots.cjs"),
            str(run / "planning/html_visual/scene-token-closure.json"),
            str(times),
            str(frames),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout_sec=120,
    )
    if result.returncode:
        raise RuntimeError(result.stderr)
    snapshots = []
    for index, time_ms in enumerate([1200, 7000, 18000]):
        path = frames / f"snapshot-{index:03d}.png"
        with Image.open(path) as image:
            dimensions = list(image.size)
        snapshots.append(
            {
                "timeMs": time_ms,
                "file": str(path.relative_to(run)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "dimensions": dimensions,
            }
        )
    assert len({frame["sha256"] for frame in snapshots}) == 3
    evidence = {
        "status": "draft_rendered_awaiting_human_review",
        "paid_generation_calls": 0,
        "candidate": candidate,
        "scene_store": stored,
        "browser_review": report,
        "snapshot_result": json.loads(result.stdout),
        "snapshots": snapshots,
        "gates": gates,
        "formal_resource_registry_exists": False,
        "production_exports": "not_run: asset and scene approval pending; confirmed audio absent",
        "llm_storyboard_generation": "not_run: manually authored fixture content",
        "efficiency_conclusion": "Local reference cost improvement observed in previous pair; batch throughput improvement remains unproven",
    }
    write(run / "closure-evidence.json", evidence)
    print(
        json.dumps(
            {
                "run": str(run),
                "static_passed": report.get("passed"),
                "frames": 3,
                "gates": gates,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
