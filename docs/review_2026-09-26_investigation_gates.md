# 2026-09-26 审查第四阶段：调查关口结论

对应四阶段优化流程的第四阶段。每项审查发现先取得可复现证据（最小测试或
调用链记录），再决定是否进入修复队列。复现证据以可执行测试固化在
`checks/test_investigation_gates_phase4.py`：

- **已修复**的项：随本文件提交转绿，作为长期回归保留。
- **修复队列**的项：以 `xfail(strict=True)` 固化——任何人修复（或行为意外
  改变）时该测试都会显式失败，强迫更新本文件结论。
- **关闭**的项：写明既有保护机制与残余风险。

---

## 调查项 1：Step 2 并发覆盖与下游失效 —— 调用链记录，进入修复队列

**证据（静态调用链，确定性）**：

- `storyboard_service.py:1256-1270` `update_step2_result`：读旧契约 → 比对 →
  `write_json_atomic` 整包覆写，全程无 `project_artifact_lock`（grep 0 命中）。
- `storyboard_service.py:752-765` / `:863-871`：2A/2B 计划文件覆写同样无锁，
  且不触发 `invalidate_after_upstream_edit`。
- 对照组：同仓库 Manifest 写者（`mask_manifest_service.py:400-446`、
  `storyboard_background.py:176-196`）全部持 `project_artifact_lock(run_dir)`。

**可复现后果**：双开标签页同时自动保存（Step 2 前端 700ms debounce 高频触发）
时，后写者基于过期快照整包覆盖，静默丢编辑；`shutil.rmtree`（:1273-1276）
与 Step 3 生成并发时可删除正在使用的 slide 目录。

**修复方向**：Step 2 契约/计划写路径统一包 `project_artifact_lock(project.run_dir)`
（同键 RLock，无死锁风险）；如需更强的多标签页保障再加版本冲突检测（409）。
未直接修复原因：锁的粒度选择（run_dir 级 vs 契约文件级）与前端提交协议
（是否返回冲突码）需要一起设计，避免掩盖问题。

## 调查项 2：一键续跑策略缺 ai_mask 阶段 —— ✅ 已复现并修复

复现测试 `test_resume_plan_honors_ai_mask_stage`（修复前断言
`effective_start_stage == "preflight"`，失败）。

**修复**：`one_click_resume_policy.STAGE_IDS` 补 `"ai_mask"`（位于
`confirm_images` 与 `narration` 之间，与 `one_click_orchestrator.STAGES`
顺序一致）；`VALIDATORS` 补 `_validate_ai_mask`（reveal manifest 页集合
匹配 + `ai_mask_annotation.status ∈ {completed, completed_needs_review}`）；
`STAGE_INTERNAL_STEP` 补 `"ai_mask": 5`（`_project_state_reasons` 消费）。
AI Mask 质量门暂停后点"继续"现在从 ai_mask 阶段恢复，不再全量重跑。

降级语义回归 `test_resume_plan_still_degrades_on_invalidated_earlier_stage`
确认前置阶段失效时仍按既有规则一路降级。

## 调查项 3：PPTX 失败任务卡 running —— ✅ 已复现并修复

复现测试 `test_pptx_fail_path_recovers_from_poisoned_session`：真实 SQLite
会话注入重复主键提交 → pending-rollback；现状 `fail_job(db)` 的 query 立即
抛 `PendingRollbackError`（测试内 `pytest.raises` 证明了机制），任务停留
running 直到重启。

**修复**：`pptx_service.run_job` 的 except 路径改走新增的
`fail_job_after_poisoned_session`：先 `db.rollback()` 复位会话再写失败终态；
回滚本身失败时改用独立短会话（与 video 终态写法对齐）。

**残余风险**：若 DB 连接本身不可用（rollback 与新会话都失败），终态仍写不进
去——该场景与"数据库宕机"同级，由启动期 interrupted 恢复兜底，已接受。

## 调查项 4：渲染旧快照覆盖项目状态 —— 调用链记录，进入修复队列

**证据（调用链）**：`video_render_service.py:616-620` 渲染开始时加载 project
（此后只读事务释放，渲染全程可达小时级）；`:701-702` 渲染结束时用该 ORM
快照执行 `complete_stage(project, 8)` 并 commit——期间用户改旁白/字幕等
HTTP 提交的新 `step_status` 被旧快照整体回写覆盖（例如刚触发的"音频确认
已清"状态被抹掉）。`pptx_service.py:504-511 → :580,:595` 同构。

