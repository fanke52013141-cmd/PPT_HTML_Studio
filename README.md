# HTML Studio

2026-10-18 当前交接：[可重复捕获、素材恢复与生产需求预检](docs/plans/html-backend-development/handoff-capture-recovery-preflight-2026-10-18.md)。契约0.9.91/API1.49；保留原图的受控端点修复通过工程验证，第二/四页已有设计待审，真实HTML/语义/整课发布另验。

2026-10-18 离线结构补齐：[四页统一修复验证](docs/plans/html-backend-development/handoff-course-structures-offline-2026-10-18.md)。契约0.9.88/API1.47；显式关系、平台图表和三阶段模板已接入离线验证，默认GPU分数缩放像素限制、真实课程与发布仍待验。无新增付费调用。

前一阶段交接：[编辑器与视频优化验收](docs/plans/html-backend-development/handoff-editor-validation-2026-10-18.md)。契约0.9.87/API1.46；原图复用仍需新候选接受，整课尚待签收。真实单页正式视频、AI协作固定对照和设备压力通过，修复AAC合成延迟。真实多页课程与全库架构门禁仍待完成，状态partial。

2026-10-17 当前本地入口：[单页视频输出验证](docs/plans/html-backend-development/handoff-single-page-video-2026-10-17.md)。编辑后冻结导出/对应帧/过期批准阻断/重建缓存21项通过；真实旁白页音频已确认，当前缺视觉批准，已生成审阅图。无生产API变更，未发布。

2026-10-17 最新本地增量：[真实旁白与音频新鲜度](docs/plans/html-backend-development/handoff-editor-audio-freshness-2026-10-17.md)。真实MP3隔离副本编辑/跳转/重开通过；增加音频指纹过期409、保留草稿刷新配音/时序。契约0.9.83、Agent API1.43；未提交或发布。

2026-10-17 最新本地优化：[P3人工字段保护与保存边界](docs/plans/html-backend-development/handoff-editor-protection-p3-2026-10-17.md)。AI候选/最终保存共用叶字段保护，允许未保护兄弟字段，拒绝间接资源覆盖并定位冲突；契约0.9.82，未提交或发布。

2026-10-17 最新本地开发：[P2动作时间轴交接](docs/plans/html-backend-development/handoff-editor-timeline-p2-2026-10-17.md)。正式编辑器接入已有动作偏移/拉伸、只读讲稿与同一音频时钟；合成音频浏览器通过，真实旁白/输出待验。契约0.9.81，尚未提交或发布。

2026-10-17 本地开发：正式编辑器已接入 P1 布局编辑，支持移动、缩放、多选移动、撤销及原服务保存；工程与隔离浏览器通过范围、未验收项见[最新开发交接](docs/plans/html-backend-development/handoff-editor-layout-p1-2026-10-17.md)。契约0.9.80；尚未提交、推送或部署。

2026-10-17 最新发布：[文字边缘报告与开源编辑交接备注](docs/releases/2026-10-17-edge-reports-editor-handoff.md)，契约0.9.78；本批5个相关测试文件98项通过。换机从[最新handoff](docs/plans/html-backend-development/handoff-open-source-editor-2026-10-17.md)继续，下一步P0开源组件适配、P1布局编辑。Moveable/Selecto/时间轴目前是已调研方案，尚未集成；人工逐行标注不作前置条件。

2026-10-17 前一批发布：[流程优化与文字边缘核验发布备注](docs/releases/2026-10-17-review-and-handoff.md)。契约包0.9.76；本批相关隔离回归255项通过。换机继续步骤、已验证边界和数据迁移说明见[交接文档](docs/plans/html-backend-development/handoff-cross-machine-optimization-2026-10-17.md)。本机`data/`、`runs/`、`outputs/`及模型凭据不随Git同步；跨机代码与可重建控制组已纳入本次发布。

此前10月16日各条目记录的是当时的未提交状态，仅作历史账本。本批代码、契约和交接已在本次提交推送；前一批交接保留于[2026-10-17流程交接](docs/plans/html-backend-development/handoff-cross-machine-optimization-2026-10-17.md)，当前继续步骤以本文顶部最新handoff为准。

2026-10-16当前运行状态：[8010已完成换版](docs/plans/html-backend-development/handoff-runtime-activation-2026-10-16.md)，实际API1.39.0/hash2f9000d34a3b464d，静态资源与数据完整性核对通过。此前旧版/审批阻塞记录保留为历史；未发起真实模型实验，未推送。

2026-10-16验证增量：[完整应用隔离TCP冒烟](docs/plans/html-backend-development/handoff-runtime-smoke-2026-10-16.md)，验证新版API1.39.0的候选核对与原课程恢复，修复一键Web冲突误转400；固定清单30/30通过。8010仍旧版，等待手动关闭旧开发服务后换版；隔离测试使用供应商替身，未验证真实模型质量。

2026-10-16本地增量：[容量进展判断](docs/plans/html-backend-development/handoff-capacity-progress-2026-10-16.md)，修复盒尺寸相同但行数/边缘触发项变化时的提前停止，并覆盖已保存报告details。源码API1.39.0，原预算与门禁保持；运行服务仍1.37.0，未推送。

2026-10-16本地增量：[讲稿核对闭环](docs/plans/html-backend-development/handoff-script-review-workflow-2026-10-16.md)，候选独立保留、明确修正保存、原课程等待并复用修正稿继续。源码API1.38.0；服务换版命令被自动审批拒绝，当前8010仍为1.37.0，尚未推送。

2026-10-16本地增量：[讲稿限定范围与容量诊断](docs/plans/html-backend-development/handoff-script-fidelity-capacity-2026-10-16.md)，写前对照原句停止风险结果，容量报告列明有效限值与触发维度；固定清单25/25通过。真实模型保真效果仍待验证，本批未推送。

