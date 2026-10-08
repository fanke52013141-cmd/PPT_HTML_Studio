from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import server  # noqa: E402
import visual_contract_service as service  # noqa: E402


def test_module_owns_contract_logic_without_application_wiring() -> None:
    source = (ROOT / "visual_contract_service.py").read_text(
        encoding="utf-8"
    )
    server_source = (ROOT / "server.py").read_text(encoding="utf-8")
    for forbidden in (
        "APIRouter",
        "Depends(",
        "get_db",
        "server_module",
        "import server",
    ):
        assert forbidden not in source
    for function_name in (
        "normalize_visual_type",
        "narration_dedupe_key",
        "dedupe_narration_beats",
        "normalize_visual_contract",
        "contract_slide_ids_from_payload",
        "read_contract_slide_ids",
    ):
        assert f"def {function_name}(" in source
        assert f"def {function_name}(" not in server_source
        assert getattr(server, function_name) is getattr(
            service,
            function_name,
        )


def test_visual_type_aliases_and_fallbacks_are_stable() -> None:
    assert service.normalize_visual_type("文字") == "text"
    assert service.normalize_visual_type("diagram") == "picture"
    assert service.normalize_visual_type("unknown", has_text=True) == (
        "text"
    )
    assert service.normalize_visual_type("unknown") == "picture"


def test_narration_dedupe_ignores_markup_spacing_and_punctuation() -> None:
    first = "<#0.5#> Token 的核心作用！"
    second = "Token的核心作用。"
    assert service.narration_dedupe_key(first) == (
        service.narration_dedupe_key(second)
    )
    beats = [
        {"id": "first", "spoken_text": first},
        {"id": "duplicate", "tts_text": second},
        {"id": "empty"},
        {"id": "empty_2"},
        "invalid",
    ]
    assert [
        beat["id"]
        for beat in service.dedupe_narration_beats(beats)
    ] == ["first", "empty", "empty_2"]


def test_contract_normalization_removes_subtitle_and_enriches_beats() -> None:
    contract = {
        "presentation_policy": {
            "subtitle_policy": "all_slides_have_subtitle"
        },
        "slides": [
            {
                "slide_id": "slide_001",
                "subtitle": "旧副标题",
                "visual_groups": [
                    {
                        "id": "content",
                        "role": "content_body",
                        "visible_text": "核心信息",
                        "display_text": "核心信息",
                        "speak_policy": "speak",
                    },
                    {
                        "id": "subtitle",
                        "role": "subtitle",
                    },
                ],
                "narration_beats": [
                    {
                        "group_id": "content",
                        "spoken_text": "围绕“核心信息”，给出结论。",
                    },
                    {
                        "id": "duplicate",
                        "group_id": "content",
                        "spoken_text": "给出结论！",
                    },
                    {
                        "id": "orphan",
                        "group_id": "missing",
                        "spoken_text": "不应保留。",
                    },
                ],
            }
        ],
    }

    normalized = service.normalize_visual_contract(contract)

    policy = normalized["presentation_policy"]
    assert policy["subtitle_policy"] == "no_slides_have_subtitle"
    assert policy["subtitle_decided_by"] == (
        "system_no_subtitle_contract"
    )
    slide = normalized["slides"][0]
    assert slide["subtitle"] == ""
    assert [group["id"] for group in slide["visual_groups"]] == [
        "content"
    ]
    group = slide["visual_groups"][0]
    assert group["visual_type"] == "text"
    assert group["content_unit_id"] == "content_unit"
    assert group["mask_target"] == "核心信息"
    assert group["reveal_order"] == 1
    assert "speak_policy" not in group
    assert len(slide["narration_beats"]) == 1
    beat = slide["narration_beats"][0]
    assert beat["id"] == "beat_01"
    assert beat["content_unit_id"] == "content_unit"
    assert beat["visible_anchor"] == "核心信息"
    assert beat["spoken_text"] == "给出结论。"


def test_manual_mode_keeps_free_standing_beats() -> None:
    contract = {
        "slides": [
            {
                "slide_id": "slide_manual",
                "visual_groups": [],
                "narration_beats": [
                    {"spoken_text": "自由旁白。"}
                ],
            }
        ]
    }

    normalized = service.normalize_visual_contract(contract)

    beat = normalized["slides"][0]["narration_beats"][0]
    assert beat["id"] == "beat_01"
    assert beat["content_unit_id"] == "slide_manual_unit_001"
    assert beat["spoken_text"] == "自由旁白。"


def test_contract_slide_ids_preserve_order_and_file_failures_are_safe(
    tmp_path: Path,
) -> None:
    payload = {
        "slides": [
            {"slide_id": " slide_002 "},
            "invalid",
            {"slide_id": ""},
            {"slide_id": "slide_001"},
        ]
    }
    assert service.contract_slide_ids_from_payload(payload) == [
        "slide_002",
        "slide_001",
    ]
    assert service.read_contract_slide_ids(str(tmp_path)) == []

    planning = tmp_path / "planning"
    planning.mkdir()
    contract_path = planning / "visual_contract.json"
    contract_path.write_text("not json", encoding="utf-8")
    assert service.read_contract_slide_ids(str(tmp_path)) == []

    contract_path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    assert service.read_contract_slide_ids(str(tmp_path)) == [
        "slide_002",
        "slide_001",
    ]

import pytest


def test_blank_and_duplicate_slide_ids_are_rejected() -> None:
    """R1-002: 重复 ID 在写入前被拒绝;空白 ID 由 normalize 宽容(旧工件修复),
    在用户手写保存入口由 reject_blank_slide_ids 拒绝;空列表合法。"""
    from fastapi import HTTPException

    from visual_contract_service import (
        reject_blank_slide_ids,
        validate_slide_identifiers,
    )

    # 空列表仍合法
    validate_slide_identifiers({"slides": []})

    # 共享 normalize(旧工件修复路径)对空白 ID 宽容,重复 ID 拒绝
    validate_slide_identifiers({"slides": [{"slide_id": "slide_001"}, {}]})
    with pytest.raises(HTTPException) as dup:
        validate_slide_identifiers({"slides": [{"slide_id": "slide_001"}, {"slide_id": "slide_001"}]})
    assert dup.value.status_code == 400
    assert "重复" in dup.value.detail

    # 用户手写保存入口拒绝空白 ID
    with pytest.raises(HTTPException) as blank:
        reject_blank_slide_ids([{"slide_id": "slide_001"}, {"slide_id": "   "}])
    assert blank.value.status_code == 400

    # 合法场景不抛
    validate_slide_identifiers({"slides": [{"slide_id": "slide_001"}, {"slide_id": "slide_002"}]})
