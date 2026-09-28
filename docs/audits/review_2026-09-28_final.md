# 最近四周更新代码审查 · 最终合并报告（2026-09-28/29）

适用方案：`docs/code_review_plan_2026-09-28.md`。本报告合并 R0–R5 全部结论
（R0 主线基线 + 5 个并行深审代理），是本次审查的最终放行依据。
基线记录见 `docs/audits/review_2026-09-28_R0.md`。

## 审查元数据

- 目标：`62d5052`（HEAD）；基线 `1b66bbe`；1,070 文件 / 111 提交 / +108,730 −2,734。
- 环境：Windows 10.0.26200，Python 3.13.5，Node v24.12.0；隔离 DB/runs 目录；未触碰用户数据。
- 方法：主线静态基线 + 5 个只读深审代理（R1 下游影响、R2 并发任务、R3 Mask 双图、
  R4 勾画标注、R5 账号安全）。P0 结论均经主线独立复核（AST/grep 实证）。
- 限制：R1–R5 为静态审查；真实渲染、真实供应商调用、浏览器人工走查未执行（见"未验证"）。

## 放行结论：**不放行**（存在 2 个 P0）

9/28 交付的勾画标注模块（ae6bf95，106 文件）存在两个装配级 P0 断裂，
其"AI 辅助链路"与"画布可视链路"在 HEAD 上实际不可用——尽管 1414 个测试全绿
（现有测试恰好没覆盖这两条路径）。修复 P0 后仍需处理 2 个 P1 再放行。
其余模块（分镜/图片/Mask/旁白/TTS/视频/复用失效链/账号契约/迁移）静态审查质量良好。

## P0（放行前必须修复）

### R4-001 · annotation_service.py 类边界断裂，7 条生产路由运行时 500
- 位置：`annotation_service.py:984-1297`；调用方 `annotation_routes.py:76/87/100/110/139/149/159`。
- 证据（主线运行时实证，非静态推断）：`python -c` 导入后
  `hasattr(AnnotationService, "submit_job")` 等全部为 False；
  `get_text_layout`、`patch_text_layout`、`submit_job`、`get_prompts`、`put_prompts`、
  `get_job`、`cancel_job`、`_op_restore`、`_prompt_preview`、`_prompt_store_version`、
  `_deps_job_or_404` 共 11 个方法被缩进进包装类 `_ItemWithStrokesView` 类体，
  服务实例上不存在 → AttributeError → 500。
- 后果：OCR 文字识别、AI 规划、任务提交/轮询/取消、Prompt 编辑、`op:"restore"`
  在 UI 与 API 层全部不可用。触发点：`annotation_routes.py:76/87/100/110/139/149/159`
  共 7 条路由直接调用缺失方法。
- 漏检原因：`checks/test_annotation_routes.py` 只覆盖 W1 面（无 text-layout/jobs/prompts
  调用）；`test_annotation_jobs.py` 直测 manager；compileall 对缩进级错误不报错。
- 修复：把 `_ItemWithStrokesView`（:984-992）移出类体（建议模块底部或独立模块），
  11 个方法回归 `AnnotationService`；补一条类表面完整性测试
  （如 `assert hasattr(AnnotationService, "submit_job")`）。
- 关联提交：ae6bf95。

### R4-002 · index.html 漏加载 annotation_playback.js，浏览器标注覆盖层崩溃并引发标注重复
- 位置：`static/index.html:1753-1755`（只加载 core/workspace/editor，大小写不敏感
  搜索 "playback" 零匹配）；`static/annotations_editor.js:87` 在
  `renderAnnotationOverlay()`（:48 起）内无条件调用 `AnnotationsPlayback.renderScene`
  （唯一定义点 `static/annotation_playback.js:14`，页面未加载）。
- 后果链：`renderAnnotationOverlay` 被 `annotations_workspace.js:77/213/399/649`
  及 editor 三处调用——其中 :77 位于 `flushAnnotationsSave` 成功路径内，因此
  第一次保存成功 → 渲染覆盖层即 ReferenceError → 异常落在保存 try 块内被自身
  catch 捕获 → 已成功的保存被误报失败、操作回灌 pendingOps → 下次 flush 重发
  add → **服务端再次新建 → 标注重复创建**。