2026-10-16本地开发：[流等待诊断](docs/plans/html-backend-development/handoff-stream-wait-diagnostics-2026-10-16.md)与[课程父子暂停修复](docs/plans/html-backend-development/handoff-course-pause-2026-10-16.md)，区分读取断流和总预算，明确取消/占用的停止与核实方向。用户选择暂不重发原未知请求；本批尚未推送，最新线上发布仍见下文。

最新发布：[2026-10-15 流程 Agent 与多标签能力发布备注](docs/releases/2026-10-15-workflow-agents-and-labeled-capabilities.md)。契约包0.9.53、Agent API1.34.0；审核依据、能力路由与等待规则已修复，通用多标签和呈现能力已接入，固定流程清单21/21通过。真实遴选案例的新规划因供应商ReadTimeout停止，尚无新计划或HTML通过结果。

最新实施交接：[多标签能力与真实复验停点](docs/plans/html-backend-development/handoff-labeled-capabilities-2026-10-15.md)。[审核规则同案例复验](docs/plans/html-backend-development/handoff-design-review-fix-2026-10-15.md)已证明本例可提前拦截缺少代码标签，但耗时更长；模型效果、工程验证与人工签收分别记录。原[2026-10-14发布交接](docs/plans/html-backend-development/handoff-2026-10-14-model-stream-publication.md)保留为历史。

界面整理记录：[HTML流程与工作区交接](docs/plans/html-backend-development/handoff-html-workspace-flow-2026-10-14.md)，明确设计图先行、独立还原/动画面板、配音同步与可选数字人，去掉HTML旧勾画步骤。

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

当前新增开发路线为[开源组件驱动的还原与二次编辑](docs/plans/html-backend-development/open-source-editor-optimization-2026-10-17.md)，状态及依赖以最新handoff为准。下方早期条目保留为历史背景。

最新进展：[多标签规划与注册呈现能力](docs/plans/html-backend-development/handoff-labeled-capabilities-2026-10-15.md)。六个代码标签、三个代码关系槽及四个变体已实现并通过本批工程检查；真实模型尚未返回使用新能力的完整计划。设计、还原、视觉/逐句语义/音频签收及整课仍分别验证，旧失败不自动改为成功。

[流程先行与并行开发计划](docs/plans/workflow-first-parallel-2026-10-09/README.md)细化七步制作职责、人工确认、失败恢复和多对话文件分工，配合下方视觉参考库路线执行。

**前期视觉参考库执行记录：[视觉参考库收束与详细开发计划](docs/plans/html-backend-development/visual-reference-roadmap-2026-10-09.md)。**

后续以 [标准组件库 1.0](html_engine/reference-library/STANDARD-LIBRARY.md) 为静态组件基线：24 张黑白灰参考页、32 个基础组件、16 种呈现变体、28 种效果、18 个组合及 5 种字体。组件源代码、截图、编号查询和验证记录一同保存；配色与图片风格独立输入。见 [发布交接备注](html_engine/reference-library/HANDOFF-1.0.md)。被否定的模板不再作为入口，历史批准实例保留。生产适配和课程量产仍按计划验证。

原图片后端与 guided HTML 后端并存。受约束生产、项目资产、审阅/批准、句子动作绑定、持久任务、视频和快照 PPTX 已接入本地应用并通过本轮工程验收；真实模型、真实课程、数字人、PowerPoint 打开及用户视觉评审仍待完成。

**当前执行入口：[HTML 后端开发与验收交接包](docs/plans/html-backend-development/README.md)。** 包含逐项开发任务、固定源码版本的开源借鉴映射、测试输入与验收标准、Agent 提示词和任务清单。应用源码已合并到 main；远端包含已提交的应用基线与 HTML 改造，不包含本地继承的未提交改动、凭据和运行数据。

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

已实现 [独立内核](html_engine/README.md) 与 [预览入口](html_engine/preview/index.html)。纸飞机/云朵两份 JSON 共用渲染代码，支持资源校验、文字容量、目标几何及确定取帧。现行契约包 0.7.1，限定实施记录见 [E1 交付](docs/plans/e1-data-driven-engine-completion.md)。当时应用运行原图片后端；此处为 E1 历史记录；当前应用集成见下方更新说明，真实课程音频仍待验收。

## E2 受约束配方

[交付记录](docs/plans/e2-constrained-template-completion.md)：两个配方、课程复用和资产质量检查已实现；视觉和生产批准待审阅。查看 [预览](html_engine/preview/index.html) 或 [资产对照](html_engine/preview/e2-assets.html)。

## 用户 Token 课程

[课程预览](html_engine/courses/token/index.html) 和 [实施记录](docs/plans/e2-token-course-validation.md)：五场景复用一个公共三步配方，包含事实修订与实际分词证据。无音频，视觉待审阅。

## 2026-10-08 代码与验收更新

[本轮更新说明](docs/releases/2026-10-08-html-backend-update.md) 记录修复提交、555 项通过的回归、真实输出证据和未完成项。应用源码现已合并至 main；后续开发直接基于主分支。html-studio 保留合并前源码历史。上方实验章节为历史记录，当前状态以更新说明和逐 AC 账本为准。

## 主分支源码合并

2026-10-08：将 html-studio 已提交源码合并到 main，保留双方历史及主分支规范。后续直接从 main 开发。[合并说明与未完成项](docs/releases/2026-10-08-main-source-merge.md)。工程链通过不等于真实服务和完整课程验收通过。
本地工作区的流程闭环与布局增量见 [2026-10-15交接](docs/plans/html-backend-development/handoff-html-workflow-closure-2026-10-15.md)；代码提交 `fa5488a`，工程检查与真实课程签收分开。
