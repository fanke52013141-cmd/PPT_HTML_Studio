# HTML 场景规划失败证据 0.1.0

2026-10-16。关联 HPS-011、HPS-013—017。只调整结构化 HTML 场景规划的失败解释、证据与 Prompt 约束；不放宽作者 Schema、容量或人工批准门禁。

## 运行规则

- 流明确返回 `finish_reason=length` 时，计划 JSON 视为输出额度耗尽。记录 `output_limit`、安全的 token 计数及终止原因；不解析残缺内容、不进入 JSON 修复、不自动重发。此类请求的生成结果已知失败，费用仍以实际账单为准。
- 流中断、没有终止帧或读取超时时仍保留原来的结果未知与查单规则。历史 `unknown` 任务不重分类。
- 任务证据只保存 `prompt_tokens`、`completion_tokens`、`total_tokens` 及 `reasoning_tokens` 等计数；不保存供应商扩展元数据、思考正文或密钥。修复轮使用独立日志名，保留首轮流证据。
- `html-semantic-plan/0.3.2` 明列模板必填槽位，要求 `slots` 与 `objects` 逐项覆盖；模型资料不足时选择适合模板，不得编造。`assets.role` 限 64 字，详细需求写入 `need`。现有一次完整响应结构修复、严格校验与作者门禁保持。
- 原快照的同身份输出额度失败不能作为未知结果继续查单，也不能原样重发；修改规划输入后以新实验身份执行。

## 实验边界

旧真实请求在 `reasoning_effort=max` 下耗尽 64,000 completion tokens（其中 62,196 reasoning），约 813 秒未返回完整 JSON。新实验复用同一第一页讲稿和视觉合同；`low`、Prompt 0.3.2 的完整规划经过一次受控结构修复，在约 67 秒内通过严格结构校验。单页结果显示明显的耗时和用量改善，但不证明九页全流程、视觉美感、素材与后续 HTML 还原通过。实验产物见 `outputs/live-linxuan-runtime-20261016-131819/low-scene-plan-comparison-v4/`。