- 漏检原因：`checks/test_frontend_quality.js:1103-1110` 的加载顺序断言恰好没列该文件；
  `checks/test_annotation_playback.js` 是 Node 直 require，浏览器加载链无覆盖。
- 修复：index.html 在 annotations_core 之前加 `<script src="annotation_playback.js">`；
  把该文件纳入 test_frontend_quality 顺序断言。
- 关联提交：ae6bf95。

## P1（放行前修复）

### R2-001 · PPTX 重试丢失 account_id，非 default 账号重试导出必然失败
- 位置：`pptx_service.py:344`（retry 路径 `_new_job(project_id, mode=mode)`，
  account_id 落默认值 :745）；对照创建路径 :237 正确传入。
- 后果：worker 以 payload 的 account_id 设上下文（:504-506）后按
  `Project.account_id == get_current_account_id()` 查询（:507-513）找不到项目 →
  任务 failed，报"项目不存在，无法继续导出"。
- 修复：retry 继承原 job 的 account_id。

### R5-001 · project_or_404 无账号过滤（127 处调用点），已知未修项
- 位置：`project_path_service.py:23-28`；对照 `project_service.py:612`、
  `video_render_service.py:646` 的带过滤查询。
- 定级依据（R5 代理）：`docs/code_review_2026-09-06_handoff.md:55-59` 已记为 **P0-03**
  并给出修复方向，属"已知未修"而非接受风险。信任模型下（客户端头声明身份、
  单机部署）不构成对抗性安全边界，但多创作用户已是产品一等场景，
  helper 是防误串号的最后一道闸，且修复是单点。
- 后果最重端点：① MP4/字幕下载与删除（video/subtitle_export routes）；
  ② 62d5052 新增 `PUT /impacts/reuse-storyboard` 整体覆盖写；
  ③ one-click/render/批量生图任务提交（可燃烧他人额度）；
  ④ 图片/音频/PPTX 删除路由；⑤ `GET /impacts/storyboard-reuse-preview` 跨账号读正文。
- 修复：helper 单点加 `Project.account_id == get_current_account_id()` 过滤，
  同步为 annotation_jobs 线程补 `set_current_account_id`（R2-004/R5-003）。
  若产品明确单机单用户，可降 P2 并在 AGENTS.md 记录豁免理由。

## P2（明确修复计划或记录接受理由）

| 编号 | 标题 | 位置 |
| --- | --- | --- |
| R4-003 | 保存 catch 无代次守卫 + 非法操作永不丢弃：A 页 region add 可**静默落进 B 页/其他项目**（add 不引用 id，服务端校验拦不住）；一条非法 op（如 width=0）可永久毒化 pendingOps | static/annotations_workspace.js:82-98 |
| R4-004 | 已确认条目编辑不重置 draft，旧 annotation_timeline 带旧笔迹通过导出门禁，视频渲染旧样式、预览显示新样式 | annotation_service.py:594-698；invalidation_service.py:320-330 |
| R4-005 | summary/切页/候选/轮询四条异步路径均无代次守卫；409 冲突下切页静默丢弃本地编辑 | static/annotations_workspace.js:135-145/183-203/577-588/530-556 |
| R4-006 | 409 冲突无恢复路径（currentRevision 被丢弃，重试永远 409） | static/annotations_core.js:252-260 |
| R0-001 | 标准检查门红：45 个 ruff 错误（勾画模块为主），ae6bf95 合入前未跑 run_checks | annotation_geometry.py 等；`run_checks.py` quick 起 |
| R1-002 | 重复/空 slide_id 未在 diff 前被拒绝，异常页改动静默丢失影响记录 | storyboard_contract_diff.py:45-50；visual_contract_service.py:33-35 |
| R2-004/R5-003 | annotation_jobs 线程池未固化账号上下文、payload 无归属 | annotation_jobs.py:70/107-127 |
| R5-002 | reuse-storyboard 端点复用无过滤 helper（随 R5-001 一并修复） | project_routes.py |
| R5-004 | zip 导入 config.json 主条目无大小上限（可内存 DoS） | config_portability_service.py:1215 |

## P3（记录，不阻塞）

