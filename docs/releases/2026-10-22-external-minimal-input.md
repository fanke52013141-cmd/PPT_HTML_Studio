# 外部 Agent 最小输入发布备注 · 2026-10-22

仓库 [PPT_HTML_Studio](https://github.com/fanke52013141-cmd/PPT_HTML_Studio)，main。
方案见[还原优化方案](../plans/html-backend-development/restoration-optimization-plan-2026-10-22.md) W4。

## 行为变化

任务包新增 `task-minimal.json`（`hps.html.external_minimal_task` 0.1.0），作为 Agent 的**最小输入视图**；
`task.json` 仍是权威、封存、不可修改的完整包，二者并存，导入与校验逻辑不变。

最小视图只保留：

- 任务身份与幂等：`task_id`、`idempotency_key`、修订/音频修订、goal/scope；
- scope 内对象（id/type/slot/当前 presentation/公开文字部位），不含全量 scene、binding、beats、bound_scene；
- 类型化缺陷清单（时间点、对象对、测量原因、容量触发维度）；
- **确定性候选**：穿字冲突由 `geometry-repair/0.2.0` 预生成 `set_endpoint_point` 候选，附
  `requires_original_qa=true`；Agent 只能选用候选或返回空操作；
- 相关文件引用（设计参考/实际截图/原音轨）与 hash，不再携带契约文档、工具脚本、read-only 邻居等；
- 允许操作 schema（仍完整）与结果契约（operations-only）；
- 供应商回执要求：`submission_id/task_id/status`，unknown 不得盲目重发。

## 优化前后数据（代表性任务包，同一构建）

`scripts/benchmark_external_minimal_input.py` 用版本化课程计划编译真实 scene、真实能力事实与执行约束，
加冻结证据字段构建代表性 packet，比较 `task.json` 与 `task-minimal.json` 的序列化字节：

| 指标 | 全量 `task.json` | `task-minimal.json` |
|---|---|---|
| 字节数 | 113,922 | **26,403** |
| 降幅 | — | **76.8%** |
| 顶层字段 | 17（含 scene/binding/capabilities/execution） | 19（无上述大块） |
| 缺陷条目 | — | 2（穿字 + 容量） |
| 确定性候选 | — | 支持注入（穿字路由） |
| 幂等键 / 回执要求 | — | 有 |

这是输入体积对比，不是实时 Agent 运行；真实导出包会同时包含两份文件，`task.json` 保持权威。

## 验证

`checks/test_external_minimal_input.py` 4 passed：scope 过滤、缺陷/文件角色保留、重历史字段剔除、
候选转发与 QA 边界、幂等键稳定且随修订变化、序列化确定性。无新 HTTP 路由、无数据库迁移、
不写作者、不签发批准；契约包 0.9.114 / Agent API 1.61.0 保持。

## 未决

真实外部 Agent 在最小输入下的完成率、候选采用率与成本尚未实测（需要外部执行环境）；
下一批按同一任务同时导出全量与最小视图做配对实验。
