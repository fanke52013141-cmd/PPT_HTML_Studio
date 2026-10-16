---
name: qa-video
description: Evaluate actual PPT Studio previews or outputs and route concrete defects to their owning stage. Use for 成片检查、音画不对应、输出验收; separate engineering/model findings from human approval and image/HTML routes.
---

# 预览与输出QA

读取 [共用边界](../workflow-contracts.md)。输入为当前实际预览/视频、权威讲稿、timeline、项目配置与相关批准身份；拿不到实际媒体应标未测，不仅凭文件名评判。

逐项记录slide_id、时间/区域、证据、严重度、需求与下一阶段，不写“感觉不好→全重做”：

| 问题 | 所有者 |
| --- | --- |
| 事实/限定词/缺语义对象 | 原文章/分镜规划 |
| 声音/断字/字幕文案 | 原旁白与TTS |
| HTML缺呈现工具 | capabilities；图内语义文字不是assets |
| HTML可执行静态布局/字号 | 受控编辑/还原；先核对注册工具 |
| 图片错误/Mask归属 | 图片生成或AI Mask；builder不重匹配 |
| 动作时机/绑定 | 相应backend的绑定服务 |
| 输出格式/缺帧/解码 | 原导出任务 |

HTML逐句语义使用原A04实际音频三帧，终态审核不替代；诊断qa_log是建议，不等于应用签收。用户决定须绑定对应报告/候选和当前版本走原入口。

检查时长、比例和平台规格以用户目标为准，不强制所有成片3–6分钟或横屏。未检查的音频/动态/平台不宣称通过；不确定问题标needs_review并给可核查建议。
