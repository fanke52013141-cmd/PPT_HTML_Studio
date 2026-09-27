# -*- coding: utf-8 -*-
"""勾画标注 AI 规划器(W3):最小载荷、输出校验、与人工修改合并。

- 窄 LLM 依赖:``llm_generate(system, user) -> dict`` 由装配注入(生产为
  ``json_llm_service.generate_json_with_configured_llm`` 的受控包装);
  本模块不导入 server、不持有客户端。
- 格式损坏最多一次修复/重试(LLM 服务内建);解析失败保留现有草稿并报告。
- 重规划不覆盖 locked/modified 条目;AI 初始建议作为可恢复快照保存
  (页级 ai_suggestion_snapshot)。
- 校验:beat 存在、码点切片与 quote 一致、token 存在、样式合法、
  密度上限(默认每页最多 3 条,emphasis=weak 1 条)、重复建议剔除。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from annotation_contracts import (
    AnnotationItem,
    AnnotationPage,
    Issue,
    anchor_quote_matches,
    next_annotation_id,
)
from annotation_prompt_templates import AnnotationPromptStore, compose_plan_prompts

logger = logging.getLogger("PPTStudio.AnnotationPlanner")

VALID_STYLES = ("ellipse", "underline", "highlighter")
MAX_SUGGESTIONS = {"weak": 1, "moderate": 2, "strong": 3}
MAX_RANGE_CODEPOINTS = 40


@dataclass(frozen=True)
class AnnotationPlannerDependencies:
    prompt_store: AnnotationPromptStore
    llm_generate: Callable[..., Dict[str, Any]]  # (system_prompt=, user_prompt=, ...) -> dict


class AnnotationPlanningError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class AnnotationPlanner:
    def __init__(self, dependencies: AnnotationPlannerDependencies):
        self._deps = dependencies

    # ------------------------------------------------------------ 主流程

    def plan_slide(
        self,
        run_dir: str,
        slide_id: str,
        beats: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        page: Optional[AnnotationPage],
        *,
        emphasis: str,
        image_hash: Optional[str],
        narration_hash: Optional[str],
        now_iso: str,
        replace_all: bool = False,
    ) -> Tuple[List[AnnotationItem], Dict[str, Any], List[Issue]]:
        """对本页执行一次 AI 规划,返回 (新增条目, 建议快照, 校验问题)。

        - 不覆盖 locked/modified 条目(replace_all 时先快照,由调用方保存
          可撤销版本;本函数只产出"新增"条目,删除仍由用户显式操作)。
        - LLM 输出非法字段一律拒绝并记录 issue;不猜测 ID。
        """
        system_prompt, source = self._deps.prompt_store.effective_system_prompt(run_dir)
        protected = self._protected_summaries(page)
        prompts = compose_plan_prompts(
            system_prompt=system_prompt,
            beats=beats,
            candidates=candidates,
            protected_items=protected,
            emphasis=emphasis,
        )
        try:
            raw = self._deps.llm_generate(
                system_prompt=prompts["system"],
                user_prompt=prompts["user"],
                run_dir=run_dir,
                artifact_prefix=f"annotation_plan_{slide_id}",
                schema_hint='{"suggestions": [{"beat_id","range","quote","target_candidate_ids","style","reason","ambiguous"}]}',
            )
        except Exception as exc:
            raise AnnotationPlanningError("llm_failed", str(exc)) from exc

        snapshot = {
            "version": 1,
            "prompt_source": source,
            "emphasis": emphasis,
            "created_at": now_iso,
            "suggestions": raw.get("suggestions") if isinstance(raw, dict) else None,
        }
        issues: List[Issue] = []
        suggestions = self._normalize_suggestions(raw, beats, candidates, issues)
        return suggestions, snapshot, issues

    # ------------------------------------------------------------ 校验

    def _protected_summaries(self, page: Optional[AnnotationPage]) -> List[Dict[str, Any]]:
        protected: List[Dict[str, Any]] = []
        for item in page.items if page else ():
            if item.protection.locked or item.protection.modified_fields:
                protected.append(
                    {
                        "quote": item.anchor.quote if item.anchor else (item.target.quote or ""),
                        "style": item.style.type,
                        "locked": item.protection.locked,
                    }
                )
        return protected

    def _normalize_suggestions(
        self,
        raw: Any,
        beats: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        issues: List[Issue],
    ) -> List[AnnotationItem]:
        from annotation_contracts import (
            AnnotationAnchor,
            AnnotationInputs,
            AnnotationProtection,
            AnnotationStatus,
            AnnotationStyle,
            AnnotationTarget,
            AnnotationTiming,
        )

        if not isinstance(raw, dict) or not isinstance(raw.get("suggestions"), list):
            issues.append(Issue("suggestions", "bad_structure", "模型输出缺少 suggestions 数组"))
            return []
        beat_map = {str(b.get("beat_id")): str(b.get("spoken_text") or "") for b in beats}
        candidate_map = {str(c.get("token_id")): c for c in candidates}
        token_order = {str(c.get("token_id")): index for index, c in enumerate(candidates)}

        items: List[AnnotationItem] = []
        seen_quotes: set[tuple[str, str]] = set()
        for index, suggestion in enumerate(raw["suggestions"]):
            path = f"suggestions[{index}]"
            if not isinstance(suggestion, dict):
                issues.append(Issue(path, "bad_structure", "建议必须是对象"))
                continue
            beat_id = suggestion.get("beat_id")
            spoken = beat_map.get(str(beat_id))
            if spoken is None:
                issues.append(Issue(f"{path}.beat_id", "unknown_beat", f"语块 {beat_id} 不存在"))
                continue
            style_type = suggestion.get("style")
            if style_type not in VALID_STYLES:
                issues.append(Issue(f"{path}.style", "bad_enum", f"style 必须是 {VALID_STYLES} 之一"))
            range_value = suggestion.get("range")
            quote = suggestion.get("quote")
            if (
                not isinstance(range_value, list)
                or len(range_value) != 2
                or not all(isinstance(v, int) and not isinstance(v, bool) for v in range_value)
            ):
                issues.append(Issue(f"{path}.range", "bad_range", "range 必须是 [start, end] 整数"))
                continue
            start, end = range_value
            if not isinstance(quote, str) or not quote:
                issues.append(Issue(f"{path}.quote", "bad_quote", "quote 必须是非空字符串"))
                continue
            if end - start > MAX_RANGE_CODEPOINTS:
                issues.append(Issue(f"{path}.range", "too_long", f"锚点范围超过 {MAX_RANGE_CODEPOINTS} 个码点"))
                continue
            if start < 0 or end > len(spoken) or not anchor_quote_matches(spoken, AnnotationAnchor(
                beat_id=str(beat_id), range_start=start, range_end=end, quote=quote,
                occurrence=1, context_before="", context_after="",
            )):
                issues.append(Issue(f"{path}.quote", "quote_mismatch", "quote 与讲稿码点切片不一致"))
                continue

            token_ids_raw = suggestion.get("target_candidate_ids")
            if not isinstance(token_ids_raw, list) or not token_ids_raw:
                issues.append(Issue(f"{path}.target_candidate_ids", "required", "必须给出画面候选"))
                continue
            token_ids: List[str] = []
            polygons: List[List[List[int]]] = []
            unknown_tokens = False
            for token_id in token_ids_raw:
                candidate = candidate_map.get(str(token_id))
                if candidate is None:
                    issues.append(Issue(f"{path}.target_candidate_ids", "unknown_token", f"候选 {token_id} 不存在"))
                    unknown_tokens = True
                    break
                token_ids.append(str(token_id))
                polygons.append(candidate.get("polygon") or [])
            if unknown_tokens:
                continue
            if style_type not in VALID_STYLES:
                continue
            granularity = "line" if any(candidate_map[t].get("granularity") == "line" for t in token_ids) else "char"
            quote_key = (str(beat_id), quote)
            if quote_key in seen_quotes:
                continue  # 重复建议静默剔除(同语块同短语只保留一条)
            seen_quotes.add(quote_key)
            reason = str(suggestion.get("reason") or "")[:200]
            ambiguous = bool(suggestion.get("ambiguous"))
            items.append(
                AnnotationItem(
                    annotation_id="",  # 由调用方分配
                    target=AnnotationTarget(
                        kind="text",
                        layout_revision=None,
                        token_ids=tuple(token_ids),
                        polygons=tuple(tuple((p[0], p[1]) for p in poly) for poly in polygons if len(poly) == 4),
                        quote=quote,
                        granularity=granularity,
                        mask_group_ids=(),
                    ),
                    anchor=AnnotationAnchor(
                        beat_id=str(beat_id),
                        range_start=start,
                        range_end=end,
                        quote=quote,
                        occurrence=1,
                        context_before="",
                        context_after="",
                    ),
                    style=AnnotationStyle(type=style_type, color="#F46A38", opacity=0.85, width=5, padding=8, seed=0),
                    timing=AnnotationTiming(
                        trigger_mode="anchor_start", offset_sec=0.0, draw_duration_sec=0.6,
                        hold_mode="beat_end", hold_duration_sec=None, exit_duration_sec=0.15,
                    ),
                    status=AnnotationStatus(
                        content="draft",
                        spatial="needs_review" if ambiguous or granularity == "line" else "valid",
                        temporal="awaiting_audio",
                    ),
                    protection=AnnotationProtection(source="ai", modified_fields=(), locked=False),
                    inputs=AnnotationInputs(image_hash=None, narration_hash=None, audio_hash=None),
                    review_issues=({"code": "ambiguous", "message": reason},) if ambiguous else (),
                )
            )
        return items
