# Pi Agent M4–M5 工程交付与验收边界

后续增量：[GLM原生参数修复与真实复测](handoff-glm-native-parameters-2026-10-20.md)。用户指定启用thinking、65536输出额度、温度1.0，替代下文初版8192/off运行描述；新参数实测Legacy完整返回unsupported，Pi600秒未交付且结果未知，均未保存新页。

2026-10-20。契约0.9.106，Agent API1.59.0，produce1.14；完整Pi SDK/pi-ai1.3.0。接续[M0–M3](handoff-pi-agent-m0-m3-2026-10-20.md)，规范见[正式卡](../../contracts/html-presentation/runtime/visual-v1/pi-production-api-0.1.0.md)。

## 当前可用

- M4修复：编辑器“AI自动修改”可勾选“检查通过后自动另存版本”。固定输入增加delivery_policy=save_revision，通过原严格交付、预览、人工保护和当前版本检查后，沿原save_result和html_scene_changed保存AI版本；保留历史，独立批准不变。默认仍返回候选。
- M4新页：设计确认工具区选择“Pi Agent”、独立配图额度0–2次，再确认当前设计。复用原html_review.produce异步生产队列、生成快照、规划/主体资产/还原/DOM/视觉审查/提交回执；全部文字阶段经完整Pi SDK的submit_json执行，仍由原业务校验器验收。提交即授权原生产入口保存可编辑页；当前不提供新页candidate-only任务。已选设计须当前有效，不能绕过选图或反签旧设计。新页来源为AI，事务包含版本检查点；历史恢复继续当前编辑器的结构与来源校验。
- M5项目候选：article.generate、storyboard.plan（script/visual）及scene.batch_repair固定API。文章使用原项目Prompt；分镜使用现行Prompt/归一化/原文限定和逐句映射。输出仅候选，不覆盖正式文章或讲稿。网页Step1/Step2可生成、恢复、停止、下载Markdown/JSON；二次采用仍走原导入/编辑/保存入口。
- 批量修复：API支持1–5个不同已保存页，共享模型/工具/时间总额度，不按页重置；逐页严格结果、失败和not_started保留。父任务编排完成时succeeded，必须再检查outcome是否all_succeeded；partial_failure不能作全部通过。网页批量向导未实现。
- 兼容与切换：新页runner=legacy|pi，默认legacy；旧修复/外部文件交换与图像、TTS、导出入口保持。没有删除仍在使用的LangGraph编排。

## API输入与交付

新页沿原Web/Agent/MCP/CLI能力，不增加第二个scene.generate存储或API：

```http
POST /api/projects/{project_id}/html-review/{slide_id}/produce
```

```json
{
  "runner": "pi",
  "plan_version": "0.2.0",
  "design_candidate_key": "替换为当前已审阅设计的64位key",
  "max_image_calls": 1,
  "pi_limits": {"max_model_calls": 12, "max_tool_calls": 24, "max_candidate_rounds": 2, "timeout_seconds": 900}
}
```

原任务查询/取消、未知请求恢复和提交回执继续有效。Pi读取真实PNG，只有submit_json工具，无shell、文件发现或批准工具。复用已返回资产不计新增图像调用；预算在原ProductionStages调用前执行，供应商请求意图/回执和缓存仍由原owner处理。文字预算为全部阶段共享，不替换图像供应商。Pi适配器当前固定OpenAI兼容聊天、thinking off、最多8192输出tokens；与旧执行器比较须同时固定这些实际参数，不能仅按业务request.json中的期望thinking记录判断。

项目候选沿agent-job/1.0：

```http
POST /api/projects/{project_id}/agent/jobs
```

```json
{
  "idempotency_key": "article-trial-20261020-001",
  "task": {"task_type": "article.generate", "topic": "人工智能如何辅助课程开发"},
  "delivery_policy": "candidate",
  "limits": {"max_model_calls": 4, "max_tool_calls": 8, "max_candidate_rounds": 2, "timeout_seconds": 180}
}
```

讲稿task改为`{"task_type":"storyboard.plan","phase":"script","requirement":"保留原文事实、否定与适用条件"}`；可视化phase=visual，须已保存讲稿且无待处理限定词审阅。task不能夹带正文绕过项目权威原文，服务器冻结实际原文/Prompt/讲稿；默认候选不审批。

批量task为`{"task_type":"scene.batch_repair","items":[{"slide_id":"当前页ID","task":{"task_type":"static_repair","goal":"具体可验收目标","scope":["真实对象ID"],"expected_revision":当前修订}}]}`，每页仍使用原ExportRequest，可带字号/范围条件。

Agent路径在上述Web路径中插入`/agent/v1`；能力agent_workflow.create/read/result/cancel同步MCP/CLI。GET `/{job_id}`、GET `/{job_id}/result`、POST `/{job_id}/cancel`（{}）。同键同输入只返回原任务；异输入409。未知POST先恢复同一键，不能用新键自动重试。文章输出result.candidate.content；分镜输出result.candidate；批量输出result.items、outcome和partial_results。成本未知保持null。

## 一致性与恢复

局部修复保存前重验账户、项目、目录、后端、当前版本/音频及人工保护。开始提交后can_cancel=false，不将迟到取消伪称撤销；写前意图和完成回执在planning/html_visual/pi-commits。进程退出时未完成提交返回save_outcome_unknown，需核对作者与回执，不自动重放。新页沿原author commit封存/恢复机制。

