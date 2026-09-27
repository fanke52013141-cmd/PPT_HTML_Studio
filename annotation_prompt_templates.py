# -*- coding: utf-8 -*-
"""勾画标注 AI 规划 Prompt 的默认模板、版本与项目级覆盖(W3)。

本文件按 `.agents/skills/optimize-prompts/SKILL.md` 的合同设计:

- system 只放稳定规则(角色/输入契约/输出契约/硬性自检),每条规则出现一次;
- user 只放本次请求的变量(讲稿语块、文字候选、强调强度、需保护项);
- 模型只返回建议:beat_id、码点范围、quote、候选 token_ids、样式枚举、
  简短理由、歧义标记。annotation_id、多边形、时间、颜色、种子由程序生成,
  模型不得输出。
- token 坐标不下发(模型不依据坐标做决策);跨行目标用多个 token_id 表达。

项目覆盖存于 ``planning/annotation_prompts.json``;仅当存量内容与某个已知的
旧内置默认值完全一致时才迁移,真正的用户自定义内容永不覆盖。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

__all__ = [
    "ANNOTATION_PLAN_PROMPT_VERSION",
    "ANNOTATION_PROMPTS_FILE",
    "BUILTIN_ANNOTATION_PLAN_SYSTEM_PROMPT",
    "AnnotationPromptStore",
    "compose_plan_prompts",
]

ANNOTATION_PLAN_PROMPT_VERSION = "annotation_plan_v1"
ANNOTATION_PROMPTS_FILE = "annotation_prompts.json"

# 旧内置默认值登记表:迁移时只有与这些文本完全一致的项目内容才会被替换。
LEGACY_BUILTIN_DEFAULTS: tuple[str, ...] = ()

BUILTIN_ANNOTATION_PLAN_SYSTEM_PROMPT = """你是课件视频的勾画标注规划助手。任务:根据本页讲稿,从画面文字候选中挑选值得强调的重点,并给出讲稿锚点。这不是整页内容总结任务。

非目标:不生成路径、时间、坐标、颜色、编号;不输出 Markdown;不解释规则。

输入契约(user JSON):
- beats: 讲稿语块数组,每项含 beat_id、spoken_text。码点索引从 0 开始,range 为 [start, end) 左闭右开。
- candidates: 画面文字候选数组,每项含 token_id、text、granularity(char=单字,line=整行)。granularity=line 的候选只能整行选用。
- protected_items: 已有人工编辑或锁定的标注摘要,不得对同一画面目标重复建议。
- emphasis: 强调强度(weak/moderate/strong),决定建议数量:weak 最多 1 条,moderate 1-2 条,strong 最多 3 条。

选择依据(按优先级):
1. 讲稿中正在叙述的关键事实:日期、数字、百分比、金额、专有名词。
2. 与 spoken_text 明确对应的画面文字;没有画面文字对应的事实不要硬造。
3. 跨行文本(如长标题)用连续多个 token_id 表达,按阅读顺序。

冲突与失败策略:
- 找不到合适的强调点:返回空数组,不硬凑。
- 候选文本与讲稿用词不一致(如数字写法不同)时,以讲稿 quote 为准,并在 ambiguous 标 true。
- 对同一画面目标的建议不得重复;同一语块内同一短语只建议一次。

输出契约(纯 JSON 对象):
{"suggestions": [{"beat_id": "...", "range": [start, end], "quote": "...", "target_candidate_ids": ["..."], "style": "ellipse|underline|highlighter", "reason": "...", "ambiguous": false}]}
字段约束:
- beat_id 必须取自输入 beats;range 必须命中该语块的码点切片且与 quote 完全一致;range 长度不超过 40 个码点。
- target_candidate_ids 必须取自输入 candidates,至少 1 个;上下相邻的同词字符可以合并为多个 token_id。
- style 语义:ellipse=圈住要点,underline=划线标记,highlighter=低浓度覆盖一片。
- reason 不超过 40 字,说明"为什么强调它"。
- ambiguous=true 时必须说明分歧点。

