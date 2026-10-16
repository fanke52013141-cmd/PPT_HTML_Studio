# 六步界面集成交接 · 2026-10-15

六页 Codex 生图及 Stitch 候选已适配现有 HTML 工作区。界面实现已完成，隔离工程验证通过；真实课程视觉验收和用户审美确认仍待进行。本次没有请求生成课程、批准候选、导出视频、提交或发布代码。

## 来源与范围

- Stitch 私有项目：[六步工作区](https://stitch.withgoogle.com/projects/16819466348601712538)。最终六页 ID、设计资产和第三步第二版历史见 [来源登记](../../../.stitch/six-step-workspace-20261015.json)。第三步原中断请求仍为未知，未追认为成功。
- 本地设计对照：`outputs/ui-redesign-20261015/index.html`；原生图片、Stitch HTML/截图和功能约束均在该忽略目录。MCP 使用图像审阅后的文字描述与功能约束，未上传参考图片。
- HPS-010/013/023—025 的兼容呈现调整，定义见 [UI 规范](../../ui-spec.md) 和 [工作区流程](../../contracts/html-presentation/runtime/visual-v1/html-workspace-flow-0.1.0.md)。不新增幻灯片能力、作者字段或生成 Prompt。

## 已实现

- `static/html_workflow.css`：仅 HTML 路线的 224px 侧栏、18px 标题、30px 标题工具、统一品牌橙和白色工作面；正文编辑区、分镜双栏、设计大预览/确认栏、对象编辑布局、同步试听/核验分栏及数字人预览优先布局；窄屏依次堆叠。
- `static/html_audio_review.js`：只为既有工具与核验内容增加呈现容器和类名。原 API、共享音频时钟、页面/项目隔离及人工签收逻辑保持。
- `static/index.html`：更新该 CSS 的版本查询参数。
- `.stitch/DESIGN.md`、来源登记、UI 规范及契约索引/变更记录：同步候选来源和呈现边界。契约 0.9.47 记录本轮；后续其他工作的版本不回退。

顶栏保留实际应用入口；没有加入设计稿中虚构的分享、通知、指标或波形编辑功能。图片路线、现有任务恢复、缺前置条件时的禁用状态保持。

## 已验证

所有验证均使用隔离夹具或独立浏览器，不启动生产服务、不连接用户数据库、不请求付费提供者。

| 验证 | 实际证据 |
| --- | --- |
| `checks/test_html_workbench_layout.cjs` | 实际静态应用 DOM，六页 × 1600/768/420px；正文/分镜/设计/旁白夹具及缺页面/缺音频状态，无横向溢出；数字人预览与精调布局；缺页面不能审核、编辑或批准；导航无写请求，退出恢复 |
| `checks/test_html_normal_entry.cjs` | 七个面板 × 1280/768/420px，正常入口、导航、旁白初始化、输出前置、无生成/批准请求、图片路线恢复 |
| `checks/test_frontend_quality.js`、`checks/test_visible_flow.js` | 前端质量与 HTML/图片可见流程 |
| `checks/test_html_audio_review.cjs`、`checks/test_html_audio_review_runtime.cjs` | 音频唯一时钟、逐句定位、切页停止、过期绑定拒绝；实际共享播放器配合合成 WAV，帧差小于 80ms，不代替真实 TTS |
| `checks/test_html_review_panel.cjs` | 独立审核按钮、原候选身份、迟到响应保护；浏览器通过现有运行时解析，不修改测试路径 |
| `checks/test_html_semantic_qa.cjs`、`checks/test_html_output_readiness.cjs`、`checks/test_html_workflow_state.cjs` | 语义签收、输出前置、真实状态及响应当前性 |

本轮应用截图在 `outputs/ui-integration-20261015/`，明确标为隔离夹具。第四步采用缺实际场景状态，第五步采用缺配音状态；不能据此声称真实课程画面、完整对象编辑或真实音频已验收。

## 后续推进

1. 在正常应用查看现有课程六页视觉效果，优先检查长文章、长分镜、多页面、实际对象编辑及数字人精调。保留原候选与人工编辑，不自动续跑旧未知请求。
2. 对已有有效音频的课程试听逐句同步并人工检查；如需重新生产，先明确具体课程/页面及当前冻结配置，再使用原有流程。
3. 根据用户审美反馈进行局部布局调整，复跑受影响的隔离检查。发布、提交和实际课程生产分别记录，不能用设计稿或工程检查代替验收。

工作区同时存在其他开发改动，本交接仅覆盖上述 UI 文件和记录；未回退或接管其他模块。

## 真实课程界面复查（后续推进）

本机实际库仅有 `d1f5885a_122521`（A06 Token 五页课程 · 正常应用验收），不能沿用其他机器项目或旧交接的音频完成结论。正常服务原未运行；从本 checkout 的 `.venv/Scripts/python.exe start_server.py` 恢复 `127.0.0.1:8010`，显式使用本目录 `data/projects.db` 和 `runs`。未创建另一份运行项目。正常启动恢复将原库的三条 queued、两条 running HTML 任务标记 interrupted；未提交 resume、生成、批准或作者保存请求。服务日志中应用 POST/PUT/PATCH/DELETE 为零。

- 第一步：真实文章五节正文恢复完整。
- 第二步：真实五页分页、讲稿及画面映射可读；切到第五页后标题、107 字讲稿及六组映射正确切换。发现 AI 辅助模式原仍上下排列，已补齐宽屏双栏；只作用于 renderer 设置 `display: block` 的审阅区，保留原隐藏条件。隔离测试新增 AI/手动模式、三宽度及手动模式审阅区不可见断言，全部通过。
- 第三步：第一页原图可回看且 stale，确认禁用；第 3、4 页有 needs_review 且未过期的设计，第 2、5 页暂无设计。当前每页任务均 interrupted，未触发继续。原失败任务、未知外部结果与旧候选历史仍保留。
- 第四步：无已保存正式页面，审核、编辑及确认不可用，提示先确认设计。
- 第五步：无实际音频和已保存旁白，提示同步旁白；无场景时同步试听不可用，逐句开始/签收/退回禁用。未用合成音频代替本课程验收。
- 第六步：数字人未启用，状态如实恢复；数字人服务健康检查 503，不影响可选关闭状态。未为界面验收启用或启动数字人模型。
- 输出：MP4、PPTX、字幕下载均禁用，列出缺批准等前置；未执行导出。输出原因仍有 `no_approval` 等底层文本，可在后续输出文案收敛时改为用户语言。

实际界面已通过本机浏览器查看；本轮不是完整课程通过。事实摘要在 ignored `outputs/ui-real-course-20261015/page-facts.json`，服务日志同目录；隔离 AI 布局截图为 `outputs/ui-integration-20261015/step-2-auto-{1600,768,420}.png`。新增布局、正常入口、frontend quality、可见流程与 diff 空白检查通过。

第三页加载完毕后进一步确认：虽有未过期设计，但任务 `html_eb1347e111fc42b3b7c3` 的 recovery 为 `requires_verification=true`、`can_resume=false`、`external_outcome_unknown`；界面正确显示原请求待核实，并禁用设计确认。`input_state=current` 不能替代外部请求结果核实，正常启动也没有解除这个门禁。

接续顺序：先核实第三页旧外部请求，原结果不可取回时须建立明确新版本并保留旧账本；然后人工审阅可操作的当前设计，处理第 1 页过期及第 2、5 页缺设计，再逐页生成/确认正式 HTML；随后同步旁白、真实配音、逐句核验与输出。是否认可构图需要用户决定，不能由本次界面工程检查代签。

## 第三页原请求核实与实际产物审阅

后续只读审计确认：未完成阶段为 `json:f461c7920153a3e96408c430777eb253138c79c7a93142fb195e73f4ea4c37f5`，状态仍是 `intent`，并非已返回或已证明供应商失败；`lookup_supported=false`，无 returned/upstream 回执、无可用上游任务 ID。因此本地 request_id 不能用于供应商查单，不能补发同一请求或改账本。其余 10 个 returned 阶段文件散列均匹配。

已在 `outputs/ui-real-course-20261015/third-page-review/` 建立隔离审阅包，复制原图、原截图及有效素材字节，用原 `allocation-capacity-repair.json` 的未修改场景通过当前共享 `review-scene.cjs` 重演。严格检查 `passed=true`、`capacityIssues=[]`，实际截图与归档 `current.png` 的 SHA-256 完全相同；无生产 API、外部模型、作者保存或人工决定写入。

Codex 对照意见为 `changes_requested`：右侧主体过小、面板/胶囊缺失、标签引线偏离参考、总结条层次和页码造型不同。这是本地视觉审阅意见，不能登记为模型 fidelity pass 或用户驳回。现有人工候选入口要求 failed + 一个 unknown，而本任务为 interrupted + intent，不能改状态强行开放。

审阅包 `index.html` 提供原图与重演图；`audit.json` 保留核实证据，`current-strict-review.json` 为本轮检查。`new-version-proposal.json` 准备了有明确视觉修正的新版设计请求草案，尚未执行、外部调用为零；如用户选择新版，仍须经新设计确认、正式 HTML 还原与独立批准，不将旧请求当作已恢复。

## 用户授权的第三页新版设计

用户随后明确选择“生成第三页新版设计（推荐）”。已按草案通过原 `produce` 接口提交 `plan_version=0.2.0` 和具体 `design_instruction`，新任务 `html_3e22b1acce4244aaa055`，`reused=false`。这段是上述未执行草案的后续执行记录，不回写旧提案或旧任务。

提交回执为 `outputs/ui-real-course-20261015/third-page-review/new-version-submission.json`，授权/范围为同目录 `new-version-execution.json`。授权只到新设计参考并停在 `design_review`，不包含自动接受设计、HTML 还原、作者保存、音频、逐句签收或输出。原 `html_eb1347e111fc42b3b7c3` 仍是 interrupted，原缺结果阶段仍是 intent。

新任务规划阶段超过六分钟，期间持续返回模型处理进度，尚未完成设计生成；最终结果另行追加。没有因等待时间长而重复提交或改变冻结模型配置。

最终新任务 `status=succeeded, stage=design_review`，规划模型约 477.943 秒后返回，随后生图成功。候选 key `ee4f7699d7dd70909738f12ddd19396987e5dbc4120783689b4377f16ffa3fde`，图片 SHA-256 `75b8420649cfe9ba630dda624d451fab5b218b4b98eef8db3d35981628df6f1d`、2048×1152，实际解码及散列核验通过；`design/current` 为 needs_review、stale=false；`saved.changed=false`、`approval_status=not_recorded`。旧原图、旧任务和 intent 阶段仍保留。

新版实际采用三栏构图，未完整执行原修正要求中的右侧主体面板、输入/输出胶囊及高光锚点，因此只记录生成成功，视觉遵循仍需审阅，不能称原图保真已修正。未接受设计、生成独立素材、还原 HTML 或写作者批准。实际图片与新旧对照在 ignored `outputs/ui-real-course-20261015/third-page-review/new-version.html`；完整最终回执为同目录 `new-version-final-task.json`。
