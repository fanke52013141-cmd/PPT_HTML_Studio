# HTML Studio

2026-10-23 批量配图：[16:9 / 9:16 四宫格布局](docs/releases/2026-10-23-asset-sheet-layout.md)。素材板最多 4 个需求，按项目方向自动排成 1536×864 / 864×1536 / 1024×1024，外边距与格子间隙 24px，透明底，生成一次后按固定槽位拆成独立资产；逐资产人工审阅，不自动批准。4 个横版插图的理论输出像素 4.19M→1.33M（约 -68%），调用 4→1；主 produce 流程仍为每页 1 个插图槽位，跨页自动合板尚未接入。

2026-10-22 实测修复：[图片连接测试、计划版本、审阅错误透出、用量与浏览器预检](docs/releases/2026-10-22-provider-test-plan-version-errors.md)。ToAPIs 连接测试补传凭据与任务级超时（真实验证 48.9 秒成功）；Web/Agent produce 省略 plan_version 默认 0.2.0，设计/计划版本不一致返回 409 不再静默复用；审阅脚本失败错误带报告原因与路径；流式调用记录真实 token usage，HTML 任务在付费出图前预检 Chromium 不可用即停。Agent API 1.62.1、capability 1.15。

2026-10-22 优化数据汇总：[还原优化前后数据](docs/plans/html-backend-development/optimization-results-2026-10-22.md)。W1 端点归一化 0/32→32/32、W2 穿字路由 0/2→2/2、W3 容量候选 0→25、W4 外部输入 113,922→26,403 字节（-76.8%）；全部为冻结/受控基准，0 模型/供应商/作者写入。

2026-10-22 识别迁移：[跨机样本封存工具](docs/releases/2026-10-22-recognition-transfer.md)。新增 feature_recognition_bundle：只传输 dataset 引用的图片/请求/响应/标签，逐文件 SHA-256 与路径边界校验，导入先验证后落盘、拒绝覆盖；4 项测试通过，受控夹具往返 8 文件/2 页/69,258 字节且计分完全一致。真实跨课程材料仍需另一台机导出并标注。

2026-10-22 还原优化（W3）：[容量溢出确定性修复](docs/releases/2026-10-22-capacity-repair.md)、[契约 0.1.0](docs/contracts/html-presentation/runtime/visual-v1/capacity-repair-0.1.0.md)。新增 capacity_first：尺寸候选按原容量触发并限制画布/变体，排版候选仅缩小已显式字号且不低于24px；首个通过原检查者返回，全部失败显式无解、不调用模型。离线候选 0→25、模型调用0；generate1.7、Agent API1.62.0、契约包0.9.115。

2026-10-22 还原优化（W4）：[外部 Agent 最小输入](docs/releases/2026-10-22-external-minimal-input.md)。任务包新增 task-minimal.json：scope 对象、类型化缺陷、确定性候选、相关文件引用、幂等与回执要求；task.json 仍为权威。代表性任务包 113,922→26,403 字节（-76.8%），候选由 geometry-repair/0.2.0 预生成且仍需原 QA。4 项测试通过；契约0.9.114/API1.61.0保持。

2026-10-22 还原优化（W2）：[关系附着点确定性路由](docs/releases/2026-10-22-endpoint-routing-repair.md)、[契约 0.2.0](docs/contracts/html-presentation/runtime/visual-v1/geometry-repair-0.2.0.md)。显式 point 端点箭头在目标边界枚举附着点，要求对所有可见文字无穿越后再交原编译器/30fps QA；不移动文字、不改关系对象，anchor/隐式槽位不参与，无解返回空提案且不调用模型。冻结基准 2/2 路由、3/3 非路由跳过、0 误生成、0 模型调用；预览/保存1.8、generate1.6、Agent API1.61.0，契约包0.9.114。

2026-10-22 还原优化（W1）：[规划端点确定性归一化](docs/releases/2026-10-22-plan-endpoint-normalization.md)、[可执行优化方案](docs/plans/html-backend-development/restoration-optimization-plan-2026-10-22.md)。唯一且类型兼容的槽位名端点按对象表归一化并留痕，未知/歧义/类型不符仍严格拒绝；同一基准 32 例槽位名计划 0/32→32/32 通过、编译 scene 全部一致、非法引用 32/32 仍拒。无供应商调用、无作者写入；契约 0.9.113/API1.60.0 未变。

