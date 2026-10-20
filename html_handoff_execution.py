"""Portable execution facts and typed acceptance from registered production owners."""
import copy
import json
from pathlib import Path

import html_scene_editing as editor
from html_handoff_models import ExternalVerification

ROOT = Path(__file__).resolve().parent
CRITERIA = [
    ("input_identity", "输入身份/材料hash", "portable"),
    ("schema_and_scope", "结果与逐对象操作Schema/范围", "portable"),
    ("content_and_motion", "原文/关系/动作/素材/身份保持", "portable_and_original"),
    ("manual_protection", "人工保护", "original"),
    ("production_compile", "原生产编译（含保留入场位移边界）", "portable"),
    ("dom_capacity", "原DOM字体/实际容量", "original"),
    ("overlap_coverage", "指定对象对有限采样遮挡/允许重叠", "original"),
    ("baseline_visual_review", "实际原图理解", "agent"),
    ("candidate_visual_review", "修改后实际画面/可读性（无对应渲染不能自检）", "agent_and_human"),
]


def checker_bytes():
    built = editor._node("""
const esbuild=require('./html_engine/node_modules/esbuild');
const build=esbuild.buildSync({entryPoints:['html_engine/tools/handoff-preflight.cjs'],bundle:true,
 platform:'node',target:'node20',write:false,minify:true,legalComments:'inline'});
console.log(JSON.stringify({source:build.outputFiles[0].text}));
""", {})
    return built["source"].encode()


def definition_files():
    return ["html_handoff_execution.py", "html_handoff_assistance.py", "html_repair_static.py", "html_handoff_diagnostics.py", "html_handoff_workbench.py", "scripts/check_external_task.py",
            "html_engine/tools/handoff-preflight.cjs", "html_engine/visual/compiler.cjs",
            "html_engine/visual/generated/validators.cjs", "html_engine/package-lock.json",
            "html_engine/src/registry.cjs", "html_engine/src/timeline.cjs", "html_engine/visual/icons.cjs",
            "html_engine/visual/presentation-variants.json", "html_engine/visual/course-structures.cjs", "html_engine/visual/relationship-capacity.cjs",
            "docs/contracts/html-presentation/runtime/visual-v1/external-agent-execution-2.0.0.md",
            "docs/contracts/html-presentation/runtime/visual-v1/external-agent-workbench-0.1.0.md",
            "docs/contracts/html-presentation/runtime/visual-v1/repair-assistance-0.1.0.md", "docs/agent/external-agent-entry.md"]


def create_execution(doc, request):
    criteria = [{"id": id, "description": description, "verifier": verifier} for id, description, verifier in CRITERIA]
    context = {"version": "2.1.1", "verification_required": request.require_verification,
               "required_abilities": {"can_view_images": request.require_image_understanding,
                                      "can_run_preflight": request.require_verification and request.task_type == "static_repair"},
               "environment": {"python": "3.10+", "node": "20+", "pip_or_npm_install": False,
                               "preflight_network_required": False, "extra_paid_tools_authorized": False, "real_audio_required": request.task_type == "animation_repair"},
               "portable_checker_scope": "static operations + exact production compile, no browser/audio/visual approval",
               "font_requirements": [item.model_dump() for item in request.font_requirements],
               "criteria": criteria, "temporal_spec": {"overlap_policy": request.overlap_policy,
                                                        "overlap_pairs": request.overlap_pairs, "step_ms": 250}}
    if doc is None:
        context["hard_constraints"] = {"status": "not_applicable", "reason": "design_reference has no editable scene"}
        return context
    nodes = {n["id"]: n for n in doc["scene"]["nodes"]}
    from html_repair_static import PARTS
    used_ids = set()
    for requirement in request.font_requirements:
        if (requirement.id in used_ids or requirement.id in {item["id"] for item in criteria}
                or requirement.targetId not in request.scope
                or requirement.part not in PARTS.get(nodes[requirement.targetId]["type"], [])
                or (requirement.part in ("heading", "tag", "note") and not nodes[requirement.targetId].get(requirement.part))):
            raise ValueError("字号验收条件须使用唯一ID、scope内对象与公开文字部位")
        used_ids.add(requirement.id)
        criteria.append({"id": requirement.id, "description": "作者字号下限（不替代实际可读性）", "verifier": "portable_and_original"})
    facts = editor._node("""
const fs=require('fs'),p=JSON.parse(fs.readFileSync(0,'utf8'));
console.log(JSON.stringify(require('./html_engine/tools/handoff-preflight.cjs').facts(p)));
""", {"scene": doc["scene"], "assets": doc["resources"]["assets"], "spec": context["temporal_spec"]})
    context["capacity_constraints"] = [item for item in facts["capacity"] if item["targetId"] in request.scope]
    context["overlap_coverage"] = facts["overlap"]
    context["overlap_coverage"]["limit"] = "Only listed pairs tested; no claim about omitted pairs, alpha-content occlusion or continuous time. Human review covers remaining visual conflicts."
    catalog = editor.read_json(ROOT / "html_engine/visual/generated/catalog.json")
    layout = next(item for item in catalog["layouts"] if all(item[k] == doc["scene"]["layoutRef"][k] for k in ("id", "version")))
    context["hard_constraints"] = {"units": "logical canvas px; presentation offset relative to registered slot; action offset relative to author box",
        "canvas": facts["layout"]["canvas"], "source": "original compiler + original overlapPolicy",
        "objects": [{"targetId": id, "slot_box": copy.deepcopy(layout["slots"][nodes[id]["slot"]]["box"]),
                     "current_author_box": facts["layout"]["slots"][nodes[id]["slot"]]["box"],
                     "retained_actions": [a for a in doc["scene"]["motion"] if a["targetId"] == id],
                     "rule": "base x/y >=0; right<=1600; bottom<=800; enter offset endpoint must also stay inside; static repair keeps all action/binding data"}
                    for id in request.scope]}
    return context


