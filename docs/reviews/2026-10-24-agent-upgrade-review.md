# Agent 互联升级审查报告（2026-10-24）

审查对象：2026-10-18 → 2026-10-23 的 Agent 互联改造（`f248ab1^..0a9d27c`，40 个提交，306 个文件，约 2.38 万行新增），覆盖外部 Agent 交付（`html_handoff_*` / `html_external_handoff.py`）、Pi Agent 执行（`html_agent_*` / `html_pi_json.py` / `agent_runner/`）、Agent 契约层（`agent_contract/` / `agent_api/` / `mcp_server/` / `cli/`）以及 HTML 修复候选链（`html_geometry_repair.py` / `html_capacity_repair.py` / `html_candidate_agent.py`）。

审查方法：三路并行只读审查（契约层、执行层、逐提交差异）+ 全部头条发现由主审在源码中逐条复核 + AGENTS.md Required Validation 基线实测。本报告只记录发现与计划，未修改任何生产代码。

## 结论摘要

- **无 P0。** 测试基线全绿（Agent 套件 460 passed、契约生成检查 OK、编译/前端/迁移/失效/Reveal/音频检查全部通过、Remotion tsc 通过）。
- **1 项 P1**：外部/Pi Agent 拿到的几何候选在契约上不可提交（`set_endpoint_point` 不在任务包 `operation_schema` 内），穿字场景的 Agent 修复形成确定性死循环。
- **对接规范总体完备且机制真实生效**（路由↔能力双向测试、MCP/CLI 由 registry 派生、matrix 自动生成 + CI 强制、MCP 版本协商 fail-closed），但存在三类系统性缺口：MCP dispatch 手写映射与 schema 漂移、8 个功能模块的模型绕过 `models.py` 单一来源、对外交付物与校验口径不同源（P1 的根因模式）。
- **同步机制真实有效**：升级窗口内所有应触发契约同步的提交都完成了"能力版本 + `AGENT_API_VERSION` + matrix 再生成"三件套；仅有 1 处边缘缺口（新增失败码未更新能力描述）。

---

## 一、验证基线（2026-10-24 实测，HEAD = 0a9d27c）

| 检查 | 结果 |
| --- | --- |
| `git fetch origin --prune` | 本地 main 与 `origin/main` 同步，无落后提交 |
| `py scripts/generate_agent_contracts.py --check` | OK（matrix 与 registry/契约哈希一致） |
| `py -m pytest checks/agent/ -q` | **460 passed** |
| `py -m compileall`（Agent 改造全部模块 + mcp_server + cli + scripts + checks） | 通过 |
| `node --check static/workflow_state.js` / `static/flow.js` / `node checks/test_visible_flow.js` | 通过 |
| `py -m pytest checks/test_database_migrations.py checks/test_invalidation_service.py checks/test_source_runtime_safeguards.py -q` | 25 passed |
| `checks/test_reveal_mask_integrity.py` / `test_reveal_pipeline_isolation.py` / `test_slide_visual_invalidation.py` / `test_audio_confirmation.py` / `test_audio_tail_padding.py` | 全部通过 |
| Remotion `npx tsc --noEmit -p tsconfig.json` | 通过 |

环境备注：本机 Python 3.13 缺装 `requirements.txt` 已声明的 `langgraph==1.2.14`，导致 `checks/agent/test_html_geometry_routes.py` 收集失败（`html_candidate_agent.py:16` 模块级硬导入，且被 `html_external_handoff.py`、`html_production_service.py` 等生产模块间接依赖）。已按声明版本补装后全绿。**建议**：在外部 Agent 改造的交接文档中把"langgraph 是核心链路硬依赖（非可选）"写明，避免新机器按"可选依赖"漏装。

---

## 二、发现一：最近改造的 Bug

### P1-1 几何候选"可看不可交"：转发给 Agent 的候选在契约上必然被拒（已亲证）

跨三个提交组合造成（4ac1561 → 6f44fbe → 4e65ee7）：

- `html_geometry_repair.py:142`：`propose_endpoint_routes` 产出 `{"targetId": …, "kind": "set_endpoint_point", "values": …}` 操作；
- `html_external_handoff.py:180-198`：`_deterministic_candidates` 把这些操作原样写进任务包候选，并在 `result_contract.candidate_selection` 中指示 Agent"可原样返回某个候选"；
- `html_handoff_contract.py:8-76`：任务包 `operation_schema` 只注册 `set_presentation / set_text_style / set_variant / set_motion / set_binding` 五种 kind（每个变体 `additionalProperties: False` + `kind: const`），不含 `set_endpoint_point`；
- `html_external_handoff.py:531-532`：导入路径 `if operations and not all(validate_operations(packet["operation_schema"], operations)): raise HandoffError("HANDOFF_OPERATION", …, 422)`。

后果：Agent 按指引返回几何候选 → AJV 校验必拒（`HANDOFF_OPERATION` 422）→ 空跑候选轮次。Pi Agent 同样受害（`html_agent_execution.py:88-128` 的 `check_candidate` 走同一校验）。服务端直连修复路径（`html_repair_orchestration.py`）不受影响。`checks/test_external_minimal_input.py:46-58` 只验证"候选被转发"，未验证"候选可提交"，因此测试全绿但链路断裂。

