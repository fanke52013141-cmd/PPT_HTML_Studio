# 正式对象布局编辑定义卡 0.1.0

细化 HPS-007/009/010/011/013—017/023—025/037，承接 editor-adapters-p0。只扩展编辑 UI，不新增 scene、binding 或 Agent 操作；已有 preview 请求增加可选 expected_revision，冲突按原409路径处理。

- 布局模式暂停原播放器，调用共享 renderer 的独立 layout 求值：所有节点使用作者基础位置，未入场/已退场对象以编辑轮廓标识；不修改 initialVisibleIds、动作或字幕数据。播放、seek、关闭和切页移除布局辅助状态；正式截图/导出继续原 renderAt 默认路径。
- Moveable/Selecto 在同源 iframe 内使用辅助框，采用 layout.canvas 和实际 stage 显示比例换算作者坐标。单对象移动、右/下/右下 resize；图片保持其容器比例。annotation 仅跟随原锚点/引线，不独立修改坐标；其它公开节点可选择。
- Shift/框选建立临时选择集合；一次群组移动最多20对象，映射一次原子本地 presentation 操作和一个撤销项；不新增 group 节点，不开放群组 resize、旋转、warp。可切换吸附，参考画布/字幕安全区/登记槽位与其它公开对象。
- 连续事件仅移动编辑辅助框，结束后先用原 editor preview 和共享 renderer 校验完整候选；通过才替换草稿、登记历史。越界/容量/过期失败保留原文档和画面，明确报错；同值不增加撤销项。不会调用生图或 TTS。
- 对象列表、画布和属性主对象同步；多选显示数量并以首选对象为属性目标。属性更改后可用原校验预览刷新布局。撤销/重做同样先校验，再恢复整个 scene/binding/anchor 草稿。
- 保存继续原 expected_revision、人工编辑保护、no-op 和最小重建；不放宽已有 AI 保护或批准/音频门禁。旧0.3/0.4首次添加覆盖升级0.5，语义0.6/0.7不变，actionId、beatId、原句hash保持。
- 前端桥接模块拥有控件生命周期，主编辑器拥有草稿与历史。开关/切页销毁 Moveable/Selecto/ResizeObserver/事件，拒绝迟到 preview。canvas bundle 独立于 React 时间轴；源码、锁文件、生产依赖许可证和产物哈希进入构建及快照闭包，生成文件从源重建。

工程/真实浏览器/正式应用入口/真实课程及视觉签收分别留证；隔离服务中的正式编辑器不等于真实课程签收。P2真实音频时间轴、P4Agent对照和P5视频输出不由本卡的实现自动通过。

本批实现与分层验证见[P1交接](../../../../plans/html-backend-development/handoff-editor-layout-p1-2026-10-17.md)，完整P1验收仍为partial。
