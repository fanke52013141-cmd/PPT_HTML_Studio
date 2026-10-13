# S06 受控运行时 Skill 0.1.0

2026-10-13增量：[设计Agent0.1](design-agent-0.1.0.md)新增三个明确stage：design_understanding、design_reconstruction、design_fidelity_review，与原candidate_capacity_repair共四个运行片段。loader按已允许stage和固定输入输出合同选择，原容量策略/body/reference版本不变；快照捕获所有已登记片段。下方“第一批只接容量”是S06历史范围，不是当前全集。新阶段使用runtime_skill模式；真实模型质量另验。

2026-10-12；HPS-010/011/013/014/015/017/023—025。沿用候选 Agent 的 LangGraph、编辑权限、最多三次决策和严格浏览器校验，不新增自主 Agent、公共请求字段或任务账本。

| 项目 | 定义 |
|---|---|
| 第一批 | 只接未保存候选的 CONTENT_CAPACITY_EXCEEDED 排版修复；其他五项职责和已保存修复仍由原工具/编排负责 |
| 注册源 | config/html_runtime_skills.json，hps.html.runtime_skill_registry 0.1.0。显式 ID、版本、stage、输入/输出合同、正文/引用路径及 SHA-256；默认模式只能是 legacy_prompt 或 runtime_skill |
| 信任边界 | 不加载整篇 Codex SKILL.md；仅加载 config/html_runtime_skills 中的受控片段。引用通过显式占位符和注册 hash 展开，不加载网络、用户上传、模型返回路径或自行跟随 Markdown 链接。不提供动态注册 API |
| 装载 | 调用前校验注册、合同、路径/大小、正文与全部引用 hash；非法或不兼容失败，不静默回退。任务运行期间内容变化拒绝继续。外部文本只出现在 JSON user 数据，不能选择高优先级 Skill |
| 出站 | 原 Prompt 保持精确版本化对照；Skill 模式是同一固定工具/输出合同 + 按 stage 加载的修复策略。输入仍有当前对象/public parts、槽位、主题默认、人工保护、真实诊断、前轮错误与剩余预算；实际截图相同 |
| 记录 | 每轮保存实际 system/user/schema、模型输入 hash、图片 hash、mode、Prompt hash、Skill ID/version/content hash、引用 hash 与装载身份；运行 summary 可追溯该身份。模型不生成这些字段 |
| 生产快照 | generation 快照捕获 loader、注册文件、运行片段及引用。内容/注册改变会改变快照和请求身份；S02 未知付费请求保护不变，不因更新 Skill 重复请求 |
| 路由 | 结构化阶段/状态/错误类别决定是否适用；自然语言触发测试使用已标注事实，不能宣称确定性测试证明模型的自然语言 Skill 自动选择。现有目录实际 24 项，全部保留 |
| 评估 | 固定 scene/binding/manual/资源、代码、模型配置、截图和相同预算；AB/BA 交叉顺序，每个 arm 从原候选开始。保留全部失败，不择优重试。分别统计模型适配器调用、真实上游请求/usage、工程结果/轮次/耗时/人工介入；缺失费用为 null |
| 默认切换 | 不合格维持 legacy_prompt。只有工程门禁和真实固定样本对照完成后，可在同变更中记录理由并启用受控版本。小样本不承诺总体成功率/美感提升；视觉、音频和导出签收仍独立 |

实现与证据见 [S06 handoff](../../../../plans/workflow-first-parallel-2026-10-09/deliveries/S06.md)；注册配置是代码发布资源，不是用户 Prompt 编辑器。原手动编辑、已保存修复、图片后端、音频与 S05 导出保持原边界。