修复方向：在 `html_handoff_contract.operation_schema` 为 scope 内箭头注册 `set_endpoint_point` 变体（字段约束复用 `html_repair_static.py` 的 0-1 值域校验），或导出时按 `operation_schema` 过滤候选。修复须按政策完成 `html_handoff.*` 能力版本 + `AGENT_API_VERSION` + matrix 三件套。

### P2 级（均已亲证或双源一致）

| # | 问题 | 证据 |
| --- | --- | --- |
| P2-1 | `mask_enabled` 默认值在两条传输上语义相反：契约模型缺省 `False`（schema 也向 MCP 调用方宣告 `False`），MCP dispatch 与 Python 客户端却写缺省 `True`。同一能力 `project.create@1.6` 行为不一致 | `agent_contract/models.py:84`；`mcp_server/tools.py:102`；`agent_client/client.py:148` |
| P2-2 | `task-minimal.json` 的 `protected_paths` 过滤条件永假（`path[0]` 恒为 `"scene"/"binding"` 前缀，不可能命中对象 id scope），精简任务视图对人工保护字段完全沉默。完整包与服务端 `assert_manual_fields_unmodified` 兜底仍在，属信息失真而非绕过 | `html_external_handoff.py:259-260`；`html_scene_editing.py:410-435` |
| P2-3 | 诊断基线路径（`allow_diagnostic_baseline`，恰是容量溢出场景）下，`diagnose` 把容量问题放在 `issues` / `capacity_measurements` 键，而 `_deterministic_candidates` 读 `measurements_path` + `capacityIssues`、`_minimal_task` 的容量缺陷分支读 `capacityIssues` → 容量候选与 `CAPACITY_EXCEEDED` 缺陷双双缺失，`defects` 退化为空对象。最需要确定性修复的场景反而拿不到候选 | `html_handoff_diagnostics.py:38-41`；`html_external_handoff.py:183,199,236-243,344-349` |
| P2-4 | Agent 认证中间件被装在最外层（`add_middleware` 逆序生效：Auth → Tracing → RateLimit），未认证 401 流量完全绕过限流，可无限爆破 token | `server.py:1072-1077` |
| P2-5 | scopes 为空的数据库账号 token 跳过全部 scope 检查，等同全量权限（legacy 环境变量 token 无 scopes 是有意设计，但 DB token 空 scopes 走同一豁免路径） | `agent_api/auth.py:108,138` |
| P2-6 | agent/handoff 路由自身无鉴权依赖，完全依赖全局中间件；未配置 `PPT_STUDIO_ACCESS_TOKEN` 时默认放行，本机任意进程可无鉴权触发付费模型调用与全页材料导出。回环单用户属有意设计，但无部署防线（文档/显式依赖级鉴权均缺） | `app_security.py:95-97,121-122`；`html_agent_routes.py:56-93`；`html_handoff_routes.py:72-119` |
| P2-7 | MCP dispatch 静默丢弃 `project.create/update` 已向 schema 宣告的 `production_mode` / `presentation_mode` / `visual_backend` 三字段 | `mcp_server/tools.py:95-116,129-134` |
| P2-8 | `ArtifactInfo` 同包双定义且 `agent_contract/__init__.py:31-33` 导出的类与生产代码（`agent_api/routes.py:63`、`capabilities.py`）引用的类不是同一个；`mime_type` 必填性已漂移 | `agent_contract/artifacts.py:50-72` vs `agent_contract/models.py:342-357` |
| P2-9 | `narration.update`、`digital_human.config.get/health/generate` 的响应为裸 dict，capability 声明 `response_model=BaseModel`，响应字段在任何契约层都不存在 | `agent_api/routes.py:1439-1444,1667,1701,1737`；`agent_contract/capabilities.py:636,713,739,752` |
| P2-10 | 422 校验错误不走统一错误信封（未注册 `RequestValidationError` 处理器），Agent 客户端必须处理两种错误形状 | `agent_api/errors.py:57-82`；`agent_api/__init__.py:15-33` |

### P3 级（择要，修复建议见优化计划）

**契约/传输**
- 8 个功能模块（`html_semantic_qa_models` 等）的 Agent 请求模型定义在 `agent_contract/models.py` 之外并被 `capabilities.py` 直接引用，绕过 `test_contract_model_parity.py` 守护（`capabilities.py:23-33`；`models.py:437,451,526-533`）。
- 多条 `service_ref` 描述与实际委托不符（如 `tts.synthesize` 写 `tts_service.start_synthesis`，实际走 `pipeline_services`），无机器校验（`capabilities.py:624,638,651,718,731`）。
- OpenAPI 缺 202/403/409/500 声明；`requestBody` 恒为 required，与 `produce` / `plan_generate` 可省略 body 漂移（`openapi_docs.py:86-107`；`html_agent_routes.py:17,37`）。
- `(method, path)` 无唯一性测试，重复时 openapi 静默覆盖（`openapi_docs.py:124-127`）。
- SSE 流 progress 0..1 与 `pipeline.status` 0..100 刻度不一（`routes.py:1031-1035` vs `models.py:202`）。
- `stage.get` 对未知 stage 名静默返回空 200（`routes.py:1240-1292`）。
- token 支持 query 参数传递（GET），未在 OpenAPI 文档化，有日志泄露面（`auth.py:69-73`）。
- 内存限流器 key 无界增长（部署默认已接 SQLite store，暴露面小，`rate_limit.py:47,80-90`）。
- `html_review.produce` 的 schema 默认 `plan_version="0.1.0"` 与路由实际默认 0.2.0 及能力描述矛盾（`html_production_models.py:14`；`html_visual_review_routes.py:222-226`）。

