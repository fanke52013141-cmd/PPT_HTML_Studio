# 勾画标注模块:阶段验收报告(2026-09-27)

## 1. 概述

按《勾画标注模块开发与验收交接》实施的首期交付,截至本报告已完成
**W0–W4 全部核心、W5 渲染链路主体**;尚未完成的项在第 5 节如实列出。
本文不是"全部通过"的声明——未验证范围逐项写明。

- 代码基线:`5670f0e`(开工时 HEAD)
- 测试机器:Windows 10 x64(10.0.26200),Python 3.13.5,Node 24.12.0
- 隔离验证:全部测试经 `checks/conftest.py` 的临时 DB/runs;E2E 浏览器
  验证与真实 OCR 调用均使用独立临时目录与 8642 端口,未触碰真实用户数据。

## 2. 自动化测试证据(全部本轮实跑)

| 套件 | 结果 |
| --- | --- |
| `checks/test_annotation_contracts.py` | 31 passed |
| `checks/test_annotation_store.py` | 8 passed |
| `checks/test_annotation_routes.py` | 21 passed(含确认门禁/账号隔离/409) |
| `checks/test_annotation_ocr_baidu.py` | 25 passed + 1 real-engine(opt-in,已带真实密钥跑过) |
| `checks/test_annotation_text_layout.py` | 6 passed |
| `checks/test_annotation_jobs.py` | 8 passed(生命周期/去重/取消/脱敏/重启中断) |
| `checks/test_annotation_planner.py` | 12 passed |
| `checks/test_annotation_alignment.py` | 6 passed |
| `checks/test_annotation_timeline.py` | 12 passed |
| `checks/test_annotation_geometry.py` | 7 passed |
| `checks/test_annotation_invalidation.py` | 6 passed |
| `checks/test_annotation_workspace.js` | passed |
| `checks/test_annotation_playback.js` | passed |
| `checks/test_visible_flow.js` / `test_frontend_quality.js` / `test_ai_mask_auto_state.js` | passed |
| `checks/test_source_runtime_safeguards.py` + `test_step_ownership_contract.py` | 7 passed |
| `checks/test_database_migrations.py` + `test_invalidation_service.py` | 12 passed |
| 全部 annotation 套件合计 | **127 passed, 1 skipped** |
| `npx tsc --noEmit`(Remotion) | exit 0(含新 AnnotationOverlay.tsx) |

## 3. 真实功能场景验证

| 场景(对照交接 11.3) | 方法 | 结果 |
| --- | --- | --- |
| A01 独立入口/缺失提示 | 浏览器实测 | ✅ 步骤条"可选"徽标、缺图片/讲稿提示、必选进度不增(5/7 不变) |
| 手动链路(新增→保存→重开→编辑) | 浏览器实测 | ✅ 框选→ann_001→已保存→刷新重开→改样式→撤销→重做,服务端 revision 单调 1→4 |
| 讲稿关联 | 浏览器实测 | ✅ 选词→锚点关联,卡片/讲稿高亮/画布三处联动 |
| A02/A06 类 | 同上 | ✅ 草稿状态、revision 保护、beforeunload 拦截 |
| 启用门禁 | 浏览器+API | ✅ 启用后 readiness 逐条列 unconfirmed;关闭后 can_render=true 且草稿保留 |
| 真实 OCR(冻结样本) | 服务端 API + 真实密钥 | ✅ 135 字级候选/1.4s;同 request_key 去重;二次运行 cache 命中零模型请求;token 纠正落盘 |
| 规划链路降级 | 服务端 API | ✅ 无 LLM 配置时干净报错"未配置大模型 API 密钥",不破坏数据 |
| 确认→时间轴构建 | CLI 实跑 | ✅ 未确认被门禁拦截;确认后构建 1 event(highlighter rect),**两次构建字节一致**(确定性) |

## 4. 质量门对照(交接 11.2)

- **精确度诚实**:字级候选全部来自引擎真实检测(`recognize_granularity=small`);无字级结果时诚实标 `line` 并进入 needs_review;0 个行框均分。✅
- **确定性**:同输入两次构建 timeline 字节一致(实测);几何路径固定种子 LCG,无内置随机。✅
- **人工保护**:锁定/修改字段由服务端 diff 维护;重规划不覆盖 protected;测试覆盖 0 次覆盖。✅
- **空间/时间正确性的 ≥90% 自动选对率门**:**未评测**——冻结样本集仅 2 页(交接要求 ≥20 页),属于未完成范围(第 5 节)。
- **时间同步门**:word_aligned 组不存在;首期发布明确收窄为 sentence_fallback + manual(交接允许的收窄条款),并在 adapter-decision 第 8 节声明。✅(按收窄条款)
- **无勾画兼容**:未启用时不新增请求;`build_remotion_props` 对缺 annotation_timeline 的页不携带字段 → 空覆盖层;旧 props 全量回归(迁移/失效/AI Mask/音频确认)全绿。✅(逻辑层;真实 MP4 渲染对照未做,见第 5 节)

## 5. 尚未完成/未验证范围(不冒充完成)

1. **真实 MP4 渲染验收(A14)**:带勾画的端到端 Remotion 渲染与逐帧截图对照未执行(需要完整 scene fixture 与渲染环境验证;链路代码已就位:props 字段、`AnnotationOverlay.tsx`、共享采样)。
2. **冻结评测集扩充(交接 11.1 的 ≥20 页/≥40 目标/≥8 页盲测)**:当前 2 页,空间正确性 ≥90% 门无法据此宣布。
3. **字级音频对齐引擎**:WhisperX preflight 已记录(torch 未装、Python 3.13 兼容性未验);按交接属可选 worker 子进程评测项,未执行。
4. **Agent 契约同步**:annotation 路由未登记进 `agent_contract/capabilities.py`,parity 测试未扩展——按 AGENTS.md 规则,这是发布前必做项。
5. **Prompt 编辑器 UI**:PUT/GET `/annotations/prompts` 已实现并测试,工作区 UI 未做。
6. **A10/A11/A12/A15/A18 等多窗口/缩放/渲染中编辑场景**:未实测。
7. **fingerprint/sidecar 扩展**:`.render.json` 尚未携带勾画 resolver 版本与输入摘要;`artifact_fingerprint.py` 未接入勾画输入。
8. **提交**:全部改动留在工作区未提交,等待确认。

## 6. 回退说明

- 项目勾画开关 `enabled=false` 时,既有视频/PPTX 流路不受影响(路由独立、props 不携带字段、渲染层空覆盖)。
- 勾画产物全部为新增 JSON 文件,删除即回到未使用状态;数据库无 schema 变更,无迁移文件。
- 失效链路对勾画失败做了兜底(`invalidation_service` 的 annotation 钩子不阻塞既有清理流程)。