2026-10-21 评测版本：[跨布局受控标签0.2.0](docs/plans/html-backend-development/feature-recognition-benchmark-2026-10-21.md)、[溢出与穿字冻结评测](docs/plans/html-backend-development/overflow-crossing-benchmark-2026-10-21.md)、[发布备注](docs/releases/2026-10-21-benchmark-versions.md)。计分器新增ownership/模糊理由分类（0.1.0输出不变）；溢出与穿字按真实检测谓词评分，含真实测量重放、贴边/端点接触/密集负例及未决与耗时。均为受控证据，真实跨课程页与真实穿字对仍需另一台机按hash移交。CI红修复见[该批交接](docs/plans/html-backend-development/handoff-ci-red-2026-10-21.md)；契约0.9.113/API1.60.0未变。

2026-10-21 CI 修复：[全量检查红因与修复](docs/plans/html-backend-development/handoff-ci-red-2026-10-21.md)，[发布备注](docs/releases/2026-10-21-ci-red-fix.md)。近8次push连续红；根因为检查脚本硬编码仓库`.venv`解释器（CI无`.venv`），另加59da921后理解替身缺`feature_observations`。修复不改生产校验/断言，目标测试通过、canonical quick通过；`single_page_video`一例`EXPORT_PAGE_FAILED`按flake保留观察。契约0.9.113/API1.60.0未变。

2026-10-21 已推送：[问题发现优化与跨机 handoff](docs/plans/html-backend-development/handoff-detection-optimization-2026-10-21.md)，[发布备注](docs/releases/2026-10-21-detection-optimization.md)。源码59da921；统一交付几何扩样、规划诊断、正文溢出/穿字前置、理解0.7.5及固定标签评测；包0.9.113/API1.60.0保持。发布前217项回归、quick和视觉14组通过，CI终态另验。目标是减少系统漏检，非逐页手修；下方“未提交/未发布”保留历史状态。Git不含课程样本/运行数据，应用未重启，正式输出与跨课程泛化待验。

2026-10-21 固定样本：[识别漏检率基线与新版同图对比](docs/plans/html-backend-development/feature-recognition-benchmark-2026-10-21.md)。理解0.7.5将逐对象观察与能力分工分离；同三图同标签插图识别4/4、图标负例6/6，未决2→0；系统能力缺口拦截2/2、负例8/8。0.7.4容器误拦保留，最终例未再误拦；原模型问题类型仍错分，程序派生与原模型分开计。仅一课开发样本，非总体性能。

2026-10-21 系统问题：[问题台账与本批优化](docs/plans/html-backend-development/system-issues-2026-10-21.md)。明确区分问题发现、规则实现和真实效果；独立插图/图标边界、完整观察与不确定停止已实现并同图复测；模型类型一致性、跨课程泛化、unknown/默认GPU捕获仍待处理；未逐页手修作者。

2026-10-21 工程前置：[正文父容器边界与动态检查](docs/plans/html-backend-development/handoff-production-preflight-2026-10-21.md)。还原每轮前后复用原30fps/registered检查；正文裁切或箭头/对象碰撞未通过，不进入独立保真审核或生成可保存生产结果。程序Prompt0.6.2/运行片段0.7.4，原预算和批准边界保持；无新供应商调用，原页实际修复另验。

2026-10-21 规划优化：[准确诊断与重试输入](docs/plans/html-backend-development/handoff-planning-diagnostics-2026-10-21.md)。Prompt0.3.6区分对象/槽位/需求ID，保留严格拒绝并反馈字段路径与合法ID；新增11项通过。相关组105通过、默认浏览器像素一致性1项失败，原校验器同输入对照也复现，场景字节一致；无新供应商调用，真实纠错效果待验。

2026-10-21 本机新课程：[水循环四页真实流程试验](docs/plans/html-backend-development/handoff-water-cycle-trial-2026-10-21.md)。第2—4页经用户接受用于还原测试，三页均未通过、作者保存0/3；保留素材及自然故障模型回退两个unknown，不重发。自然候选检出箭头穿字/卡片重叠；本地修正还原首轮缺当前HTML截图，双图出站与真实质量分别验证。声音、保存恢复和输出尚未执行。

2026-10-21 本地续进：[几何扩样、真实回退与跨机验证包](docs/plans/html-backend-development/handoff-geometry-corpus-2026-10-21.md)。槽位箭头兼容修复与人工保护评测补齐；受控双标签真实回退1次请求、473时刻通过，独立原课程扩样等待另一台电脑材料。包0.9.113/API1.60.0保持；尚未提交/推送或切换正式服务。

