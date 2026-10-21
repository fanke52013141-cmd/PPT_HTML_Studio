# 规划端点确定性归一化 · 2026-10-22

仓库 [PPT_HTML_Studio](https://github.com/fanke52013141-cmd/PPT_HTML_Studio)，main。
方案与后续工作包见[还原优化方案](../plans/html-backend-development/restoration-optimization-plan-2026-10-22.md)。

## 行为变化

模型常用槽位名（`stage-1`）代替对象 ID（`obj-stage-1`）引用关系端点，原实现直接 `PLAN_RELATION_ENDPOINT`
拒绝，真实页面因此多花两轮规划。现在 `normalize_html_scene_plan` 在严格校验前做**确定性归一化**：

- 仅当引用不是已注册对象/素材 ID，且**恰好**匹配一个非 arrow/annotation 对象；
- `point` 端点要求目标类型兼容，`anchorId` 端点要求目标是同 anchor 的图片；
- 改写后 `plan.registered.endpoint_resolutions` 记录 `requested / resolved / basis`，可审计；
- 未知名称、素材 ID、歧义槽位、类型或 anchor 不符**一律不改写**，仍由原严格校验拒绝。

## 优化前后数据（同一基准，`--baseline` 对照）

`scripts/benchmark_plan_endpoint_normalization.py` 基于四页版本化计划，把对象 ID 统一改成 `obj-` 前缀后，
把每个关系端点改写成目标槽位名（共 32 个端点变体），再比较归一化前后的结果：

| 指标 | 优化前 | 优化后 |
|---|---|---|
| 槽位名端点计划通过 | 0/32（0%） | **32/32（100%）** |
| 编译 scene/binding 与规范计划完全一致 | — | **32/32** |
| 归一化回执 | 0 | 32 |
| 未知端点仍被拒 | 32/32 | **32/32** |
| 类型不符（指向 arrow）仍被拒 | 32/32 | **32/32** |
| 供应商调用 / 作者写入 / 批准 | 0 / 0 / 0 | 0 / 0 / 0 |

真实依据：2026-10-21 水循环第 1 页因该错误连续两轮 `PLAN_RELATION_ENDPOINT` 失败；该类错误现在无需重试。

## 验证

新增 `checks/test_plan_endpoint_normalization.py` 10 passed（含逐页 scene 一致、未知/类型/素材/歧义/anchor 负例、
基准汇总断言）；`scripts/benchmark_plan_endpoint_normalization.py` 可重复运行。无数据库迁移、无公开 API/Agent 参数变化，
契约 0.9.113 / Agent API 1.60.0 保持；不写作者、不签发批准、不调用供应商。

## 边界

归一化只消除“同一语义的不同写法”，不猜测未知引用，不改变关系对象、样式或时间；几何与容量缺陷仍由后续
W2/W3 确定性求解器处理。浏览器/真实课程终态以远端 CI 与另一台机证据为准。
