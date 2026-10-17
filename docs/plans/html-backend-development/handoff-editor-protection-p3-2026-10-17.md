# P3 人工保护保存边界补强（2026-10-17）

承接[P2时间轴](handoff-editor-timeline-p2-2026-10-17.md)，本批聚焦人工字段保护。实际checkout及分支仍见P2，未提交、推送、合并或部署。定义：[editor-protection-0.1.0](../../contracts/html-presentation/runtime/visual-v1/editor-protection-0.1.0.md)，契约0.9.82，Agent API1.42、repair.preview/save1.4。

## 发现与修正

- AI repair候选已有人工保护检查，但`save_editor(origin="ai")`依赖上游检查，本批将规则收束到`html_scene_editing.assert_manual_fields_unmodified`，候选与最终持久化复用。最终检查发生在锚点私有资源引用转换之后、任何写入之前，避免间接改变assetRef绕过保护。
- 首次增加可选presentation等字典，旧差异函数保护整个容器；现在登记实际变更叶字段。人工仅改offsetX时，AI可改未保护width；改offsetX、删除presentation或通过重建锚点资源改变人工assetRef仍拒绝。旧父级保护记录保持保守范围，不自动缩窄历史保护。
- 保护冲突继续`MANUAL_FIELD_PROTECTED`，消息列出最多三个稳定字段路径，便于定位；不泄漏字段值。来源合法性在no-op之前检查，非法来源同值请求也拒绝。公开Web/Agent编辑来源语义未改变，不接受客户端任意origin；AI修正仍走既有repair。
- 允许的AI修改不新增人工保护，显式人工修改原字段仍允许。最小重建路径不变，布局宽度修改可复用素材与TTS；保护拒绝不写scene/binding/revision/manual/重建/批准/音频或私有图片。

## 验证

新增真实compiler/store服务测试：叶字段范围、未保护兄弟字段AI保存成功、AI不扩大人工保护、直接AI覆盖/删除容器拒绝且全目录逐字节不变、人可继续修改、非法origin no-op拒绝、历史父级保护保守、实际PNG锚点转换后受保护assetRef拒绝且无图片文件泄漏；repair候选使用同一规则并返回字段路径。

首轮相关scene editing/repair/rebuild及完整checks/agent回归480项通过；最终移动保护检查位置并新增锚点反例后，scene editing15项通过，最终整组结果见末尾补记。唯一提示为既有Starlette anyio弃用。此批为后端保护优化，无前端功能变化，未重复浏览器验收。

## 下一步与验收边界

P3此切片完成，完整端到端签收仍partial；不把服务层通过当作真实课程、音频或视频批准。P2真实旁白/重新配音、音频并发新鲜度、P1多DPR/40对象压力、P5视频仍待验。本机存在已有旁白及时间轴，可后续只读复制到隔离目录验证，勿修改原run或把音频文件提交。

下一轮优先做真实旁白与重新配音后的原句偏移保持，并处理编辑器打开期间音频替换的新鲜度；当前仍需重开编辑器刷新配音。AI生成优化与输出批准继续分层验证，不自动扩大动作类型或执行TTS。

最终整组481项通过（scene editing/repair/rebuild及完整checks/agent）；Agent生成核对、Python语法和git diff空白检查通过。候选直接调用共享保护函数，删除多余转发包装；无新增浏览器测试或真实旁白/输出通过声明。
