"""2026-09-26 审查第四阶段"调查关口"的最小复现集合。

每一项对应一个审查发现：能确定性复现的进入修复队列（随本文件落成回归，
修复后转绿）；暂不修复的以 ``xfail(strict=True)`` 固化证据——行为一旦
改变（修复或回归）测试都会显式失败，强迫更新结论。
结论与调用链记录见 docs/review_2026-09-26_investigation_gates.md。
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# 调查项 2：一键续跑策略缺 ai_mask 阶段（可复现 → 已入修复队列并修复）
#
# 复现：orchestrator STAGES 含 ("ai_mask", "AI Mask 标注")，失败时
# current_stage="ai_mask"；而 one_click_resume_policy.STAGE_IDS 无 ai_mask，
# build_resume_plan 把它强制回退 "preflight" → 断点续跑从零重跑。
# ---------------------------------------------------------------------------

def test_resume_plan_honors_ai_mask_stage(tmp_path: Path, monkeypatch) -> None:
    import one_click_resume_policy as policy

    for stage in ("preflight", "storyboard", "images", "confirm_images", "ai_mask"):
        monkeypatch.setitem(policy.VALIDATORS, stage, lambda _project: [])
    project = SimpleNamespace(run_dir=str(tmp_path), get_step_status=lambda: {})

    plan = policy.build_resume_plan(project, "ai_mask")

    assert plan["previous_failed_stage"] == "ai_mask"
    assert plan["effective_start_stage"] == "ai_mask"
    assert [entry["stage"] for entry in plan["revalidation"]] == [
        "preflight",
        "storyboard",
        "images",
        "confirm_images",
        "ai_mask",
    ]


def test_resume_plan_still_degrades_on_invalidated_earlier_stage(tmp_path: Path) -> None:
    """ai_mask 入表后，前置阶段校验失败时仍须按既有规则继续降级。"""
    from one_click_resume_policy import build_resume_plan

    project = SimpleNamespace(run_dir=str(tmp_path), get_step_status=lambda: {})
    plan = build_resume_plan(project, "ai_mask")

    assert plan["previous_failed_stage"] == "ai_mask"
    # 空目录连文章都没有：一路降级到 preflight（既有降级语义保持不变）
    assert plan["effective_start_stage"] == "preflight"
    assert plan["revalidation"][-1]["stage"] == "ai_mask"


# ---------------------------------------------------------------------------
# 调查项 3：PPTX 失败路径复用脏会话，任务永久 running（可复现 → 已入修复队列并修复）
#
# 复现：run_job 主会话在最终提交处遇到 DB 级异常后进入 pending-rollback；
# 现状 except 路径直接 fail_job(db) —— 同一会话上的 query 立即抛
# PendingRollbackError，失败终态写不进去，任务停留 running 直到重启。
# 对照：tts_service 失败路径先 db.rollback()，video 走独立短会话。
# ---------------------------------------------------------------------------

def test_pptx_fail_path_recovers_from_poisoned_session(tmp_path: Path) -> None:
    import pytest
    from sqlalchemy.exc import IntegrityError, PendingRollbackError

    from database import LocalJob, SessionLocal
    from pptx_service import PptxExportService, PptxServiceDependencies

    service = PptxExportService(
        PptxServiceDependencies(session_factory=SessionLocal, runs_root=tmp_path)
    )
    job_id = "pptx-poisoned-job"
    db = SessionLocal()
    try:
        db.add(
            LocalJob(
                id=job_id,
                project_id="project-poisoned",
                job_type="pptx",
                status="running",
                stage="rendering",
            )
        )
        db.commit()

        # 注入一次 DB 级异常：重复主键提交使会话进入 pending-rollback。
        db.add(LocalJob(id=job_id, project_id="x", job_type="pptx"))
        try:
            db.commit()
        except IntegrityError:
            pass
        with pytest.raises(PendingRollbackError):
            db.query(LocalJob).filter(LocalJob.id == job_id).first()

        # 修复后的失败终态路径：先 rollback 复位会话再写终态。
        service.fail_job_after_poisoned_session(db, job_id, "boom")

        db.rollback()
        job = (
            db.query(LocalJob)
            .filter(LocalJob.id == job_id)
            .first()
        )
        assert job is not None
        assert job.status == "failed"
        assert job.error == "boom"
    finally:
        db.close()
        from database import engine
        cleanup = SessionLocal()
        try:
            row = cleanup.query(LocalJob).filter(LocalJob.id == job_id).first()
            if row is not None:
                cleanup.delete(row)
                cleanup.commit()
        finally:
            cleanup.close()
            engine.dispose()


# ---------------------------------------------------------------------------
# 调查项 5：TTS 预留令牌数可超令牌桶容量（确定性复现 → 修复队列，暂不修）
#
# 复现：rpm<=4（UI 允许下限 1）时 tts_async_reservation 返回 cost+polls
# 超过容量（=rpm），令牌桶 capacity=rpm 永远凑不齐 safe_cost → 每页白等
# max_wait 再 GovernorTimeout 暂停。修复方向（二选一）：预留时把
# cost+polls 钳制到 rpm 以内；或轮询令牌分段小额预留。
# ---------------------------------------------------------------------------



from generation_governor import (  # noqa: E402
    RESOURCE_TTS,
    GenerationGovernor,
    GovernorDependencies,
)


def test_tts_reservation_fits_token_bucket_at_low_rpm() -> None:
    """分段预算修复:预留可超过桶容量,但 _acquire 按"满桶放行+债务结转"推进,
    低 RPM 下队列不再确定性死局。"""
    governor = GenerationGovernor(
        GovernorDependencies(
            get_bounded_int_setting=lambda *_args, **_kwargs: 4,
            write_log=lambda *_args, **_kwargs: None,
        )
    )
    reservation, _interval = governor.tts_async_reservation(
        base_url="https://gateway.test",
        expected_duration_sec=40.0,
    )
    assert reservation == 5, "rpm=4、expected=40s 的诚实欠计量(cost+polls)"

    state = governor._state(RESOURCE_TTS, "https://gateway.test")
    # 满桶即可放行,即使预留超过容量;扣减后债务为负,跨窗口结转
    governor._acquire(state, cost=reservation, want_slot=False, timeout_sec=5.0)
    assert state.tokens < 0, "超容量预留应以债务结转,而不是等待永不可达的令牌数"
    # 债务恢复:回拨 updated_at 模拟 75 秒流逝(债务 -1 → 回到满桶 4),
    # 第二页可再次放行(队列可推进,长期吞吐 = rpm/cost 页/分钟)
    state.updated_at -= 75.0
    governor._acquire(state, cost=reservation, want_slot=False, timeout_sec=10.0)
    assert state.tokens <= 0, "恢复窗口后第二页应继续放行并结转债务" 


# ---------------------------------------------------------------------------
# 调查项 6：生图超大结果被误判 corrupt_image 反复重试（复现 → 修复队列，暂不修）
#
# 复现：open_validated_image 对生成字节执行 20MB 上限检查并抛
# ImagePayloadTooLarge(ValueError)；错误分类器把"无 empty 标记的
# ValueError"归为 corrupt_image/retryable → 确定性失败却重试 3 次烧配额。
# 修复方向：按异常类型归类 invalid_parameters（不可重试）。
# ---------------------------------------------------------------------------

def test_oversized_generation_is_not_retried_as_corrupt() -> None:
    from image_generation_errors import classify_image_error
    from ai_provider_service import ImagePayloadTooLarge

    failure = classify_image_error(
        ImagePayloadTooLarge("generated image exceeds 20MB payload limit"),
        phase="download",
    )
    assert failure.retryable is False
    assert failure.code != "corrupt_image"
