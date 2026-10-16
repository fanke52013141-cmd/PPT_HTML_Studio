---
name: optimize-prompts
description: Diagnose and improve production LLM/image prompts using actual runtime inputs, schemas and consumers. Use for 优化提示词、精简模型输入、Prompt输出错误; not for executing the business task inside a prompt or editing ordinary UI copy.
---

# 生产Prompt优化

把Prompt当运行接口，坚持输入最小且必要。修改前定位实际默认值/自定义覆盖、组装函数、出站输入、解析/修复、消费者及失败证据；未找到实际调用不能宣称系统已优化。

1. 确定模型唯一任务和非目标，区分缺能力、数据错误、规则冲突和提示词表达问题；不是所有失败都靠加Prompt解决。
2. 对每个字段说明支持哪项决策：删除冗余/无关日志；可确定性计算的ID/hash/计数交程序；保留准确来源、对象工具和安全边界。稳定规则在system，实例变量在user。
3. 输出只留消费者需要的字段，枚举/唯一性/失败结构和图片顺序明确，简短证据替代思考过程。既有请求预算和模型参数不因“优化”静默降低。
4. 修改唯一运行来源；自定义Prompt保持，只迁移可识别旧默认。受控runtime片段更新须同步版本/hash/合同和源闭包，不能只改操作Skill或编辑器预览。
5. 用合法/坏输出、缺字段、真实签名、迁移保留和出站负载验证。未知结果不自动重发；无付费授权不增加模型实验。

复杂改造时按需读 [references/prompt-engineering.md](references/prompt-engineering.md) 的输入删减、案例和验证；历史方法不要求每次固定报告模板。

交付“证据→修复→验证→未测”，给实际文件；结构、离线替身、真实模型和人工走查分开。少字节不能自动换算成少token、少费用或更快。
