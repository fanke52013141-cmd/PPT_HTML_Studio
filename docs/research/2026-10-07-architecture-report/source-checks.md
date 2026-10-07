# 一手来源核对与报告修正

档案：RES-20261007-01。核对日期：2026-10-07。
方法：对照官方文档、项目维护者仓库与论文；未做源码全量审计或本机性能实验。
链接指向核对时的公开页面，部分主分支/文档会变化；正式接入前应固定版本或提交并复核。
不以星数、第三方宣传或报告中的绝对化表达作为选型证据。

## 1. 来源目录

| 来源编号 | 一手资料 | 此次确认的范围 |
| --- | --- | --- |
| S01 | [Remotion 基础](https://www.remotion.dev/docs/the-fundamentals) | 以帧号表达视频中的状态 |
| S02 | [Remotion 渲染等待](https://www.remotion.dev/docs/delay-render) | 有显式等待/继续机制，并非只能靠固定延时 |
| S03 | [HyperFrames 引擎](https://hyperframes.heygen.com/packages/engine) | seek、chrome-headless-shell 与 beginFrame 捕获；底层引擎接入不等于应用全套方案 |
| S04 | [HyperFrames 确定性约束](https://github.com/heygen-com/hyperframes/blob/main/skills/hyperframes-core/references/determinism-rules.md) | 作者代码也需遵守时间、随机、资源、布局等约束 |
| S05 | [Slidev 自定义布局](https://sli.dev/guide/write-layout) | 自定义布局与命名插槽 |
| S06 | [Slidev 动画](https://sli.dev/guide/animations) | 点击步序和默认透明度显隐机制 |
| S07 | [PPTist AI 页面结构](https://github.com/pipipi-pikachu/PPTist/blob/master/doc/AI_PPT_SCHEMA.md) | 官方数据结构说明，含坐标/文本等属性；不等于所有运行校验已证明 |
| S08 | [VideoLingo 发布记录](https://github.com/Huanshere/VideoLingo/releases) | 语音识别、对齐与字幕处理是版本相关的工作流 |
| S09 | [WhisperX 官方项目](https://github.com/m-bain/whisperX) | 对齐使用语言相关模型，存在缺少时间戳等限制 |
| S10 | [WhisperX 论文](https://arxiv.org/abs/2303.00747) | VAD 与强制音素对齐的技术依据 |
| S11 | [Manim Voiceover 快速开始](https://voiceover.manim.community/en/stable/quickstart.html) | 可在旁白词语位置插入书签 |
| S12 | [Manim Voiceover API](https://voiceover.manim.community/en/stable/api.html) | 旁白持续时间、剩余时间与等待书签接口 |
| S13 | [MuseTalk 官方项目](https://github.com/TMElyralab/MuseTalk) | 潜空间口型修复路线；公开速度绑定具体硬件和条件 |
| S14 | [Linly-Talker 官方项目](https://github.com/Kedreamix/Linly-Talker) | 多模型集成的数字人对话系统；不直接证明报告中的低延迟指标 |
| S15 | [Rhubarb 官方项目](https://github.com/DanielSWolf/rhubarb-lip-sync) | 输出口型序列；非英语识别有不同路径与精度限制 |

## 2. 需要修正或保留疑问的结论

| 编号 | 原报告位置/主张 | 核对与判断 | 本项目处理 |
| --- | --- | --- | --- |
| COR-01 | 第一部分：任何环境/负载都输出像素一致 | S03/S04 没有支持无条件跨环境保证；作者约束与资源环境仍重要 | 记录环境，先验证固定环境的重复渲染；跨环境单独测量 |
| COR-02 | 第一部分：React diff 在高并发下造成时序错乱 | 本次未获得直接支持此归因的官方证据；性能开销与输出正确性不能混为一谈 | 不因这个说法否定 Remotion；按同一场景比较 |
| COR-03 | 第一部分表格：Remotion 只靠轮询与启发式等待 | S02 有显式等待机制；该表格不足以公平比较 | 对实际适配器的就绪与错误行为做实验 |
| COR-04 | 第一部分：data-start/data-duration 就能定义所有运动 | S03 还涉及 seek 运行时；属性不自动替代动作求值器 | 动作语义属于场景层，属性仅为适配器编译形式 |
| COR-05 | 第二部分：少量插槽布局保证无限内容绝不崩坏 | S05 确认插槽能力，不提供这个保证 | 增加内容容量、字体、溢出、拆页与视觉验收 |
| COR-06 | 第二部分：PPTist 的严格 JSON Schema 杜绝所有越界 | S07 是页面结构资料；字段合法与内容能排下、美观是不同问题 | 本项目自行定义正式 Schema，另做语义和几何校验 |
| COR-07 | 第二部分：slidev-addon-studio 可完整拖拽回写 Markdown | 本次没有足够可追溯一手证据确认该具体插件与完整能力 | 标记待核实；只吸收编辑器回写思路 |
| COR-08 | 第三部分：强制对齐解决图像粘连切分 | S09/S10 处理语音与文本时间；不会生成图像对象边界 | 使用独立素材/HTML 目标；音频对齐单独负责时间 |
| COR-09 | 第三部分：字/句时间戳精确到毫秒、音画绝不偏移 | 时间表示精度不等于测量准确率；S09 明列词典、重叠语音与语言模型限制 | 中文实测、质量状态、人工修订与句级降级 |
| COR-10 | 第三部分：VideoLingo 使用 Aeneas；第五部分固定服务组合 | S08 能确认工作流参考，未充分确认报告中的固定组合 | 不把 Aeneas 记成该项目的已证实核心依赖；接入前查固定版本 |
| COR-11 | 第四部分：MuseTalk 的音频特征/NeRF 泛化描述 | S13 的官方模型说明是潜空间修复，并以 Whisper 编码音频；不能归为 NeRF | 按真实模型接口评估，不照报告实现描述重写 |
| COR-12 | 第四部分：Linly-Talker 提供已证明的 WebRTC 超低延迟双工 | S14 可确认集成路线；本次未验证相应传输实现和端到端延迟 | 当前离线产品不因此引入实时传输 |
| COR-13 | 第五部分：videoTime 等于开始时刻即改变 opacity | 这是算法问题：采样不一定命中等值；单次事件也不能可靠倒退 | 改成指定时刻的区间/进度求值 |
| COR-14 | 第五部分：CSS 简单抠除绿幕，模型产物可直接透明 | 没有支持默认透明输出的充分证据；普通 CSS filter 不具备通用色键抠除语义 | 单独选择抠像/合成方案并验证媒体格式 |
| COR-15 | 第五部分：可十倍速且不会丢帧 | 没有本项目场景和硬件测量 | 记录正确性、耗时、内存与成本，速度不能替代正确性 |

报告对资源的原话提供“base64 内联或严格监听加载”两种路径，不能误读成强制全量内联。
本项目进一步把资源完成状态细化为下载、解码、字体与媒体就绪，并比较打包策略。

## 3. 尚未解决的核对事项

- `markdown-to-zundamon`、`remotion-voicevox-template`、`talking-avatar-with-ai`
  的具体作者、仓库与版本未由原文提供，本次不把它们记为已验证依赖。
- 既有 `html-ppt-skill`、`guizang-ppt-skill`、`ppt-master` 的视觉模板研究是另一项工作；
  本报告未充分覆盖它们，本次不能宣称已完成其代码/视觉比较。
- 所有候选的安装、Windows/GPU 兼容、成本、许可与生产性能均未通过本次文档核对验证。
- 首轮接入前补充候选提交/发布版本、浏览器与模型版本；有差异时追加决策，不修改原文。
