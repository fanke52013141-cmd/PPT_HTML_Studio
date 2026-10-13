"""Verified D packages consumed by the E design request, never runtime IDs."""

from __future__ import annotations

import hashlib
import base64
import json
from pathlib import Path

from artifact_fingerprint import sha256_json
from pipeline_lifecycle import write_json_atomic
from html_visual_review_service import HtmlReviewError

PROMPT_VERSION = "html-design-reference/0.3.1"
SEMANTIC_PROMPT_VERSION = "html-design-reference/0.4.1"


def _fail(message):
    raise HtmlReviewError(message, code="REFERENCE_PACKAGE_INVALID")


def verify_package(directory: Path) -> dict:
    """Verify complete manifest and actual attachment bytes before each use."""
    try:
        root = directory.resolve()
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        body = {k: v for k, v in manifest.items() if k != "manifestSha256"}
        if (manifest["format"] != "hps.visual.reference-request-package"
                or manifest["version"] != "1.0.0"
                or sha256_json(body) != manifest["manifestSha256"]):
            _fail("参考包 manifest 身份或哈希不匹配")
        files = {}
        for entry in manifest["files"]:
            name = entry["path"]
            file = (root / name).resolve()
            if (Path(name).is_absolute() or not file.is_relative_to(root)
                    or file == root or name in files or not file.is_file()
                    or any(p.is_symlink() for p in [root / name, *(root / name).parents] if p != root)):
                _fail("参考包文件路径无效")
            payload = file.read_bytes()
            if len(payload) != entry["size"] or hashlib.sha256(payload).hexdigest() != entry["sha256"]:
                _fail("参考包文件字节发生变化")
            files[name] = entry
        if {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} != set(files) | {"manifest.json"}:
            _fail("参考包含未登记文件")
        for field in ("exactContent", "visualGuidance"):
            entry = manifest[field]
            if files[entry["path"]]["sha256"] != entry["sha256"]:
                _fail("参考包内容或指导未登记")
        from PIL import Image
        references = []
        for entry in manifest["attachments"]:
            if files[entry["path"]]["sha256"] != entry["sha256"]:
                _fail("参考附件哈希不匹配")
            path = root / entry["path"]
            with Image.open(path) as image:
                image.load()
                if image.format != "PNG" or image.size != (entry["width"], entry["height"]):
                    _fail("参考附件尺寸或格式不匹配")
            references.append(str(path))
        if not references:
            _fail("参考包没有实际图片附件")
        return {"manifest": manifest, "references": references,
                "content": json.loads((root / manifest["exactContent"]["path"]).read_text(encoding="utf-8")),
                "guidance": json.loads((root / manifest["visualGuidance"]["path"]).read_text(encoding="utf-8"))}
    except HtmlReviewError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HtmlReviewError("参考包无法验证", code="REFERENCE_PACKAGE_INVALID") from exc


