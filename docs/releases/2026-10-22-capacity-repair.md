# 容量溢出确定性修复发布备注 · 2026-10-22

仓库 [PPT_HTML_Studio](https://github.com/fanke52013141-cmd/PPT_HTML_Studio)，main。
契约见[capacity-repair 0.1.0](../contracts/html-presentation/runtime/visual-v1/capacity-repair-0.1.0.md)，
总方案见[还原优化方案](../plans/html-backend-development/restoration-optimization-plan-2026-10-22.md) W3。

## 行为变化

新增 `capacity_first` 修复策略：容量溢出先由代码生成有界候选，再交原容量/时间检查验收，**不调用模型**。

- 尺寸候选：按原容量触发计算建议 `width/height`，限制在画布与注册变体内，并给出槽位内可行偏移；
- 排版候选：仅对已显式字号的公开部位按步进缩小，**不低于 24px 可读下限**；
- 不改文字内容/身份/关系/动作/主题/人工保护；`annotation` 不参与尺寸覆盖；
- 首个通过原检查的候选即返回；全部失败返回 `NO_DETERMINISTIC_CAPACITY_FIT`（保留尝试与错误），
  不调用模型、不产生 unknown、不修改原页面；
- `model` 与 `geometry_first` 行为不变；`capacity_first` 只接受固定指令。

## 优化前后数据（离线候选基准）

`scripts/benchmark_capacity_repair.py`，基于版本化场景 + 注册布局 + 冻结容量测量：

| 指标 | 优化前（无确定性路径） | 优化后 |
|---|---|---|
| 文字行数超限候选 | 0 | **13**（字号 72→24，下限 24） |
| 16.65 canvas px 底部越界候选 | 0 | **5**（1 个尺寸候选 + 字号步进） |
| 合计候选 | 0 | **18** |
| 模型调用 / 供应商 / 作者写入 | 0 / 0 / 0 | 0 / 0 / 0 |
| 候选生成耗时 | — | 约 0.0001 秒 |

真实依据：2026-10-21 第 3 页三卡片约 16.65 CSS px 底部越界被拦截后无自动修复路径；本批提供
确定性尺寸/排版候选，且在无解时显式停止。

## 验证

- `checks/test_capacity_repair.py` 5 passed（边界、可读下限、身份保持、scope 过滤、策略校验、基准快照）。
- `checks/test_capacity_first_strategy.py`（CI 真实浏览器）2 项：溢出页确定性修复通过且 0 模型调用；
  120 字超长文本在可读下限内仍溢出时显式无解、不调用模型。
- Agent API **1.62.0**；`html_repair.generate` **1.7**（策略枚举 additive）；契约包 **0.9.115**；
  capability matrix 已重新生成；无数据库迁移、无新 HTTP 路由。

## 未决

真实第 3 页原始 scene/binding 不在本机，需按 hash 封存移交后复验；本批只证明候选与停止语义，
不证明真实页已修复、视觉/音频/输出已通过。