2026-10-21 已推送：[最新发布与跨机 handoff](docs/plans/html-backend-development/handoff-release-2026-10-21.md)。源码662b725，契约0.9.113/API1.60.0；重叠判定、反馈/流式观测、几何优先候选及显式保存。发布回归158项、编辑器17项和quick通过；远端CI另验，未部署服务。

2026-10-20 几何入口：[几何优先修复、候选对照与显式保存](docs/plans/html-backend-development/handoff-geometry-entry-2026-10-20.md)，包0.9.113/API1.60.0。两张真实原页经新入口通过633/606时刻检查、0模型调用；浏览器保存/恢复及切页保护通过。真实模型回退质量另验，未发布。

2026-10-20 几何避让：[候选与扩样验证](docs/plans/html-backend-development/handoff-geometry-repair-2026-10-20.md)，包0.9.112/API1.59.0；有限布局试算＋原检查器，原页/受控扰动/正常与能力反例分别统计，候选不保存。

2026-10-20 分级真实测试：[JSON→单图→整页结果](docs/plans/html-backend-development/handoff-staged-live-diagnostics-2026-10-20.md)。两侧三层全部通过，6次真实调用；整页Legacy224秒/Pi272秒且都通过606时点检查，主要长等待伴随持续推理，单次结果不用于默认切换。

2026-10-20 本地优化：[修复输入与流式观测记录](docs/plans/html-backend-development/handoff-repair-stream-context-2026-10-20.md)，包0.9.111/API1.59.0。真实页输入字节减少45%/52%，接通两侧进度；未追加模型请求，实际延迟改善待验。

2026-10-20 真实模型评测：[Legacy / Pi 评测记录](docs/plans/html-backend-development/handoff-real-runner-evaluation-2026-10-20.md)。两次新请求均超时，尚无完整配对，不能判定优劣；保留unknown与not_run，保持Legacy默认。

2026-10-20 本地增量：[真实重叠修复与反馈闭环](docs/plans/html-backend-development/handoff-overlap-repair-feedback-2026-10-20.md)，包0.9.110/API1.59.0；两页候选及原检查/显式保存流程在隔离课程验证，真实模型接受另列。

2026-10-20重叠判定：[实际线段、文字区域与合法端点接触复验](docs/plans/html-backend-development/handoff-vector-overlap-2026-10-20.md)。合同0.9.109/API1.59.0；两组实际穿字继续阻断，原课程未修改；未发布。

2026-10-20动态优化：[模板策略补齐、箭头几何误报修复及容量请求留证](docs/plans/html-backend-development/handoff-temporal-capacity-2026-10-20.md)。真实三阶段页30fps检查通过，其他页保留重叠待核查项；未发布。

2026-10-20本机容量优化：[三类固定案例、真实课程取证与容量输入修复](docs/plans/html-backend-development/handoff-capacity-baseline-2026-10-20.md)。离线工程与真实模型验收分别记录；未发布。

2026-10-20本机接手：[跨机编辑器指纹修复与验证](docs/plans/html-backend-development/handoff-local-checks-2026-10-20.md)。已同步main；本地修复尚未发布，原课程运行数据在另一台电脑。

2026-10-20源码同步：[最新发布与跨机handoff](docs/plans/html-backend-development/handoff-release-2026-10-20.md)；契约0.9.108/API1.59.0。候选编辑、关联修复、Pi M0–M5和设计对应约束；真实新页尚未验收，Legacy默认保持。提交/检查终态以发布回执为准。

2026-10-20：[设计图与计划对应修复、新对照任务](docs/plans/html-backend-development/handoff-design-plan-alignment-2026-10-20.md)，契约0.9.108；实际新图已核对，原计划不改，Legacy/Pi同输入重测；正式视觉批准独立。

2026-10-20：[Pi Agent M4–M5工程交付](docs/plans/html-backend-development/handoff-pi-agent-m4-m5-2026-10-20.md)，契约0.9.106/API1.59.0。新页选择Pi、预授权修复另存AI版本，文章/讲稿/可视化与批量候选固定API；保留旧默认，真实重复质量与默认切换另验。源码未发布，正式服务未重启。

前序：[M0–M3交付与真实验证](docs/plans/html-backend-development/handoff-pi-agent-m0-m3-2026-10-20.md)，真实简单任务通过，复杂任务失败分别留证。

2026-10-20：[中文联动修复、关联组采用与四类评测](docs/plans/html-backend-development/handoff-repair-assistance-2026-10-20.md)，契约0.9.104/API1.57.0；外部真实自主效果与离线流程验证分别记录。

