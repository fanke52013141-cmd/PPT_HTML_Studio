# B 线交付：标准库实内容样页与生产映射建议

日期：2026-10-10（Asia/Shanghai）
工作目录：`D:\software\PPT_HTML_Studio`
基线 HEAD：`7499e4a5b4f40842f6dd4d559a8067550b15a86e`
分支：`main`。开始时工作树干净；过程中发现 A 线在其登记范围新增了 `interface-baseline.md`、`ownership.json` 和 `integration-status.md`，本交付没有修改这些文件。未切换分支、reset、clean、stash、全仓暂存、commit、push，也未启动应用服务。

## B01：标准库 1.0 核对

本轮构建并核对现行 `standard/` 入口，范围与交接记录相符：24 张 1920×1080 黑白灰参考页、32 项基础组件、16 项呈现变体、28 项静态效果、18 组静态组合、5 种字体。稳定 ID、父组件归属、PNG 页清单、尺寸、源码/截图哈希及离线渲染由标准验证链检查。五种字体在本机 Edge/Chromium 中均可用；Noto Sans SC、Noto Serif SC 对实际中文字形有 CDP 平台字体证据。字体没有随参考库打包，结论只适用于本机环境。

`palettes.json` 中清爽多彩、温暖编辑、冷静科普三套颜色保持为独立 theme 输入，每套有 primary、secondary、accent、category 角色。基础标准页继续是中性灰阶。水循环与纸飞机样页都通过三套 palette 重渲染；角色色不同，文字、组件身份及几何不变，没有把所有组件涂成一个颜色。

## B02：内容样页与职责

独立查看入口：[样页 HTML](../../../../html_engine/reference-library/samples/index.html)。工具栏可切换两个主题与三套配色。截图仅截取实际 1920×1080 页面，不含工具栏。

