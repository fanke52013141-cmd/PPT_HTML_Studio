"""Persistent image-only PPTX export jobs and artifact lifecycle."""

from __future__ import annotations

from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import threading
import uuid
from typing import Any, Callable

from sqlalchemy.orm import Session

from artifact_fingerprint import presentation_input_fingerprint
from project_impact_service import snapshot_impacts
from database import ArtifactRecord, LocalJob, Project
from account_context import get_current_account_id, reset_current_account_id, set_current_account_id
import invalidation_service
from pptx_export import (
    PPTX_MIME_TYPE,
    PptxReadinessError,
    build_image_only_pptx,
    inspect_pptx_readiness,
)
from pptx_reveal_export import (
    PptxRevealExportError,
    build_reveal_pptx,
    inspect_reveal_pptx_readiness,
)
from project_storage import (
    UnsafeProjectPath,
    presentation_file,
    presentation_sidecar,
    project_run_dir,
)
from visual_settings_service import sync_project_background_color


logger = logging.getLogger("PPTStudio.PPTX")


class PptxServiceError(RuntimeError):
    def __init__(self, status_code: int, detail: Any) -> None:
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class PptxServiceDependencies:
    session_factory: Callable[[], Session]
    runs_root: Path
    executor: Executor | None = None
    # Repository root for the html snapshot pipeline; defaults to the runs
    # parent so legacy constructors keep working.
    repo_root: Path | None = None


