# 时间接口与三类动作定义卡

以下四卡版本 0.1.0；公共时间/动作库；HPS-004/008/009/011/012/014/018。
均定义 specified；实现 not_implemented；验证 partial（样例算术/引用，非播放测试）。
P04 固定测试时间求值，P06/09 消费现有音频时间结果。

## DEF-TIMELINE

timingInput 为 `{mode,unit:"ms",pageDurations,beatIntervals}`；mode=manual 时本例必须给齐。
pageDurations 为 `{slideId,durationMs}` 数组，>0 整数；beatIntervals 为
`{beatId,slideId,startMs,endMs,source:"manual"}` 数组，0≤start<end≤页时长，语块主属相符。
三个语块的顺序与 beatIds 相符，同一讲稿轨不重叠，允许静音间隔。页面尾留为页时长
减去已安排音频/动作结束，不由组件自行追加。首轮没有转场/跨页音频。

mode=existing_audio 时输入引用现有产物快照 `audioTimingRef:{artifactId,sha256,audioHash,
narrationHash,unit,coordinateSpace}`；unit 可 ms/seconds，coordinateSpace=page/audio/document
必须明确。映射字段由 DEV-06 对现有产物逐项定义，本阶段不冒充已可接受该输入。
首轮样板实现必须明确返回该模式未接入，而非猜测或改换对齐方案。

ResolvedTimeline 为 `{inputFingerprint,unit:"ms",pages,beats,actions,diagnostics}`。
pages 项 `{slideId,documentStartMs,durationMs}`；本例从 0 开始，多页由文档累计页时长。
beats 项 `{beatId,slideId,pageStartMs,pageEndMs,documentStartMs,documentEndMs,source}`。
actions 项 `{actionId,slideId,startMs,drawEndMs?,activeEndMs,effectEndMs,channel,source}`。
start/active/effect 均页面局部；document 值按所属 page 偏移计算，source 记录触发语块与输入来源。
ResolvedTimeline 没有 audio 文件时只表示人工时间，不声称语音对齐完成。

帧时间为 `tMs=frameIndex*1000*fps.denominator/fps.numerator`，从 0 帧开始，
以有理数求值不累计四舍五入。源毫秒参数为整数，求值时间可为分数。视频总帧数
ceil(totalDurationMs*fps.numerator/(1000*fps.denominator))；最后帧不足整帧的时间填充
由编码器统一处理，不改语块时间。静态最终状态明确取 pageDurationMs，而非假装它是最后视频帧。

## 所有动作共用输入

| 字段 | 类型 / 必填 | 默认 / 范围 | 归属与影响 |
| --- | --- | --- | --- |
| actionId, typeRef | Id, VersionRef / 是 | 三动作确切版本 | 实例身份，公共语义 |
| target | TargetRef / 是 | 单公开目标，可文字锚点 | 实例；重排影响几何，改字影响锚点 |
| trigger | 对象 / 是 | {beatId,edge,offsetMs}；edge=start/end，offset 整数可负 | 实例意图；解析 start 不得<0 |
| durationMs | 整数 / 可缺省 | 风格动作默认；≥0；动作值优先风格 | 实例已确认值；时间 |
| easing | 枚举 / 可缺省 | 风格默认；linear/ease-out-cubic | 风格默认，实例可选公共缓动 |
| endPolicy | 对象 / 是 | 各动作所列，不用缺省猜保持时长 | 实例时间意图 |

linear(p)=p；ease-out-cubic(p)=1-(1-p)^3，p 夹到 [0,1]。trigger 在解析时变成 startMs；
负偏移允许表达视觉提前，但解析越过页起点报 TIMING_OUT_OF_RANGE，不自动截为 0。
不存在 beat → MISSING_REFERENCE；未接音频 → UNRESOLVED_TIMING。

## DEF-REVEAL / action.reveal

语义：透明度从 0 到 1，布局占位不变，不增加位移/缩放。通道 visibility.opacity；
target 必须是整体 part，不接受文字/资源子锚点。没有该目标 reveal 时基础 alpha
来自 initialVisibility；只要安排 reveal，该有效目标在动作开始前 alpha=0。

