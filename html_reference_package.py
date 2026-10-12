"""Verified D packages consumed by the E design request, never runtime IDs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artifact_fingerprint import sha256_json
from pipeline_lifecycle import write_json_atomic
from html_visual_review_service import HtmlReviewError

PROMPT_VERSION = "html-design-reference/0.3.0"


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
    return {"title": title, "exactText": list(dict.fromkeys(texts)) or [title],
            "templateRef": plan["templateRef"], "layoutRef": plan["layoutRef"],
            "slots": slots, "asset_needs": brief["asset_needs"]}


def assemble_reference(plan, brief, *, repo_root, directory, runner):
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
    input_path = directory.parent / (directory.name + "-input.json")
    write_json_atomic(input_path, request)
    result = runner(["node", str(Path(repo_root) / "html_engine/tools/catalog-assemble.cjs"),
                     "--input", str(input_path), "--out", str(directory)],
                    cwd=str(repo_root), capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout_sec=120)
    if result.returncode:
        raise HtmlReviewError("分类参考包装配失败，请检查源定义或保留的包", code="REFERENCE_ASSEMBLY_FAILED")
    return verify_package(directory)


def design_prompt(package, *, instruction=""):
    # Accurate slot content appears once; hashes, sample IDs and audit metadata
    # stay outside the model input. Reference examples never become new content.
    return (
        f"PromptVersion: {PROMPT_VERSION}。生成一张完整页面的设计参考。"
        "只使用黑、灰、白；白色背景。精细字阶、充足留白、清晰线条、柔和灰阶阴影和渐变。"
        "附件分类图只供美感与组件外观参考，不复制其样例文字、数字、编号或栏目。"
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
