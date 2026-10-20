"""Preauthorized author publication through original guards; no human approval."""
from pathlib import Path
from html_agent_execution import ExecutionError
from pipeline_lifecycle import project_artifact_lock, write_json_atomic


def save_repair(store, run, project_id, slide, job_id, final):
    from database import Project
    from html_external_handoff import save_result
    from invalidation_service import html_scene_changed
    from account_context import get_current_account_id
    preview = final["preview"]
    receipt_path = Path(run) / "planning/html_visual/pi-commits" / f"{job_id}.json"
    with project_artifact_lock(run), store.factory() as db:
        project = db.get(Project, project_id)
        metadata = store.read(project_id, slide, job_id, private=True)["payload"]["model"]
        if (project is None or project.account_id != metadata.get("account_id", get_current_account_id())
                or Path(project.run_dir).resolve() != Path(run).resolve() or project.visual_backend != "html"):
            raise ExecutionError("stale_input", "项目身份、目录或后端已变化，未保存")
        store.begin_commit(project_id, slide, job_id)
        write_json_atomic(receipt_path, {"state": "intent", "job_id": job_id,
            "result_hash": preview["result_hash"], "candidate_key": preview["candidate_key"]})
        try:
            saved = save_result(run, project_id, slide, {"result": preview["result"],
                "candidate_key": preview["candidate_key"], "result_hash": preview["result_hash"]})
            if saved["changed"]:
                html_scene_changed(project, [slide], rebuild_plan=saved.get("rebuild_plan"))
            db.commit()
            write_json_atomic(receipt_path, {"state": "committed", "job_id": job_id,
                "revision": saved["revision"], "result_hash": preview["result_hash"]})
        except Exception as error:
            db.rollback()
            raise ExecutionError("save_outcome_unknown", "保存阶段失败，请核对作者版本及保存回执；未自动重放") from error
        return {**final, "saved": True, "saved_revision": saved["revision"], "author_result": saved}
