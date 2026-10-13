# A01 讲稿语义合同与规划输入交付

2026-10-13，Asia/Shanghai。按 [10月13日新计划](handoff-2026-10-13.md) 的 A01/N01 执行。开发目录 `D:\Program Files (x86)\PPT_HTML_Studio`，分支 main，父提交 `53410cf`；本轮未启动/部署服务、未推送远端、未调用付费模型，未修改真实项目、凭据或批准记录。实际提交以本记录所在的 Git 提交为准。

**A01 合同/结构校验已完成；讲稿与实际画面的语义验收仍待 A04。下一步 A02，不继续调审美，不把五页实例手改当系统修复。**

## 完成内容与归属

- [合同卡](../../contracts/html-presentation/runtime/visual-v1/narration-semantics-0.2.0.md)：scene_plan 0.2.0，HPS-011/013/028/030；契约包 0.9.32，Agent API 1.22.0，能力 html_review.plan_generate@1.1。
- `html_scene_plan_models.py`：Web/Agent 同一版本化请求、目标/动作/预期状态类型与区分版本的返回模型；`html_narration_semantics.py`：归属纯规划层的源/引用/身份校验；`html_storyboard_planning.py`：注册模板/槽位/对象校验及逐语块证据。
- 保留原句及 UTF-8 SHA-256；多目标角色/含义、每句多个动作、同对象重复强调、动作 key 独立生成 actionId。源顺序决定冻结顺序，重排保留身份；改源/伪造冻结字段拒绝。
- 无理由纯旁白、背景/装饰冒充讲解、未知/重复对象或动作、错误状态、缺语块和降级结果拒绝。缺源/错误源 ID 在调用模型前阻断，结构修复仅一轮。
- `html_visual_review_service.py`：PromptVersion 0.5.0，实际输入仅保留 beat ID/原句；宿主派生字段不交给模型计算；旧 0.4.0 Prompt 保留。新 records/review 文件加版本后缀，旧规划证据不被覆盖。
- `html_visual_review_routes.py`、`agent_api/routes.py`、AgentClient、MCP dispatch、CLI：显式选择 0.2.0；未指定仍为 0.1.0。CLI 增加原命令的可选请求文件；修正旧客户端把 `json={}` 传给只接受 body 的请求函数的问题。无新增业务路径或独立任务池。
- `html_production_service.compile_plan`：在 A02/A03 接入前明确拒绝 0.2.0，避免用旧 object:type 身份/单目标编译悄悄丢失新语义。旧生产路线继续回归。

## 本轮验证

| 检查 | 实际结果与范围 |
|---|---|
| 开始前规划/审阅/编译基线 | 27 passed |
| 综合回归：新合同/HTTP/MCP/CLI、旧规划/审阅/brief/生产/创建/恢复/模型绑定、运行保护、数据库/失效、全部 Agent | 550 passed，退出0；Starlette/anyio 既有弃用警告1项 |
| 最终版本证据隔离、状态 JSON Schema 与身份规则集中后定向复验 | 45 passed，退出0；不是额外550项或课程通过数量 |
| Ruff、本轮文件编译、Agent生成文档一致性、source registration、startup hooks、限定 diff 空白 | 通过；没有改架构大小上限 |
| 二十个 S08 实际语块 | 精确原句/ID/顺序可追踪；旧单目标映射在新合同中拒绝。新合成 fixture 仅用于合同测试，semantic:not_run，不声称已重新制作课程 |
| 实际 HTTP 适配器 | 隔离项目/数据库、模型替身；Web与Agent选择新/旧版本、账号隔离、image项目拒绝、非法字段不触发请求；不写场景或批准 |
| V01 架构门禁 | 仍失败：server.py 1162>1100；另一项前端退役检查通过。server.py本轮未修改，不以该既存失败冒充本轮全仓通过 |
| 实际付费模型/图像、课程动态语义、听审/正式输出/数字人 | 本轮 not_run；没有操作音频确认或正式课程批准 |

可重复命令与源散列见 [验证记录](evidence/a01-narration-validation-2026-10-13.json)。`checks/test_html_narration_semantics.py` 和 `checks/test_html_semantic_plan_transports.py` 是本轮新增行为回归；其余旧测试未为新行为降低断言。

## 审查与兼容

按 code-review-and-quality 的正确性、可读性、职责、安全和性能检查。修复审查发现的 legacy beats=None 类型错误、MCP参数丢失、CLI无文件入口及新旧证据覆盖。源与动作派生采用单一规则，未知状态不放宽。没有新增依赖、复制外部源码或借用 AGPL 实现；本次无新增 OSS 借鉴项。

原 image 后端、E1/E2、场景和 binding 的现行格式不升级；无数据库迁移、业务失效事件或自动作者迁移。新接口只生成规划/证据，不能完成制作阶段、批准素材/场景/音频，也不能触发正式导出。Agent 生成文档已同步。

## 下一步入口

1. **A02/N02**：在此规划基础上声明所有实际对象的角色、表达职责与初始/变化/结束状态，把语块状态序列接入 html_design_brief/html_reference_package；代码关系/数据与独立素材分工、预算和真实锚点明确，能力不足阻断。
2. **A03/N03**：编译新多动作身份，并升级绑定/场景兼容读取，instructional 对象由真实 beat 驱动；禁止默认0ms和新流程比例缩放。此时才解除 SEMANTIC_COMPILER_PENDING。
3. **A04—A06**：独立语义 QA、既有任务系统课程调度、正常入口真实课程与改稿/恢复/听审/导出。N06—N08和V01保持未完成。

旧交接的未处理列表是写作时状态。本记录只将 A01 的合同/结构实现更新为完成，不把 N01 的真实表达正确性或 S08 整课改为通过。
