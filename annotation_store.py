# -*- coding: utf-8 -*-
"""勾画标注模块的文件持久化:读取、校验、原子写入。

对应交接文档 5.1/8.1:

- 产物路径全部由服务端从 run 目录派生(``project_storage`` 的安全路径
  工具),不接受客户端文件系统路径。
- 写入复用 ``write_json_atomic`` 的安全语义(同目录临时文件 + 原子替换,
  失败保留原文件并抛错,绝不直写兜底)。
- 缺文件 = 功能未使用(返回 None);损坏文件抛 :class:`AnnotationStoreError`
  (code=corrupt),携带路径与解析错误,**不当作空成功**。
- revision 的 CAS(读→校验→合并→写→+1)由服务层在项目锁内完成;
  本存储层只做无状态读写,锁通过依赖注入由上层持有。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from annotation_contracts import (
    ANNOTATION_PAGE_FILE,
    ANNOTATION_SCHEMA_VERSION,
    ANNOTATION_SETTINGS_FILE,
    AnnotationPage,
    AnnotationSettings,
    Issue,
    collect_issues,
    default_annotation_settings,
)
from project_storage import planning_path, slide_dir

logger = logging.getLogger("PPTStudio.AnnotationStore")


class AnnotationStoreError(Exception):
    """存储层错误;corrupt 必须可诊断,绝不降级为空成功。"""

    def __init__(self, code: str, message: str, *, path: Optional[str] = None):
        super().__init__(message)
        self.code = code  # missing | corrupt | io | schema
        self.path = path
        self.message = message


@dataclass(frozen=True)
class AnnotationStoreDependencies:
    """窄依赖:原子写出函数注入,便于测试模拟写失败。"""

    write_json_atomic: Callable[[Path, Any], None]


class AnnotationStore:
    """annotations 产物的无状态读写器。"""

    def __init__(self, dependencies: AnnotationStoreDependencies):
        self._write_json_atomic = dependencies.write_json_atomic

    # ------------------------------------------------------------ 路径

    def settings_path(self, run_dir: str) -> Path:
        return planning_path(run_dir, ANNOTATION_SETTINGS_FILE)

    def page_path(self, run_dir: str, slide_id: str) -> Path:
        return slide_dir(run_dir, slide_id) / ANNOTATION_PAGE_FILE

    # ------------------------------------------------------------ 设置

    def read_settings(self, run_dir: str) -> Optional[AnnotationSettings]:
        path = self.settings_path(run_dir)
        payload, error = self._read_json(path)
        if error is not None:
            raise error
        if payload is None:
            return None
        issues: List[Issue] = []
        settings = self._parse_settings(payload, issues)
        if settings is None or issues:
            raise AnnotationStoreError(
                "schema",
                "annotation_settings.json 结构非法: " + "; ".join(i["message"] for i in collect_issues(issues)),
                path=str(path),
            )
        return settings

    def write_settings(self, run_dir: str, settings: AnnotationSettings) -> None:
        path = self.settings_path(run_dir)
        try:
            self._write_json_atomic(Path(path), settings.to_dict())
        except Exception as exc:
            raise AnnotationStoreError("io", f"写入 annotation_settings.json 失败: {exc}", path=str(path)) from exc

    # ------------------------------------------------------------ 页面

    def read_page(self, run_dir: str, slide_id: str, *, canvas: Tuple[int, int]) -> Optional[AnnotationPage]:
        path = self.page_path(run_dir, slide_id)
        payload, error = self._read_json(path)
        if error is not None:
            raise error
        if payload is None:
            return None
        issues: List[Issue] = []
        page = AnnotationPage.from_payload(payload, issues, canvas=canvas)
        if page is None or issues:
            raise AnnotationStoreError(
                "schema",
                f"{ANNOTATION_PAGE_FILE} 结构非法: " + "; ".join(i["message"] for i in collect_issues(issues)),
                path=str(path),
            )
        return page

    def write_page(self, run_dir: str, slide_id: str, page: AnnotationPage) -> None:
        path = self.page_path(run_dir, slide_id)
        try:
            self._write_json_atomic(Path(path), page.to_dict())
        except Exception as exc:
            raise AnnotationStoreError("io", f"写入 {ANNOTATION_PAGE_FILE} 失败: {exc}", path=str(path)) from exc

    # ------------------------------------------------------------ 内部

    def _read_json(self, path: Path) -> Tuple[Optional[Any], Optional[AnnotationStoreError]]:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except FileNotFoundError:
            return None, None
        except OSError as exc:
            return None, AnnotationStoreError("io", f"读取 {path.name} 失败: {exc}", path=str(path))
        try:
            return json.loads(text), None
        except json.JSONDecodeError as exc:
            return None, AnnotationStoreError(
                "corrupt", f"{path.name} 不是合法 JSON(第 {exc.lineno} 行:{exc.msg})", path=str(path)
            )

    def _parse_settings(self, payload: Any, issues: List[Issue]) -> Optional[AnnotationSettings]:
        if not isinstance(payload, dict):
            issues.append(Issue("settings", "not_object", "设置必须是对象"))
            return None
        if payload.get("schema_version") != ANNOTATION_SCHEMA_VERSION:
            issues.append(Issue("schema_version", "bad_version", f"schema_version 必须是 {ANNOTATION_SCHEMA_VERSION}"))
            return None
        enabled = payload.get("enabled")
        if not isinstance(enabled, bool):
            issues.append(Issue("enabled", "not_bool", "enabled 必须是布尔"))
            enabled = False
        revision = payload.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            issues.append(Issue("revision", "bad_revision", "revision 必须是 >=1 的整数"))
            revision = 1
        defaults = payload.get("defaults")
        if defaults is None:
            defaults = dict(default_annotation_settings().defaults)
        if not isinstance(defaults, dict):
            issues.append(Issue("defaults", "not_object", "defaults 必须是对象"))
            defaults = {}
        decision = payload.get("decision", "none")
        if decision not in ("none", "no_annotations"):
            issues.append(Issue("decision", "bad_enum", "decision 必须是 none/no_annotations"))
            decision = "none"
        if issues:
            return None
        return AnnotationSettings(
            revision=revision,
            enabled=enabled,
            defaults=defaults,
            updated_at=str(payload.get("updated_at") or ""),
            decision=decision,
        )


_STORE: Optional[AnnotationStore] = None


def configure_annotation_store(dependencies: AnnotationStoreDependencies) -> None:
    global _STORE
    _STORE = AnnotationStore(dependencies)


def get_annotation_store() -> AnnotationStore:
    if _STORE is None:
        raise RuntimeError("annotation store 尚未配置依赖(启动装配缺失)")
    return _STORE
