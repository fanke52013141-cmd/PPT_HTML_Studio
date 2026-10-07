# E1-OPACITY / MOVE-PATH / ROTATE / PATH-PROGRESS

版本 0.1.0；公共时间求值维护；HPS-004/008/011/012/018/021/027；定义 specified。
新增动作不修改 P01 reveal/highlight/annotate 的字段或语义。仅 manual 毫秒，求值 t 可为分数，必须有限且 0≤t≤durationMs。

动作共同必填：id、type/typeVersion、target{nodeId,part:self}、startMs/endMs、easing。0≤start≤end≤时长；零时长到 start 立即取终值。
缓动：linear(p)=p；smoothstep=p²(3−2p)；ease-out-cubic=1−(1−p)³；p 夹 [0,1]。

| 动作 | 目标与字段 | 通道/初末状态 |
| --- | --- | --- |
| opacity | 任意整体节点，from/to∈[0,1] | opacity；开始前基础透明度，结束保持 to |
| rotate | image，fromDeg/toDeg∈[-180,180] | rotation；二维平面旋转，不是转面；结束保持 toDeg |
| move-path | image，pathId，orientation=fixed 或 tangent{minDeg,maxDeg} | position；锚点沿四点曲线，末点保持；tangent 同时写 rotation，切线近零保留节点初始角度 |
| path-progress | path，from/to∈[0,1] | progress；显示参数区间 [0,u]；不按弧长匀速，结束保持 to |

position 指 image 资源锚点的画布位置。节点 box 的初始位置决定基础锚点；第一条 move 路径起点必须一致，后续路径与前一末点相接。本轮不支持跳跃路径，需作者改路径。
scalar 通道第一动作 from 与节点基础值一致，后续 from 与前一终值一致；切线旋转是明确的动态通道，衔接时另做检查，不容许无意瞬移。
同目标同通道动作活动区间不可相交；tangent move 与 rotate 同通道冲突，即使 type 不同也报 ACTION_CONFLICT。两个同刻零时动作冲突；相邻 [start,end) 允许，结束保持值由下一动作替代。
纯求值每次从基础状态重建，再按通道时间顺序计算。不依赖播放历史/墙钟。RAF 仅推进播放器时间；同一 evaluate(t) 给预览、几何与导出使用。
路径进度与移动可不同步，只有输入显式共享 pathId/时段/缓动才保持同轨；校验不替作者虚构关联。
修改动作只重编相关画面/时间，不改语音素材。E1 没有音频适配或跨页转场；不接受 existing_audio 伪输入。
验收：中间取值、端点、零时长、重叠/切线冲突、倒放、跳转、帧间时间、终态过渡对象消失；几何矩阵只施加一次。
输出：t→状态；视频 ceil(duration×fps/1000) 帧、帧时刻 i×1000/fps，最终静态帧另取 durationMs。PPTX 动画本轮不声明支持。