class PptxExportService:
    def __init__(self, dependencies: PptxServiceDependencies) -> None:
        self.dependencies = dependencies
        self.executor = dependencies.executor or ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="pptx-export",
        )
        self._create_lock = threading.Lock()

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return value.isoformat(timespec="seconds") if value else None

    def project_run_dir(self, project: Project) -> str:
        try:
            return str(
                project_run_dir(
                    self.dependencies.runs_root,
                    project.run_dir,
                    project.id,
                )
            )
        except UnsafeProjectPath as exc:
            logger.error(
                "Unsafe project run directory for %s: %s",
                project.id,
                exc,
            )
            raise PptxServiceError(
                500,
                "项目运行目录安全校验失败",
            ) from exc

    def get_project(self, db: Session, project_id: str) -> Project:
        """按 id + 当前账号读取项目(R5-001):路由面禁止跨创作用户访问。"""
        project = (
            db.query(Project)
            .filter(
                Project.id == project_id,
                Project.account_id == get_current_account_id(),
            )
            .first()
        )
        if not project:
            raise PptxServiceError(404, "项目不存在")
        return project

    def job_item(
        self,
        job: LocalJob,
        *,
        queue_ahead: int | None = None,
    ) -> dict[str, Any]:
        return {
            "id": job.id,
            "project_id": job.project_id,
            "job_type": job.job_type,
            "status": job.status,
            "progress": int(job.progress or 0),
            "stage": job.stage,
            "error": job.error,
            "result_artifact_id": job.result_artifact_id,
            "created_at": self._iso(job.created_at),
            "started_at": self._iso(job.started_at),
            "finished_at": self._iso(job.finished_at),
            "updated_at": self._iso(job.updated_at),
            "queue_ahead": (
                queue_ahead if job.status == "queued" else None
            ),
        }

    @staticmethod
    def _queued_ahead(db: Session, job: LocalJob) -> int | None:
        """Advisory cross-project queue position for one queued export.

        Counts earlier queued jobs of the same type; zero means the job is
        next in line.  Uses the caller's session, so it must only run while
        that session is open.
        """
        if job.status != "queued":
            return None
        return (
            db.query(LocalJob)
            .filter(
                LocalJob.job_type == job.job_type,
                LocalJob.status == "queued",
                LocalJob.created_at < job.created_at,
            )
            .count()
        )

    def artifact_item(
        self,
        project: Project,
        artifact: ArtifactRecord,
        *,
        current_fingerprint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run_dir = self.project_run_dir(project)
        metadata = artifact.get_metadata()
        stored_fingerprint = artifact.get_source_fingerprint()
        try:
            path = presentation_file(run_dir, artifact.filename)
        except UnsafeProjectPath:
            path = Path(run_dir) / "__invalid__"
        exists = path.is_file()
        current_fingerprint = (
            current_fingerprint
            or presentation_input_fingerprint(run_dir)
        )
        state = "missing"
        if exists:
            state = (
                "current"
                if stored_fingerprint.get("digest")
                == current_fingerprint.get("digest")
                else "stale"
            )
        return {
            "id": artifact.id,
            "artifact_type": artifact.artifact_type,
            "filename": artifact.filename,
            "size_bytes": (
                path.stat().st_size
                if exists
                else int(artifact.size_bytes or 0)
            ),
            "mime_type": artifact.mime_type,
            "created_at": self._iso(artifact.created_at),
            "slide_count": int(metadata.get("slide_count") or 0),
            "content_mode": (
                metadata.get("content_mode")
                or "full_slide_bitmap"
            ),
            "artifact_state": state,
            "is_current": state == "current",
            "is_stale": state == "stale",
            "exists": exists,
            "download_url": (
                f"/api/projects/{project.id}/exports/"
                f"{artifact.id}/download"
            ),
        }

    def readiness(
        self,
        db: Session,
        project_id: str,
    ) -> dict[str, Any]:
        project = self.get_project(db, project_id)
        mode, payload = self._project_export_readiness(project)
        return {"success": True, "export_mode": mode, **payload}

    def _project_export_readiness(self, project: Project):
        if (getattr(project, "visual_backend", "image") or "image") == "html":
            from html_input_manifest import html_readiness
            from visual_contract_service import read_contract_slide_ids
            run = self.project_run_dir(project)
            root = self.dependencies.repo_root or Path(__file__).resolve().parent
            return "html_snapshot", html_readiness(run, root, read_contract_slide_ids(run))
        return self._resolve_export_mode(self.project_run_dir(project))

    def _prepared_export_job(self, project: Project, mode: str) -> LocalJob:
        """首发与重试共用的任务构造(R2-001)。

        账号归属取自已验证归属的项目,输入指纹与影响快照按提交时刻的当前
        状态重新生成——重试绝不沿用失败任务的旧输入摘要。
        """
        return self._new_job(
            project.id,
            mode=mode,
            account_id=getattr(project, "account_id", None) or get_current_account_id(),
            input_digest=presentation_input_fingerprint(self.project_run_dir(project))["digest"],
            impact_snapshot=snapshot_impacts(self.project_run_dir(project), affected=("output",)),
        )

    def create_export(
        self,
        db: Session,
        project_id: str,
    ) -> dict[str, Any]:
        project = self.get_project(db, project_id)
        mode, readiness = self._project_export_readiness(project)
        if not readiness["ready"]:
            raise PptxServiceError(
                409,
                {
                    "message": "当前项目还不能生成 PPTX。",
                    "issues": readiness["issues"],
                },
            )
        with self._create_lock:
            active = self._active_job(db, project.id)
            if active:
                return {
                    "success": True,
                    "reused": True,
                    "job": self.job_item(
                        active,
                        queue_ahead=self._queued_ahead(db, active),
                    ),
                }
            job = self._prepared_export_job(project, mode)
            db.add(job)
            db.commit()
            db.refresh(job)
        self.submit(job.id)
        return {
            "success": True,
            "reused": False,
            "job": self.job_item(
                job,
                queue_ahead=self._queued_ahead(db, job),
            ),
        }

    def list_jobs(
        self,
        db: Session,
        project_id: str,
        *,
        job_type: str | None = None,
    ) -> dict[str, Any]:
        self.get_project(db, project_id)
        query = db.query(LocalJob).filter(
            LocalJob.project_id == project_id
        )
        if job_type:
            query = query.filter(LocalJob.job_type == job_type)
        jobs = (
            query.order_by(LocalJob.created_at.desc())
            .limit(50)
            .all()
        )
        return {
            "success": True,
            "jobs": [self.job_item(job) for job in jobs],
        }

    def get_job(
        self,
        db: Session,
        project_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        self.get_project(db, project_id)
        job = (
            db.query(LocalJob)
            .filter(
                LocalJob.id == job_id,
                LocalJob.project_id == project_id,
            )
            .first()
        )
        if not job:
            raise PptxServiceError(404, "任务不存在")
        return {"success": True, "job": self.job_item(job)}

    def retry_job(
        self,
        db: Session,
        project_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        project = self.get_project(db, project_id)
        previous = (
            db.query(LocalJob)
            .filter(
                LocalJob.id == job_id,
                LocalJob.project_id == project_id,
                LocalJob.job_type == "pptx_export",
            )
            .first()
        )
        if not previous:
            raise PptxServiceError(404, "任务不存在")
        if previous.status not in {"failed", "interrupted"}:
            raise PptxServiceError(
                409,
                "只有失败或中断的任务可以重试",
            )
        _, readiness = self._project_export_readiness(project)
        if not readiness["ready"]:
            raise PptxServiceError(
                409,
                {
                    "message": "当前项目还不能重新导出。",
                    "issues": readiness["issues"],
                },
            )
        with self._create_lock:
            active = self._active_job(db, project_id)
            if active:
                return {
                    "success": True,
                    "reused": True,
                    "job": self.job_item(
                        active,
                        queue_ahead=self._queued_ahead(db, active),
                    ),
                }
            mode, _ = self._project_export_readiness(project)
            job = self._prepared_export_job(project, mode)
            db.add(job)
            db.commit()
            db.refresh(job)
        self.submit(job.id)
        return {
            "success": True,
            "reused": False,
            "job": self.job_item(
                job,
                queue_ahead=self._queued_ahead(db, job),
            ),
        }

    def list_exports(
        self,
        db: Session,
        project_id: str,
    ) -> dict[str, Any]:
        project = self.get_project(db, project_id)
        artifacts = self._artifacts(db, project_id)
        fingerprint = presentation_input_fingerprint(
            self.project_run_dir(project)
        )
        return {
            "success": True,
            "artifacts": [
                self.artifact_item(
                    project,
                    artifact,
                    current_fingerprint=fingerprint,
                )
                for artifact in artifacts
            ],
        }

    def download_export(
        self,
        db: Session,
        project_id: str,
        artifact_id: str,
    ) -> tuple[Path, ArtifactRecord]:
        project = self.get_project(db, project_id)
        artifact = self._artifact_or_404(
            db,
            project_id,
            artifact_id,
        )
        try:
            path = presentation_file(
                self.project_run_dir(project),
                artifact.filename,
            )
        except UnsafeProjectPath as exc:
            raise PptxServiceError(
                400,
                "PPTX 文件名无效",
            ) from exc
        if not path.is_file():
            raise PptxServiceError(404, "PPTX 文件已不存在")
        return path, artifact

    def delete_export(
        self,
        db: Session,
        project_id: str,
        artifact_id: str,
    ) -> dict[str, Any]:
        project = self.get_project(db, project_id)
        artifact = self._artifact_or_404(
            db,
            project_id,
            artifact_id,
        )
        try:
            path = presentation_file(
                self.project_run_dir(project),
                artifact.filename,
            )
        except UnsafeProjectPath as exc:
            raise PptxServiceError(
                400,
                "PPTX 文件名无效",
            ) from exc
        sidecar = presentation_sidecar(path)
        for target in (path, sidecar):
            if target.exists():
                target.unlink()
        db.delete(artifact)
        db.commit()
        remaining = self._artifacts(db, project_id)
        fingerprint = presentation_input_fingerprint(
            self.project_run_dir(project)
        )
        return {
            "success": True,
            "artifacts": [
                self.artifact_item(
                    project,
                    item,
                    current_fingerprint=fingerprint,
                )
                for item in remaining
            ],
        }

    def _export_html_snapshots(self, db: Session, project: Project, filename: str | None = None) -> dict[str, Any]:
        """HTML 后端：渲染各页终态并输出一张图片式 PPTX（E03 分派路径）。

        快照为同步小任务：页数 = 已存场景数；产物登记进 artifact 记录，
        失败保留旧产物并给出对象级原因。"""
        import uuid
        from datetime import datetime

        from html_pptx_snapshot import (
            HtmlSnapshotDependencies,
            build_snapshot_pptx,
            render_snapshots,
            snapshot_plan_for_scene,
        )
        from html_visual_store import load_scene_with_revision
        from project_path_service import (
            project_run_dir_or_500,
            read_current_slide_ids_or_404,
        )

        run_dir = project_run_dir_or_500(project)
        slide_ids = read_current_slide_ids_or_404(project)
        deps = HtmlSnapshotDependencies(
            run_dir=Path(run_dir),
            repo_root=(
                getattr(self.dependencies, "repo_root", None)
                or self.dependencies.runs_root.parent
            )
        )
        out_dir = Path(run_dir) / "presentations"
        out_dir.mkdir(parents=True, exist_ok=True)
        pages: list[dict[str, Any]] = []
        images = []
        for index, slide_id in enumerate(slide_ids, start=1):
            document = load_scene_with_revision(run_dir, slide_id)
            if document is None:
                raise PptxServiceError(
                    409, f"页面 {slide_id} 尚未保存 HTML 场景，无法导出快照"
                )
            scene = {**document["scene"], "beats": []}
            plan = snapshot_plan_for_scene(scene)
            slide_dir = out_dir / f"{index:03d}-{slide_id}"
            slide_images = render_snapshots(
                scene, [page["timeMs"] for page in plan],
                slide_dir, deps=deps,
            )
            for page, image in zip(plan, slide_images):
                pages.append({
                    "slide_id": slide_id,
                    "timeMs": page["timeMs"],
                    "label": f"{slide_id}:{page['label']}",
                })
                images.append(image)
        filename = filename or (
            "pptx_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + f"_{uuid.uuid4().hex[:6]}.pptx"
        )
        out_path = out_dir / filename
        manifest = build_snapshot_pptx(pages, images, out_path)
        from pipeline_lifecycle import write_json_atomic
        fingerprint = presentation_input_fingerprint(run_dir)
        metadata = {"content_mode":"html_snapshot", "slide_count":len(pages),
                    "snapshot_manifest":manifest,"source_fingerprint":fingerprint}
        write_json_atomic(presentation_sidecar(out_path),metadata)
        out_path.with_suffix(".pptx.manifest.json").unlink(missing_ok=True)
        return {
            "path": str(out_path), "filename": filename,
            "size_bytes": out_path.stat().st_size,
            "fingerprint": fingerprint,
            "metadata": metadata,
        }

    def submit(self, job_id: str) -> None:
        self.executor.submit(self.run_job, job_id)

    def recover_jobs(self) -> None:
        db = self.dependencies.session_factory()
        queued_ids: list[str] = []
        try:
            running = (
                db.query(LocalJob)
                .filter(
                    LocalJob.job_type == "pptx_export",
                    LocalJob.status == "running",
                )
                .all()
            )
            now = datetime.now()
            for job in running:
                job.status = "interrupted"
                job.stage = "interrupted"
                job.error = (
                    "应用上次运行时退出，任务已中断；可以重新导出。"
                )
                job.finished_at = now
                job.updated_at = now
            queued_ids = [
                job.id
                for job in (
                    db.query(LocalJob)
                    .filter(
                        LocalJob.job_type == "pptx_export",
                        LocalJob.status == "queued",
                    )
                    .all()
                )
            ]
            db.commit()
        finally:
            db.close()
        for job_id in queued_ids:
            self.submit(job_id)

    def run_job(self, job_id: str) -> None:
        account_context_token = None
        db = self.dependencies.session_factory()
        output_path: Path | None = None
        try:
            job = (
                db.query(LocalJob)
                .filter(LocalJob.id == job_id)
                .first()
            )
            if not job:
                return
            payload = job.get_payload() or {}
            payload_account = str(payload.get("account_id") or "").strip()
            if payload_account:
                account_context_token = set_current_account_id(payload_account)
                project = (
                    db.query(Project)
                    .filter(
                        Project.id == job.project_id,
                        Project.account_id == payload_account,
                    )
                    .first()
                )
            else:
                # 历史 payload 缺账号字段:按项目行归属固化,不无条件 default
                project = (
                    db.query(Project)
                    .filter(Project.id == job.project_id)
                    .first()
                )
                if project is not None:
                    account_context_token = set_current_account_id(
                        str(project.account_id or "default")
                    )
            if not project:
                raise RuntimeError(
                    "项目不存在，无法继续导出"
                )
            job.status = "running"
            job.stage = "validating"
            job.progress = 5
            job.started_at = datetime.now()
            job.updated_at = datetime.now()
            db.commit()

            payload = job.get_payload() or {}
            filename = str(payload.get("filename") or "")
            queued_digest = str(payload.get("input_digest") or "")
            if queued_digest and presentation_input_fingerprint(self.project_run_dir(project))["digest"] != queued_digest:
                raise RuntimeError("导出排队期间输入已变化，请重新提交 PPTX 导出")
            mode = str(payload.get("mode") or "") or self._resolve_export_mode(
                self.project_run_dir(project)
            )[0]
            if mode == "html_snapshot":
                ready = self._project_export_readiness(project)[1]
                if not ready["ready"]:
                    raise RuntimeError("HTML 快照输入或批准已失效")
                result = self._export_html_snapshots(db, project, filename)
            elif mode == "reveal":
                try:
                    sync_project_background_color(project)
                except RuntimeError:
                    logger.info(
                        "PPTX background sync skipped:"
                        " visual settings service not configured"
                    )
                result = build_reveal_pptx(
                    self.project_run_dir(project),
                    filename,
                    title=project.name,
                    progress=lambda value, stage: self.set_job_progress(
                        job_id,
                        value,
                        stage,
                    ),
                )
            else:
                result = build_image_only_pptx(
                    self.project_run_dir(project),
                    filename,
                    title=project.name,
                    progress=lambda value, stage: self.set_job_progress(
                        job_id,
                        value,
                        stage,
                    ),
                )
            output_path = Path(result["path"])
            if queued_digest and presentation_input_fingerprint(self.project_run_dir(project))["digest"] != queued_digest:
                raise RuntimeError("PPTX 生成期间输入已变化，请重新提交导出")
            artifact = ArtifactRecord(
                id=uuid.uuid4().hex,
                project_id=project.id,
                artifact_type="pptx",
                filename=result["filename"],
                relative_path=(
                    f"presentations/{result['filename']}"
                ),
                mime_type=PPTX_MIME_TYPE,
                size_bytes=result["size_bytes"],
                source_fingerprint=json.dumps(
                    result["fingerprint"],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                metadata_json=json.dumps(
                    result["metadata"],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            )
            db.add(artifact)
            invalidation_service.complete_stage(project, 8)
            job = (
                db.query(LocalJob)
                .filter(LocalJob.id == job_id)
                .first()
            )
            if not job:
                raise RuntimeError("PPTX 导出任务记录不存在")
            job.status = "succeeded"
            job.stage = "completed"
            job.progress = 100
            job.error = None
            job.result_artifact_id = artifact.id
            job.finished_at = datetime.now()
            job.updated_at = datetime.now()
            db.commit()
        except PptxReadinessError as exc:
            self.fail_job(
                db,
                job_id,
                "导出条件已变化，请刷新页面后重新检查。",
            )
            logger.info(
                "PPTX readiness changed for job %s: %s",
                job_id,
                exc.readiness,
            )
        except PptxRevealExportError as exc:
            self.fail_job(
                db,
                job_id,
                f"带 Mask 流程的导出未就绪：{exc.detail}",
            )
            logger.info(
                "PPTX reveal readiness changed for job %s: %s",
                job_id,
                exc.detail,
            )
        except Exception as exc:
            self._remove_partial_output(output_path)
            logger.exception("PPTX export failed for job %s", job_id)
            self.fail_job_after_poisoned_session(db, job_id, str(exc))
        finally:
            db.close()
            if account_context_token is not None:
                reset_current_account_id(account_context_token)

    def set_job_progress(
        self,
        job_id: str,
        progress: int,
        stage: str,
    ) -> None:
        db = self.dependencies.session_factory()
        try:
            job = (
                db.query(LocalJob)
                .filter(LocalJob.id == job_id)
                .first()
            )
            if not job or job.status not in {"queued", "running"}:
                return
            job.status = "running"
            job.progress = max(0, min(100, int(progress)))
            job.stage = str(stage or "running")
            job.updated_at = datetime.now()
            db.commit()
        finally:
            db.close()

    def fail_job_after_poisoned_session(
        self,
        db: Session,
        job_id: str,
        message: str,
    ) -> None:
        """失败终态写入的兜底路径：主会话可能已处于 pending-rollback。

        历史缺陷：run_job 的最终提交遇到 DB 级异常后，except 路径直接在
        同一会话上 fail_job —— query 立即抛 PendingRollbackError，失败终态
        写不进去，任务停留 running 直到重启（对照：tts 失败路径先 rollback，
        video 用独立短会话写终态）。
        """
        try:
            db.rollback()
        except Exception:
            logger.exception(
                "PPTX rollback before fail_job failed for job %s", job_id
            )
            fresh = self.dependencies.session_factory()
            try:
                self.fail_job(fresh, job_id, message)
            except Exception:
                logger.exception(
                    "PPTX fresh-session fail_job failed for job %s", job_id
                )
            finally:
                fresh.close()
            return
        self.fail_job(db, job_id, message)

    @staticmethod
    def fail_job(
        db: Session,
        job_id: str,
        message: str,
    ) -> None:
        job = (
            db.query(LocalJob)
            .filter(LocalJob.id == job_id)
            .first()
        )
        if not job:
            return
        job.status = "failed"
        job.stage = "failed"
        job.error = str(message or "PPTX 导出失败")[:4000]
        job.finished_at = datetime.now()
        job.updated_at = datetime.now()
        db.commit()

    @staticmethod
    def _remove_partial_output(output_path: Path | None) -> None:
        if not output_path or not output_path.exists():
            return
        try:
            output_path.unlink()
        except OSError:
            pass
        sidecar = presentation_sidecar(output_path)
        if sidecar.exists():
            try:
                sidecar.unlink()
            except OSError:
                pass

    @staticmethod
    def _resolve_export_mode(
        run_dir: str | Path,
    ) -> tuple[str, dict[str, Any]]:
        """自动选择导出模式：有有效 Mask 标注时用 reveal（带流程拆页），否则回退 image_only。

        返回 (mode, readiness_payload)。
        """
        try:
            reveal = inspect_reveal_pptx_readiness(run_dir)
        except Exception:
            reveal = None
        if reveal and reveal.get("ready"):
            return "reveal", reveal
        base = inspect_pptx_readiness(run_dir)
        return "image_only", base

    @staticmethod
    def _new_job(
        project_id: str,
        mode: str = "image_only",
        account_id: str = "default",
        input_digest: str = "",
        impact_snapshot: list[dict[str, Any]] | None = None,
    ) -> LocalJob:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = (
            f"presentation_{timestamp}_{uuid.uuid4().hex[:6]}.pptx"
        )
        return LocalJob(
            id=uuid.uuid4().hex,
            project_id=project_id,
            job_type="pptx_export",
            status="queued",
            progress=0,
            stage="queued",
            payload_json=json.dumps(
                {"filename": filename, "mode": mode, "account_id": account_id,
                 "input_digest": input_digest, "impact_snapshot": impact_snapshot or []},
                ensure_ascii=False,
            ),
        )

    @staticmethod
    def _active_job(
        db: Session,
        project_id: str,
    ) -> LocalJob | None:
        return (
            db.query(LocalJob)
            .filter(
                LocalJob.project_id == project_id,
                LocalJob.job_type == "pptx_export",
                LocalJob.status.in_(("queued", "running")),
            )
            .order_by(LocalJob.created_at.desc())
            .first()
        )

    @staticmethod
    def _artifacts(
        db: Session,
        project_id: str,
    ) -> list[ArtifactRecord]:
        return (
            db.query(ArtifactRecord)
            .filter(
                ArtifactRecord.project_id == project_id,
                ArtifactRecord.artifact_type == "pptx",
            )
            .order_by(ArtifactRecord.created_at.desc())
            .all()
        )

    @staticmethod
    def _artifact_or_404(
        db: Session,
        project_id: str,
        artifact_id: str,
    ) -> ArtifactRecord:
        artifact = (
            db.query(ArtifactRecord)
            .filter(
                ArtifactRecord.id == artifact_id,
                ArtifactRecord.project_id == project_id,
                ArtifactRecord.artifact_type == "pptx",
            )
            .first()
        )
        if not artifact:
            raise PptxServiceError(404, "PPTX 产物不存在")
        return artifact


_SERVICE_LOCK = threading.Lock()
_SERVICE: PptxExportService | None = None


def configure_pptx_export_service(
    dependencies: PptxServiceDependencies,
    *,
    recover_jobs: bool = True,
) -> PptxExportService:
    global _SERVICE
    service = PptxExportService(dependencies)
    with _SERVICE_LOCK:
        _SERVICE = service
    if recover_jobs:
        service.recover_jobs()
    return service


def get_pptx_export_service() -> PptxExportService:
    if _SERVICE is None:
        raise RuntimeError("PPTX export service has not been configured")
    return _SERVICE