**执行层**
- `html_agent_store.py:92` store 层反向 import execution 层 `ExecutionError`。
- job_id 派生（含 `"html_pi_agent"` 常量 + digest）在 4 处重复（`html_agent_routes.py:29`、`html_agent_jobs.py:87`、`html_agent_workflows.py:68`、`html_agent_store.py:39`）。
- 批量共享预算"调用后检查"（`>` 判定），每子项可超额 1 次调用（`html_agent_workflows.py:194-197`；`html_agent_jobs.py:212-213`）。
- worker except 分支内 `store.update` 二次失败 → 任务滞留 running 直至进程重启（`html_agent_jobs.py:234`；`html_agent_workflows.py:152`）。
- Agent 任务 store 无 DB 级 CAS（仅进程内 RLock；对比 `html_task_store.py:268-283` 的乐观锁），多进程部署会竞态（`html_agent_store.py:63-86`）。
- pi-jobs 工作目录（完整解压包 + 候选图 + events.jsonl）任务结束后不清理，长期累积磁盘（`html_agent_jobs.py:137`；`html_agent_workflows.py:121`）。
- 守卫约 0.2s 一次轮询 DB；每次工具调用触发全量定义 + 3 个 Windows 字体（约 20MB）哈希（`html_agent_jobs.py:172-175`；`html_external_handoff.py:63-79`）。
- `reconcile_project` 裸 `except Exception` 掩盖恢复路径真实缺陷（`html_workflow_jobs.py:390-399`）。
- 跨模块使用 `_request` / `_read_revision` 私有 API（`html_agent_execution.py:59`；`html_external_handoff.py:304,523`）。
- 任务包 `CONTRACT.md` 版本（2.0.0）与 `create_execution` 实际版本（2.1.1）不同步（`html_external_handoff.py:408` vs `html_handoff_execution.py:46`）。

**修复候选链**
- `propose()` 对 targets 异常的 issue 抛 `StopIteration` 未防御（`html_geometry_repair.py:110-113`）。
- `html_agent_workflows.work` 非批量分支若 `max_candidate_rounds=0` 则 `result` 未绑定，被兜底 except 误报为候选未通过（`html_agent_workflows.py:131-148`）。
- 行高候选先于字号档插入，双部位对象会把字号候选挤出 16 上限；`lineHeight≤1.0` 时产生与现状重复的候选（`html_capacity_repair.py:108-116`）。
- `repair_capacity` 在 `scene=`/`binding=` 参数路径下 `unchanged` 判定恒 False，仅影响 benchmark 语义（`html_capacity_repair.py:135-150`）。
- `browser_preflight` 失败结果进程级钉死，`force` 参数无调用方使用；BROWSER_UNAVAILABLE 关键词误分类面偏宽（`html_visual_review_service.py:84-110,498-506`）。

---

## 三、发现二：与 Agent 的对接规范是否完备

### 机制层面：真实生效，非纸面规范

| 机制 | 证据 | 状态 |
| --- | --- | --- |
| Agent HTTP 路由 ↔ 能力注册表双向同步 | 正向：每个非 removed 能力必有对应路由；反向：每条 Agent 路由必须登记为能力（豁免仅 `/meta`、openapi、docs 三个文档端点） | ✅ 测试锁定，3 passed |
| MCP 工具全部由 registry 派生 | `mcp_server/tools.py` 不手写定义；72 个 `mcp_enabled` 能力逐条核对 dispatch 覆盖；MCP schema 与契约 schema 强制相等 | ✅ 10 passed |
| CLI 命令由 registry 派生 | `set(CLI_COMMANDS) == {cap.cli_command} ∪ 复合命令`，每条能力可达 | ✅ 封闭断言 |
| `docs/agent/capability-matrix.md` 自动生成 + CI 强制 | `run_checks.py` quick 级即运行 `--check`；本次实测 OK（78 能力、1.62.1、哈希 `3ae5cd39a668ad88` 全一致） | ✅ |
| 契约哈希三层执行 | CI 强制再生成；MCP 握手协商 fail-closed（major 不兼容拒初始化、minor 差异禁写）；交付链路 packet 内嵌 `contract_hash` 校验 | ✅ |
| 内部模型字段暴露决策守护 | `test_contract_model_parity.py` 在内部模型长字段而无暴露决策时失败 | ✅（但覆盖面有限，见缺口 1） |

### 规范完备性缺口

1. **`models.py` 单一来源政策被系统性绕过**：`html_semantic_qa_models`、`html_production_models`、`html_repair_models`、`html_handoff_models`、`html_agent_models`、`html_agent_workflow_models`、`html_asset_sheet_models` 等 8 个功能模块的 Agent 请求模型被 `capabilities.py` 直接引用，parity 守护只覆盖 `ProjectCreate/ProjectSummary`。这些模块的字段增删不会触发任何暴露决策检查——政策目标是"内部模型长字段必须有人决策"，这条防线对最近改造新增的大量 Agent 表面恰好不生效。
2. **MCP dispatch 是手写映射层，schema 变更不自动反映**：P2-1（mask_enabled 默认值相反）与 P2-7（三个字段被丢弃）都源于此。schema 由模型自动派生，dispatch 却是手工分支，两者之间没有 parity 测试。
3. **对外交付物与校验口径不同源（P1 根因模式）**：`task-minimal.json` 的 candidates / defects / protected_paths 是派生字段，但没有"派生结果必须通过 `operation_schema` 校验"的一致性回归，导致候选可看不可交、容量缺陷失真、保护路径清空三类问题同时漏网。
4. **响应建模不完整**：4 个能力的响应从未建模（P2-9），Agent 无法从契约获知响应形状。
5. **描述性元数据失真无校验**：`service_ref` 多处与实际委托不符、执行契约文档版本 2.0.0 vs 2.1.1、`plan_version` schema 默认值与行为矛盾——均为"人写描述"与"机器行为"漂移。

