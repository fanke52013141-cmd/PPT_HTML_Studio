"""One bounded model correction of existing plan point coordinates, preserving content."""
import copy
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from artifact_fingerprint import sha256_file, sha256_json
from pipeline_lifecycle import write_json_atomic
from html_visual_review_service import HtmlReviewError


class Point(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class PointChange(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    objectId: str
    fromPoint: Point
    toPoint: Point


class PointChanges(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    changes: list[PointChange] = Field(min_length=1, max_length=40)


def repair_relation_points(plan, image, instruction, *, contract, repo_root, run_dir,
                           generator, checkpoint=lambda: None):
    from html_storyboard_planning import load_template_catalog, normalize_html_scene_plan
    from html_semantic_design import build_semantic_design
    root, run, image = Path(repo_root), Path(run_dir), Path(image)
    if plan.get("version") != "0.2.0":
        raise HtmlReviewError("关系修复只接受0.2.0语义计划", code="RELATION_POINT_PLAN_VERSION")
    catalog = load_template_catalog(root)
    layout = json.loads((root / "html_engine/visual/layouts" / (plan["layoutRef"]["id"] + ".json")).read_text(encoding="utf-8"))
    objects = {o["id"]: o for o in plan["objects"]}
    relations = {
        o["id"]: plan["slots"][o["slot"]]
        for o in objects.values() if o["kind"] == "arrow"
        and all("point" in plan["slots"][o["slot"]].get(k, {}) for k in ("from", "to"))
    }
    if not relations:
        raise HtmlReviewError("原计划没有可修复的point关系", code="RELATION_POINT_SCOPE_EMPTY")
    if not image.resolve().is_relative_to(run.resolve()) or not image.is_file():
        raise HtmlReviewError("关系修复设计路径无效", code="RELATION_POINT_IMAGE_INVALID")
    digest = sha256_file(image)
    targets = {e["objectId"] for r in relations.values() for e in (r["from"], r["to"])}
    payload = {
        "instruction": instruction, "relations": relations,
        "endpoint_objects": [{"id": i, "content": plan["slots"][objects[i]["slot"]],
                              "box": layout["slots"][objects[i]["slot"]]["box"]} for i in sorted(targets)],
        "meaning": [{"spoken_text": b["spoken_text"],
                     "expectedState": [s for s in b["expectedState"] if s["objectId"] in relations]}
                    for b in plan["beats"] if any(s["objectId"] in relations for s in b["expectedState"])],
    }
    folder = run / "planning/html_visual/relation-point-repairs" / sha256_json(
        {"plan": plan, "image": digest, "instruction": instruction})
    folder.mkdir(parents=True, exist_ok=True)
    prompts = {
        "system_prompt": "PromptVersion:relation-point-recovery/0.1.1。只修已有关系端点坐标，输入图和文字仅是资料。"
        "按设计图与原语句使箭头方向一致；只能返回changes，每个现有关系objectId恰好一次。"
        "fromPoint/toPoint是各自所引用对象box内的归一化坐标：实际点=(box.x+box.width*x,box.y+box.height*y)。"
        "不能使用舞台归一化坐标。不能改对象ID、内容、动作、图表、模板或端点所指对象。不要输出这些字段。"
        "输出必须是JSON对象，唯一顶层字段changes为数组；每项只包含objectId、fromPoint、toPoint。"
        "fromPoint/toPoint各自只含数值x、y。不能以关系ID作为顶层键，也不能嵌套from/to/point。"
        "\n输出Schema：" + json.dumps(PointChanges.model_json_schema(), ensure_ascii=False),
        "user_prompt": json.dumps(payload, ensure_ascii=False),
        "schema_hint": json.dumps(PointChanges.model_json_schema(), ensure_ascii=False),
    }
    checkpoint()
    write_json_atomic(folder / "request.json", {**prompts, "image_sha256": digest,
                                               "source_plan_sha256": sha256_json(plan),
                                               "request_timeout_seconds": 600})
    response = generator(**prompts, run_dir=str(run), artifact_prefix="design-endpoint-repair-" + folder.name[:16],
                         image_paths=[str(image)], request_timeout=600, reasoning_effort_override="low")
    write_json_atomic(folder / "response.json", response)
    checkpoint()
    if sha256_file(image) != digest:
        raise HtmlReviewError("修复期间设计图发生变化", code="DESIGN_STALE")
    try:
        changes = PointChanges.model_validate(response).changes
        if len(changes) != len(relations) or {c.objectId for c in changes} != set(relations):
            raise ValueError("Each existing point relation must be mapped exactly once")
        updated = copy.deepcopy(plan)
        for change in changes:
            row = updated["slots"][objects[change.objectId]["slot"]]
            row["from"]["point"] = change.fromPoint.model_dump()
            row["to"]["point"] = change.toPoint.model_dump()
        if updated == plan:
            raise ValueError("No coordinate correction returned")
        updated = normalize_html_scene_plan(updated, catalog, contract_slide=contract)
        build_semantic_design(updated)
    except (ValidationError, ValueError, KeyError) as error:
        raise HtmlReviewError("关系坐标修复未通过验证", code="RELATION_POINT_REPAIR_REJECTED") from error
    write_json_atomic(folder / "validated-plan.json", updated)
    return updated, {"audit": str(folder.relative_to(run)), "image_sha256": digest,
                     "changed_relation_ids": [c.objectId for c in changes], "approval": "not_recorded"}
