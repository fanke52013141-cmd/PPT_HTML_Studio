# A 线交付记录

## 基线与边界

- 基线 HEAD：`7499e4a5b4f40842f6dd4d559a8067550b15a86e`；分支 `main`；开工时工作树干净。
- 实际目录：`D:\software\PPT_HTML_Studio`。未切分支、reset/clean/stash、全仓暂存、commit/push 或启动第二个服务。
- A 负责文件见 [ownership.json](../ownership.json)。执行中观察到 B 的 `html_engine/reference-library/` 变更；保留原样，A 未编辑其样页/CSS/JS/截图/目录/专属测试。
- 旧审计的 `checks/test_html_motion_service.py` 和 `checks/test_html_audio_preview.py` 在本 checkout 不存在。当前 cache owner 是 `HtmlWorkflowJobs` + `html_task_store`；冲突覆盖位于其真实执行路径。

## 定义、实现和兼容状态

- **定义：** 新增 [应用工作流状态合同 0.2.0](../../../contracts/html-presentation/runtime/visual-v1/application-workflow-0.2.0.md)，明确七业务阶段、只读事实源、状态含义、H1/H6 限制以及快照 PPTX/MP4 不同门槛。关联 HPS-011（任务与输入一致性）、HPS-013（分阶段诊断/批准）和 HPS-030（阶段证据、影响与兼容）。契约包为 0.9.16。
- **实现：** `html_creation_workflow.py` 汇总项目、分镜、场景/当前审批、音频确认、binding、可选数字人和最近任务；Web 与 Agent 共用该构造。Agent status 增加 `workflow` 响应字段并升到 1.1，Agent API 升到 1.16.0。
- **目标门槛：** HTML 快照 PPTX 仅依赖当前场景与视觉批准；MP4 另外依赖当前音频确认、逐页 beat binding，且数字人启用时依赖对应媒体。`video_render_service.py` 调用共享 video readiness，并保留 HTML 和图像后端的音频确认拒绝。
- **兼容：** `workflow` 为 HTML status 加性字段；原 scene/revision/status 字段、八个可见工作区位置、图像流程及数据库格式保持。无 DB 表/列/迁移；不写入审批或阶段状态。H1/H6 持久全局审阅模型未定义，阶段状态显式报告 `not_recorded`，不推断人类批准。
- **任务与回归：** `html_task_store.recent_task_summaries` 仅投影项目内任务生命周期摘要；测试修正五页验收 benchmark 写入 `tmp_path`，不向 tracked docs 留运行文件。新用例证明 cache hit 不启动生成、合法输入变化产生 miss 并实际生成、旧手工 scene/revision 与 conflict 诊断保留。

## 验收证据

以下命令均在项目隔离 pytest 配置下执行。浏览器用本机已安装的 Microsoft Edge，通过 `HPS_CHROME` 覆盖缺失的配置 Chromium 1247 路径。

| 命令 | 结果 |
|---|---|
| `$env:HPS_CHROME='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'; .venv\Scripts\python.exe -m pytest checks/test_html_creation_workflow.py checks/test_html_workflow_acceptance.py checks/test_html_audio_binder.py checks/test_html_production_integration.py checks/test_html_visual_review.py checks/test_html_visual_store.py checks/test_html_task_store.py checks/test_video_render_components.py checks/test_persistent_video_jobs.py checks/test_video_job_idempotency.py -q` | exit 0；62 passed；1 个第三方 Starlette deprecation warning |
| `.venv\Scripts\python.exe -m pytest checks/agent/test_html_editor_binding_integration.py checks/agent/test_contract_model_parity.py checks/agent/test_transport_contract_sync.py checks/agent/test_mcp_contracts.py checks/agent/test_mcp_protocol.py checks/agent/test_cli_contracts.py -q` | exit 0；72 passed；1 个相同第三方 warning |
| `.venv\Scripts\python.exe scripts\generate_agent_contracts.py --check` | exit 0；`docs/agent/capability-matrix.md` 同步 |
| `node checks/test_visible_flow.js` | exit 0；visible flow 与 html backend flow checks passed |
| `git diff --check` 和 `python -m json.tool docs/contracts/html-presentation/contract-index.json` | exit 0；无 whitespace/JSON 错误 |

覆盖内容：空项目、七阶段结构、音频先完成、可选数字人禁用、坏 binding、当前批准和过期批准、PPTX/MP4 门槛差异、视频未确认音频拒绝、Web/Agent 载荷一致、任务 cache hit/miss、provider 确实执行、手工修改冲突保护，以及既有 no-op/恢复/video job/image-visible-flow 回归。

五页验收使用真实受约束 scene、模板、资源读取和 HTML 技术 review，但 provider 是隔离替身；结果显示 3 页请求设计参考、2 页走不请求设计参考的路径，测试检查 PNG、binding 和关键帧。此证据不代表真实供应商、用户视觉审阅、生产美术批准或完整课程签收。

## 未验证项与剩余风险

- WF-05 多页并发 revision、自动合并/重提路径本轮未做并发复现；现有冲突保护保留，不宣称已消除该风险。
- B 线样页给出了双概念比较与曲线路径的映射提案，但现有生产布局/公共能力没有这些结构，V1 图片预算仍限单主体；A 未将样页强接成 scene/template。后续须先补对应定义卡和版本化布局/能力，再分别验证工程与视觉。
- WF-07 真实外部模型/图片服务、数字人生成、用户目标风格审阅和完整课程验收未执行。
- H1/H6 全局内容/交付审核及批量多页审批的数据模型与 UI 仍待定义；当前状态投影不会伪造这些批准。
- 未发布/推送任何改动。其他会话的 B 线样页和标准库工作按其专属交付记录处理，不并入 A 的工程验收结论。
