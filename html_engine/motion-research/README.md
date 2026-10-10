# C 线动效候选实验

记录：RES-20261010-C01；借鉴项：BOR-20261010-ANIMEJS-01。日期：2026-10-10。
这是独立的可复现实验，不是生产动作注册、渲染器或应用接线。

关联档案：[RES-20261007-03 huashu-art-motion 借鉴分析](../../docs/research/2026-10-07-huashu-art-motion/analysis-and-adoption.md)。本实验为 HPS-008 的按时间求值要求补充现有 V1 运行时证据。Anime.js 是本轮单独核对的候选；官方来源列于下文，不是原报告的直接依赖或已采纳结论。

## 当前实现核对

生产视觉运行时为 html_engine/visual。renderer.cjs 的 renderAt(ms) 按传入时间重算对象状态；预览公开 visualPlayer.seek(ms)。场景动作由 visual/schema.json 限定为 enter、exit、emphasize。

- enter：opacity 与 offsetX/offsetY 位置按 smoothstep 求值；结束后保持可见。
- exit：按 smoothstep 将 opacity 降至 0。当前共享 compiler 没有临时对象标记，也不拒绝普通文字或形状对象使用 exit；这与“临时对象生命周期终点”的定义不完全一致，交 A 处理场景身份/定义，不在此改共享 Schema/compiler。
- emphasize：固定向上 8px 再回位，无幅度参数；同目标同类型重复动作由 ACTION_CHANNEL_CONFLICT 拒绝。
- SVG 批注：当前 annotation node 用图像锚点、圆环和 SVG leader path；leader stroke-dashoffset 随 annotation 的 enter 时间推进。它不是任意文字下划线、自由画圈或通用 SVG path 动作。
- 旧 html_action_editing.py 中的 relation_draw 是纯校验词汇，当前 V1 scene Schema、compiler 和 renderer 未实现/调用它。旧 html_audio_preview_service.py、html_motion_service.py、static/html_motion_editor.js/.css 均不存在；现有编辑入口为共享 html_scene_editing.py / static/html_scene_editor.js，本线未改。

音频绑定为 hps.html.motion_binding@0.1.0，mode=beat_ids，以 targetId:type 索引 {beatId, edge, offsetMs}。显式绑定以语块 start/end 加有符号整数毫秒偏移；存在 binding 文档但未绑定的装饰动作继续使用作者绝对时间。旧的无 binding 实验场景仍按总时长比例缩放。C 修复前，空 link、非法 edge 和小数偏移可能绕过 binder 的边界检查；现在由 binder 拒绝格式错误、无效引用和孤儿目标，不将它们静默解释为未绑定。

## Anime.js 对照

精确固定为 animejs@4.5.0，仅安装在本目录，未接入生产路径。官方资料：

- [Timeline seek()](https://animejs.com/documentation/timeline/timeline-methods/seek/)：按毫秒设置时间线当前位置。
- [Timeline reset()](https://animejs.com/documentation/timeline/timeline-methods/reset/)：暂停并重置当前位置和播放状态。
- [Tween easing](https://animejs.com/documentation/animation/tween-parameters/ease/)：支持自定义 easing 函数。
- [官方仓库 package.json](https://github.com/juliangarnier/anime/blob/master/package.json) 将该包标为 MIT；实装包的许可证原文保存在本目录 ANIMEJS-LICENSE.md，锁定版本见 package-lock.json。

固定黑灰白 scene 含 4 个纯文字/形状节点，未用图像或生成素材。直接比较当前 browser runtime 与 Anime.js object timeline：22 个边界、分数毫秒、乱序 seek、倒退、重复定位样本；Anime.js 每次 seek 前 reset 后，opacity/位移最大误差为 0.0000448031。将候选状态写回隔离的克隆 DOM，与当前 runtime 实际 PNG 比较，22 个时间点所有像素完全一致。暂停、重播后回到相同时间得到相同状态。PNG 与代码环境哈希保存在 results/verification.json。

另以既有 evaporation-process scene 验证实际 SVG leader：7 个时间点（含边界、分数时间、先前进再回退）；Anime.js 与 renderer 的 stroke-dashoffset 最大误差为 0。

发现 Anime.js 的 seek() 单独使用时，在经过退场后倒退到强调前，固定 scene 的 opacity 偏差为 1.0；每次 seek 前 reset() 后则通过。reset 包装没有做性能基准。实验结论是不替换当前生产时钟：现有 renderAt 已满足可重复指定时间求值，Anime.js 候选需额外 reset 包装且会形成另一套生产动作时钟。只保留其可复核对照，不加入生产依赖，不把本结果提升为注册能力。

## 重跑

PowerShell 从仓库根目录执行。Node 依赖只安装在本实验包内；浏览器用本机 Edge，不启动应用服务，也不调用 TTS。

    npm.cmd install --prefix html_engine/motion-research --ignore-scripts --no-audit --no-fund
    $env:HPS_CHROME='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
    npm.cmd --prefix html_engine/motion-research run verify
    .venv\Scripts\python.exe -m pytest checks/html_motion_v1/test_motion_contracts.py -q

结果 PNG：results/enter-middle.png、results/emphasize-peak.png、results/exit-middle.png、results/svg-annotation-middle.png。本记录不构成视觉审美、真实旁白节奏、用户试听或导出视频批准。