---

## 四、发现三：功能修改能否同步触发 Agent 侧修改

**结论：能。同步机制真实存在、有测试与 CI 强制，且本次升级窗口内执行纪律良好。**

逐提交审计（触发同步 = 改动了 Agent 面向模型或能力注册表）：

| 提交 | 触发同步？ | 执行情况 |
| --- | --- | --- |
| 5964561（外部交付 + 人工工作台） | 是（新增 5 个 `html_handoff.*` 能力 + 模型） | ✅ 1.55.1 + matrix 再生成 |
| 1578d32（候选编辑 + Pi 工作流） | 是（新增 `html_agent.*` / `agent_workflow.*` 各 4 项） | ✅ 1.59.0 + matrix |
| 7ea5e44（Pi 能力补 MCP/CLI 传输） | 否（纯传输补齐） | ✅ 正确未 bump |
| 662b725（箭头穿字几何候选） | 是 | ✅ 1.60.0 + matrix |
| 6f44fbe（端点路由） | 是 | ✅ 1.61.0 + matrix |
| 1e82bda（容量修复） | 是 | ✅ 1.62.0 + matrix |
| 6212ad7（供应商探测/计划版本） | 是 | ✅ 1.62.1 + matrix |
| 9cd84d1 / e5ce1c / 7e8696e / 4e65ee7 / cb1c9ab | 否 | ✅ 正确未 bump |
| 59da921（缺陷检测） | 边缘（新增 `GEOMETRY_PREFLIGHT_REJECTED` 等失败码，无模型/注册表变更） | ⚠️ 按政策字面不强制，但能力描述未提及新失败码，Agent 侧可观测行为已变化 |

`AGENT_API_VERSION` 从 1.18 → 1.62.1 的 bump 链条与提交历史逐条吻合。**结构性风险**在于：同步强制的边界是"模型/注册表变更"，而行为变更（失败码、默认值、候选族）不在此列——59da921 和 P1（6f44fbe 新增服务端 kind 但交付 schema 未跟上）都说明"Agent 可观测行为"的变更面需要比现有触发条件更宽的同步意识。

---

## 五、优化计划

> **修订记录（2026-10-24 二次审查）**：本节已按二次审查修正——撤销"模型迁入 models.py"方案（与 AGENTS.md 所有权冲突）；替换 protected_paths 位置索引谓词（实测路径文法证明其错误）与 agent 路由级鉴权方案（改为启动预检）；为 mask_enabled 与 422 信封补契约同步三件套约束；空 scopes 处理收敛为 fail-closed。修正依据均已实测落证。

### 第一批：P1 + 默认值语义（建议立即，约 1-2 天）

1. **P1-1 几何候选可提交性**：在 `html_handoff_contract.operation_schema` 为 scope 内箭头注册 `set_endpoint_point` 变体（0-1 值域、anchor 不可改等约束与 `html_repair_static._apply_endpoint_point` 一致）。
   - 选择注册而非"导出时过滤候选"：该 kind 已在派生源 `html_scene_repair.KINDS` 中（`MODEL_KINDS` 仅为 Prompt 隐藏它），过滤会丢掉穿字场景的确定性修复价值，注册则与"从注册能力派生"的政策一致。
   - 实现约束：验证整条链三段都认识该 kind——schema 校验（`html_handoff_contract`）→ 应用（`html_repair_static`）→ 服务端原系统复核；evidence issue 的 `allowed_repairs` 若列举可修 kinds 一并同步。
   - 新增**通用**一致性回归：导出时对任务包每个候选操作跑 `validate_operations`，失败即导出期报错（顺带覆盖"容量候选 target 不在 scope"类情况，不只防 set_endpoint_point 复发）。
   - 同变更集完成 `html_handoff.export/preview` 能力版本 + `AGENT_API_VERSION` + matrix 三件套。
2. **P2-1 mask_enabled 语义统一（产品语义决策，非纯技术对齐）**：实测 True 缺省在三处——`mcp_server/tools.py:102`、`agent_client/client.py:148`、`cli/pptctl.py:665`（`--mask-enabled` argparse default=True）；契约模型是唯一持 False 的一方（`agent_contract/models.py:84`，其描述"新项目默认整页展示"表明 False 是产品意图）。统一方向（对齐 False）确认后四处一起改，含 CLI。
   - **必须走契约同步三件套**（`project.create` 版本 bump + `AGENT_API_VERSION` + matrix）：缺省语义变化是 Agent 可观测行为变化。
   - 加"MCP/CLI dispatch 缺省 == 契约模型缺省"的 parity 测试。
3. **P2-7 MCP dispatch 丢字段**：`project.create/update` 的 dispatch 透传 `production_mode/presentation_mode/visual_backend`（schema 已宣告这些字段，本修复是行为向 schema 收敛）。

