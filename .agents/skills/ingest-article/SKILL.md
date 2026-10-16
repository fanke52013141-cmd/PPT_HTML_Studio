---
name: ingest-article
description: Import or verify the complete source article for PPT Studio. Use for 导入文章、原文保存、核对文章源; do not summarize, rewrite facts or plan slides.
---

# 完整文章接入

读取 [共用边界](../workflow-contracts.md)。输入为用户完整Markdown/文本与实际项目身份，输出为当前项目inputs/article.md。

1. 拒绝空白输入；保留标题、章节、数字、引文、限定词和段落顺序。请求导入不等于授权摘要或改写。
2. 正常应用使用source.set/原文章服务保存，让服务处理失效；不旁路写文件导致项目状态不同步。仅独立离线导入任务才直接UTF-8落盘并说明范围。
3. 核对保存回读与输入一致；同内容应保持下游，实际变更依失效服务处理。
4. 旧项目缺article.md时通过原兼容入口读取完整article_brief.content；没有完整内容不能用summary替代，不删历史文件。

缺原文时停止并指出缺项。若用户只给主题，走原文章生成入口、明确生成来源，不能把主题当已验证文章。检查点：后续规划读取完整文章，不依赖摘要。