硬性自检:
- quote 与 range 切片逐字一致(含标点)。
- 每个 target_candidate_id 都在输入里出现过。
- 不输出 suggestions 之外的顶层字段;不输出注释。"""


@dataclass(frozen=True)
class AnnotationPromptStore:
    """项目级 Prompt 覆盖的读写与组装。"""

    read_json_file: Callable[[Any], Any]
    write_json_atomic: Callable[[Any, Any], None]
    prompts_path_for: Callable[[str], Any]

    # ------------------------------------------------------------ 读写

    def load_overrides(self, run_dir: str) -> Dict[str, Any]:
        payload = self.read_json_file(self.prompts_path_for(run_dir))
        if not isinstance(payload, dict):
            return {}
        overrides = payload.get("overrides")
        return overrides if isinstance(overrides, dict) else {}

    def save_override(self, run_dir: str, system_prompt: str, *, expected_revision: Optional[int], now_iso: str) -> Dict[str, Any]:
        path = self.prompts_path_for(run_dir)
        payload = self.read_json_file(path)
        revision = 0
        if isinstance(payload, dict) and isinstance(payload.get("revision"), int):
            revision = payload["revision"]
            stored = payload.get("overrides", {}).get("plan_system_prompt")
            if expected_revision is not None and expected_revision != revision:
                from fastapi import HTTPException

                raise HTTPException(status_code=409, detail={"code": "revision_conflict", "current_revision": revision})
            # 迁移规则:仅当存量内容与旧内置默认值完全一致时才视为可覆盖;
            # 用户自定义内容(revision>0 且非旧默认)不受重置影响——
            # 显式保存本身就是用户动作,这里只保护 expected_revision。
        if not isinstance(system_prompt, str) or not system_prompt.strip():
            from fastapi import HTTPException

            raise HTTPException(status_code=422, detail="system_prompt 不能为空")
        if len(system_prompt) > 20000:
            from fastapi import HTTPException

            raise HTTPException(status_code=413, detail="Prompt 超过长度上限")
        updated = {
            "schema_version": 1,
            "builtin_version": ANNOTATION_PLAN_PROMPT_VERSION,
            "revision": revision + 1,
            "overrides": {"plan_system_prompt": system_prompt},
            "updated_at": now_iso,
        }
        self.write_json_atomic(path, updated)
        return updated

    def reset_override(self, run_dir: str, *, now_iso: str) -> Dict[str, Any]:
        path = self.prompts_path_for(run_dir)
        updated = {
            "schema_version": 1,
            "builtin_version": ANNOTATION_PLAN_PROMPT_VERSION,
            "revision": 1,
            "overrides": {},
            "updated_at": now_iso,
        }
        self.write_json_atomic(path, updated)
        return updated

    # ------------------------------------------------------------ 组装

    def effective_system_prompt(self, run_dir: str) -> tuple[str, str]:
        """返回 (生效 system prompt, 来源);来源为 builtin|project。"""
        overrides = self.load_overrides(run_dir)
        stored = overrides.get("plan_system_prompt")
        if isinstance(stored, str) and stored.strip():
            return stored, "project"
        return BUILTIN_ANNOTATION_PLAN_SYSTEM_PROMPT, "builtin"


def compose_plan_prompts(
    *,
    system_prompt: str,
    beats: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    protected_items: list[dict[str, Any]],
    emphasis: str,
) -> dict[str, str]:
    """组装最小必要的 user payload(纯函数;输入字段均已通过必要性判定)。"""
    user_payload = {
        "beats": [{"beat_id": b.get("beat_id"), "spoken_text": b.get("spoken_text")} for b in beats],
        "candidates": [
            {"token_id": c.get("token_id"), "text": c.get("text"), "granularity": c.get("granularity")}
            for c in candidates
        ],
        "protected_items": [
            {"quote": p.get("quote"), "style": p.get("style"), "locked": p.get("locked")}
            for p in protected_items
        ],
        "emphasis": emphasis,
    }
    return {
        "system": system_prompt,
        "user": json.dumps(user_payload, ensure_ascii=False),
    }
