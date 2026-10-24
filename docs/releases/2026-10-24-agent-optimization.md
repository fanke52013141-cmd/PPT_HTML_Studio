# Agent 互联优化发布备注 · 2026-10-24

仓库 [PPT_HTML_Studio](https://github.com/fanke52013141-cmd/PPT_HTML_Studio)，main。
来源：[2026-10-24 Agent 升级审查与优化核验](../reviews/2026-10-24-agent-upgrade-review.md)
（对 2026-10-18..23 Agent 互联升级共 40 个提交的审查 + 三批优化），提交
`057022c`、`c520838`、`cf9cb5e` 与本备注。无 P0；原审查唯一 P1 已修复。

## 行为变化

### 交接与修复链（HTML 后端）

- **几何候选可提交（P1 修复）**：任务包 `operation_schema` 现为 scope 内无 anchor
  绑定端点的箭头注册 `set_endpoint_point`（精确 `{x,y}`、0–1 值域）；此前候选
  "可看不可交"，Agent 返回必被 `HANDOFF_OPERATION` 422 拒绝。导出期守卫：
  scope 外目标的候选被过滤（路由器允许"仅文本在 scope"的不对称），形状缺陷抛
  `HANDOFF_CANDIDATE_SCHEMA` 阻断导出。`html_handoff.export` 0.5.0、`preview` 0.5.2。
- **精简任务保护可见**：`task-minimal.json` 的 `protected_paths` 改经文法属主
  `html_scene_editing.scoped_protected_paths` 裁剪，binding 与文法外路径保守保留，
  不再恒为空。
- **诊断基线同形**：容量失败页的诊断基线现在输出与 `repair.evidence` 相同键
  （`capacityIssues`/`measurements_path` 等），容量候选与 `CAPACITY_EXCEEDED` 缺陷
  不再双双缺失；defects 不再出现空对象。
- **容量候选排序**：字号档优先于行高档（16 上限不再挤出字号候选），行高候选跳过
  等于/放宽现状的重复值；`propose()` 对畸形单目标 issue 不再 `StopIteration`。
- **浏览器预检失败 5 分钟 TTL** 后自动重探（此前钉死到进程重启）。

### Agent 契约与传输

- **字段对齐**：`mask_enabled` 缺省四处对齐契约值 `false`（MCP dispatch、Python
  客户端、CLI；服务端创建时该字段本由 `presentation_mode` 推导，行为中性）；
  `project.create/update` 透传 schema 已宣告的 `production_mode` /
  `presentation_mode` / `visual_backend`；`project.list` dispatch 修复
  `status_filter` 被静默丢弃。
- **响应建模**：`narration.update` 与 `digital_human.config.get/health/generate`
  从裸 dict 改为注册响应模型（`response_model_exclude_unset` 保持线格式不变）。
- **刻度与错误**：SSE progress 统一为与 `pipeline.status` 相同的 0..100 整数；
  `stage.get` 未知 stage 返回 404 `STAGE_NOT_FOUND`；Agent 路径 422 校验错误走统一
  `VALIDATION_ERROR` 信封（非 Agent 路径保留 FastAPI 默认形状）；OpenAPI 补
  403/409/422/500。
- **注册表守护**：能力模型必须来自已登记属主模块（新模块须刻意登记）；
  `(method, path)` 唯一性断言；44 个显式 MCP dispatch 分支的**值流字段覆盖**
  parity 测试（字符串字段携带唯一哨兵，改名与位置转发仍可检出）。
- **去重**：`ArtifactInfo` 单一 schema 来源（`artifacts.py` 保留工具函数，类为
  `models.py` 再导出）；4 条失真 `service_ref` 改为实际委托。

### 安全

- 限流中间件移到认证之外：未认证 401 流量计入限流（爆破受限）。
- 空/空白 scopes 的数据库 token fail-closed（403 `INSUFFICIENT_SCOPE`）；
  scope 解析 strip 去空（`"  ,  "` 不再解析出空白权限集）。

### Pi 执行层

- worker 失败路径的终端 `store.update` 加保护并留痕（启动恢复兜底）；
  pi-jobs 工作目录终态后清理（保留最新 8 个供排障）；guard 轮询退避
  （槽位等待 1s、消息循环 2s）；job_id 派生收敛为
  `html_agent_store.derive_job_id`。

### 工具链护栏（随本批入库）

- 编辑器密封清单新鲜度进 CI 快检（`scripts/check_editor_manifests.py`）；
  `start_server.py` 在导入组合根前预检 `langgraph`；`docs/environment.md`
  新增本机依赖表（Playwright Chromium / langgraph / 清单重建）。

## 契约同步

同变更集完成三件套：受影响能力版本（`project.create` 1.7、`project.update` 1.4、
`narration.update` 1.2、`digital_human.*`、`pipeline.stream` 1.2、
`html_review.produce` 1.16、`html_handoff.export/preview`）、
`AGENT_API_VERSION` 1.62.1 → **1.63.0**、`docs/agent/capability-matrix.md`
再生成（契约哈希 `abba0961c7c56e78`）。AGENTS.md 新增"功能属主模型是合法契约
来源但须登记"政策澄清与"Agent 可观测行为变更 → 更新能力描述"同步触发行。

## 验证

- `checks/agent/` **515 passed**（含 44 能力字段覆盖、registry 来源守护、SSE 刻度、
  422 信封、限流顺序、scopes fail-closed 等新增回归）。
- 交接/修复链组 48 passed；Pi/容量/几何/启动组 71 passed；
  `checks/test_html_e_production.py` + `checks/test_html_pi_workflows.py` **53 passed**；
  时序 QA 12 passed；`generate_agent_contracts.py --check` OK；
  编译/前端语法/visible flow/Reveal Mask/音频完整性检查全部通过。
- **环境修复**：两个"预先存在失败"根因为本机缺 Playwright Chromium，付费前预检
  正确拦截（`BROWSER_UNAVAILABLE`）；`cd html_engine && npx playwright install
  chromium` 后全绿。CI 本就安装 Chromium，故线上此前为绿。

## 已知限制

- 本机 GPU 捕获像素不确定（`test_four_page_shared_browser_and_deterministic_geometry[default]`
  仅在本机失败；`software` 后端通过）。按政策不为单机削弱验收约束，已标注为该机
  环境限制。
- `html_agent_store` 未加 DB 级 CAS：单进程部署由进程内锁保护，多进程不在部署
  模型内，有意不实施。
- 实机可见步骤、真实课程与视觉验收仍按 AGENTS.md 保持独立验收状态。
