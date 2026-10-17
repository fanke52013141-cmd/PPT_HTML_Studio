# P2 动作时间轴开发交接（2026-10-17）

承接[P1布局及补验](handoff-editor-layout-p1-2026-10-17.md)。实际checkout `D:\Program Files (x86)\PPT_HTML_Studio`，分支`codex/editor-adapter-p0-20261017`，基线origin/main `2cfb2dcb8bb765c67e362d2342088b7e1cfa7e47`。P0/P1/P2均未提交、推送或部署。

## 本批实现

正式场景编辑器已接入独立React Timeline Editor bundle：只读讲稿、已有动作条、动作与对象选中联动、左右拉伸、原句偏移及游标。桥接模块`static/html_editor_timeline_bridge.js`拥有音频/RAF/监听/组件生命周期，主编辑器仍拥有草稿/preview事务/undo/save，`commands.mjs`拥有纯适配。`effects={}`且不调用timeline engine.play；音频`currentTime`驱动共享播放器seek和时间轴游标。无有效音频时轨道只读，播放仍使用原作者预览播放器。

`html_audio_binder.editor_timing`在原binder验证/解析之后附加只读timing，含聚合语块窗口、作者duration/offset、实际动作时间及beat_end/next_action/audio_end裁短原因。`mediaDurationMs`与内容`durationMs`分开，允许合法尾部静音。未增加scene/binding字段。preview Web/Agent同响应；Agent API1.41、preview能力1.2。原输出批准门禁不变。

移动裁短动作保持作者duration，只有resize才改作者duration；edge/beatId/actionId/sourceBeats保持。跨句、无有效绑定、过短及同对象次序改变拒绝；原preview再次校验候选，失败恢复轨道、不消耗历史。一次手势一次undo。原属性面板继续拥有显式重绑，时间轴不自动跨句。进入布局/预览/关闭暂停音频，布局状态屏蔽媒体seek事件以保持隐藏对象辅助视图；关闭销毁React根、监听、RAF，拒绝迟到preview。

独立timeline.js/CSS/notices/manifest与原canvas闭包一起进入generation/render snapshot tooling；P0 editor.js仍不进入产品。notice覆盖esbuild输入及上游ESM已内联的锁定运行依赖，保留timeline-engine ISC元数据与上游MIT证据差异；不把构建记录称为发行法律认证。定义卡：[editor-timeline-0.1.0](../../contracts/html-presentation/runtime/visual-v1/editor-timeline-0.1.0.md)。

## 已取得的验证

- Node16项通过，含移动保留裁短作者时长、左右resize偏移、越句/无绑定/次序拒绝、双bundle源/产物/notice闭包、无timeline引擎播放调用。
- 后端及完整checks/agent相关回归464项通过（含只读timing裁短原因、不改作者输入、原preview/save/冲突和snapshot）；随后因尾部静音/最终源更新按需补跑binder及snapshot。Agent生成核对、前端质量、语法/空白检查通过。原Starlette anyio弃用提示保留。
- 正式编辑器真实浏览器、18秒合成静音：动作延后0.3秒，保存后原句offset300ms、作者时长800ms不变；右拉到1000ms并单次undo/redo；左拉同时改变偏移/时长并单次undo；跨句拒绝、同值保存不增revision；重开保留、4300/500/17000/0ms乱序seek音频与共享播放器DOM一致；播放暂停使用实际audio元素。
- 刻度点击实测2004ms，游标右拖40px后2500ms（刻度80px/s）；均回到同一音频currentTime。无音频fixture轨道不可move/resize、audio无src、原作者播放器播放暂停正常。
- 接入后原0.7布局13项完整回归及500ms迟到preview关闭重开通过，包含隐藏轮廓、seek退出、容量失败、409草稿恢复及annotation排除多选。
- 证据本机忽略输出：`outputs/editor-timeline-p2/2026-10-17/browser-results.json`、`preview.png`。脚本`checks/test_html_editor_timeline.browser.mjs`，用新`--presentation`fixture执行generator，`verifyTimelineCursor`补游标；另开`--presentation --no-audio`fixture执行`verifyNoAudioTimeline`。每次完整generator使用干净服务，避免已保存时长影响固定断言。

隔离音频服务补了Content-Length及Range/206支持；原先浏览器只识别3.072秒或seekable=[0,0]的问题属于测试服务，修正后完整识别18秒并可seek。生产媒体接口未替换。

## 仍待验收与下一步

P2为已实现且合成音频浏览器通过的产品切片，整体partial。真实旁白/课程、真实重新配音后的偏移保持、音频状态并发变化与最终视频对应帧尚未验收；不把静音fixture写成真实配音成功，不调用TTS或自动批准。本轮音频状态在打开时读取，生成/替换配音后需重开编辑器刷新媒体与时序。

接下来优先选一张已有真实旁白的页验证音画与重绑，再完成P3人工保护/最小重建的端到端反例；P1多DPR/40对象压力覆盖及P5真实输出独立补验。不要扩大动作类型、增加第二时钟、自动跨句或将派生绝对秒数覆盖作者数据。

最终补跑binder/snapshot共19项通过，Node16项通过，Agent契约生成核对及前端质量/语法/空白检查通过。截图复核后修正时间轴库默认黑底黑字问题，采用原工作区浅底深字和橙色选中态；初始选中对象同步到动作轨道。该样式调整未改变动作或时钟语义。