def check_fonts(packet, scene):
    nodes = {n["id"]: n for n in scene["nodes"]}
    checks = []
    for requirement in packet["context"].get("execution", {}).get("font_requirements", []):
        actual = nodes[requirement["targetId"]].get("presentation", {}).get("typography", {}).get(requirement["part"], {}).get("fontSizePx")
        checks.append({"criterion_id": requirement["id"], "status": "system_passed" if actual is not None and actual >= requirement["minimum_px"] else "failed",
                       "actual": actual, "minimum": requirement["minimum_px"]})
    return checks


def verification_template(packet):
    return {"format": "hps.html.external_verification", "version": "1.0.0", "task_id": packet["task_id"],
            "abilities": {name: False for name in ("can_view_images", "can_listen_audio", "can_run_preflight", "can_access_original_preview")},
            "checks": [{"criterion_id": item["id"], "status": "not_run", "evidence": [], "note": ""}
                       for item in packet["context"]["execution"]["criteria"]]}


def validate_verification(packet, result, files):
    execution = packet["context"].get("execution", {})
    if not execution.get("verification_required"):
        return None
    if "verification.json" not in files:
        raise ValueError("当前任务须交付ZIP，根目录包含verification.json能力声明和逐项验收")
    value = ExternalVerification.model_validate_json(files["verification.json"])
    required = {item["id"] for item in execution["criteria"]}
    supplied = [check.criterion_id for check in value.checks]
    if value.task_id != result.task_id or set(supplied) != required or len(supplied) != len(required):
        raise ValueError("验收记录必须覆盖当前任务全部条件，ID不得重复或借用其他任务")
    if result.status == "proposed":
        for name, needed in execution["required_abilities"].items():
            if needed and not getattr(value.abilities, name):
                raise ValueError(f"缺少任务要求的能力{name}，应交付needs_input/unsupported而非候选")
        if any(check.status == "failed" for check in value.checks):
            raise ValueError("存在已知failed验收项，请先修订或如实停止，不作为可采用候选")
        checks = {check.criterion_id: check for check in value.checks}
        if execution["required_abilities"].get("can_view_images") and "baseline_visual_review" in checks:
            baseline = checks["baseline_visual_review"]
            if baseline.status != "self_checked" or not any(item.strip() for item in baseline.evidence):
                raise ValueError("要求看图的候选须实际审阅原图，baseline_visual_review记录self_checked和实际证据；仅声明能力true不足")
        if not value.abilities.can_access_original_preview and any(checks[id].status == "self_checked" for id in ("dom_capacity", "overlap_coverage", *(["candidate_visual_review"] if "candidate_visual_review" in checks else []))):
            raise ValueError("没有原预览能力时，DOM容量、实际遮挡和修改后画面必须标为not_run/unknown，不能声明已检查")
        if packet["task_type"] == "static_repair":
            portable_ids = {"input_identity", "schema_and_scope", "content_and_motion", "production_compile"}
            portable_ids.update(item["id"] for item in execution["font_requirements"])
            if any(checks[id].status != "self_checked" or not checks[id].evidence for id in portable_ids):
                raise ValueError("静态候选须为每个便携验收项记录self_checked及真实preflight证据，原播放器项仍可not_run")
            import hashlib
            preflight = json.loads(files.get("preflight.json", b"{}"))
            if (preflight.get("format") != "hps.html.preflight" or preflight.get("task_id") != result.task_id
                    or preflight.get("preflight_passed") is not True
                    or preflight.get("result_file_sha256") != hashlib.sha256(files["result.json"]).hexdigest()):
                raise ValueError("静态严格任务须包含与result.json原字节绑定的官方preflight.json通过报告；外部报告不代替系统复核")
    return value.model_dump(mode="json")