start≤t<start+duration：alpha=ease(progress)；duration=0 时 t≥start 即 alpha=1；
结束保持 alpha=1 至页末，endPolicy 必须 `{kind:"keep-to-page-end"}`。
首轮同一目标最多一个 reveal，重复报 ACTION_CONFLICT；不提供消失动作。
Concept.self 的 opacity 与 part opacity 相乘；保留布局不意味着隐藏内容能接收交互，
预览隐藏目标不参与直接点击选择，编辑器仍可在结构列表选中。
输出为时刻可见度；支持原子与概念公开整体；无持续几何变化。
正常 action.reveal-html；非法对 asset-anchor reveal → TARGET_CAPABILITY。
验收 C15/C16/C22/C23/C27；PPTX 本期只转快照，原生动画未支持。

## DEF-HIGHLIGHT / action.highlight

语义：独立强调覆盖层，不改文字、字体、原始素材及可见度。通道 emphasis；
params 可缺省 `{mode:"outline",colorRole:"accent"}`，mode=outline/background，
colorRole=accent/highlight；公共 style stroke.width 使用风格值，不任意写 CSS。
background 仅文字目标可用，覆盖放在文字之后的视觉背景层，不盖住原文。

从 start 到 start+duration 覆盖层 alpha 从 0 到 1；此后保持至 endPolicy 指定边界，
在边界恢复基础（alpha=0）。endPolicy 为 `{kind:"restore-at-beat-end",beatId}`
或 `{kind:"restore-at-page-end"}`；结束必须≥start+duration，否则报范围错误。
activeEndMs 与 effectEndMs 均为恢复时刻；动画过渡后保持期也属于本通道占用，
同目标重叠强调报 ACTION_CONFLICT。隐藏目标仍隐藏，强调不能替代 reveal。
正常两概念在第三语块强调；非法强调尚未出现对象不会让其出现，返回遮蔽警告。
验收 C16/C22/C23/C27；输出可截图，原生 PPTX 以后独立映射。

## DEF-ANNOTATE / action.annotate

语义：新增标注层，不改原文字/图像。通道 annotation（首轮一个目标一次只能有一笔方案）；
params 必填，shape=underline/outline、colorRole=accent 必填，strokeWidth 可缺省；
strokeWidth>0 且符合风格 overrideRules 的 stroke.width；未显式宽度时也可缺省继承风格。
underline 仅文字 part/文字锚点；outline 接整体/文字/图片锚点。

多行 underline 每行一段，由分行矩形的下边生成；outline 每个可见 polygon 一条闭线。
标注完全跟随目标裁切；绘制顺序按阅读行顺序（首轮 zh-CN 横排）及每线左到右。
路径按总弧长分配进度，非按点数；没有几何则阻断，不用近似整页框代替文字范围。

start 前无笔画；start≤t<drawEnd=start+duration 根据进度取路径前缀；结束保持全部笔画
至 endPolicy。允许 `{kind:"keep-to-page-end"}` 或 `{kind:"remove-at-beat-end",beatId}`，
后者边界移除且必须≥drawEnd。duration=0 立即完整显示。activeEndMs=drawEnd，
effectEndMs=保持结束；P01 为避免混乱，同目标 annotation 在整个 effect 区间内不许重叠。
正常 action.annotate-control；文字无几何或 anchor 过期 → TARGET_UNRESOLVED/STALE_ANCHOR。
验收 C06/C07/C14/C22/C23/C27。

## 统一冲突与求值

有效目标键=nodeId+part+规范化 selector；同一 part 的相交文字范围写同通道同样冲突。
不同通道可并行；父/子 visibility 相乘是规定合成，不是错误。父/子强调不互相覆盖数据，
但视觉遮挡仍需检查。相邻区间 [start,end) 不重叠，边界先结算前段再应用后段。
零时长且同刻的同通道写入无法唯一求值即报冲突，首轮不引入人工播放先后列表。

reveal 结束保持值作为后续基础；highlight 在保持期占用；annotate 按 effect 区间限制，
三者明确区分“绘制完成”和“效果结束”。每次由输入 t 重新求值，回退不保留未来状态。
修改动作重编时间/画面；不改基础排版/原音频。超页动作必须报错或作者显式延长页时长。
预期区间见 [样例说明](examples/README.md)，文档算术检查不能替代浏览器播放验证。
