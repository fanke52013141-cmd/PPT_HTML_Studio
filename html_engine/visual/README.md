# 阶段一：共享视觉定义与统一渲染

> 2026-10-08：用户明确否定本预览的简化视觉，状态 changes_requested。技术结果保留；柔和彩色科普风格并未完成。请先查看[按原参考补齐的实际风格样板](style-review/index.html)，不得依据此工程稿直接扩展生产流程。

已实现独立格式 0.1.0；[定义卡](../../docs/contracts/html-presentation/runtime/visual-v1/README.md)是本模块的归属契约。预览：[打开两个复用案例](preview/index.html)。这不是应用级 HTML 后端，原图片路线与 E1/E2 保持原样。

## 哪些公用，哪些属于风格

组件代码只认识 text/badge/label/image/arrow/annotation，不认识杯子、蒸发或某一套颜色。文字通过 CSS 排版，箭头与圈注通过 SVG 绘制，主体通过固定 PNG 资产加载。Canvas 在此仅用于既有资源透明边界检查；本阶段没有为装饰增加 Canvas 动画。

风格包是以下已登记属性的集合。换内容不用改它，换风格也不用复制组件：

| 属性 | 当前字段 | 影响 |
| --- | --- | --- |
| 身份/兼容范围 | id、version、compatibleLayouts | 明确版本，拒绝不兼容布局 |
| 字体环境 | font.family、platform | Microsoft YaHei / Windows；缺字体阻断，不默默回退 |
| 色彩角色 | colors.background/ink/body/accent/blue/green/muted/panel/pinkWash/blueWash/greenWash/line | 组件按语义取色；部分角色预留于当前科普色板，未声称已有全部对应效果 |
| 文字角色 | text.eyebrow/title/lead/stepTitle/body/phase/callout/conclusion/source/subtitle/number | 各有 size、weight、lineHeight、letterSpacing、color |
| 形状 | shapes.badgeRadius、labelRadius | 相同编号/标签组件的外观变化 |
| 矢量线条 | shapes.strokeWidth | 箭头、圈注和引线宽度 |
| 阴影 | shapes.shadow.y/blur/opacity | 色彩取 ink，位移/模糊/透明度均为有界数字 |
| 插画规则 | illustrationPolicy | 生产时配图约束，仍需人工审阅；不是自动审美判断 |

风格包没有坐标、课程正文、资产锚点和播放顺序；实例没有自由 CSS 覆盖。字幕字号是作品预览参数，20—44，独立于正文。实际字幕颜色/字重/行高来自风格，默认字号32；不改变固定底部区域。

完整体系里的渐变、图标集、组件变体、风格动作默认值、字体文件分发可以以后登记；本轮没有这些字段，也不接受用任意 CSS 字符串补进去。主题并非规范的另一套实现，它只能选择公共规范已实现的属性和能力。

## 四份源定义如何组合

1. [布局包](layouts/object-right.json)给出槽位 box、maxLines、align、z；另一个[布局](layouts/object-left.json)交换主体与讲解位置，保留标题与字幕的角色。坐标是1600×900逻辑单位，内容不得进入y≥800字幕区。
2. [风格包](themes/soft-science.json)提供外观。[中性主题](themes/neutral-science.json)仅作风格切换证据，尚未得到视觉批准。
3. [实例](scenes/condensation.json)选择版本引用、填写对象和文字、分段强调、enter 动作和字幕语块。[蒸发实例](scenes/evaporation.json)更换内容、布局、主体和锚点，组件代码完全相同。
4. [资产登记](assets.json)固定已有PNG哈希、版本、来源和原图像素锚点。构建生成自然尺寸、透明边界与归一化锚点，运行再次验证哈希/解码/尺寸/边界。

构建得到离线资源包，编译器检查定义，渲染器测量实际字体容量，再原子替换已就绪画面。派生结果不是另一份源定义；不要手工修改 preview/player.js、data.js 或 generated 下文件。

## 运行、修改与新增

在 html_engine 目录执行：

```powershell
node visual/build.cjs
node visual/tests/verify.cjs
```

然后打开 preview/index.html。可选择内容、主题，播放/暂停/拖动、查看终态、改变字幕字号。JSON编辑仅在当前浏览器会话应用，不自动写回仓库；无效输入保留旧场景。磁盘修改源文件后必须重新构建、刷新预览。

新增内容：复制实例数据，保持登记节点类型，选择容量适合的布局，填入时间与字幕；不复制 HTML。新增布局：新增布局包，在主题兼容表登记并重新验证。新增风格：新增主题包，引用已有组件/布局，补视觉审阅与参考图；不得将场景坐标搬进主题。新增资产：登记独立主体文件/固定哈希/锚点/来源；不通过放宽图片预算凑整页。

资源版本不可在已发布身份下悄悄换像素。当前局部版本只接受0.1.0；后续升级须显式更新Schema和迁移说明。此处没有兼容全部P01能力，也不把E2作者配方自动转换到新格式。

## 已验证与限制

[验证记录](evidence/verification.json)覆盖两个内容、两个布局、两个主题、随机跳转像素一致、运动锚点与两种窗口大小、文字容量失败、恶意文字按文字显示、无效资源保留旧画面、字幕字号与区域、播放暂停。终态截图：[冷杯](evidence/condensation-final.png)、[蒸发](evidence/evaporation-final.png)。截图是实际渲染证据，不是新生图；新增图片生成次数为0。

当前能力：单场景、固定镜头、最多一张独立主体、CSS文字与标签、SVG箭头/圈注、透明度与平移入场、统一时钟。没有连续流体/角色动画、群组/镜头/旋转缩放、任意路径、自动排版、应用数据库编辑、自动生成流程、音频/数字人接入或视频/PPTX导出。未来导出必须直接驱动同一 renderAt，不能另造一个视频布局。

容量和区域检查是技术门槛；局部遮挡、插画边缘质量、小屏观看及整体美感仍须人工审阅。冷杯实验获用户“还OK”的限定反馈，这不等于所有新布局/主题均已批准。本阶段是在既有构图上固化可复用工程，不新增一轮任意生图来替换已验证目标。
