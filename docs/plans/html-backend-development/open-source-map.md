# 开源借鉴定位表

2026-10-08 核验。以下为本轮开发需要的参考，不是要求安装四套系统。固定提交避免执行 Agent 跟随上游变化。文件读取记录见[source-evidence.json](source-evidence.json)。不沿用上游视觉风格、品牌、固定文字或未经核验的性能结论。

## OSS-01：公共样式与主题分离

项目：[html-ppt-skill](https://github.com/lewislulu/html-ppt-skill)，MIT，固定 `fd1629067909ff55b36b905476de4e5f26062a1f`。

源码：[assets/base.css](https://github.com/lewislulu/html-ppt-skill/blob/fd1629067909ff55b36b905476de4e5f26062a1f/assets/base.css)、[assets/themes/swiss-grid.css](https://github.com/lewislulu/html-ppt-skill/blob/fd1629067909ff55b36b905476de4e5f26062a1f/assets/themes/swiss-grid.css)、[references/authoring-guide.md](https://github.com/lewislulu/html-ppt-skill/blob/fd1629067909ff55b36b905476de4e5f26062a1f/references/authoring-guide.md)。

借鉴 base/theme 分层、先提纲再选结构的编排方法。落点 A01–A03：公共组件消费主题参数、模板选择独立于色系。不能复制 Swiss Grid 外观替代用户的科普参考，也不把其所有模板当作本系统已支持。验收 AC02、AC03：同一内容/结构更换主题只改变外观，不更改对象 ID、语义和时间绑定。

## OSS-02：布局槽位与真实渲染校验

项目：[guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill)，**AGPL-3.0，非 MIT**，固定 `c91369c449d34755d320a8b81d0734000d99d1ab`。

源码：[references/swiss-layout-lock.md](https://github.com/op7418/guizang-ppt-skill/blob/c91369c449d34755d320a8b81d0734000d99d1ab/references/swiss-layout-lock.md)、[scripts/validate-swiss-deck.mjs](https://github.com/op7418/guizang-ppt-skill/blob/c91369c449d34755d320a8b81d0734000d99d1ab/scripts/validate-swiss-deck.mjs)。后者重点阅读 `runRenderedMeasurements`、`overflowFix` 及 `data-image-slot` 检查。

借鉴布局注册、资产槽位、静态检查加真实浏览器测量的思路；本轮独立实现，不直接移植 AGPL 源码。落点 A03、C04：容量/溢出/覆盖检测与诊断。不要抄其 Swiss 专属比例、标题规则、21:9 约束；不能以字体等待超时或缺少浏览器跳过测量后仍报告通过。验收 AC03、AC06、AC10。

## OSS-03：预览与导出运行时一致

同上项目及许可。源码：[scripts/check-presenter-runtime-sync.mjs](https://github.com/op7418/guizang-ppt-skill/blob/c91369c449d34755d320a8b81d0734000d99d1ab/scripts/check-presenter-runtime-sync.mjs)。

借鉴校验运行时是否一致的思路，独立实现 bundle/version/hash 对照；不复制两份运行时再靠人工同步。落点 A04、E01；验收 AC05、AC14：同一包、同一时间点、同一字体与资产，在同一浏览器环境的预览截图与导出帧一致。

## OSS-04：关键帧先行与对象过程编排

项目：[huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion)，MIT，固定 `26dba25b2b495c2138848c29a2c90df356a20325`。

源码：[references/03-一帧先行四条路线.md](https://github.com/alchaincyf/huashu-art-motion/blob/26dba25b2b495c2138848c29a2c90df356a20325/references/03-一帧先行四条路线.md)、[references/09-视频动画语法.md](https://github.com/alchaincyf/huashu-art-motion/blob/26dba25b2b495c2138848c29a2c90df356a20325/references/09-视频动画语法.md)。

借鉴先看关键画面再编排、按讲解语义选择过程/关系/数据表现。落点 C01、C02、D01：初始/关键过程/终态与完整对象清单，包含最终消失的过渡对象。终态图不能替代完整资产清单，不要求每页生成两张图，更不引入绿幕或 AI 视频作为必经步骤。验收 AC07、AC11。

## OSS-05：确定性时间与逐帧导出

同上项目。源码：[scripts/engine/engine.js](https://github.com/alchaincyf/huashu-art-motion/blob/26dba25b2b495c2138848c29a2c90df356a20325/scripts/engine/engine.js) 的 `renderFrame(t)` / `layersAt(t)`；[scripts/engine/clip.js](https://github.com/alchaincyf/huashu-art-motion/blob/26dba25b2b495c2138848c29a2c90df356a20325/scripts/engine/clip.js) 的 `draw(c,t,ctx)` 和资源就绪边界；[scripts/engine/render.py](https://github.com/alchaincyf/huashu-art-motion/blob/26dba25b2b495c2138848c29a2c90df356a20325/scripts/engine/render.py) 的浏览器逐帧至 FFmpeg；[scripts/engine/lib/motion.js](https://github.com/alchaincyf/huashu-art-motion/blob/26dba25b2b495c2138848c29a2c90df356a20325/scripts/engine/lib/motion.js) 的纯时间运动计算。

落点 A04、D01、E01。优先复用本项目已有 timeline/easing/resources 能力，只补缺口。不移植其整套 Canvas 引擎、不照搬 eval/同步 XHR/关闭浏览器安全的启动方式，不引入自动年份标签。涉及直接复制片段时另核该片段及其依赖许可并保留声明。验收 AC05、AC11、AC14。

## OSS-06：PPTX 能力矩阵与降级报告

项目：[ppt-master](https://github.com/hugohe3/ppt-master)，MIT，固定 `2d72da616cf9fa40d4dcaf59fd4c980ecf534b7d`。

源码：[docs/powerpoint-svg-mapping.md](https://github.com/hugohe3/ppt-master/blob/2d72da616cf9fa40d4dcaf59fd4c980ecf534b7d/docs/powerpoint-svg-mapping.md)：原生稳定能力、文本/形状/图表映射及不支持效果的处理边界。

落点 E03、E04：建立本系统自己的 `native/rasterized/unsupported` 导出表，声明快照与原生编辑能力，按对象 ID 生成降级清单。不是把整个生产链改成 SVG→PPTX，也不是导入它的音频或模型方案。E04 开始时再核验选用转换器源码、版本及依赖；本次没有宣称核验过完整转换器。验收 AC16。

## 已有项目直接复用，不再寻找替代

原应用的项目、身份、任务、TTS、时间轴、音频确认、数字人、作品登记、原图片 Remotion 路线继续使用。具体文件见[任务表](tasks.md)。HTML 导出采用共享浏览器渲染器生成基础视频，再进入既有数字人和作品登记链。已有 Remotion 是原应用依赖，不要求本轮引入新的 Remotion 场景实现。

已有研究 HBA-01/02/03/04/05/06/07/08/09 分别对应主题、结构化计划、资产/模板分层、槽位、校验、时间几何、导出分级、局部重做和最小模型输入；AM 系列对应关键帧/对象/动作/动态审查。参考原 `docs/research/2026-10-07-skill-and-workflow-reports/` 与 `docs/research/2026-10-07-huashu-art-motion/`，不把报告中所有建议都变成强制依赖。

本轮默认采用方法借鉴和独立实现。任何第三方代码引入均须记录固定提交、文件、修改说明、许可证及必要 NOTICE；许可未明确不得先复制再补。无需为了借鉴重新安装整套开源项目。