- R1-003 diff 不比较 slides 外的顶层契约字段（storyboard_contract_diff.py:41-50）。
- R1-001 同倍率调速重复点击无限累积变体文件（video_artifact_service.py:513-517）。
- R2-006 无锁直调路径误释放他人项目锁；R2-007 全帧项目 resume 被 ai_mask 校验误判；
  R2-008 one-click 状态写入失败放弃原子性；R2-010 TTS 闸门持锁 sleep 与无淘汰字典；
  R2-011 跨线程共用 ORM 写日志；R2-012 调速变体并发竞态。
- R4-007 Remotion 未传实际 fps、矢量回退 viewBox 硬编码横屏；
  R4-008 enabled+零标注导出报错误导；R4-009 OCR 密钥仅环境变量等装配遗留；
  R4-010 occurrence 不校验、OCR 置信度不透出。
- R5-005 重复 asset 静默覆盖；R5-006 0014 迁移死条件；R5-007 legacy checksum 放宽。
- R3-001 候选应用 same_visual 未先验 marker；R3-002 is_island 闭包不可导入（防复制）。
- 历史遗留（9/26 调查七项复核）：① Step 2 并发覆写仍存在（无版本令牌无锁，
  storyboard_service.py:1296-1325）；⑦ 两处非原子写仍存在（低危，project_runtime_service.py:212、
  narration_audio_service.py:368）；两个 xfail（TTS 低 RPM 预留、超大图误判）维持已知未修。

## 已验证通过（静态审查确证）

- **检查基线**：pytest 1414 通过（8 skip/2 xfail 均合法）；compileall、全部 node 检查、
  6 项脚本检查、Remotion tsc、Agent 契约生成器全部通过。唯一红项是 ruff（R0-001）。
- **R1 复用/失效链**：复用确认端点三重绑定（source_version+文件哈希+锁内按范围 resolve）、
  渲染按起始快照结清、article_changed 只影响 storyboard 且不无依据宣布旧产物兼容、
  set_decision 不绕过门禁、音频确认五项 sha256 真实校验、三类 diff 归类正确。
- **R2 并发/任务**：锁序无环、异常路径释放完整；governor 限流键=（resource, gateway_scope）
  刻意不含 api_key，min(global, project) 语义成立；各层重试全部有界；
  GovernorTimeout→暂停映射完整；四类任务终态持久化+成功清 error+重启恢复齐备；
  幂等键覆盖实际输入；TTS staging 提升与回滚安全。
- **R3 AI Mask/双图**：五条写路径 raw pair 维护无缺口；消费版本逐点正确；
  container-island gate 单一实现；残余补全与 VL 纠错距离语义按契约区分无互借；
  手绘修正保护完备；检测缓存键完备不跨项目不膨胀。
- **R4 勾画（契约层）**：码点/UTF-16 转换边界全部正确；undo 页隔离；
  revision CAS+原子写；坐标映射两端一致；失效三向分离正确、同值保存无新代次；
  浏览器与 Remotion 共用同一采样实现；确认门禁不可伪造。
- **R5 账号/契约/迁移**：one-click 与 image workflow 账号上下文正确；
  config 导入 zip-slip 不成立、导出默认不泄漏凭据；Agent 契约无注册违规
  （勾画为内部路由，先例成立）；迁移 checksum 机制成立。

## 未验证（需真实环境，不能被单元测试替代）

- E01–E08 端到端场景与 MP4/PPTX 人工验收（含勾画在真实浏览器中的实际表现——
  R4-002 的影响面建议浏览器开一次工作区实锤）。
- 真实供应商调用（LLM/生图/TTS/百度 OCR 真机）。
- 便携包干净目录启动、低 RPM 真机额度行为。
- Mask 冻结基准重跑（本轮未触碰冻结样本）。

## 建议处置顺序

1. **修 R4-001**（方法回归 AnnotationService + 类表面完整性测试）。
2. **修 R4-002**（补 script 标签 + 加载顺序断言）。
3. 修 R4-003（catch 守卫 + validation_failed 丢弃策略）与 R2-001（retry 继承 account_id）。
4. 决策 R5-001：helper 单点加账号过滤（连带 R5-002/R2-004），或记录单用户豁免。
5. 清 ruff 恢复检查门，把 `run_checks.py quick` 设为合入前置。
6. 修复后跑隔离浏览器走查勾画模块 + 一次真实渲染，再进入 E01–E08 验收。