def design_content(plan: dict, brief: dict) -> dict:
    # Runtime tone names are semantic token keys, not image palette choices.
    # Keep accurate text intact, including any literal color word in the text.
    def neutral_content(value):
        if isinstance(value, dict):
            return {key: neutral_content(child) for key, child in value.items() if key != "tone"}
        if isinstance(value, list):
            return [neutral_content(child) for child in value]
        return value
    slots = neutral_content(plan["slots"])
    texts = []
    def collect(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ("title", "text", "body", "eyebrow", "subtitle", "caption") and isinstance(child, str) and child.strip():
                    texts.append(child)
                elif isinstance(child, (dict, list)):
                    collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
    collect(slots)
    title = str((slots.get("header") or {}).get("title") or (slots.get("headline") or {}).get("text") or plan["slide_id"])
    content = {"title": title, "exactText": list(dict.fromkeys(texts)) or [title],
               "templateRef": plan["templateRef"], "layoutRef": plan["layoutRef"],
               "slots": slots, "asset_needs": brief["asset_needs"]}
    if plan.get("version") == "0.3.0":
        from html_object_decomposition import narration_design

        expected = narration_design(plan)
        if brief.get("narration_design") != expected:
            _fail("设计 brief 与当前对象/语块状态不一致")
        content["narrationDesign"] = expected
        # Subject generation payload belongs to the asset provider, not the full-page design model.
        content["asset_needs"] = [{key: value for key, value in need.items()
                                  if key not in ("generation_request", "state_sequence")}
                                 for need in brief["asset_needs"]]
    return content


def assemble_reference(plan, brief, *, repo_root, directory, runner, run_dir=None):
    subjects = _existing_subjects(plan, run_dir)
    ids = ["page:component-01"]
    kinds = {v["kind"] for v in plan["slots"].values()}
    for types, page in (({"arrow"}, "component-02"), ({"card", "figure", "summary"}, "component-03"),
                        ({"annotation", "badge", "label"}, "component-05")):
        if kinds & types:
            ids.append("page:" + page)
    catalog = json.loads((Path(repo_root) / "html_engine/visual/generated/catalog.json").read_text(encoding="utf-8"))
    layout = next((value for value in catalog["layouts"] if value["id"] == plan["layoutRef"]["id"]
                   and value["version"] == plan["layoutRef"]["version"]), None)
    if layout is None or any(slot not in layout["slots"] for slot in plan["slots"]):
        _fail("设计参考缺少匹配的注册布局")
    content = design_content(plan, brief)
    content["layoutGeometry"] = {"canvas": layout["canvas"],
                               "slots": {slot: layout["slots"][slot]["box"] for slot in plan["slots"]}}
    request = {"task": "HTML 注册槽位设计参考", "mode": "standard", "referenceIds": ids,
               "selectionReasons": {id: "按当前计划的文字、容器、关系或标注类型选取；仅借鉴外观。" for id in ids},
               "content": content}
    directory = Path(directory)
    if (directory / "manifest.json").is_file():
        cached = verify_package(directory)
        attached = {entry["sha256"] for entry in cached["manifest"]["attachments"]
                    if entry.get("type") == "subject-reference"}
        if cached["content"] != content or attached != {subject["sha256"] for _, subject in subjects}:
            _fail("已有参考包不匹配当前布局或主体；请使用新版本目录")
        if not any(entry.get("type") == "layout-guide" for entry in cached["manifest"]["attachments"]):
            _fail("已有参考包没有布局参考；请使用新版本目录")
        return cached
    input_path = directory.parent / (directory.name + "-input.json")
    write_json_atomic(input_path, request)
    result = runner(["node", str(Path(repo_root) / "html_engine/tools/catalog-assemble.cjs"),
                     "--input", str(input_path), "--out", str(directory)],
                    cwd=str(repo_root), capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout_sec=120)
    if result.returncode:
        raise HtmlReviewError("分类参考包装配失败，请检查源定义或保留的包", code="REFERENCE_ASSEMBLY_FAILED")
    if subjects:
        _attach_subjects(directory, subjects)
    from html_layout_reference import attach_layout_guide
    attach_layout_guide(directory)
    return verify_package(directory)


def _existing_subjects(plan, run_dir):
    """Only accepted project resources; verify current bytes against the frozen plan."""
    if plan.get("version") != "0.3.0":
        return []
    selected = [check for check in plan["anchorChecks"].values() if check["status"] != "pending_asset"]
    if not selected:
        return []
    if run_dir is None:
        _fail("已有主体参考必须提供实际项目资源目录")
    from html_scene_editing import SceneEditError, resources

    try:
        verified = resources(run_dir, [check["assetRef"] for check in selected])
    except SceneEditError as exc:
        raise HtmlReviewError("已有主体字节未通过核验", code="REFERENCE_PACKAGE_INVALID") from exc
    from html_object_decomposition import normalize_decomposition
    from html_narration_semantics import NarrationSemanticError

    try:
        refreshed = normalize_decomposition(plan, asset_budget=plan["assetPolicy"]["budget"], resources=verified)
    except NarrationSemanticError as exc:
        raise HtmlReviewError("已有主体分工或锚点已失效", code="REFERENCE_PACKAGE_INVALID") from exc
    if refreshed["decomposition_sha256"] != plan["decomposition_sha256"]:
        _fail("已有主体字节、锚点或分工已变化，须重新规划")
    subjects = {}
    for check in selected:
        asset = next((entry for entry in verified["assets"] if {"id": entry["id"], "version": entry["version"]} == check["assetRef"]), None)
        if not asset or asset["file"]["sha256"] != check["file_sha256"]:
            _fail("已有主体已变化，不能沿用旧状态规划")
        name = "subject-" + sha256_json({"assetRef": check["assetRef"], "sha256": check["file_sha256"]})[:24] + ".png"
        subjects[name] = {"assetRef": check["assetRef"], "sha256": check["file_sha256"],
                          "width": asset["intrinsic"]["width"], "height": asset["intrinsic"]["height"],
                          "bytes": base64.b64decode(verified["pack"][asset["file"]["path"]], validate=True)}
    return [(name, subject) for name, subject in subjects.items()]


def _attach_subjects(directory, subjects):
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, subject in subjects:
        path = directory / name
        if path.exists():
            _fail("主体参考文件名冲突")
        path.write_bytes(subject["bytes"])
        manifest["files"].append({"path": name, "size": len(subject["bytes"]), "sha256": subject["sha256"]})
        manifest["attachments"].append({"path": name, "sha256": subject["sha256"], "width": subject["width"],
                                        "height": subject["height"], "type": "subject-reference", "assetRef": subject["assetRef"]})
    manifest["cacheKey"] = sha256_json({"original": manifest["cacheKey"],
                                       "subjects": [{"assetRef": subject["assetRef"], "sha256": subject["sha256"]} for _, subject in subjects]})
    manifest["manifestSha256"] = sha256_json({key: value for key, value in manifest.items() if key != "manifestSha256"})
    write_json_atomic(manifest_path, manifest)


def design_prompt(package, *, instruction=""):
    # Accurate slot content appears once; hashes, sample IDs and audit metadata
    # stay outside the model input. Reference examples never become new content.
    if "narrationDesign" in package["content"]:
        return _semantic_design_prompt(package, instruction=instruction)
    return (
        f"PromptVersion: {PROMPT_VERSION}。生成一张完整页面的设计参考。"
        "只使用黑、灰、白；白色背景。精细字阶、充足留白、清晰线条、柔和灰阶阴影和渐变。"
        "附件分类图只供美感与组件外观参考，不复制其样例文字、数字、编号或栏目。"
        "layout-guide附件只用于槽位位置与比例，编号、英文槽位名及字幕预留提示不得进入成品。"
        "准确文字和结构以下面的内容为准，注册槽位不改变；文字、卡片和关系由代码复刻，独立主体为图片。"
        "layoutGeometry是代码布局真值：坐标相对于canvas，按比例适配输出尺寸。"
        "每个槽位保持给定位置与范围，不重排、不新增关系；全部正文、标签、说明和结论完整呈现。"
        "canvas.contentBottom以下完全留白，容器、阴影和主体不得侵入字幕区。"
        "16:9，底部1/9留白给字幕，不添加品牌或来源页脚。"
        "主体图片与代码采用统一的灰阶材质与光照。风格指导："
        + json.dumps(package["guidance"]["style"], ensure_ascii=False)
        + "。准确内容：" + json.dumps({k: v for k, v in package["content"].items() if k != "exactText"}, ensure_ascii=False)
        + ("。本轮修改方向：" + instruction if instruction else "")
    )


def _semantic_design_prompt(package, *, instruction):
    content = {key: value for key, value in package["content"].items() if key != "exactText"}
    content["narrationDesign"] = {key: value for key, value in content["narrationDesign"].items()
                                  if key not in ("source_sha256", "anchor_checks")}
    content["subjectAttachments"] = [
        {"attachmentIndex": index + 1, "assetRef": entry["assetRef"]}
        for index, entry in enumerate(package["manifest"]["attachments"])
        if entry.get("type") == "subject-reference"
    ]
    return (
        f"PromptVersion:{SEMANTIC_PROMPT_VERSION}。生成一张完整页面的设计参考，保留已认可的视觉方向。"
        "分类附件仅供组件外观与材质参考，样例文字不属于本课；subjectAttachments标明实际主体附件与素材身份，"
        "layout-guide附件是确定性布局参考，保持其位置与比例；不把编号、英文槽位名、边框或字幕提示画入成品。"
        "这些已有主体保持形象与归属，不改成另一对象。讲稿和准确槽位内容决定表达，"
        "objectSemantics 对应的对象职责和 sequence 的初始/逐句/结束状态必须能由独立组件承载。"
        "本图可展示最终构图，但不能把终态所有对象在初始阶段可见当成制作计划。"
        "input、处理和output、容量/预留关系分别由代码文字、容器与关系组件承担；"
        "图片只承担单独主体，不烘焙文字、数字、价格、箭头或多阶段，不发明数值、容量或换算比例。"
        "layoutGeometry坐标以canvas为基准，等比映射到输出；逐槽保持给定矩形，不重排、不交换标题与简介。"
        "canvas.contentBottom以下留空；不超出资产预算，不增加未声明主体。"
        "配色与材质沿用风格指导，不另改审美；16:9，底部1/9留空，不加品牌或来源页脚。"
        "锚点须后续实际定位，不把通用focus冒充具体部位；设计图不证明组件重建或语义QA通过。"
        "风格指导：" + json.dumps(package["guidance"]["style"], ensure_ascii=False)
        + "。本课唯一内容与状态输入：" + json.dumps(content, ensure_ascii=False)
        + ("。本轮修改方向：" + instruction if instruction else "")
    )