2026-10-20：[候选画布、中文属性与保存版本恢复交接](docs/plans/html-backend-development/handoff-candidate-canvas-history-2026-10-20.md)，契约0.9.103/API1.56.0。新功能与验证边界以该交接为准。

2026-10-19 本批源码更新：[外部Agent真实交接与二次编辑handoff](docs/plans/html-backend-development/handoff-external-agent-and-secondary-editing-2026-10-19.md)，[发布备注](docs/releases/2026-10-19-external-agent-handoff-and-editing.md)。契约0.9.102/API1.55.1；真实外部首轮已通过严格导入和原预览，尚未保存/批准。下一批优先候选画布编辑、易懂属性与恢复能力，当前仍为参数接手。Git更新不含课程数据或应用部署；下方“待回传/本地未发布”为历史阶段记录。

2026-10-19 本地勘误：[执行2.1.1能力与交付修订](docs/plans/html-backend-development/handoff-execution211-2026-10-19.md)，契约0.9.102/API1.55.1。缺必需能力须停止、要求看图的候选须记录原图审阅；原播放器/after接续另列。旧输入2.1试验包保持历史，重试须重新导出；本地未发布。

2026-10-19 本地增量：[输入2.1与人工接手](docs/contracts/html-presentation/runtime/visual-v1/external-agent-workbench-0.1.0.md)，契约0.9.101/API1.55；同源容量/结构化目标、持久工作草稿、原检查/混合来源保存。本地源码未发布，正式验收与P2扩展单列。

2026-10-19：[外部执行合同2.0](docs/contracts/html-presentation/runtime/visual-v1/external-agent-execution-2.0.0.md)，
契约0.9.100/API1.54；每包带同源静态预检、硬约束/覆盖、能力及逐项验收模板，严格候选经原系统复核后采用。
已针对实际Token页面准备新Agent独立测试；本地源码未推送或切换真实服务。

2026-10-19 外部结果接入：[交接说明](docs/agent/external-page-handoff.md)，契约0.9.99/API1.53。
页面接收delivery.zip或result.json、保留交付报告/证据并导出系统检查反馈，通过后单独保存。
真实首轮结果格式合规，原编译器因底栏入场安全区拒绝；未保存、未批准，第二轮需带反馈修订。

2026-10-19 真实试验输入：[Token 第3页外部 Agent 任务](docs/agent/real-trial-token-2026-10-19.md)。
契约0.9.98新增随包[执行/验收/交付规范](docs/agent/external-agent-execution.md)；真实历史候选和原素材在隔离副本试验，
输出 result.json + report.md 后用原服务核验，实际外部效果待回传。本地源码未推送或切换真实服务。

2026-10-19 本地开发：[外部 Agent 完整任务包与导入交接](docs/plans/html-backend-development/handoff-external-bundle-2026-10-19.md)，契约0.9.97/API1.52。新增实际截图/素材/解析风格及严格操作Schema的ZIP、设计材料导出与局部修复结果导入预览/显式保存；真实外部Agent质量待验，未推送或切换真实服务。接入见[使用说明](docs/agent/external-page-handoff.md)。

2026-10-18 主分支合并完成：[PR #2](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/pull/2)已合入main，合并提交23c7019。合并前完整GitHub CI通过（[运行60](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/actions/runs/39140034104)），含全量检查、编辑器构建及Remotion TypeScript。下方“开发分支/未合入”描述为此前阶段记录；当前从main获取代码。源码合并不包含公网部署或课程数据迁移。

2026-10-18 源码试用更新：[课程闭环与外部Agent试用说明](docs/releases/2026-10-18-course-and-external-agent-testing.md)。目标分支codex/editor-adapter-p0-20261017、PR #2；本次仓库同步不包含公网部署，main尚未合入。发布前511项相关隔离回归及共享视觉检查通过。

2026-10-18 当前开发：[动作诊断与外部Agent交接](docs/plans/html-backend-development/handoff-external-agent-2026-10-18.md)。契约0.9.96/API1.51；四页课程已正式导出并登记当前作品。新增客户端标准任务/结果交接、原修复报告的动作时间风险提示及音频版本保护；本地传输与回归通过，真实外部Agent能力和自动转交尚未验证。下方记录保留为阶段历史。

2026-10-18 当前交接：[课程修复与整课输出](docs/plans/html-backend-development/handoff-capture-recovery-preflight-2026-10-18.md)。契约0.9.95/API1.50；四页已保存，整课原音频已确认且20个文件hash不变。第二、三、四页签收有效；第一页八方向程序修复及独立语义、核对视频通过，待当前画面与语义人工确认后正式导出整课。

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