**确定性并发测试未落成原因**：需要真实双线程 + 可控渲染时长 + DB 状态
断言的完整夹具；修复本身很小（终态回写前在新鲜会话重读 project）。
建议随下一批 pptx/video 终态写法统一（独立短会话模式推广）一并处理。

## 调查项 5：TTS 配额预留超桶容量 —— ✅ 确定性复现，进入修复队列

复现测试 `test_tts_reservation_fits_token_bucket_at_low_rpm`
（`xfail(strict=True)`，当前以断言失败固化证据：rpm=4 时
`tts_async_reservation` 返回 cost+polls=5 > 容量 4）。

机制：令牌桶容量被钉在 rpm，`_acquire` 要求 `tokens >= safe_cost`
（`generation_governor.py:350`），桶上限 rpm < safe_cost 时等待时间永远算
不完 → 每页白等 `max_wait_sec`（默认 600s）再 `GovernorTimeout` 暂停，
确定性复现。UI 允许 `tts_gateway_requests_per_minute` 设到 1-4。

**修复方向（二选一，需拍板）**：① 预留时把 `cost + polls` 钳制到
`requests_per_minute` 以内（最小改动，语义是"欠额运行、网关侧自担"）；
② 轮询令牌改为分阶段小额预留（语义准确，改动面大）。未直接修复原因：
两方案对"预留不足时网关真实请求超出预留"的语义取舍是产品决策。

## 调查项 6：生图超大结果与参数探测 —— ✅ 复现，进入修复队列

复现测试 `test_oversized_generation_is_not_retried_as_corrupt`
（`xfail(strict=True)`，当前证据：`classify_image_error(ImagePayloadTooLarge(...))`
→ `corrupt_image / retryable=True`）。

机制：`ai_provider_service.py:266-273` 对生成字节执行 20MB 上限检查抛
`ImagePayloadTooLarge(ValueError)`；`image_generation_errors.py:387-403`
把无 empty 标记的 ValueError 归为可重试的 corrupt_image → 用户配置 4K
分辨率时确定性失败却重试 3 次烧付费配额。参数探测重放问题
（`ai_provider_service.py:921-950` 无 (model, base_url) 参数形状缓存，严格
网关下每页固定多扣 1 次）同队列，修复方向：按异常类型归类
`invalid_parameters`（不可重试）+ 进程内缓存首次成功的参数形状。

## 调查项 7：其他非原子文件写 —— 调用链记录，进入修复队列

**残留清单与读取入口后果**（写入中断 → 截断文件被消费）：

| 写者 | 位置 | 读取入口与后果 |
| --- | --- | --- |
| `scene.json` | `storyboard_background_render.py:35-36,115` | 渲染输入 + `artifact_fingerprint.py:72-93` 指纹组件：截断→渲染失败+指纹漂移 |
| Step 3 样式清单 | `step3_image_style_service.py:42-45` | 样式选择读取：截断→样式丢设置 |
| 项目风格参考清单 | `project_style_reference_store.py:30-32` | 参考图列表：截断→参考图丢失 |
| 风格反推清单 | `image_style_reverse_service.py:132-134` | 同上 |
| `tts_text.txt` / `subtitles.srt` | `narration_audio_service.py:355-371`（`_write_text_if_changed`） | 指纹输入：截断→无谓重渲染（mtime 保持设计本身合理） |
| TTS 子进程 `audio_timeline.json` | `scripts/minimax_tts.py:672-674,853-854`、`scripts/generic_tts.py:134-138` | `tts_service.py:752-756` 缓存命中路径裸 `json.load` → 合成/确认卡死（与审查 M-21 同族） |

**修复方向**：`pipeline_lifecycle` 增加 `write_text_atomic`（复用既有
临时文件 + `os.replace` + fsync + 锁）替换文本写者；JSON 写者统一收敛到
`write_json_atomic`；TTS 子进程时间轴落盘改原子写，并让
`rewrite_audio_timeline_by_beats` 对坏 JSON 返回类型化错误。未直接修复
原因：涉及 6 个模块 + 1 个子进程协议，属于同一主题的批量迁移，宜作为
独立变更组一次完成并配全量回归。

---

## 与已修复缺陷的关系

第一阶段与第二阶段的 6 项（AI Mask NameError、旁白跨项目污染、ComfyUI
客户端、`write_json_atomic` 直写兜底、AI Mask 设置局部更新、视频任务内存
状态）在调查前已有明确源码证据，按实施原则不等待本阶段，已各自成组提交。
