"""End-to-end regression for the real ``_annotate_project`` orchestration body.

历史回归背景：``checks/test_ai_mask_services.py`` 把 ``_annotate_project`` 整体
monkeypatch 掉，导致 ``ai_mask_engine.py`` 在 2026-09-26 引入的"定义前引用
``match_slide``"（NameError，ruff F821）随提交入库而所有必需验证全绿。本文件
驱动真实编排体：只注入视觉匹配边界（返回 None 走确定性回退），图片检测、
匹配、质量门禁与 Manifest 落盘全部走生产实现。
"""

import json
import logging
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

import ai_mask_engine
from visual_contract_service import normalize_visual_contract


def _capabilities(logs: list) -> ai_mask_engine.AiMaskEngineDependencies:
    return ai_mask_engine.AiMaskEngineDependencies(
        get_setting=lambda key, default="": default,
        get_openai_client=lambda **_kwargs: None,
        read_style_tokens_data=lambda: {},
        step2_llm_vendor_options=lambda *_args, **_kwargs: {},
        clean_json_markdown=lambda value: value,
        is_timeout_exception=lambda _exc: False,
        write_project_log=lambda project, event, **fields: logs.append(
            (project.id, event, fields)
        ),
        logger=logging.getLogger("ai-mask-annotate-e2e"),
    )


def _build_project(run_dir: Path, *, with_slide: bool = True) -> None:
    slide_dir = run_dir / "slides" / "slide_001"
    planning_dir = run_dir / "planning"
    planning_dir.mkdir(parents=True, exist_ok=True)
    if not with_slide:
        contract = normalize_visual_contract(
            {"version": "visual_contract_v1", "slides": []}
        )
        (planning_dir / "visual_contract.json").write_text(
            json.dumps(contract, ensure_ascii=False), encoding="utf-8"
        )
        (run_dir / "reveal_manifest.json").write_text(
            json.dumps({"slides": []}, ensure_ascii=False), encoding="utf-8"
        )
        return

    slide_dir.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (96, 64), "#ffffff")
    for x in range(12, 36):
        for y in range(12, 36):
            image.putpixel((x, y), (17, 17, 17))
    image.save(slide_dir / "visual_draft.png")

    narration = "重点结论是迁移必须先验证回滚。"
    contract = normalize_visual_contract(
        {
            "version": "visual_contract_v1",
            "slides": [
                {
                    "slide_id": "slide_001",
                    "main_title": "重点结论",
                    "subtitle": "",
                    "core_message": narration,
                    "body_content": [narration],
                    "visual_groups": [
                        {
                            "id": "group_001",
                            "element_id": "group_001",
                            "role": "content_body",
                            "visible_text": narration,
                            "display_text": narration,
                            "visual_anchor": narration,
                            "narration_function": narration,
                            "reveal_order": 1,
                            "reveal_mode": "sequential",
                            "content_unit_id": "unit_001",
                            "mask_target": narration,
                            "visual_type": "text",
                        }
                    ],
                    "narration_beats": [
                        {
                            "id": "beat_001",
                            "group_id": "group_001",
                            "visible_anchor": narration,
                            "spoken_intent": narration,
                            "spoken_text": narration,
                            "content_unit_id": "unit_001",
                        }
                    ],
                }
            ],
        }
    )
    (planning_dir / "visual_contract.json").write_text(
        json.dumps(contract, ensure_ascii=False), encoding="utf-8"
    )
    manifest = {
        "slides": [
            {
                "slide_id": "slide_001",
                "groups": [
                    {
                        "id": "group_001",
                        "group_id": "group_001",
                        "role": "content_body",
                        "box": {"x": 10, "y": 10, "w": 28, "h": 28},
                    }
                ],
            }
        ]
    }
    (run_dir / "reveal_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )


def test_annotate_project_matches_scheduled_slide_and_writes_manifest(
    tmp_path,
) -> None:
    run_dir = tmp_path / "run"
    _build_project(run_dir)
    logs: list = []
    project = SimpleNamespace(id="proj-e2e", run_dir=str(run_dir))
    settings = ai_mask_engine.normalize_settings({"doclayout_enabled": False})

    result = ai_mask_engine._annotate_project(
        _capabilities(logs),
        project,
        settings,
        "methodology",
        "output",
        lambda *_args, **_kwargs: None,
        None,
    )

    assert result["success"] is True
    assert result["processed_slide_count"] == 1
    # 确定性回退必须命中先验框内的元素并至少更新一个语块。
    assert result["updated_group_count"] >= 1
    assert result["complete"] is True

    manifest = json.loads(
        (run_dir / "reveal_manifest.json").read_text(encoding="utf-8")
    )
    annotation = manifest.get("ai_mask_annotation")
    assert isinstance(annotation, dict)
    assert annotation["status"] == "completed"
    assert annotation["processed_slide_count"] == 1
    assert annotation["scope_slide_ids"] == ["slide_001"]

    slide_dir = run_dir / "slides" / "slide_001" / "auto_mask"
    auto_match = json.loads((slide_dir / "auto_match.json").read_text(encoding="utf-8"))
    assert auto_match["matches"], "prior-box fallback must produce one match"
    assert auto_match["matches"][0]["group_id"] == "group_001"


def test_annotate_project_with_no_slides_finishes_cleanly(tmp_path) -> None:
    run_dir = tmp_path / "run"
    _build_project(run_dir, with_slide=False)
    logs: list = []
    project = SimpleNamespace(id="proj-empty", run_dir=str(run_dir))
    settings = ai_mask_engine.normalize_settings({"doclayout_enabled": False})

    result = ai_mask_engine._annotate_project(
        _capabilities(logs),
        project,
        settings,
        "methodology",
        "output",
        lambda *_args, **_kwargs: None,
        None,
    )

    assert result["success"] is True
    assert result["processed_slide_count"] == 0
    assert result["complete"] is False
    manifest = json.loads(
        (run_dir / "reveal_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["ai_mask_annotation"]["quality_status"] == "failed"
