# 关系附着点确定性路由发布备注 · 2026-10-22

仓库 [PPT_HTML_Studio](https://github.com/fanke52013141-cmd/PPT_HTML_Studio)，main。
契约见[geometry-repair 0.2.0](../contracts/html-presentation/runtime/visual-v1/geometry-repair-0.2.0.md)，
总方案见[还原优化方案](../plans/html-backend-development/restoration-optimization-plan-2026-10-22.md)。

## 行为变化

箭头穿字修复新增**确定性附着点路由**：对显式 `point` 端点的关系箭头，代码在目标对象边界上枚举附着点，
用原 `vector-overlap` 谓词确认对所有可见文字无穿越，再交原编译器/30fps QA 验收。不移动作者文字、
不改关系对象、不改样式与时间；图片 anchor 端点与隐式槽位箭头不参与；无解时返回空提案（确定结论），
不调用模型。

新增操作 `set_endpoint_point`（仅确定性路径产出，模型 Prompt 不提供）；人工保护字段仍不可覆盖，
候选仍需显式保存，不自动批准。

## 优化前后数据（同一冻结帧基准，`--baseline` 对照）

`scripts/benchmark_geometry_endpoint_routing.py`，数据集
`checks/fixtures/geometry-endpoint-routing/dataset.json`（hash `4e027ec3…`）：

| 指标 | 优化前 | 优化后 |
|---|---|---|
| 可路由穿字用例求解 | 0/2 | **2/2（100%）** |
| 非路由用例正确跳过（无解 / anchor / 隐式槽位） | 3/3 | **3/3** |
| 误生成候选 | 0 | 0 |
| 模型调用 / 供应商调用 / 作者写入 | 0 / 0 / 0 | 0 / 0 / 0 |
| 基准耗时 | 0.030 秒 | 0.032 秒 |

真实依据：2026-10-21 第 4 页 540 时点 3 组穿字，单对象数值搜索无合法提案，模型回退 593 秒后
返回空正文 unknown；本批为同类冲突提供确定性候选路径，且无解时显式停止。

## 兼容与验证

- Agent API 1.60.0 → **1.61.0**；`html_repair.preview`/`save` 1.8、`html_repair.generate` 1.6；
  capability matrix 重新生成；无数据库迁移、无新 HTTP 路由，旧客户端请求不受影响。
- 契约包 0.9.113 → **0.9.114**；新增 runtime/visual-v1/geometry-repair-0.2.0.md 并更新 CHANGELOG/index。
- 验证：`checks/test_geometry_endpoint_routing.py` 11 passed；基准可重复运行；`git diff --check` 通过。
  浏览器与真实课程终态以远端 CI 与另一台机证据为准。

## 未决

真实第 4 页原始 scene/binding 不在本机，需按 hash 封存移交后复验；本批只证明确定性求解与无解结论，
不证明真实页已修复、视觉已批准或输出已通过。
