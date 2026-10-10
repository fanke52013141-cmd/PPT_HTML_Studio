# A 线接口与状态基线

记录时间：2026-10-10（Asia/Shanghai）
工作目录：`D:\software\PPT_HTML_Studio`
基线 HEAD：`7499e4a5b4f40842f6dd4d559a8067550b15a86e`
分支：`main`；开始时工作树干净。
本记录描述当前 checkout；旧审计中的 `edd477a...`、旧测试路径和 `D:\Program Files (x86)\PPT_HTML_Studio` 不作为本轮运行状态。

## 已存在接口

| 责任 | 当前来源/格式 | 当前运行事实 |
|---|---|---|
| 项目/UI流程 | `static/flow.js`；数据库 `Project.step_status`；可见工作区保持 8 个稳定位置，HTML 后端复用位置并将“视觉素材/场景与对象”替换到现有入口 | 这是应用全局导航，不等同于 workflow.md 的 7 个 HTML 生产阶段。可选数字人/勾画模块不应改变必选进度语义。 |
| 分镜输入 | `planning/visual_contract.json` | `visual_contract_service.read_contract_slide_ids()` 是场景页集合来源；空集合不可就绪。 |
| 作者场景 | `planning/html_visual/scene-<slide>.json`；`revision.json`；`html_visual_store.py` | 项目级乐观 revision。相同字节保存是 no-op；当前文件存在 `edits-<slide>.json` 时拒绝覆盖。 |
| 动作绑定 | `planning/html_visual/binding-<slide>.json`，`hps.html.motion_binding 0.1.0` | 绑定摘要参与场景批准和输入新鲜度。视频渲染要求绑定文件，并在执行阶段根据 `slides/<slide>/audio_timeline.json` 进行结构/时间校验。 |
| 视觉审阅/批准 | `html_visual_review_service.py`；`approval-<slide>.json` | 只能批准已保存场景；指纹绑定场景、注册定义、运行时、使用的资源/字体及 binding。编辑后旧批准会失效。 |
| 输入就绪 | `html_input_manifest.html_readiness()` | 仅检查分镜页集合、场景存在和当前视觉批准，不代表音频、binding、数字人或目标输出就绪。 |
| HTML 任务 | `HtmlWorkflowJobs` + `html_task_store.py`，`LocalJob` 类型 `html_plan_generate` 等 | 同提交键复用 active/succeeded；失败可在最多 3 次内重试；启动将 active 任务置为 interrupted；条件更新阻止旧任务迟到覆盖终态。 |
| PPTX 目标 | `PptxExportService` | HTML 快照 PPTX 采用视觉批准就绪；不需要音频/binding。 |
| 视频目标 | `VideoRenderService` + `HtmlRenderRunner` + TTS 确认状态 | 在 HTML 视觉就绪外，要求确认音频及每页 binding；错误 binding 在渲染前/绑定时失败。 |
| Web/Agent | Web HTML visual/review routes；Agent `/projects/{id}/html-visual/status` 调用同一 scene store 与 readiness 函数 | 当前返回 scene revision/count 与视觉 `ready/issues`；尚无七阶段聚合状态字段。Agent 与 Web 共用来源，但路由组装有重复代码。 |

## 七阶段映射约束

workflow.md 的七阶段是项目制作流程（内容与规划、设计/素材/实际 HTML、音频、动画、可选数字人、审阅输出以及先行项目设定）；它不是数据库现有七个状态列，也不能替换 `Project.step_status` 或改写八位置前端轨道。任何新增聚合状态必须从上述已保存事实派生，读取不得调用供应商、创建任务、保存批准或修改项目。阶段“待审/通过/需修改/过期”只能按现有人工批准记录与输入指纹得出；不得以静态检查、AI 建议或任务成功伪造人工决定。

就绪按目标分别判定：快照 PPTX 依赖当前视觉批准；视频还依赖有效已确认音频与可用动作绑定。公共视觉就绪字段继续保持原有含义，不能把视频前置条件强加给 PPTX，也不能让 PPTX 就绪误报视频可渲染。

H1 内容/规划和 H6 整段交付尚无持久化人工审阅记录定义。本轮不得虚构这两项批准；状态输出应明确 `not_recorded`/缺失，或只报告已有机器事实。定义和实现新审批记录需另有明确卡片、版本及迁移。

