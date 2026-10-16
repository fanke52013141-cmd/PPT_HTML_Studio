---
name: bind-animation-timeline
description: Bind current slide visuals to real narration timing in PPT Studio. Use for 动画音频绑定、出现时机修正; route PNG reveal and HTML actionId binding separately, without changing source narration.
---

# 动作与真实声音绑定

先读 [共用边界](../workflow-contracts.md)，确定backend和当前声音/timeline/视觉身份。

- 图片：由scripts/bind_reveal_timeline.py消费当前scene、已保存事件/beat与audio_timeline。诊断命令 `python scripts/bind_reveal_timeline.py --run-dir <run> --slide-id <slide> --lead-sec <configured>`；参数先查--help。不得把全部层统一在开头两秒出现，不重写Mask语义。
- HTML：通过原音频确认/绑定服务html_audio_binding_service与html_audio_binder，使用plan0.2稳定objectId/actionId及原句hash。不把PNG层事件写入HTML，也不按截图位置编造动作。

检查enter在emphasize之前、时间不越真实音频、target存在、原句与顺序一致、估算来源明确。保留人工时序和已完成同值产物；修改先查看原编辑影响。

无Mask的静态页是合法结果，不以“只有full_slide”强制拆层。没有真实声音时停止正式同步，不把作者等分时钟当声音证据。错内容回规划，错Mask回Mask，只有动作偏移才在本阶段调整。