### 第二批：交付物同源 + 安全硬化（1 周内）

4. **P2-2 protected_paths**：实测路径文法为——scene 路径 `["scene", <顶层键>, ...]`（仅 `path[1]=="nodes"` 时 `path[2]` 是节点 id，另存在 `themeRef` 等与对象无关的路径）、binding 路径 `["binding", <键>, <action/beat id>, ...]`（其中的 id 不在节点 scope 内）。因此**不得在 `html_external_handoff` 里按位置索引猜结构**：由路径文法属主 `html_scene_editing`（`protected_edit_paths`，`html_scene_editing.py:410`）提供"这条 path 涉及哪些对象"的判定助手，handoff 层调用属主助手裁剪；binding 保护路径（scope 语义不适用且数量少）整段保留并注明原因。补 `_minimal_task` 单测断言非空。
5. **P2-3 诊断基线字段对齐**：让 `diagnose` 返回 `measurements_path` / `capacityIssues` 同形键（或在消费端同时兼容 `issues`/`capacity_measurements`）。注意 `measurements_path` 要求量测文件落盘（`diagnose` 目前只写临时目录），实现时明确落盘位置与生命周期。新增"诊断基线导出含容量候选与 CAPACITY_EXCEEDED 缺陷"的端到端检查。
6. **交付物一致性回归（护栏，防 P1 模式复发）**：对 `export_bundle` 产物断言候选操作、defects 派生、protected_paths 均符合该任务包 `operation_schema` / 键形约定。与第 1 项的导出期校验共用同一实现，避免两套口径。
7. **P2-4 中间件顺序**：调整 `server.py` 中间件添加顺序使 RateLimit 位于 Auth 之外（401 也计入限流）。测试覆盖两点：无效 token 爆破被限流；随机 token 构造的限流 key 依赖 SQLite store 过期清理不膨胀（呼应 C4）。
8. **P2-5 空 scopes token（fail-closed，不发明权限）**：DB token scopes 为空/残缺时直接 403 + 明确错误码，让运维修复 token；不授予"最小只读"之类的发明权限；legacy 环境变量 token 的豁免路径保留不动。
9. **P2-10 422 统一信封**：注册 `RequestValidationError` 处理器映射为 `{"error": {code: "VALIDATION_ERROR", …}}`。两个附带决策：错误形状变化是 Agent 可观测变化，**走契约同步三件套**；实测 `openapi_docs.py:91` 声明的校验错误是 400 而 FastAPI 实际返回 422，修复时统一状态码（保留 422 并改文档，或统一 400），不再留分叉。
10. **P2-6 部署防线（启动预检，不加第二套路由门禁）**：沿用 `distribution_profile` 在 `start_server.py` 预检失败即拒绝启动的既有模式：绑定非回环地址且未配置 `PPT_STUDIO_ACCESS_TOKEN` → 拒绝启动；部署文档同步标注"未配置令牌 + 非回环 = 付费调用暴露"。不采用 agent/handoff 路由级 Depends（会形成第二套门禁机制，与仓库单一机制原则相悖）。

### 第三批：规范完备性与运维健壮性（持续批次）

11. **模型来源政策澄清 + parity 扩展（不迁移模型）**：模型留在各属主模块——AGENTS.md 已明文所有权（`html_agent_models.py` 拥有无人值守请求/结果模型、`html_handoff_models.py` 拥有交换模型等），迁移反而制造新违规。步骤：先修订 AGENTS.md 措辞，明确"已注册的功能模块模型是合法契约来源，但必须纳入 parity 守护"（当前政策文本自身有张力：一处说 `models.py` 是唯一来源，另一处把模型所有权赋给功能模块）；再把 `test_contract_model_parity.py` 映射表扩展覆盖这 8 个模块。`ArtifactInfo`/`ArtifactCollection` 去重：`agent_contract/__init__.py:31-33` 的导出与生产引用（`agent_api/routes.py:63`）统一为同一个类。
12. **响应建模**：为 `narration.update`、`digital_human.*` 建 response model。
13. **MCP dispatch parity 化**：长期目标为通用 dispatch 从 capability schema 派生参数（流式/二进制能力保留显式分支）；短期把第 2 项的缺省 parity 测试推广到全部手写分支的字段集合。
14. **元数据修正**：`service_ref` 已被 `generate_agent_contracts.py:63` 写入已发布 matrix，属对外文档，但委托是命令式代码、**无法自动比对**——人工修正失真字符串并在 code review 清单加提醒，或删除该列（二选一，不建比对脚本）；统一 `CONTRACT.md` 版本来源（当前 2.0.0 vs 2.1.1）；`plan_version` schema 默认值与路由行为对齐；`(method, path)` 唯一性断言加入 `test_capability_registry.py`；SSE progress 与 status 刻度统一；`stage.get` 未知 stage 返回 404 或错误码。
15. **执行层健壮性**：except 分支内 store.update 加保护并留痕；批量预算判定改 `>=` 或预扣；pi-jobs 工作目录任务终态后清理（保留最近 N 个供排障）；guard 轮询加退避 + 身份哈希结果缓存；`reconcile_project` 收窄 except 范围；job_id 派生抽公共函数；`html_agent_store` 增加乐观锁（对齐 `html_task_store._transition`；单进程部署下优先级低）；`propose()` 对畸形 targets 防御；`workflows.work` 校验 `max_candidate_rounds >= 1`；`browser_preflight` 接线 `force`；行高候选去重与排序调整。
16. **行为变更同步意识**：在 AGENTS.md 同步政策表中补一行"新增 Agent 可观测失败码 → 更新能力描述"（轻量，不强制 bump 版本），避免 59da921 类边缘缺口。
17. **依赖 fail-loud**：`start_server.py` 预检加一条"启用 HTML 后端时 `langgraph` 必须可导入"（它是 `html_production_service.py` 等生产模块的模块级硬依赖，本次审查本机缺装即导致 Agent 测试收集失败）——优于单纯文档注明。

