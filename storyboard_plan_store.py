"""Step 2 plan persistence and freshness, separate from request orchestration."""
from __future__ import annotations
import json
import logging
import os
from typing import Any, Dict
import invalidation_service
from pipeline_lifecycle import write_json_atomic
from storyboard_planning import _step2_script_plan_fingerprint
logger = logging.getLogger("PPTStudio.StoryboardPlanStore")

def _step2_visual_plan_status(project: Any, script_plan: Dict[str, Any], *, visual_path: str) -> tuple[bool, bool]:
    if not os.path.isfile(visual_path):
        return False, False
    try:
        with open(visual_path, "r", encoding="utf-8-sig") as file:
            visual_plan = json.load(file)
    except (OSError, json.JSONDecodeError):
        return True, True
    if not isinstance(visual_plan, dict):
        return True, True
    stored_hash = str(visual_plan.get("source_script_hash") or "")
    return True, bool(stored_hash and stored_hash != _step2_script_plan_fingerprint(script_plan))


def _mark_step2_visual_plan_stale(project: Any, previous_plan: Dict[str, Any], current_plan: Dict[str, Any], *, visual_path: str) -> None:
    if previous_plan == current_plan:
        return
    if not os.path.isfile(visual_path):
        return
    try:
        with open(visual_path, "r", encoding="utf-8-sig") as file:
            visual_plan = json.load(file)
        if isinstance(visual_plan, dict) and visual_plan.get("slides"):
            current_hash = _step2_script_plan_fingerprint(current_plan)
            existing_hash = str(visual_plan.get("source_script_hash") or "")
            if existing_hash and existing_hash == current_hash:
                return
            # Preserve a real old fingerprint; legacy plans get a sentinel.
            visual_plan.setdefault("source_script_hash", "legacy-stale")
            write_json_atomic(visual_path, visual_plan)
    except (OSError, json.JSONDecodeError):
        logger.warning("Could not mark the existing visual plan stale after script edit")


def _sync_visual_plan_for_script_reorder(project: Any, previous_plan: Dict[str, Any], current_plan: Dict[str, Any], *, visual_path: str) -> bool:
    """Keep existing visuals when only the order of unchanged script pages moves."""
    previous_slides = previous_plan.get("slides") or []
    current_slides = current_plan.get("slides") or []
    if (not previous_slides or len(previous_slides) != len(current_slides)
            or previous_plan.get("title") != current_plan.get("title")):
        return False
    old_by_id = {slide.get("slide_id"): slide for slide in previous_slides if isinstance(slide, dict)}
    new_by_id = {slide.get("slide_id"): slide for slide in current_slides if isinstance(slide, dict)}
    if (len(old_by_id) != len(previous_slides) or old_by_id != new_by_id
            or [slide.get("slide_id") for slide in previous_slides]
            == [slide.get("slide_id") for slide in current_slides]):
        return False
    if not os.path.isfile(visual_path):
        return False
    try:
        with open(visual_path, "r", encoding="utf-8-sig") as file:
            visual_plan = json.load(file)
        visual_slides = visual_plan.get("slides") if isinstance(visual_plan, dict) else None
        if not isinstance(visual_slides, list):
            return False
        visual_by_id = {slide.get("slide_id"): slide for slide in visual_slides if isinstance(slide, dict)}
        if len(visual_by_id) != len(current_slides) or set(visual_by_id) != set(new_by_id):
            return False
        old_hash = _step2_script_plan_fingerprint(previous_plan)
        if visual_plan.get("source_script_hash") not in (None, "", old_hash):
            return False
        visual_plan["slides"] = [visual_by_id[slide["slide_id"]] for slide in current_slides]
        visual_plan["source_script_hash"] = _step2_script_plan_fingerprint(current_plan)
        write_json_atomic(visual_path, visual_plan)
        return True
    except (OSError, json.JSONDecodeError):
        logger.warning("Could not retain visual plan after script reorder")
        return False


def _persist_step2_script_plan(
    project: Any,
    plan: Dict[str, Any],
    previous_plan: Dict[str, Any],
    *, visual_path: str, script_path: str,
) -> tuple[bool, bool, bool, bool]:
    _sync_visual_plan_for_script_reorder(project, previous_plan, plan, visual_path=visual_path)
    write_json_atomic(script_path, plan)
    _mark_step2_visual_plan_stale(project, previous_plan, plan, visual_path=visual_path)
    visual_plan_exists, visual_stale = _step2_visual_plan_status(project, plan, visual_path=visual_path)
    existing_contract = os.path.isfile(
        os.path.join(project.run_dir, "planning", "visual_contract.json")
    )
    if existing_contract and not visual_plan_exists and previous_plan != plan:
        visual_stale = True
    visual_exists = visual_plan_exists or existing_contract
    statuses = project.get_step_status()
    visual_work_stale = visual_stale
    workflow_changed = (
        previous_plan != plan
        and visual_work_stale
        and statuses.get("2") != "in_progress"
    )
    if workflow_changed:
        invalidation_service.storyboard_script_changed(project)
    step2_status = project.get_step_status().get("2")
    workflow_pending = step2_status is not None and step2_status != "completed"
    return visual_exists, visual_stale, workflow_changed, workflow_pending