| 页面 | 来源及使用范围 | 图文职责 |
|---|---|---|
| 水的状态变化 | 使用仓库已有 `html_engine/recipes/course-everyday.recipe.json` 中的湿衣物蒸发、冷杯凝结内容，并保留 USGS 的[蒸发来源](https://www.usgs.gov/water-science-school/science/evaporation-and-water-cycle)和[凝结来源](https://www.usgs.gov/water-science-school/science/condensation-and-water-cycle)。这是仓库内有来源的课程样稿，不标为用户确认课程。 | 文字、术语、相态方向、双向比较箭头和限定说明均为可编辑 HTML/SVG；两张既有独立 PNG 只表达水容器分子示意与冰水杯观察对象。正文明确图示不等于衣物实物图，水蒸气通常不可见。 |
| 纸飞机主题复用 | 使用 `html_engine/examples/paper-plane.scene.json` 已有标题、图层主题和资源，页面显式注明它是 E1 design-exploration 复用/容量测试，不是用户确认课程。 | 纸飞机、云层复用两张既有独立 PNG；示意轨迹、方向箭头、三处路径标签及素材职责说明为代码对象。轨迹注明不是实测飞行路线或空气动力学计算。 |

样页为静态构图，不含动效。每页均使用两项独立图片资产，未加新图或新生图调用；符合 HPS-036 对明确双对象比较/组合页最多两个主体的边界。页面与标准库输入均离线读取，没有请求远程资源。

## B03/B04：全尺寸检查、主题复用与容量

已查看最终全尺寸 1920×1080 PNG：

- [水循环 · 冷静科普](../../../../html_engine/reference-library/samples/output/course-everyday-science.png)
- [纸飞机 · 冷静科普](../../../../html_engine/reference-library/samples/output/paper-plane-science.png)
- [纸飞机 · 温暖编辑](../../../../html_engine/reference-library/samples/output/paper-plane-editorial.png)

六张截图（两页 × 三配色）及校验摘要见 `html_engine/reference-library/samples/output/`。工程截图不是用户审美签收，`userVisualApproval` 保持 `pending`。

全尺寸人工检查记录：

- 字阶：样页主标题 52px，二级标题约 29–34px，正文 21px，解释文字 15–16px，图注 14px。实际 Noto Sans SC 中文字形清楚；两页的标题与正文都保留为 HTML 文字。
- 留白：标题/导语与内容区分开；双对象页左右图片与解释平衡，中心只用一组方向提示。纸飞机页把大幅轨迹板与窄职责说明并置，图片不会取代结构文字。
- 边界与阅读顺序：页面内容落在 1920×1080 画布内；正文行、图片、路径标签均无越界或裁切；从标题→关系/过程→说明→限定脚注的阅读顺序清晰。
- 图文融合：既有透明素材置于低对比色面中；素材有独立图注，代码负责文字、状态与关系。图像仍保留自身蓝/红等颜色，配色仅驱动标注、局部浅色面、路径与边界。
- 身份/几何：三套角色配色重渲染后，`data-instance-id`、稳定组件 ID、文本及被测几何边界相同；仅对应色彩角色变化。实测 primary/secondary 颜色值互异。
- 容量：第二页主标题 33 个字符，最长说明 71 个字符，另有 3 个路径标签和 3 行对象职责；全尺寸不溢出。水循环页最长说明 52 个字符。容量结论只针对本静态布局与本机字体，不外推至任意字号、字体或 production scene。

样页试排时，第二页标题最初在“同/一”之间换行，影响词组连读；已统一主标题字号并让标题占用整行宽度后重排。该问题属于样页版式分配，标准组件外观源本身没有发现可复现的公共风格缺陷，所以本轮没有修改 `standard-library.css`/组件基础 CSS。六张截图在修订后重新生成。

## B05：提交 A 的生产映射提案

有足够工程证据提出映射方向，但当前不生成 scene fixture、不接共享 Schema/renderer，也不把静态样页写成 production template。

| 样页元素 | 可复用的现有公共能力 | 当前精确缺口/处理 |
|---|---|---|
| 标题、导语、术语、解释和限定 | V1 `text`/`label`/`header`/`card`；0.2.0 有文字角色、明确容量与测量。纸飞机标题 33 字低于现有 header 的 40 字限制；较长解释低于 card body 的 120 字限制。 | 样页实际用 Noto Sans SC；当前 V1 theme 字体字段锁定 Microsoft YaHei/Windows。字体与尺寸不能因截图相近而直接视作同一版式，生产主题须选已支持字体并重测容量和视觉。 |
| 蒸发/凝结双概念和相反相态方向 | 可组合 `text`、`label`、`card`、`summary`、`arrow` 等公共语义能力。 | 已注册 `explanation-cards-v1` 有一个 subject image 槽位与固定三卡结构；V1 0.2.0 的运行视觉定义保留单主体图片预算。水循环页需要两张独立图片与两个并列概念，不能塞进单张复合图或复用一个槽伪装兼容。建议新增通用、显式版本的 two-concept comparison 模板/布局，注册左右概念槽和最多两个 asset 对象、关系方向及容量；旧模板保持不变。 |
| 纸飞机、云层、路径与三处标签 | 可复用 `image`、`label`、`text`；清晰关系箭头可沿用已注册 `arrow`。 | 当前公共 node 没有 path/trajectory 数据对象；样页的曲线路径含三个控制点、箭头端和标签位置。不能把它近似转换为固定直箭头或硬编码到主题。若列为 production 能力，需由 A 定义受限的通用 path/trajectory 能力与坐标/标签锚定规则、容量和验证；否则此结构应返回模板覆盖不足。 |
| 三套独立 palette 角色 | 公共 theme 字段已有语义颜色角色，可供同一组件复用。 | `reference-library/palettes.json` 不是 V1 theme API。颜色映射需成为经注册的 theme 值；primary/secondary/accent/category 分别对齐公共角色，不能把配色名或颜色常量放入业务组件分支。 |

建议 A 按 HPS-023—025、HPS-035—037 更新对应定义卡/接口映射后，再安排新的模板版本、资产预算和生产验证。水循环比较页可作为首个映射候选；纸飞机页仅用于代码路径能力的差距验收。实现时继续分别记录定义、代码、工程、视觉与导出状态，并先取得新模板视觉审阅；不得把本轮 pending 样页登记为批准模板。

## 验证命令与结果

在 PowerShell 从仓库根执行；`HPS_CHROME` 指向本机 Edge Chromium：`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`。

| 命令 | 退出码 | 结果 |
|---|---:|---|
| `node html_engine/reference-library/build-components.cjs` | 0 | 生成组件板与三个主题配对；同时重建完整标准库 HTML。 |
| `node html_engine/reference-library/verify-components.cjs` | 0 | 32 组件、16 变体、28 效果、18 组合、三组主题配对；所有字体真实加载，零越界/页面错误/远程请求。视觉批准仍 pending。 |
| `node html_engine/reference-library/export-standard-library.cjs` | 0 | 导出 24 页 1920×1080 PNG、总览及 manifest。 |
| `py html_engine/reference-library/verify-standard-pixels.py` | 0 | 验证 24 页和总图的中性像素、尺寸、源和图像哈希。首轮发现当前 Pillow 没有 `get_flattened_data()`；已改为 `ImageChops` 通道差校验并通过。 |
| `node html_engine/reference-library/verify-samples.cjs` | 0 | 两页六图离线渲染；图片解码、字体、容量、边界、ID/几何稳定及配色角色断言通过。 |

`verify-samples.cjs` 保存实际 PNG 与 `verification.json`，并从 `palettes.json` 比较样页使用的三组 palette 数据。直接打开样页：`html_engine/reference-library/samples/index.html`。

## 状态与未完成项

- 定义：引用现有 HPS 规则，无新 production capability 定义。
- 参考库实现与工程验证：已通过本轮命令。
- 用户视觉批准：待用户查看两页 HTML/PNG 后给出结论；不以本轮人工构图检查代替。
- Production template/scene mapping：仅向 A 提交提案，未接入、未证明兼容。
- 未验证：真实生产 planner/scene 接线、应用入口、多页真实用户课程、动作/音频、导出、其他平台字体和正式素材审批。