## 缓存审计复现结论

旧 `audit.json` 点名的 `checks/test_html_motion_service.py::test_actual_production_preserves_manual_and_reports_identity_conflict` 在本 checkout 不存在；旧命令中的 `checks/test_html_audio_preview.py` 也不存在。因此不能把旧用例失败称为当前可复现缺陷。

当前相邻边界是 `HtmlWorkflowJobs.submit()` 的持久提交键去重：提交键由 contract、冻结模型摘要、当前场景哈希和注册定义哈希组成。相同有效输入应复用任务、不调用第二次生成；改变合法输入必须产生新任务并运行生成。`checks/test_html_production_integration.py` 已覆盖无缓存时的人工冲突保护，但没有同时证明“缓存命中不生成”和“有效输入变化 cache miss 后真实执行并保护人工改动”。A 线将补当前架构对应的成对回归，并断言新生成器调用。

基线定向检查：

| 命令 | 结果 |
|---|---|
| `node checks/test_visible_flow.js` | exit 0；两组可见流程检查通过。 |
| 旧审计 pytest 命令 | exit 1；当前 checkout 缺 `checks/test_html_audio_preview.py`，未运行测试。 |
| `pytest checks/test_html_workflow_acceptance.py checks/test_html_audio_binder.py checks/test_html_production_integration.py checks/test_html_visual_review.py checks/test_html_visual_store.py checks/test_html_task_store.py -q` | 27 passed、8 failed。8 项均在 `html_engine/tools/review-scene.cjs` 的真实浏览器检查子进程失败；检查到工程内 Playwright 包存在，但需验证当前配置的 Chromium 路径/可执行依赖。不是流程断言失败。完整终端输出留在本任务执行记录。 |

## 核心源文件基线 SHA-256

仅供本轮归属核对；新增文档及本轮后续变更不改写这些基线值。

| 文件 | SHA-256 |
|---|---|
| `html_visual_store.py` | `f0758575b72f79aa4ccb53834107f8df41b922bdc1791d43ed28a841eada983a` |
| `html_visual_review_service.py` | `c0d567f893c4cadb8e8eb37283f062ba314351482717fe63bc9cc6fae381e3b5` |
| `html_input_manifest.py` | `fcd3e46d755cfdbb98009a2bede419b66b99a72bbcfee4077c837cb756a95fa2` |
| `html_workflow_jobs.py` | `473ed1c4ac9043139e6a2360a9522863ef4616cf65e7fd0f8930a584e6b238b0` |
| `html_task_store.py` | `1d7587c0812e65638cd3d3e8de06bf02f5ff33afdaa91b27bc761a041fe4c096` |
| `html_visual_routes.py` | `390cf206d8fbf079e5903e990eda44071a0269fb2be096c3f482c528eff440e7` |
| `html_visual_review_routes.py` | `44cee0ee1cd03e13b2606cf101f2e4a12dfd52428248099351d21ff34856f6be` |
| `static/flow.js` | `6eb6ef8eab07a7024e76af1d8a5ee45aebc2afaa7a50791b35fc6d4af4de130b` |
| `static/workflow_state.js` | `43d082cf94566e593f937b99081e84679c2aee68903fd5d34b776dca143b3bed` |
| `static/workspace_navigation.js` | `cbe430f9db0cb031b01aa9346d30c33ddaf31a3b71097d2c605a2e8cb795283c` |
| `static/event_bindings.js` | `0f991bfa5d54f696f7bef0e700efced34ccd786f7c0fc065cb0a2159a46279c1` |
| `static/index.html` | `35446b501fe87a467012114db025f8d444d35015adf33ce439fcfc033b0f2ae5` |
| `agent_api/routes.py` | `9be47351ff462069eacdcb07350e4d782058b977dd56d4a536f32dd33c5d8877` |
| `agent_contract/models.py` | `e39d2e5a122851c30f6a2465f29c4ace7910943e61c00fa3b7214aea0083c7d1` |
| `agent_contract/versions.py` | `308f17b9672b8f880755d139dd2b0342cafc1fb285d0b8fba650192826d590ce` |
