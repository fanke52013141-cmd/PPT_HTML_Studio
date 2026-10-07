# 来源核对、可用范围与报告修正

核对日期：2026-10-07。原报告 A/B 的行号按各自原始文本计数。
本次读取与实际改造相关的章节和现有代码；语音、数字人及训练部署细节不进入开发建议。
只核对选中机制的关键一手证据，没有对所有列举项目做全量源码审计、许可审计或性能测试。

## 1. 一手资料

| 编号 | 来源 | 确认范围 |
| --- | --- | --- |
| NEW-S01 | [html-ppt-skill](https://github.com/lewislulu/html-ppt-skill) | 基础样式、主题、布局、图片容器与真实预览的资产组织 |
| NEW-S02 | [主题 CSS](https://github.com/lewislulu/html-ppt-skill/blob/fd1629067909ff55b36b905476de4e5f26062a1f/assets/themes/swiss-grid.css) | 不仅有 token 值，也存在主题选择器样式，不能说纯参数就覆盖所有表现 |
| NEW-S03 | [guizang 静态/渲染检查器](https://github.com/op7418/guizang-ppt-skill/blob/c91369c449d34755d320a8b81d0734000d99d1ab/scripts/validate-swiss-deck.mjs) | 版式和图片槽位检查、渲染测量、错误与 warning、修复提示 |
| NEW-S04 | [共享运行时同步检查](https://github.com/op7418/guizang-ppt-skill/blob/c91369c449d34755d320a8b81d0734000d99d1ab/scripts/check-presenter-runtime-sync.mjs) | 多模板的一致性检查；本项目可优先采用同一公共模块避免副本漂移 |
| NEW-S05 | [ppt-master 技术设计](https://github.com/hugohe3/ppt-master/blob/main/docs/technical-design.md) | 可读设计与机器锁分工、显式结构和能力范围 |
| NEW-S06 | [ppt-master 能力映射](https://github.com/hugohe3/ppt-master/blob/2d72da616cf9fa40d4dcaf59fd4c980ecf534b7d/docs/powerpoint-svg-mapping.md) | 项目规范 SVG 与 PPTX 能力分级，不保证任意 SVG/HTML 转换 |
| NEW-S07 | [frontend-slides](https://github.com/zarazhangrui/frontend-slides/blob/9906a34d640d2111f724544cbc50f7f130569ae1/SKILL.md) | 固定舞台、真实预览和按需读取的参考方式；作为研究阅读，不执行其工作流 |
| NEW-S08 | [PPTAgent 论文](https://arxiv.org/abs/2501.03936) | 编辑式两阶段生成思路；论文指标不作为本项目验收指标 |
| NEW-S09 | [Presenton 官方模板议题](https://github.com/presenton/presenton/issues/67) | Zod/组件模板方案；议题不证明所有当前实现与导出细节 |
| NEW-S10 | [Style Dictionary](https://styledictionary.com/info/tokens/) | token 引用与多端编译；具体编译器仍是候选 |
| NEW-S11 | [DTCG 2025.10](https://www.w3.org/community/reports/design-tokens/CG-FINAL-format-20251028/) | 格式与版本；不能将报告简化示例当作完整正式结构 |
| NEW-S12 | [Slidev 导出](https://sli.dev/guide/exporting) | 图片型及有限原生对象输出、局部/整页降级和字体差异 |
| NEW-S13 | [CSS 单位](https://www.w3.org/TR/css-values-4/#absolute-lengths) | 96px = 72pt = 1in 的换算关系 |
| NEW-S14 | [WCAG 对比说明](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) | 对比检查的依据与适用条件，不代表全部美感 |

部分仓库资料已读取固定提交，文件哈希见 [外部证据元数据](external-evidence.json)。
没有把第三方源码复制进项目。主分支链接仍可能变化，正式接入前固定版本再查。
GitHub 树 API 请求遇到限流，已读取的文件用直接链接核对；未读取文件不宣称已审计。

## 2. 对本项目有影响的修正

| 编号 | 原报告位置与问题 | 本项目采用的判断 |
| --- | --- | --- |
| NEW-C01 | B §2.2/4.1/6.3 要求改用 Remotion | 本地已经使用；需要扩展 PNG 画面表示，不整体换引擎 |
| NEW-C02 | B §2.11/6.3 要求接入 WhisperX | 现有时间链路已有 provider/Qwen/人工路径，且保护历史引擎迁移；不新增选型 |
| NEW-C03 | B §6.3 重新选择语音合成与数字人方案 | 用户明确排除，沿用现有方案，仅适配消费与合成 |
| NEW-C04 | A §1.4、B §2.6/5.4/6.3 假定已有模板库 | 当前工程资产盘点未确认；不是开发前置，不据此编造模板数量 |
| NEW-C05 | A §2.2 声称主题均为纯 token | NEW-S02 含组件/页面选择器；本项目用参数、呈现变体与组合配方承载差异 |
| NEW-C06 | A §2.4/5.2 将修复阶梯描述为绝对禁止删内容 | NEW-S03 的大溢出提示仍允许有意合并/移除；我们采用禁止静默丢内容，而不是复制原数字/行为 |
| NEW-C07 | A §5.2 缺 Playwright 降为 warning 即可 | 本地可做部分预检，但未测量不能标记通过；正式输出的必需检查缺失应阻断 |
| NEW-C08 | A §3.2 说 1pt = 1px | NEW-S13 为 1px = 0.75pt；先明确定义画布/输出尺寸与坐标参考系 |
| NEW-C09 | A §3.3 截图叠文字即可保真且自由改字 | 原截图有旧文字，可能重影；需移除原文字像素或独立背景层，并实测修改 |
| NEW-C10 | A §3.2 单页失败插空白页继续 | 不作为默认成功降级；按输出策略阻断或明确部分结果 |
| NEW-C11 | B §6.3 Vue/HTML 组件直接当 Remotion 组件复用 | 语义数据可共用，框架组件不能默认直接互换；先定义适配接口 |
| NEW-C12 | B §2.12/5.8 color 强制 hex、三层 token 自动保证一致 | NEW-S11 的颜色含色彩空间等结构；token 仍需解析、检查、参考页和素材审阅 |
| NEW-C13 | A §1.5/5.2 强制引入 BLOCKING 人工门与哈希防漂移 | 借鉴机器快照和校验，哈希只证明身份/变化；不复制反复签字门或署名门作为视觉验收 |
| NEW-C14 | A/B 把少量布局、Schema/HTML 视作排版绝不失败 | 容量、字体、几何、素材和美感仍需分别验收，框架数量不是保证 |
| NEW-C15 | B §2.9/5.6 默认部署 IP-Adapter/ControlNet/LoRA | 当前复用 provider 与参考图方式；只吸收独立素材和画风规范，不新增模型部署 |

## 3. 剔除内容

不进入借鉴任务：语音合成/数字人/音频对齐模型选型、实时对话、LoRA 训练、社交封面分发、
星数与活跃度排行榜、未知本机 Skill 的安装、第三方强制签字工作流。
这些内容只存在于原文证据，不扩写为项目方案。

报告里准确的 Slidev 可编辑导出能力仍值得参考，但“唯一真可编辑”“视觉 100%”“全链路
问题当场消失”等无范围保证不采用。项目只承诺经过支持集定义与实际验收的能力。
第三方模板/代码的许可是实际引入前的核对项；当前没有直接引入这些资产，也不根据
仓库星数或报告中的许可解释做技术/法律结论。
