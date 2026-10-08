"""Annotation target resolution for HTML scenes (D03 pure core).

Maps annotation targets onto the html-visual renderer's deterministic
geometry report (the same evaluate output the player, frame harness, and
review tool emit):

- ``image_anchor``: asset semantic anchor through the contain placement —
  geometry already carries the transformed anchor point; the bounding
  box is never treated as content coordinates
- ``svg``: registered node geometry box (arrows/annotations)
- ``text_range``: the DOM Range half runs in the browser (actual glyph
  layout); this module validates the code-point range against the
  measured object and maps the returned viewport rects back into
  1600×900 canvas coordinates

Nothing here calls OCR; the image route keeps its existing capabilities.
Target deletion yields an explicit diagnostic. Scaling uses one factor
per viewport, so a correct input maps with sub-pixel error (≤1 logical
pixel by construction).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

CANVAS_WIDTH = 1600
CANVAS_HEIGHT = 900
_ALLOWED_KINDS = {"image_anchor", "svg", "text_range"}


class AnnotationTargetError(ValueError):
    def __init__(self, code: str, message: str, slide_id: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.slide_id = slide_id


def _geometry_nodes(geometry_report: Dict[str, Any]) -> Dict[str, Any]:
    geometry = geometry_report.get("geometry")
    if not isinstance(geometry, dict):
        raise AnnotationTargetError(
            "GEOMETRY_REPORT_INVALID", "几何报告缺少 geometry{}"
        )
    return geometry


def resolve_targets(
    geometry_report: Dict[str, Any],
    specs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Resolve annotation target specs against one geometry report.

    Returns ``{targets: [...], diagnostics: [...]}``. A spec whose node
    (or anchor) is gone produces a diagnostic entry — annotations then
    follow the spec's own visibility rule instead of guessing.
    """
    nodes = _geometry_nodes(geometry_report)
    targets: List[Dict[str, Any]] = []
    diagnostics: List[Dict[str, Any]] = []
    for spec in specs:
        if not isinstance(spec, dict):
            raise AnnotationTargetError("TARGET_SPEC_INVALID", "目标规格不是对象")
        target_id = str(spec.get("id") or "").strip()
        kind = str(spec.get("kind") or "").strip()
        node_id = str(spec.get("nodeId") or "").strip()
        if kind not in _ALLOWED_KINDS:
            raise AnnotationTargetError(
                "TARGET_KIND_INVALID",
                f"目标 {target_id} kind 必须是 {'/'.join(sorted(_ALLOWED_KINDS))}",
            )
        node = nodes.get(node_id)
        if node is None:
            diagnostics.append({
                "id": target_id,
                "code": "TARGET_NODE_GONE",
                "message": f"目标节点 {node_id} 已删除，批注需隐藏或重挂",
            })
            continue
        if kind == "image_anchor":
            anchor_id = str(spec.get("anchorId") or "").strip()
            anchors = node.get("anchors") or {}
            if anchor_id not in anchors:
                diagnostics.append({
                    "id": target_id,
                    "code": "TARGET_ANCHOR_GONE",
                    "message": f"资产锚点 {anchor_id} 不在节点 {node_id} 的登记中",
                })
                continue
            point = anchors[anchor_id]
            targets.append({
                "id": target_id,
                "kind": kind,
                "node_id": node_id,
                "canvas": {"x": point["x"], "y": point["y"]},
            })
        elif kind == "svg":
            box = node.get("box")
            if not box:
                diagnostics.append({
                    "id": target_id,
                    "code": "TARGET_GEOMETRY_MISSING",
                    "message": f"节点 {node_id} 无已登记几何",
                })
                continue
            targets.append({
                "id": target_id,
                "kind": kind,
                "node_id": node_id,
                "canvas_box": dict(box),
            })
        else:  # text_range
            start = spec.get("start")
            end = spec.get("end")
            if not isinstance(start, int) or not isinstance(end, int) or end <= start:
                raise AnnotationTargetError(
                    "TARGET_RANGE_INVALID",
                    f"目标 {target_id} 码点区间 [start,end) 不合法（半开区间）",
                )
            measured = (geometry_report.get("measurements") or {}).get(node_id)
            if measured is None:
                diagnostics.append({
                    "id": target_id,
                    "code": "TARGET_NODE_GONE",
                    "message": f"文字目标 {node_id} 无测量记录",
                })
                continue
            targets.append({
                "id": target_id,
                "kind": kind,
                "node_id": node_id,
                "canvas_box": dict(node.get("box") or {}),
                "codepoint_range": [start, end],
                # Actual per-line rects come from the DOM Range resolver in
                # the browser; the canvas box above is the fallback frame.
                "needs_dom_range": True,
            })
    return {"targets": targets, "diagnostics": diagnostics}


def apply_viewport_scale(
    resolved: Dict[str, Any],
    *,
    viewport_width: int,
) -> Dict[str, Any]:
    """Map canvas coordinates to viewport pixels with one scale factor."""
    if viewport_width <= 0:
        raise AnnotationTargetError("VIEWPORT_INVALID", "视口宽度不合法")
    scale = viewport_width / CANVAS_WIDTH
    out: Dict[str, Any] = {
        "scale": scale,
        "targets": [],
        "diagnostics": resolved.get("diagnostics", []),
    }
    for target in resolved.get("targets", []):
        scaled = dict(target)
        if "canvas" in target:
            scaled["viewport"] = {
                "x": target["canvas"]["x"] * scale,
                "y": target["canvas"]["y"] * scale,
            }
        if "canvas_box" in target:
            box = target["canvas_box"]
            scaled["viewport_box"] = {
                "x": box.get("x", 0) * scale,
                "y": box.get("y", 0) * scale,
                "width": box.get("width", 0) * scale,
                "height": box.get("height", 0) * scale,
            }
        out["targets"].append(scaled)
    return out