### 批次验收口径

每批完成后：跑 AGENTS.md Required Validation 全组 + `py scripts/generate_agent_contracts.py --check`；涉及版本 bump 的项核对三件套（能力版本、`AGENT_API_VERSION`、matrix 再生成）在同一变更集内；在本报告追加核验记录。

---

## 六、核验记录（2026-10-24 优化实施）

本轮实施修正后计划的**第一批全部 + 第二批全部**；第三批（持续批次）本轮未实施。

### 第一批（P1 + 默认值语义）

1. **P1-1**：`html_design_policy.editable_capabilities` 为带显式端点的箭头声明 `set_endpoint_point`（仅 `{objectId, point}` 且无 anchorId 的侧，与 `html_geometry_repair.propose_endpoint_routes:110-113` 的预条件一致）；`html_handoff_contract.operation_schema` 物化该变体（精确 `{x,y}`、0-1 值域、仅声明侧、至少一端）；`html_external_handoff.export_bundle` 新增导出期守卫 `_submittable_candidates`——scope 外目标的候选过滤（路由器允许"仅文本在 scope"的不对称），形状缺陷抛 `HANDOFF_CANDIDATE_SCHEMA` 阻断导出。能力版本 `html_handoff.export` 0.4.1→0.5.0、`preview` 0.5.1→0.5.2 并更新描述。回归测试用真实编译场景验证 schema 接受路由器形状、拒绝越界/多余键坐标。
2. **P2-1**：`mask_enabled` 缺省四处对齐 False（`mcp_server/tools.py`、`agent_client/client.py`、`cli/pptctl.py`；契约模型本为 False）。服务端创建时该字段由 `presentation_mode` 推导（`project_service.py:168`），对齐为客户端诚实性修复、服务端行为中性。`project.create` 1.6→1.7 + 描述。
3. **P2-7**：`project.create/update` 的 MCP dispatch 透传 `production_mode/presentation_mode/visual_backend`，`agent_client` create/update 增对应参数。`project.update` 1.3→1.4 + 描述。新增 3 条 dispatch parity 测试（缺省一致 + 两能力字段透传）。

三件套：`AGENT_API_VERSION` 1.62.1→1.63.0；matrix 再生成，最终契约哈希 `0acaf25d5274a9b9`，`generate_agent_contracts.py --check` OK。

### 第二批（交付物同源 + 安全硬化）

4. **P2-2**：`html_scene_editing.scoped_protected_paths`（路径文法属主：仅 `["scene","nodes",<id>,...]` 按对象 id 裁剪；binding 与文法外路径保守保留）；`_minimal_task` 改调用属主助手。单测覆盖裁剪语义与精简任务非空。
5. **P2-3**：`html_handoff_diagnostics.diagnose` 返回与 `repair.evidence` 同形键（`issues`/`capacityIssues`/`capacity_measurements`/`measurements_path`），不再把容量问题错放进 `issues`；测试断言诊断基线产出容量候选与 `CAPACITY_EXCEEDED` 缺陷、defects 无空对象。
7. **P2-4**：`server.py` 中间件添加顺序调整，RateLimit 位于 Auth 之外；回归测试证明未认证 401 流量计入限流（第 3 次请求 429）。
8. **P2-5**：`auth.py` 空 scopes 的 DB token fail-closed（403 `INSUFFICIENT_SCOPE`）；测试暴露 `filter(None, ...)` 不去空白、`"  ,  "` 解析出空白权限集的真实缺陷，scope 解析一并改为 strip + 去空。
9. **P2-10**：`register_agent_error_handlers` 注册 `RequestValidationError` 处理器——Agent 路径 422 统一 `VALIDATION_ERROR` 信封（details 有界 20 条），非 Agent 路径保留 FastAPI 默认形状；`openapi_docs` 响应映射补 403/409/422/500、修正 400 描述。新增 2 条信封测试。
10. **P2-6**：确认 `network_guard.validate_network_security` 已实现"非回环 + 无 `PPT_STUDIO_ACCESS_TOKEN` → 拒绝启动"，且 `start_server.py:47` 与 `server.py.__main__`（委托 start_server）均走该守卫，`checks/test_start_server_security.py` 有覆盖——**已有防线，无新代码**；审查时的部署暴露面由该既有预检覆盖。

### 验证结果

