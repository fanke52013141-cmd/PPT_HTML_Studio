# PPT HTML Studio

面向课程演示与短视频的 HTML 画面系统。通过公共组件、布局、风格包、独立素材和
讲稿驱动的动作，构建兼具视觉质量与元素控制能力的演示，目标输出包括 HTML、视频
与分层次支持的 PPTX。

## 项目规范入口

**当前契约包版本以规范目录为准。** 后续设计、开发、素材生产和验收统一依据
[HTML 演示体系契约](docs/contracts/html-presentation/README.md)。

| 文档 | 说明 |
| --- | --- |
| [构建方式与公共/风格归属](docs/contracts/html-presentation/01-building-and-ownership.md) | 如何构建；哪些公用、随风格变化、由页面填写或计算生成 |
| [能力目录](docs/contracts/html-presentation/02-capabilities.md) | 各部分内容、组件与布局候选、首轮建设范围 |
| [数据与运行契约](docs/contracts/html-presentation/03-data-and-runtime.md) | 身份、公开目标、布局定位、时间、资源、编辑影响与输出 |
| [生产与兼容规则](docs/contracts/html-presentation/04-production-and-compatibility.md) | 按规则生产、处理问题、更新版本及兼容旧作品 |
| [完整分类与扩展机制](docs/contracts/html-presentation/framework/README.md) | 八层分类、组合/扩展规则、能力覆盖与风格定制流程 |
| [阶段 1 最小定义卡包](docs/contracts/html-presentation/definitions/README.md) | 19 张具体定义卡、完整场景与边界例、状态和后续项 |
| [定义卡模板](docs/contracts/html-presentation/05-definition-template.md) | 逐项定义组件、布局、风格、素材和动作的模板 |
| [规则索引](docs/contracts/html-presentation/contract-index.json) | 规范位置、版本与执行状态 |
| [契约变更记录](docs/contracts/html-presentation/CHANGELOG.md) | 规则版本、变更原因与兼容影响 |

[AGENTS.md](AGENTS.md) 规定后续开发读取和维护契约的方式，并保留原项目集成边界。

## 构建原则

- 公共能力定义语义、数据与操作接口，供不同风格和作品复用。
- 风格包定义视觉参数、公共呈现变体、素材画风、组合规则与参考页。
- 页面实例保存实际内容、讲稿、素材选择及人工约束。
- 几何、文字分行、动作时间和 HTML 等是计算生成的结果。
- 动作绑定稳定语义目标；预览和导出采用同一修订的输入。
- 规则更新记录数据、行为、视觉和输出兼容，保留旧作品及人工修改。

## 当前阶段

本地原图片应用与独立 HTML E1/E2、共享视觉模块并存，HTML 生产链尚未接入应用。共享视觉 V1 的简化外观已被用户否定；`html_engine/visual/style-review/` 是恢复指定科普参考的校正样板，尚需完成共享能力集成和视觉验收。

**当前执行入口：[HTML 后端开发与验收交接包](docs/plans/html-backend-development/README.md)。** 包含逐项开发任务、固定源码版本的开源借鉴映射、测试输入与验收标准、Agent 提示词和任务清单。应用源码完整发布需独立审计；远端克隆不能假定包含本地完整应用。

## 实施路线与背景

- [分阶段实施计划](docs/plans/html-studio-implementation-plan.md)：历史阶段规划；后续执行以新的开发交接包为准
- [调研与借鉴档案](docs/research/README.md)：保存报告、证据、借鉴判断和验证计划
- [当前项目改造借鉴指南](docs/research/2026-10-07-skill-and-workflow-reports/adaptation-guide.md)：结合现有代码筛选两份新报告，并提供实施与验收卡
- [编程式渲染架构报告借鉴分析](docs/research/2026-10-07-architecture-report/analysis-and-adoption.md)
- [基础建设路线](docs/plans/html-foundation-roadmap.md)
- [原项目复用与改造边界](docs/plans/html-studio-adaptation.md)
- [基础体系审查记录](docs/plans/html-foundation-review-20261007.md)
- [本地基线与启动规范](README_HTML_STUDIO.md)

原讨论稿保留历史标记，正式规则统一在契约目录维护。本仓库地址：
[fanke52013141-cmd/PPT_HTML_Studio](https://github.com/fanke52013141-cmd/PPT_HTML_Studio)。

## 视觉生产规则更新

科普首版样稿视觉审阅未通过。新增 [HTML 与生图分工、验收模板及内容容量规则](docs/contracts/html-presentation/framework/07-visual-production.md)，
按 [P02 重制任务书](docs/styles/science-explainer/visual-production-revision.md) 继续；尚无已批准生产模板。

已制作 [科普混合视觉实验与对照页](docs/styles/science-explainer/experiments/hybrid-01/README.md)，展示整页设计稿、独立资产、HTML 还原及真实失败记录；视觉审阅待确认。

内容可视化范围延伸到场景动画，PPT 作为其中一种模式与输出；当前扩展提案见
[动画项目借鉴与能力缺口](docs/research/2026-10-07-huashu-art-motion/analysis-and-adoption.md)。

已完成 [12 秒对象过程动画实验](docs/styles/science-explainer/experiments/motion-01/README.md)：水滴路径、汇集、镜头聚焦及逐帧 MP4；用户视觉审阅待确认。

## 视觉实现与生成协议

契约 0.7.0 修订新增 [视觉实现分工与生成契约](docs/contracts/html-presentation/framework/08-visual-generation-contract.md)：生成前确定代码层、资产层和全过程对象，设计图与 HTML 共用同一设计定义。本次只补协议，资产板与新动画测试留待下一步。

## motion-02 资产与过程验证

[实验记录](docs/styles/science-explainer/experiments/motion-02/README.md) 已形成对象/运动清单、设计参照、三个透明资产、实际 HTML 和验证证据。资产留边与源尺寸边缘质量仅部分通过，用户视觉审阅待进行；不作为生产模板或资产库发布。

## 从实验到工程

用户已认可 motion-02 的混合视觉与短对象动画方向。下一步见 [混合视觉工程流程与实施顺序](docs/plans/hybrid-visual-engineering-workflow.md)：先建设最小数据驱动渲染链，再扩模板/资产复用、音频输出及应用 AI 接入。

## 数据驱动内核 E1

已实现 [独立内核](html_engine/README.md) 与 [预览入口](html_engine/preview/index.html)。纸飞机/云朵两份 JSON 共用渲染代码，支持资源校验、文字容量、目标几何及确定取帧。现行契约包 0.7.1，限定实施记录见 [E1 交付](docs/plans/e1-data-driven-engine-completion.md)。应用仍运行原图片后端；HTML 集成和真实音频接入待后续阶段。

## E2 受约束配方

[交付记录](docs/plans/e2-constrained-template-completion.md)：两个配方、课程复用和资产质量检查已实现；视觉和生产批准待审阅。查看 [预览](html_engine/preview/index.html) 或 [资产对照](html_engine/preview/e2-assets.html)。

## 用户 Token 课程

[课程预览](html_engine/courses/token/index.html) 和 [实施记录](docs/plans/e2-token-course-validation.md)：五场景复用一个公共三步配方，包含事实修订与实际分词证据。无音频，视觉待审阅。
