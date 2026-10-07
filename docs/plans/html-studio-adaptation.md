# HTML 课程演示系统：复用边界与实施方案

HTML 体系的现行规范入口为 [项目契约](../contracts/html-presentation/README.md)。
本文件说明原项目复用与接入范围；发生定义变化时以契约目录同步维护，不在计划稿中
另建一套生产规则。

## 当前状态

2026-10-07：从本地在用源码建立独立副本，保留工作树源码快照，安装独立 Python 与 Node 依赖。此阶段只准备基线并研究复用，不实现新的业务流程。来源工作树内未提交改动并不等于已验收功能，需要在后续相关模块开发前验证。

## 一套应用框架，两种画面实现

课程/章节/项目管理、文章、讲稿、音频、字幕、数字人对接、任务状态和作品管理组成公共应用层。图片与 HTML 各自实现画面规划、构建、预览和导出准备，通过统一场景与时间接口交付下游。

建议后续新增独立的画面实现字段，例如 `visual_backend: image | html`。它与现有 `presentation_mode: full_frame | reveal` 的含义独立，不能把制作方式、画面实现和呈现方式混在一个开关中。该字段需要数据库迁移、Agent 契约同步、进度与失效规则注册，本次尚未添加。

## 逐模块复用

| 用户能力 | 当前代码入口 | HTML 路线的处理 |
| --- | --- | --- |
| 课程、项目、配置 | `course_service.py`、`project_service.py`、`creation_config_service.py` | 复用框架，扩展画面实现与风格包配置 |
| 演讲稿与分镜 | `storyboard_planning.py`、`storyboard_service.py`、`visual_contract_service.py` | 保留讲稿、稳定 ID 和内容映射；新增结构化组件、布局、资源和讲解动作 |
| 图片与风格 | `image_workflow_service.py`、`project_style_*`、`ai_provider_service.py` | 整页生成另接 HTML 场景编译器；图片生成继续用于插画、背景和图示图标，不能沿用统一白底归一化到所有素材 |
| AI Mask 与揭示 | `ai_mask_*`、`mask_manifest_service.py`、`scripts/build_reveal_scene.py` | 图片路线保留；HTML 路线直接消费元素 ID 与分组，替换像素分割与 RLE，不伪造旧 Mask 产物满足门禁 |
| 勾画 | `annotation_target_resolver.py`、`annotation_text_layout.py`、`annotation_geometry.py`、`annotation_timeline.py`、`static/annotation_playback.js` | 保留标注动作、几何与时间概念；新增 DOM/SVG 定位来源，逐步替换 OCR 定位 |
| 音频、字幕 | `narration_audio_service.py`、`tts_service.py`、`tts_provider_service.py` | 复用生成、确认与时间轴；以旁白语块绑定 HTML 对象，兼容原图片语块 |
| 数字人 | `digital_human_client.py`、`digital_human_routes.py`、`digital_human_service.py` | 复用推理接入与视频合成思路；适配新场景时长、构图安全区、任务与输入哈希 |
| 视频输出 | `video_render_service.py`、`remotion_runner.py`、`scripts/build_remotion_props.py`、`scripts/remotion/src/Video.tsx` | 保留任务和产物管理；现有图层类型仅为 PNG，需要新增 HTML 画面渲染适配 |
| PPTX 输出 | `pptx_service.py`、`pptx_export.py`、`pptx_reveal_export.py` | 保留任务管理；图片型导出和原生对象导出分开实现 |

## 统一场景契约

后续设计中，每页场景至少包括：画布、稳定对象 ID、组件类型与内容、布局、风格包版本、资源引用、旁白语块映射、讲解动作。排版完成后产出可重复查询的对象几何和文字片段几何；音频生成后再绑定动作时间。

结构化场景是编辑与导出的主要数据，HTML 是预览与视频画面的渲染产物。保存 HTML 不应丢弃原始组件数据，否则后续换风格、重排和导出 PPTX 仍需要逆向分析页面。

### 勾画定位的具体边界

DOM 元素定位可用元素矩形，句内短语可用文字 Range 的多行矩形；坐标必须换算到设计画布，并考虑缩放、字体加载和变换。布局改变后重新计算几何。任意插画内部的对象仍不能由 DOM 自动定位，应采用独立素材、作者提供的锚点或图像标注。

### 视频适配

所有动画必须能根据给定时间或帧号求出状态，支持重复取帧与任意跳转；不用依赖墙钟播放的动画作为唯一实现。HTML 浏览器逐帧渲染与组件直接进入 Remotion 都是候选路线，先以实际画质、字体一致性、导出速度和单页复杂度比较后选择，不在此阶段承诺任意 HTML 能直接进入现有 PNG 渲染器。

### PPTX 能力边界

1. 图片型 PPTX：将每页最终 HTML 渲染成图片，可较早适配现有导出器，页面内容不具备原生文字编辑能力。
2. 分步快照 PPTX：每个讲解状态变成一页，类似现有 `pptx_reveal_export.py` 的逐页累积图片机制；这不等于 PowerPoint 原生对象动画。
3. 可编辑 PPTX：从结构化场景把受支持的文字、图片、形状、路径映射为原生对象；复杂 CSS、滤镜和复杂插画允许局部栅格化。动画须单独映射支持集，并标明差异。

## 风格与组件抽象

公共规范定义内容角色、组件数据、能力和布局/时间接口。风格包提供文字与颜色、线条与容器、素材画风、组件外观版本、组合限制和参考页面。组件按表达能力复用，风格增加配置与资产；有新职责才增加通用组件。布局保留参数、内容容量和适配范围。

吸收 `html-ppt-skill` 的主题/布局/动效资产划分、`guizang-ppt-skill` 的登记版式与素材槽位限制、`ppt-master` 的规范分工和插画素材板方法。它们是参考资源，不在当前阶段整体安装其生产工作流。

## 建议实施顺序与验收

1. 固定基线与数据隔离，保留来源和已有功能边界。本次进行这一阶段。
2. 先细化模块定义，再建设独立 HTML 内核：场景、组件、布局、风格、定位与确定性动画。先用一页概念对比和一种风格审阅效果，再用第二种风格验证复用，随后用真实内容扩展少量常用布局。详见 `html-foundation-roadmap.md` 和 `html-foundation-spec-v0.md`。
3. 不依赖原应用，先打通一页测试音频的真实 MP4；验证任意时间取帧、字体、画质与同步。PPTX 分图片型和原生对象支持集分别验证。
4. 再接入原分镜、音频时间轴、对象勾画与预览；验证重新排版、修改讲稿和调整动作时的最小失效范围。
5. 接入字幕、数字人安全区与合成、任务恢复和作品管理；完成应用内真实音视频验收。未经此验证不能宣称生产链路已完成。

后续业务改动必须同步原项目的迁移、Agent API、公共流程状态、产物哈希和 downstream impact 规则。图片专属门禁保留在图片路线，HTML 路线建立自己的有效性和完成条件。
