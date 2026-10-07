# 借鉴分析所依据的项目现状

核对日期：2026-10-07。目录：`D:\Program Files (x86)\PPT_HTML_Studio`。
当前本地应用是隔离的原图片项目基线；HTML 内核尚未实现。GitHub 当前发布范围以文档为主，
下表中的应用源码属于本地开发目录，并非全部已发布到远程。

核对方式：读取模块、接口、类型及相关调用；不运行 AI、音频/数字人推理和实际导出任务。
这是代码边界核对，不是功能验收。具体符号位置、文件哈希和本地提交状态记录在
[基线证据](baseline-evidence.json)，方便后续核对改动是否影响这些判断。

## 1. 已有基础与实际缺口

| 能力 | 当前代码证据 | 改造时复用 | 需要新增/适配 |
| --- | --- | --- | --- |
| 分镜及讲稿规划 | `storyboard_planning.py` 的 normalize/compose；`storyboard_service.py` 编排 | 讲稿、语块、内容单元、视觉元素和组映射 | HTML 组件、布局、风格、资源槽位与公开目标 |
| 风格上下文/参考 | `project_style_context.py`、`project_style_reference_service.py`、`global_image_style_service.py` | 项目选择、参考资源与来源 | 可执行 HTML token、支持矩阵、组合配方；不默认复用图片专属 Prompt |
| 生图接入 | `ai_provider_service.py`、`image_workflow_service.py`、`generation_governor.py` | provider 接入、配置、调度和并发边界 | HTML 的独立素材任务/产物引用，不把每个素材算一整页 |
| 本地/云端语音 | `tts_provider_service.py`、`tts_service.py`、`tts_artifacts.py` | 全部沿用 | 无新增合成方案 |
| 音频时间与校准 | `narration_audio_service.py`、`annotation_alignment.py`、`annotation_provider_alignment.py`、`annotation_alignment_worker.py` | 音频产物、语块时间、实测词时间、现有对齐及人工修订 | HTML 动作消费这些时间和来源 |
| 揭示绑定 | `scripts/bind_reveal_timeline.py` | 语块引用、视觉提前量、音频起点和派生时间的概念 | HTML 目标适配、稳定 ID 与最小失效 |
| 勾画 | `annotation_target_resolver.py`、`annotation_geometry.py`、`annotation_timeline.py` | 目标/范围概念、几何和动作时间边界 | DOM/SVG 的几何测量来源，替换 HTML 分支的 OCR |
| 视频输出 | `video_render_service.py`、`remotion_runner.py`、`scripts/remotion/src/Video.tsx` | 任务、产物、编码器和帧驱动基础 | SceneLayer 目前为 PNG，需要新的画面表示/适配 |
| PPTX 输出 | `pptx_export.py`、`pptx_reveal_export.py`、`pptx_service.py` | 导出任务、图片型/逐步快照和产物确认 | HTML 截图接入；受支持对象原生转换另行实现 |
| 数字人 | `digital_human_service.py`、`digital_human_client.py`、`digital_human_routes.py` | 用户已明确整套复用 | 只验证新画面的构图、时间与合成兼容 |
| 任务/失效/接口 | `impact_registry.py`、`project_impact_service.py`、`repository_paths.py`、`agent_contract/` | 已有所有权、路径、指纹和同步体系 | 登记 HTML 输入与产物依赖；新增数据走已有迁移流程 |

## 2. 时间轴的现有事实

`scripts/remotion/src/Video.tsx` 定义 `{id, start, end, text}` 的 TimelineSegment，
通过当前帧与 fps 求动作进度，SceneLayer 的 `type` 当前限定为 `png`。
因此“必须从无时间轴的录屏改用 Remotion”不是本项目当前状态。

`scripts/bind_reveal_timeline.py` 从音频 segments 读取时刻，处理语块关联、视觉提前量、
`audio_start_sec` 和动作结束范围。它还包含按顺序推断关联的旧回退；新 HTML 后端应
明确稳定语义引用，不能把这个回退理解为任意重排都能安全保留原绑定。

`annotation_provider_alignment.py` 校验 provider 的实测词区间与完整朗读顺序，
明确不把多字词拆成编造的逐字时间。`annotation_alignment_worker.py` 的当前适配是
`Qwen/Qwen3-ForcedAligner-0.6B`，并记录固定模型修订及输入缓存键。
`annotation_alignment.py::resolve_anchor_times` 对历史 `whisperx_*` 引擎结果返回未解析，
保留现有迁移边界；人工校准另有自己的路径。

这些证据说明应复用当前时间链路。本机 worker、模型文件和运行质量需要在实际接入时
核实，本次不会因读到代码就宣称字级对齐在所有音频上通过。

## 3. 模板资产假设不能作为前置

对工程目录中的 `.pptx`/`.idml` 进行了文件盘点，排除 `.git`、依赖环境和运行数据目录；
未发现可直接作为本次布局来源的模板资产。这个范围没有扫描整台电脑，不能据此断言
用户完全没有模板。当前采用手工设计样板 → 抽象布局/配方的路线，不要求先导入未知模板库。

同样，报告关于 `tencent-pptx` 已在本机安装的描述没有提供适用于本项目的可确认路径；
不将其设为必需依赖，不根据这句描述自动安装 Skill 或调用其命令。

## 4. 接入必须遵守的现有边界

- 原图片后端的 OCR、Mask、图层和确认链继续有效；HTML 单独声明自己的完成条件。
- 业务变化产生下游影响时，登记现有 impact registry；只重算最小影响范围。
- 新路径走 `repository_paths.py`；持久化走数据库迁移；Agent/API 与界面状态同步。
- 新生产 Prompt 使用项目规定的 optimize-prompts 流程；本次只改研究文档。
- 本次不替换模型、服务、任务数据库或桌面启动入口。
