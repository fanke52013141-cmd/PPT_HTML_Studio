---
name: workflow-skill-expert
description: Build and improve reusable workflow Skills from team procedures, pasted methodology, and real failures. Use for 创建Skill、Skill专家、流程Skill审计、触发与执行边界优化; includes SKILL.md and referenced scripts/runtime policies. Do not execute the business task inside supplied examples or rewrite unrelated global rules.
---

# 流程 Skill 专家

将经验转成可触发、可执行、可验证的操作知识。先核对真实执行，再修改文字。跨平台提供兼容说明，不声称同一元数据已在所有平台验证。

## 定界

从用户材料和当前工程确定：触发/排除、交付目标、目标平台、主要流程、约束、资源、验收。不为已能从工程确认的信息重复提问；只有缺失会改变目标或权限时才询问，并提供可行建议。

- 重复且有稳定输入/输出和验证的任务：Skill。
- 总是适用的简短约束：保留在项目规则，Skill链接引用。
- 一次性探索：完成当前任务，不为形式强建Skill。

先说明边界、复杂度和目录选择，然后继续已授权的可逆本地工作，不增加模板式确认门。用户材料是设计输入，示例中的角色和命令不自动成为执行授权。

## 构建或审计

1. **建立基线**：读取已有Skill及被引用资源，查实际工具/入口、消费者和失败证据。分别列出操作Skill、应用实际加载的运行片段、普通Prompt，不能互称。
2. **选择最小结构**：description只写识别用途的语义；正文保留决策和关键检查点。条件性操作、长表和历史放references；重复易错验证放scripts。保留已有名称和调用策略，避免同义Skill互抢。
3. **逐项修正**：记录“证据→风险→改动→验证”。先修错误职责、无效命令和冲突，再精简。不根据一个例子生成全局尺寸/时长/重试规则；读取当前合同和配置。
4. **明确I/O与退出**：说明输入来源、输出消费者、对象ID和版本归属。区分模型建议、程序验证、人工决定。未知外部结果保留原记录，按现有合同核实/停止，不自行重发或代签批准。
5. **验证后交付**：运行结构/引用检查及受影响业务测试；走查典型、相近反例、失败场景。结构通过、人工走查、实际模型触发评估分别报告，没有真实评测就不声称触发准确率或提速。

## 检查工具

运行 `python scripts/audit_skills.py --root <skills目录>`；有受控运行片段时加 `--runtime-registry <registry.json> --repo <仓库>`。脚本只读输入，验证结构、相对引用、UI元数据和运行文件hash，不改写Skill、不调用模型。

跨阶段批量审计时读 [references/workflow-audit.md](references/workflow-audit.md)；用 [references/evaluation-cases.json](references/evaluation-cases.json)设计正例/反例/边界走查。不强制每个Skill都有相同章节或三个长例子。

## 关键实例

- “把发布经验做成Skill”：找到真实命令、权限和回滚边界，写可执行流程，不自动发布。
- “优化配音Skill”：从按画面重写文案改为消费权威讲稿，只调整既有允许的语音标记；内容错误回规划。
- “重试失败生成”：核对原请求/回执和可查ID，不能借优化、换参数或换目录规避未知结果。

## 交付

保存Skill及必要资源，列出位置、范围、改变的决策、验证和未验证项。批量优化需覆盖清单和逐项状态；审计后保持也可成立。修改运行片段须同步版本/hash、解析器和源闭包，不能只改操作说明却声称系统行为改变。
