# Skill 拆分与迭代机制

当前操作入口为 produce-editable-html 1.16.0；本文件保留分阶段历史，当前注册状态以 config/html_runtime_skills.json 为准。已有四个受控阶段片段，不代表六个自主 Agent。

2026-10-12 S05：补充正式导出快照、分段命中复验、合成后完整解码、历史作品与当前完成的区别。沿用现有任务/API；Skill 文档更新仍不是豆包运行时自动加载（S06 待接入）。

2026-10-12 S06：排版修复片段0.1.0启用，Prompt 0.2.0；原Prompt 0.1.0精确对照保留。目录/文件数不等于自主 Agent 数。后续更新片段时先保留失败样本，再固定条件重验，不能由用户文本或模型输出动态登记。

## 建议的六项职责

这是项目职责划分，不是框架数量上限。先保留当前生产与修复总入口，等边界、工具和案例稳定后再拆分。

| 职责 | 负责内容 | 当前边界 |
| --- | --- | --- |
| 生产编排 | 判断阶段、调用入口、停止和交付 | 现有 Skill 总入口 |
| 内容与组件规划 | 权威文案、注册模板、对象及素材引用 | 已有规划服务；可独立提炼 |
| 视觉设计 | 黑灰白基线、层次间距、代码与图片分工 | 需结合已批准参考和视觉审阅 |
| 排版与局部修复 | 未保存候选、已保存编辑、人工字段保护 | 当前 Skill 与有界工具 |
| 质量验收 | 工程、真实模型、审美、动态与导出分开判断 | 当前验收规则；可独立提炼 |
| 素材与可编辑交付 | 素材复用、身份版本、实际 HTML 和编辑能力 | 复用现有资源与交付服务 |

截至2026-10-16，项目已有13个Skill目录（含新增流程Skill专家），其中不少属于原有图片流程；目录数量不等于 Agent 已加载数量。容量修复、设计理解、设计还原和保真审核按注册阶段装载独立片段，并不加载整篇 SKILL.md。原有音频与导出能力继续复用；图片流程的整页位图规则不能直接套到 HTML。

## 将 Skill 接入运行时的后续验收要求

1. 注册受控的 Skill ID、版本、适用阶段、工具范围和输入输出。只加载已审核条目。
2. 先按任务选 Skill，再加载必要正文和引用；不要把全部 Skill 拼接到每次请求。
3. 审计记录实际加载的 ID、版本或内容哈希，以及 Prompt、工具和代码版本。
4. Skill 不得扩展工具权限或绕过 Schema、人工字段保护与保存门槛。用户内容、模型输出和外部引用作为数据处理。
5. 缺失或不兼容版本明确失败，不静默使用未知规则。
6. 用固定输入对比接入前后真实模型结果，证明行为变化后再宣称接入有效。

S06已实现第一批候选容量修复 loader，注册/合同/路径/hash校验、快照闭包与每轮实际 Prompt 审计；真实三模板AB/BA对照后启用。其余五职责未新增自主 Agent，已保存修复未强行改造。24项标注事实路由与真实模型评估分别记录。

## 每次迭代的闭环

保存失败输入与产物 → 核实原因 → 区分规则/Prompt/工具/资源/网络/审美问题 → 修改对应层 → 增加回归案例 → 固定条件重跑 → 保留或回退。

- 正例、反例、边界案例一起保留，避免修好一例却扩大误触发。
- 冷杯案例的具体字号不是通用规则，不能写成所有模板的固定参数。
- 观察完成率、初次通过率、修复轮数、人工介入、耗时、费用；未采集指标为 null。
- Skill 版本与运行 Prompt 版本独立；改文档不能冒充运行时升级。
- 最少覆盖既有冷杯基线、长中文、短文本、另一注册模板、人工锁定字号、错误资源、合理容器覆盖。正式视觉审阅仍需用户确认。

单次记录建议格式：

```json
{
  "case_id": "example",
  "skill_version": "1.2.0",
  "runtime_skill_loaded": false,
  "input_hash": null,
  "runtime_revision": null,
  "prompt_version": null,
  "model": null,
  "manual_plan_or_scene_edits": 0,
  "model_calls": null,
  "repair_rounds": null,
  "elapsed_seconds": null,
  "cost": null,
  "status": {
    "engineering": "not_tested",
    "real_model": "not_tested",
    "visual": "pending_review",
    "export": "not_tested"
  },
  "artifacts": [],
  "failure_cause_status": "unconfirmed"
}
```

evaluation/cases.json 是评估规范，不是已经执行的模型评分。结构验证、人工走查与真实模型实验必须分别报告。

## 1.8.0 — 2026-10-13

新增按需 semantic-planning 指南与 B17—B20，共28条结构化路由案例。表达错误进入重新规划，容量错误才进入局部排版；实际 runtime Skill 0.1.0 正文未改。A02 真实规划结构通过但 instructional 对象被标为 context，记录为待语义验收的问题，不能用结构通过或手改输出来掩盖。

## 1.9.0 — 2026-10-13

A03 explicit scene0.6/binding0.2: stable multi-actions, initial state, source-bound actual audio, exact repeated-action editing and shared preview clock. Existing 28 annotated routes retained; runtime layout Skill remains0.1.0. Semantic QA and autonomous course orchestration remain pending.

## 1.10.0 — 2026-10-13

All new production starts with a complete design image, including pure-code/reused-subject pages. Accepted designs enter bounded multimodal static reconstruction; registered variants explicitly upgrade scene0.6 to 0.7. Prompt0.4 added safety, format and CJK line-height evidence. Original timeout and thinking-disabled experiments remain historical evidence, without visual approval.

## 1.11.0 — 2026-10-13

设计理解/分工在素材生成前执行，其合法组件选择经原编辑接口实际消费。独立终态审核使用真实截图，代码SVG不可转到位图返工，其他问题按归属返回。四个受控运行Skill进入快照，保留正常思考与600秒等待。真实Pro理解、还原、审核均返回；审核发现7项问题并阻止保存。多素材拆分及A04语义QA仍是后续独立任务。
