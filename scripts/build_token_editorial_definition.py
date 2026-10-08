"""Author the approved reference's constrained definitions and example content.

Initial authoring helper only, not an application layout generator. Never replaces
an existing definition or manual scene with different bytes.
"""

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    layout = {
        "format": "hps.visual.layout",
        "version": "0.2.0",
        "id": "editorial-three-columns-v1",
        "name": "编辑式概念页：上部主视觉，下部三栏",
        "canvas": {
            "width": 1600,
            "height": 900,
            "contentBottom": 800,
            "subtitleHeight": 100,
        },
        "slots": {},
    }
    nodes = []

    def add(identity, node_type, box, **fields):
        layout["slots"][identity] = {
            "box": dict(zip(["x", "y", "width", "height"], box)),
            "maxLines": fields.pop("maxLines", 1),
            "align": fields.pop("align", "left"),
            "z": fields.pop("z", 2),
        }
        nodes.append({"id": identity, "slot": identity, "type": node_type, **fields})

    def text(identity, value, box, role="body", **extra):
        add(
            identity,
            "text",
            box,
            role=role,
            runs=[{"text": value, "emphasis": False}],
            **extra,
        )

    def shape(identity, box, fill, kind="rect", radius=0, z=1):
        fields = {"kind": kind, "fill": fill, "z": z}
        if kind == "rect":
            fields["radius"] = radius
        add(identity, "shape", box, **fields)

    text("header", "什么是 Token？", [80, 76, 790, 115], "title")
    shape("title-rule", [83, 204, 96, 10], "accent", radius=5)
    shape("definition-surface", [75, 250, 685, 88], "greenWash", radius=44)
    text("headline", "模型处理文本时使用的基本单位", [103, 268, 630, 63], "headline")
    text("intro", "具体切分方式取决于模型使用的分词器。", [90, 372, 694, 51], "intro")
    shape("hero-shadow", [805, 379, 683, 25], "blueWash", kind="ellipse")
    shape("figure", [827, 199, 150, 169], "blueWash", radius=18)
    for index, width in enumerate([111, 111, 77, 111]):
        shape(
            f"document-line-{index + 1}",
            [847, 227 + 26 * index, width, 11],
            "accent" if index == 0 else "muted",
            radius=5,
        )
    text("document-label", "文本", [854, 372, 100, 30], "caption", align="center")
    add("relation-arrow", "arrow", [990, 269, 45, 35])
    for index in range(4):
        shape(
            f"unit-{index + 1}",
            [1052 + 57 * index, 257, 46, 60],
            "yellow" if index % 2 else "greenWash",
            radius=10,
        )
    text("unit-label", "Token", [1101, 330, 120, 30], "caption", align="center")
    add(
        "subject",
        "image",
        [1239, 94, 333, 341],
        assetRef={"id": "bulb-editorial", "version": "0.1.0"},
        anchorId="focus",
        z=3,
    )
    for x, identity in [(552, "divider-1"), (1054, "divider-2")]:
        shape(identity, [x, 501, 2, 202], "line")
    points = [
        ("未必是一个完整的词", "可以是词的一部分、标点或其他文本片段。"),
        ("Token 数量不等于字数", "中文、英文和符号可能采用不同切分方式。"),
        ("上下文与用量按 Token 衡量", "许多服务按输入和输出 Token 计费。"),
    ]
    for index, (title, body) in enumerate(points):
        x = [75, 585, 1082][index]
        shape(f"number-surface-{index + 1}", [x, 500, 60, 60], "accent", kind="ellipse")
        text(
            f"number-{index + 1}",
            str(index + 1),
            [x + 2, 506, 56, 52],
            "number",
            align="center",
            z=3,
        )
        text(
            f"card-{index + 1}", title, [x + 86, 512, 385, 83], "cardTitle", maxLines=2
        )
        text(
            f"card-{index + 1}-body",
            body,
            [x + 80, 578, 390, 112],
            "cardBody",
            maxLines=3,
        )
    assert len(nodes) <= 40
    theme = json.loads(
        (ROOT / "html_engine/visual/themes/amber-science.json").read_text(
            encoding="utf-8"
        )
    )
    theme.update(
        id="amber-editorial",
        name="暖白琥珀编辑式科普",
        compatibleLayouts=["editorial-three-columns-v1"],
    )
    theme["colors"].update(
        ink="#24231F",
        body="#625C52",
        accent="#AF6908",
        blue="#AF6908",
        greenWash="#FBE6B0",
        blueWash="#F6EFE1",
        yellow="#E8AD35",
        muted="#B7A48B",
        line="#F0E5D0",
    )
    for role, size, weight, color in [
        ("title", 80, 700, "ink"),
        ("headline", 36, 700, "ink"),
        ("intro", 28, 400, "body"),
        ("cardTitle", 28, 700, "ink"),
        ("cardBody", 28, 400, "body"),
        ("number", 38, 700, "panel"),
        ("caption", 18, 400, "body"),
    ]:
        theme["text"][role].update(
            size=size,
            weight=weight,
            color=color,
            lineHeight=1.45 if role == "cardBody" else 1.3,
        )
    template = {
        "format": "hps.visual.template",
        "version": "0.1.0",
        "id": "editorial-three-columns-v1",
        "name": "编辑式三栏概念解释",
        "structure": "explanation-cards",
        "layoutRef": {"id": layout["id"], "version": "0.2.0"},
        "slots": {
            node["slot"]: {"kinds": [node["type"]], "required": True} for node in nodes
        },
    }
    scene = {
        "format": "hps.visual.scene",
        "version": "0.4.0",
        "id": "token-editorial",
        "name": "什么是 Token？",
        "themeRef": {"id": theme["id"], "version": "0.2.0"},
        "layoutRef": template["layoutRef"],
        "templateRef": {"id": template["id"], "version": "0.1.0"},
        "durationMs": 18000,
        "nodes": nodes,
        "motion": [
            {
                "targetId": node["id"],
                "type": "enter",
                "startMs": 0,
                "durationMs": 800,
                "offsetX": 0,
                "offsetY": 0 if node["type"] == "shape" else 12,
            }
            for node in nodes
        ],
        "beats": [],
        "source": "User-approved full Image2.5 design reference; authoritative text retained as code; separate bulb cutout; existing narration reused",
    }
    fixture = copy.deepcopy(scene)
    fixture.update(
        id="editorial-condensation",
        name="冷杯外的水滴",
        source="Non-Token replacement fixture using shared editorial template and primitives",
    )
    replacements = {
        "header": "冷杯外的水滴",
        "headline": "水蒸气遇冷凝结成小水滴",
        "intro": "空气中的水蒸气通常不可见。",
        "document-label": "空气",
        "unit-label": "水滴",
        "card-1": "空气里有水蒸气",
        "card-1-body": "水蒸气通常看不见，却存在于空气中。",
        "card-2": "遇冷发生凝结",
        "card-2-body": "较冷的杯壁让水蒸气凝结成水滴。",
        "card-3": "杯外水滴来自空气",
        "card-3-body": "不是杯子里的水漏到了杯壁外。",
    }
    for node in fixture["nodes"]:
        if node["id"] in replacements:
            node["runs"][0]["text"] = replacements[node["id"]]
        if node["type"] == "image":
            node["assetRef"]["id"] = "condensation"
    for relative, value in [
        ("html_engine/visual/layouts/editorial-three-columns-v1.json", layout),
        ("html_engine/visual/templates/editorial-three-columns-v1.json", template),
        ("html_engine/visual/themes/amber-editorial.json", theme),
        ("outputs/image25-sheet/token-editorial-v1/author-scene.json", scene),
        ("html_engine/visual/scenes/editorial-condensation.json", fixture),
    ]:
        target = ROOT / relative
        payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        if target.exists() and target.read_text(encoding="utf-8") != payload:
            raise SystemExit(f"Existing author edits preserved: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
    print(f"Authored {len(nodes)} independently controlled nodes")


if __name__ == "__main__":
    main()
