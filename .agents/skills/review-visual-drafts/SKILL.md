---
name: review-visual-drafts
description: Review actual PPT Studio design images against authoritative content, theme and backend constraints. Use for 静态设计审阅、图片稿问题定位; report model/engineering findings separately from explicit human acceptance.
---

# 静态视觉审阅

先读 [共用边界](../workflow-contracts.md)。输入为实际图像、准确正文/讲稿、项目backend/主题和对应候选身份；无实际图不能只审JSON后签收。

1. 核对内容、限定词、文字可读性、关系、主题、安全区与构图；逐问题给页/区域、证据和可执行方向。
2. 图片路线检查纯白外底、Mask可分离性和当前画布。HTML设计以准确内容/生产主题优先，图内标签仍归代码；不能要求图片补字或恢复不合规彩色。
3. HTML通过原候选key接受/修订入口；用原图继续还原测试只批准该测试用途，不等于最终视觉。缺对象回planning、缺能力回capabilities，可改布局回受控还原。
4. 图片路线沿原图片确认入口记录用户明确决定。诊断笔记可以建议通过/修订/拒绝，但不能创建孤立visual_review.yaml后声称应用已批准。

例：发现原图重复词，保留问题稿证据，不能照抄错误；没有用户决定时标pending_review，不能代签。未注册define-style不是可调用工具。