新页版本检查点复用html_scene_editing.history_checkpoint_files，与正式编辑使用同一格式、来源hash和事务回滚。跨内容或结构不兼容的历史仍会被原恢复校验拦截；不承诺将旧结构强行覆盖当前人工编辑。原文/讲稿变化或排队期间改页使旧候选失败；各页交付的最终采用继续原保存检查，不能从旧结果恢复旧批准。

没有数据库迁移。保留全部之前未提交改动；没有commit/push、发布、重启正式服务或写用户正式项目。旧外部包与设计因源码/能力身份变化而过期时重新导出或沿原显式复用重新审阅，历史试验不改签。

## 验证记录

- 新M4/M5测试：`checks/test_html_pi_workflows.py`，13 passed，71.07s；包含真实Pi SDK/本地SSE脚本供应商、真实PNG、跨阶段总预算、供应商失败不重试、预授权保存/AI历史/回执、保存取消界限与中断、文章候选/源变化、原讲稿限定词、可视化逐句映射、批量总预算/未启动页、图像额度/缓存，以及原produce_scene和持久HtmlWorkflowJobs两条新页路径。
- Web/Agent：`checks/agent/test_html_pi_routes.py`两项含真实SDK本地供应商；在`outputs/pi-m45-new-final.log`的14 passed批次中通过（该批次为新增第二条生产队列参数化测试之前）。账户/HTML后端隔离、幂等、状态查询和候选不写作者均覆盖。
- 原Pi/编辑/生产/阶段回执/恢复回归80项：首批78 passed；期间修改执行器/快照源码使两项按设计拒绝stale/SNAPSHOT_SOURCE_CHANGED。源码固定后单独复跑这两项均passed（`outputs/pi-m45-rerun.log`，2 passed），没有放宽身份校验。原批日志`outputs/pi-m45-regression.log`保留，不伪称该批全绿。
- 浏览器：`checks/test_html_design_panel.cjs`通过Pi选择、素材额度及原设计/修订隔离；`checks/test_html_pi_workflows.browser.cjs`通过固定输入、未知请求关闭重开、同幂等键恢复、结果展示/下载及无页面异常。截图outputs/pi-m45-workflow-ui.png；这张是隔离控件测试，不是正式应用或课程审美截图。
- canonical quick：`outputs/pi-m45-quick.log` All requested checks passed。前端ownership/语法、能力矩阵、Ruff、编辑器构建及diff检查见本轮日志；最终收尾若有新增修订，以后续附记为准。

最终附记：`outputs/pi-m45-delivery-final-stable.log` 16 passed / 93.47s（包含文章已返回对象校验失败后二轮反馈修正、生产队列和Web/Agent）；`outputs/pi-m45-contract-final.log` 71 passed / 62.13s（Registry、MCP、CLI、传输/模型对齐与生成快照）。阶段时限补强后`outputs/pi-m45-deadline-final.log` 4 passed / 63.90s，覆盖严格阶段超时、共享模型额度与两条新页保存路径；可视化补充要求/正式讲稿冻结检查`outputs/pi-m45-visual-input-final.log` 1 passed。前端补测同一自动保存结果只刷新作者一次，避免编辑器重挂载重复刷新；`outputs/pi-m45-workflow-browser.log`通过。已有警告为Starlette弃用提示，未将其称作功能错误。源码修改时触发的stale日志均保留，最终没有关闭来源校验。

全部Pi文字路径现在共享原单机Pi执行槽，项目候选持有槽时不会嵌套重复获取；生产的各文字阶段按槽串行。原业务request_timeout和整个Pi任务时限共同约束调用，以先到者为准；原图像供应商仍沿自身并发/回执。新页候选轮数按原阶段固定2，文章/分镜使用输入的至多两轮上限；只有确定已返回且校验失败的对象会收到修正反馈。

本 handoff 初稿完成时尚无付费真实模型调用；下方增量记录后续真实课程试验。脚本供应商的视觉通过不计入真实自主成功率。M0–M3真实简单/复杂任务证据继续分开保留。

## 接下来

M4工程接线和M5候选/显式选择已实现；**M5默认切换和旧编排清理尚未签收**。真实课程对照已启动，当前结果及本地证据见[2026-10-20真实课程对照记录](../../../outputs/pi-m45-real-course-20261020-m4/real-course-comparison.md)。

本轮 M5：Pi讲稿与可视化候选分别覆盖五页；Legacy讲稿仅三页、可视化缺 `slide_005` 必需正文元素；文章 Pi 超时，Legacy 文章含需要事实核查的额外主张；批量只有 Pi 单例、无 Legacy 基线。M4：同一 `slide_003` 设计输入在隔离副本运行，Legacy设计理解因8192输出额度截断；Pi供应商结果未知且不可按 request ID 查询。两边均未保存新页、revision=0。不能把未知结果记作成功或失败，也不能换幂等键重放相同输入。

先核查 M4 request ID `8510080243b2bdf4402dee99eb026bdc63926d15d1cadf29b1e5fca450c9e3f9` 的供应商状态；若无法取得确定回执，保留未知任务，改用内容或设计有实质差异的新案例做下一组对照。保持 Legacy 默认，不清理旧编排。获得可保存页面后，再复核实际 HTML 截图、播放、人工审美、版本与保护；随后按原计划布局/动画各至少10次、保护/缺能力各至少5次，记录分子/分母、二轮恢复、人工介入和成本，达到门槛再按任务类型切换默认。
