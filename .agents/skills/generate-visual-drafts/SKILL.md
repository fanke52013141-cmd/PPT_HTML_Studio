---
name: generate-visual-drafts
description: Generate or upload full bitmap slide drafts in the PPT Studio image backend using the selected canvas and current visual contract. Use for 图片路线整页生图; exclude HTML design checkpoints and editable reconstruction.
---

# 图片路线整页视觉稿

只适用于visual_backend=image；先读 [共用边界](../workflow-contracts.md)。HTML设计先行转produce-editable-html，不用位图正文替代HTML对象。

输入为当前visual_contract、项目画布/样式/可用参考与已保存Prompt；输出为slides/<slide_id>/visual_draft.png及服务维护的raw配对/状态。

1. 使用原Step3生成/上传入口及项目图片连接，保留Prompt自定义和已有素材；不默认--overwrite批量重写Prompt。
2. 画布从项目读取：16:9为1920×1080，9:16为1080×1920。图片外围纯白，内容内封闭白色保留；主体/标题/图表均在位图，独立组分离。
3. 字幕安全区从当前画布/合同取得，不把横屏y阈值套到竖屏。保持准确文字、层级和数据，不让图片创造事实。
4. 回读实际图片尺寸/文字/留白/安全区和raw/master有效配对；通过review-visual-drafts审阅。

发现乱码/颜色偏差时记录具体问题并提出修订，按授权走原局部生成，不无限自动重生。上传替换也经服务失效Mask/reveal，不能保留旧Mask冒充当前。
