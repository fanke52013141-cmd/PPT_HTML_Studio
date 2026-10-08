"""Reusable storyboard templates; storage receives its canonical path explicitly."""
from __future__ import annotations
import logging
import re
import uuid
from typing import Any, Dict, List
import yaml
from fastapi import HTTPException
from runtime_support import read_json_file
from pipeline_lifecycle import write_json_atomic
from template_utils import normalized_template_name, template_timestamp
from scripts.pipeline_profiles import role_catalog
from storyboard_profiles import (parse_storyboard_profile_text, storyboard_profile_editor_data, default_storyboard_rules, default_storyboard_profile_text, handdrawn_storyboard_rules, apply_storyboard_profile_patch)
logger = logging.getLogger("PPTStudio.StoryboardTemplates")

def storyboard_template_payload(
    template_id: str,
    name: str,
    rules: str,
    profile_text: str,
    built_in: bool = False,
    updated_at: str = "",
) -> Dict[str, Any]:
    profile = parse_storyboard_profile_text(profile_text)
    return {
        "id": template_id,
        "name": name,
        "built_in": built_in,
        "updated_at": updated_at,
        "rules": rules,
        "profile_yaml": profile_text,
        "roles": role_catalog(profile),
        "editor": storyboard_profile_editor_data(profile),
    }


def list_storyboard_templates(*, path: str) -> List[Dict[str, Any]]:
    templates = [
        storyboard_template_payload(
            "default",
            "内容优先通用分镜模板",
            default_storyboard_rules(),
            default_storyboard_profile_text(),
            built_in=True,
        ),
        storyboard_template_payload(
            "handdrawn_explainer",
            "手绘科普内容优先模板",
            handdrawn_storyboard_rules(),
            default_storyboard_profile_text(),
            built_in=True,
        ),
    ]
    stored = read_json_file(path, [])
    if not isinstance(stored, list):
        return templates
    for item in stored:
        if not isinstance(item, dict):
            continue
        try:
            templates.append(
                storyboard_template_payload(
                    str(item.get("id") or ""),
                    str(item.get("name") or ""),
                    str(item.get("rules") or ""),
                    str(item.get("profile_yaml") or ""),
                    updated_at=str(item.get("updated_at") or ""),
                )
            )
        except HTTPException as exc:
            logger.warning("Skipping invalid storyboard template %s: %s", item.get("id"), exc.detail)
    return templates


def get_storyboard_templates(*, path: str):
    return {"success": True, "templates": list_storyboard_templates(path=path)}


def save_storyboard_template(payload: Dict[str, Any], *, path: str):
    name = normalized_template_name(payload.get("name"))
    protected_names = {"默认分镜模板", "内容优先通用分镜模板", "手绘科普内容优先模板"}
    if name.casefold() in {item.casefold() for item in protected_names}:
        raise HTTPException(status_code=400, detail="内置分镜模板名称不可覆盖")
    rules = str(payload.get("rules") or "").strip() or default_storyboard_rules()
    profile_text = str(payload.get("profile_yaml") or "").strip() or default_storyboard_profile_text()
    profile = parse_storyboard_profile_text(profile_text)
    profile = apply_storyboard_profile_patch(profile, payload.get("profile_patch"))
    profile_text = yaml.safe_dump(profile, allow_unicode=True, sort_keys=False, width=1000).strip()

    stored = read_json_file(path, [])
    if not isinstance(stored, list):
        stored = []
    existing = next(
        (
            item
            for item in stored
            if isinstance(item, dict)
            and str(item.get("name") or "").strip().casefold() == name.casefold()
        ),
        None,
    )
    now = template_timestamp()
    if existing is None:
        existing = {"id": uuid.uuid4().hex[:12], "created_at": now}
        stored.append(existing)
    existing.update(
        {
            "name": name,
            "rules": rules,
            "profile_yaml": profile_text,
            "updated_at": now,
        }
    )
    write_json_atomic(path, stored)
    return {
        "success": True,
        "template": storyboard_template_payload(
            str(existing["id"]),
            name,
            rules,
            profile_text,
            updated_at=now,
        ),
        "templates": list_storyboard_templates(path=path),
    }


def delete_storyboard_template(template_id: str, *, path: str):
    if template_id == "default":
        raise HTTPException(status_code=400, detail="内置分镜模板不能删除")
    if not re.fullmatch(r"[0-9a-f]{12}", template_id):
        raise HTTPException(status_code=404, detail="分镜模板不存在")
    stored = read_json_file(path, [])
    if not isinstance(stored, list):
        stored = []
    next_stored = [
        item
        for item in stored
        if not (isinstance(item, dict) and str(item.get("id") or "") == template_id)
    ]
    if len(next_stored) == len(stored):
        raise HTTPException(status_code=404, detail="分镜模板不存在")
    write_json_atomic(path, next_stored)
    return {"success": True, "templates": list_storyboard_templates(path=path)}