| 验证 | 结果 |
| --- | --- |
| `checks/agent/` | **468 passed**（新增 3 dispatch parity + 2 scopes + 1 限流顺序 + 2 信封） |
| handoff/修复链组（minimal input、course structures、capacity、workbench、assistance） | 48 passed |
| design/repair/startup/迁移/失效组（design_policy、design_agent、scene_repair、semantic_runtime、repair_orchestration、start_server_security、safeguards、migrations、invalidation） | 120 passed |
| 时序 QA（temporal_qa） | **12 passed**（修复下述新发现后） |
| compileall / node 语法 / visible flow / reveal mask / audio 确认 / slide 失效 | 全部通过 |
| 未通过项 | `test_four_page_shared_browser_and_deterministic_geometry[default]`（GPU 捕获像素不确定性，见下方"预先存在失败根因"） |

### 计划外新发现（已修复）

提交 `0a9d27c` 修改 `static/index.html` 但未重建密封编辑器构建清单（清单停在 `662b725`），导致 main HEAD 上 `checks/test_html_temporal_qa.py` 全组失败（`EDITOR_BUILD_SOURCE_CHANGED`，未改动 HEAD 可复现，任意机器可复现）。已按"生成物从源重建、不得手改"政策执行 `editor_ui && npm run build`，重建 `canvas-manifest.json` 与 `timeline-manifest.json`（bundle 字节未变，仅清单源哈希更新），时序 QA 恢复全绿。**遗留建议**：改 `static/index.html` 必须重建清单目前无 CI/预检护栏，建议在第三批加入生成物新鲜度预检（与第 17 项 langgraph 预检同处 `start_server.py`/`run_checks.py`）。

---

## 七、核验记录（2026-10-24 优化实施 · 第三批）

第三批（规范完备性与运维健壮性）本轮已实施，含两项**复核后撤回**的原发现与一处**实施后回退**的修复。

### 已实施

11. **模型来源政策 + 守护 + 去重**：AGENTS.md 政策改为"功能属主模块的模型是合法契约来源，但必须在 `test_capability_registry.py::APPROVED_MODEL_MODULES` 刻意登记"（新增 `TestRegistrySourcePolicy::test_capability_models_come_from_registered_owner_modules`，未登记模块的能力模型会在 CI 失败）；`ArtifactInfo`/`ArtifactCollection` 去重——`agent_contract/artifacts.py` 保留工具函数（类型枚举/MIME/资源 URI），类改为从 `models.py` 再导出，两条导入路径现在解析到同一个类（测试锁定同一性）。
12. **响应建模**：`NarrationUpdateResult`、`DigitalHumanConfigRead`（extra=allow 透传配置文件）、`DigitalHumanHealthRead`、`DigitalHumanGenerateResult`/`DigitalHumanSlideJob` 落地 `models.py` 并挂到路由（`response_model_exclude_unset=True` 保持既有线格式不变）；能力版本 narration.update 1.2、digital_human.config.get 1.2、health 1.1、generate 1.1。
13. **dispatch 字段覆盖 parity**：新增 `checks/agent/test_dispatch_field_parity.py`，对全部 44 个显式分支能力做**值流探测**（字符串字段携带唯一哨兵值，改名边界与位置转发仍可检出），通用模型验证分支结构性覆盖。**又抓到并修复一个真实 bug**：`project.list` 的 dispatch 读 `args.get("status")` 而 schema 宣告 `status_filter`，按 schema 传参的 MCP 调用方被静默丢弃过滤条件。
14. **元数据修正**：4 条 `service_ref` 失真已改为实际委托（narration/tts/image 走 `pipeline_services` 操作，digital_human 四条指向 `agent_api.routes` 具体函数）；`plan_version` 默认值——见下方"回退"记录，最终以模型注释 + 能力描述双写警示；`pipeline.stream` 1.2：SSE progress 统一为与 `pipeline.status` 相同的 0..100 整数刻度（测试锁定 1/2 done → 50）；`stage.get` 未知 stage 现返回 404 `STAGE_NOT_FOUND`（列出已知 stage）；`(method, path)` 唯一性断言入 `TestRegistrySourcePolicy`。**CONTRACT.md 2.0.0 vs 2.1.1 复核为有意设计**（基础文档 + workbench 勘误节 = 2.1.1，文档头部明文说明），撤销该 P3，不改代码。
15. **执行层健壮性**：worker 失败路径的 `store.update` 加保护并 `logger.exception` 留痕（启动恢复会兜底标记 interrupted，两个 worker 均覆盖）；pi-jobs 工作目录终态后清理（保留最新 8 个供排障，`cleanup_job_folder`）；guard 轮询退避（槽位等待 1s、消息循环 2s，取消延迟仍秒级）；`reconcile_project` 异常留痕后仍保守阻断；job_id 派生收敛为 `html_agent_store.derive_job_id`（4 处归一）；`propose()` 对畸形单目标 issue 加 `len(ids) < 2` 防御（StopIteration 不再逸出为 500）；`browser_preflight` 失败结果改为 5 分钟 TTL 后自动重探（成功仍进程级记忆）；容量候选字号档优先于行高档（16 上限不再挤出字号候选）、行高候选跳过"等于或放宽现状"的重复值。
16. **同步触发行**：AGENTS.md 同步表新增"新增/变更 Agent 可观测失败码、默认值或错误形状 → 更新能力描述；线格式变化 bump `AGENT_API_VERSION`"。
17. **依赖 fail-loud + 生成物护栏**：`start_server.py` 在导入组合根前预检 `langgraph` 可导入（缺失即 SystemExit 并给出安装指引）；新增 `scripts/check_editor_manifests.py`（按 build.mjs 的三种清单路径基准校验密封源哈希），挂入 `run_checks.py` quick_checks——改 `static/index.html`/`editor_ui` 源不重建清单现在在 CI 快检即红，并附重建指引。

