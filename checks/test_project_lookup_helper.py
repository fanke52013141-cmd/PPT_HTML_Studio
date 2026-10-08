"""项目查询样板必须统一走 project_path_service.project_or_404（审查 L-11）。

回归背景：38 处服务层 `db.query(Project)...first()` + 404 判断样板，
以及 5 个路由文件各自重复定义 _project_or_404，已收敛到单一来源。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from project_path_service import project_or_404  # noqa: F401,E402

SERVICES = (
    "narration_service.py",
    "tts_service.py",
    "storyboard_service.py",
    "image_workflow_service.py",
)
ROUTES = (
    "mask_editor_routes.py",
    "one_click_routes.py",
    "digital_human_routes.py",
    "project_style_routes.py",
    "article_routes.py",
)

BOOTSTRAP = "db.query(Project).filter(Project.id == project_id).first()"


def test_services_use_single_project_lookup() -> None:
    for name in SERVICES:
        source = (ROOT / name).read_text(encoding="utf-8")
        assert BOOTSTRAP not in source, f"{name} 仍有项目查询样板"
        assert "project_or_404" in source, f"{name} 未使用统一 helper"


ACCOUNT_SCOPED_SITES = (
    "pptx_service.py",
    "storyboard_background.py",
    "visual_settings_service.py",
    "ai_mask_routes.py",
    "ip_character_service.py",
)


def test_bypass_sites_carry_account_filter() -> None:
    """R5-001 闭环:允许保留自有查询的文件必须带账号条件,防止越权访问。"""
    for name in ACCOUNT_SCOPED_SITES:
        source = (ROOT / name).read_text(encoding="utf-8")
        assert "Project.account_id == get_current_account_id()" in source, (
            f"{name} 的项目查询缺少账号过滤(R5-001)"
        )
        assert "account_context" in source, f"{name} 未导入账号上下文"


def test_routes_do_not_redefine_project_or_404() -> None:
    for name in ROUTES:
        source = (ROOT / name).read_text(encoding="utf-8")
        assert "def _project_or_404" not in source, f"{name} 仍重复定义 helper"
        assert (
            "from project_path_service import project_or_404 as _project_or_404"
            in source
        ), f"{name} 缺少统一导入"


def test_helper_returns_project_or_raises_404() -> None:
    from fastapi import HTTPException

    class _Query:
        def filter(self, *_a, **_k):
            return self

        def first(self):
            return None

    class _Db:
        def query(self, *_a, **_k):
            return _Query()

    try:
        project_or_404(_Db(), "missing-id")
    except HTTPException as exc:
        assert exc.status_code == 404
        assert exc.detail == "项目不存在"
    else:
        raise AssertionError("缺失项目必须抛出 404")

def test_style_routes_use_only_public_service_apis() -> None:
    """守护（审查 L-06）：路由不得调用其他模块的下划线私有函数。"""
    import re

    source = (ROOT / "project_style_routes.py").read_text(encoding="utf-8")
    hosts = (
        "style_service|reverse_service|reference_service"
        "|project_profile_service|template_service|reference_store"
    )
    offenders = re.findall(rf"(?:{hosts})\._[a-zA-Z_0-9]+", source)
    assert offenders == [], f"路由仍有跨模块私有调用: {offenders}"