### 复核后撤回的发现

- **"批量预算每子项可超 1 次"**：复核发现 runner 在发起模型调用**前**检查（`++calls > max` 即拒绝执行），工具调用也是"计数→检查→不执行"——预算从不会超额；改成 `>=` 反而会少给一次合法调用。原 P3 为误报，不改。
- **"`workflows.work` 的 result 可能未绑定"**：`AgentLimits.max_candidate_rounds` 已有 `ge=1` 严格校验（两个请求模型共用），0 不可达。撤回。

### 实施后回退

- **`plan_version` 默认值改为 0.2.0 后回退**：改默认值使 `checks/test_html_e_production.py` 25 个用例失败——内部任务流（`html_workflow_jobs` dump 模型默认值）依赖 0.1.0 默认规划/恢复内部场景，该默认是**承载性行为**而非误导。已回退为 0.1.0，并在模型注释与 `html_review.produce@1.16` 描述中双写警示："schema 默认 0.1.0 是内部任务流的遗留占位，路由省略始终意味着语义 0.2.0 计划"。

### 验证结果

| 验证 | 结果 |
| --- | --- |
| `checks/agent/` | **515 passed**（新增：registry 来源守护 + method/path 唯一性 + 44 能力字段覆盖 + SSE 刻度 + 422/数字人模型等；contract hash `abba0961c7c56e78`，`--check` OK） |
| Pi/容量/几何/启动/极简输入组 | 71 passed + 1 预先存在失败（见下） |
| `checks/test_html_e_production.py` | 33 passed + 1 预先存在失败（见下） |
| compileall / `check_editor_manifests.py` | 全部通过 |
| 预先存在失败 | **已解决**（见下节"预先存在失败根因"） |
| 三件套 | 本批能力版本变更（narration/digital_human/pipeline.stream/html_review.produce + project.list dispatch 行为）与 `AGENT_API_VERSION` 1.63.0、matrix 再生成同变更集完成 |

### 预先存在失败根因（2026-10-24 追查并解决）

`test_persistent_design_stop_and_revision_identity` 与 `test_pi_selected_design_runs_original_production_and_records_restorable_ai_version[True]` 在未改动 HEAD 上的失败**同根因**：本机未安装 Playwright Chromium，`0c929d3` 引入的付费前浏览器预检（`browser_preflight`）正确拦截——任务在付费生成前以 `BROWSER_UNAVAILABLE` 失败（Playwright 的"请运行 npx playwright install"横幅）。CI 装有 Chromium 因此绿。修复：`cd html_engine && npx playwright install chromium`，两个测试随即通过（连同 `test_html_pi_workflows.py` 全组 53 passed）。`docs/environment.md` 已新增"Local toolchain notes"记录 langgraph、Playwright Chromium 与编辑器清单三项本机依赖。

安装后进一步定位第三项：`test_four_page_shared_browser_and_deterministic_geometry[default]` 现已能启动浏览器并产出 16 项结果，但 GPU 捕获在 width==1600 结果上像素不确定（`software` 后端变体通过）。这是本机 GPU（RTX 5080）渲染特性而非代码缺陷；按仓库政策不为迁就单机削弱验收约束，标注为该机的已知环境限制（该机使用软件捕获模式或换用验证过的机器）。

两个测试的失败断言已增强为同时输出任务 error（`checks/test_html_pi_workflows.py:344`、`checks/test_html_e_production.py:478`），后续诊断不再需要临时插桩。

### 遗留（下轮可选）

- `html_agent_store` 的 DB 级 CAS（对齐 `html_task_store._transition`）：单进程部署由进程内 RLock 保护，CAS 收益依赖多进程部署（当前部署模型明确排除），本轮有意不实施以免破坏大量持久化测试。
- 实机浏览器可见步骤验证（AGENTS.md 独立验收状态）。

### 明确不需要动的部分

所有权边界总体执行良好（审查确认）：无 monkey-patch、服务层无 `import server`、无第二渲染器、Agent 路径无批准写入（`human_approval: "not_requested"` + 预授权发布属主 + 原子 begin_commit + 回执两阶段）；ZIP 导入双层路径防护、外部数据到 UI 全 textContent、凭据 stdin 传输 + 环境白名单 + 失败脱敏、生产 store 乐观锁、启动恢复不重放——均为干净区域，优化时不要重构这些已验证的防护。

---

## 附录：审查覆盖与证据来源

- 契约层：`agent_contract/` 6 文件、`agent_api/` 11 文件、`scripts/generate_agent_contracts.py`、`mcp_server/`、`cli/pptctl.py`、`agent_client/`、`checks/agent/` 29 个测试文件，全文阅读 + 双向同步实测。
- 执行层：`html_agent_*.py`、`html_pi_json.py`、`html_handoff_*.py`、`html_external_handoff.py`、`html_workflow_jobs.py`、`html_production_stages.py`、`agent_runner/`、4 个 `static/html_*.js`、`server.py` 装配与 `app_security.py`，全文阅读；干净项逐一 grep 验证。
- 提交差异：窗口内 14 个关键提交（8 个完整 diff），契约同步逐提交核对 `versions.py` / `capabilities.py` / matrix 的同变更集性。
- 头条发现（P1-1、P2-1/2/3/4/5/6）由主审在源码中二次复核确认。
