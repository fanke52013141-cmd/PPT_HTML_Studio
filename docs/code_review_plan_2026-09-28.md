# 最近四周更新的代码审查执行方案

制定日期：2026-09-28。适用仓库：PPT_presentation_video。

本文件是执行方案，不是已完成的代码审查报告。制定时已阅读提交历史、改动统计、仓库约束、检查入口、历史调查记录，以及最新成果复用相关的部分实现和测试；未执行测试、真实供应商请求或视频渲染。文中的风险和待验证项不等于已确认缺陷。

## 1. 固定审查范围

将“最近几周”具体化为 2026-09-01 至 2026-09-28，覆盖最近四周。固定边界如下，之后的新提交另列增量批次：

- 基线：`1b66bbea4a454292c289895fb15a3f90ac0993ef`。
- 审查目标：`62d50522914cb60949318e064b75f85b396244c1`。
- 期间可达历史共 111 个提交，包含 4 个合并提交。
- 基线到目标的最终差异：1,070 个文件，新增 108,730 行，删除 2,734 行。包含文档、验证素材等，不能据此判断生产代码规模。
- 制定方案时工作区干净；本方案文件是随后新增的文档。

审查采用两种视角：先按业务链审查目标版本的最终代码，再查看高风险提交和合并过程，追溯行为来源。已回退的 UI 实验用于检查残留，不按独立现行功能重复审查。

重点提交组：

| 时间/提交 | 主要变化 | 审查重点 |
| --- | --- | --- |
| 9/1–9/6，`3769cf9`、`db84ccb`、`6420372`、`5a2c774` 等 | Agent 接口、模型连接、多账号、创建配置 | 权限、参数映射、配置版本、迁移与兼容 |
| 9/7–9/17，`42b9914`、`61b220c`、`715e1cf` 等 | 一键/引导模式、字幕、UI、数字人、并发治理、便携包 | 模式切换、额度共享、恢复与运行环境 |
| 9/19–9/27，`660bec1`、`e947ce2`、`28bdb7a`、`98712b0` 等 | raw/normalized 双图、细粒度检测、语义分批、背景自适应 | 像素与语义双重正确性、缓存、回退 |
| 9/26，`024d594` 及后续修复 | 逐请求治理、生图补齐、跨项目异步修复、原子写、任务终态 | 重试成本、竞态与历史缺陷回归 |
| 9/28，`ae6bf95` | 勾画标注模块，106 个文件、18,144 行新增 | 编辑与任务并发、定位、时间轴、播放一致性 |
| 9/28，`a0c5893` 至 `62d5052` | 下游影响登记、按页失效、文章/分镜/图片复用、历史输出保留 | 版本绑定、最小影响范围、旧任务回写、门禁 |

建议在审查记录中保存：目标 SHA、基线 SHA、工作区差异、Python/Node 版本、依赖锁文件哈希、操作系统、执行命令与退出码。文件行号必须取自目标版本，不能沿用旧报告行号。

## 2. 审查原则与证据标准

每一轮统一按以下顺序进行：

1. 写清用户操作、预期行为、输入、输出和持久化位置。
2. 先读对应测试，确认测试覆盖什么、模拟了什么、没有覆盖什么。
3. 沿“界面/API → 校验 → 服务 → 文件/数据库 → 后台任务 → 结果展示”走完整调用链。
4. 检查正确性、可读性、架构边界、安全性和性能；优先处理数据丢失、串项目、错误复用、任务死锁等可观察问题。
5. 为怀疑点建立最小复现或确定性调用链证据，再决定是否进入修复队列。
6. 每个确认的问题补行为回归，修复前失败、修复后通过；每个修复组只处理一个主题。

审查结论只用四种状态：**已证实问题、待调查、已验证通过、未验证**。测试通过但没有覆盖某种竞态，不能把竞态标为通过；历史报告有缺陷记录，也不能直接认定 HEAD 仍有缺陷。

重点识别以下“验证看似充分”的情况：

- 路由测试直接调用函数、替换项目查询，未覆盖实际认证和账号归属。
- 断言源码包含某个字符串，未证明运行行为。
- 测试模拟掉锁、数据库、版本检查或产物替换，绕过了最关键的风险。
- 只测一个项目、一页、顺序执行；没有跨页、跨项目、乱序返回。
- 只报总体通过数量，没有列出 skip、xfail、未运行的脚本式检查和真实渲染。
- 只看 Mask 像素覆盖率，没有检查逐组语义归属。

## 3. 执行轮次与交付物

建议单人安排 8–12 个工作日，按有效审查时间调整。较大的 AI Mask 与标注模块允许继续拆批；发现严重问题时先修复，再回到本轮。这个时间是工作量估计，不是通过承诺。

| 轮次 | 建议用时 | 范围 | 必须产出 |
| --- | --- | --- | --- |
| R0 | 0.5–1 天 | 环境隔离、变更地图、现有验证基线、历史问题复核 | 基线报告、失败/xfail 清单、提交到模块映射 |
| R1 | 1.5–2 天 | 最新下游影响、复用、失效和任务结果提升 | 输入依赖表、版本绑定矩阵、竞态复现 |
| R2 | 1–1.5 天 | 并发额度、后台任务、一键恢复 | 任务状态图、锁顺序、重试与成本记录 |
| R3 | 1.5–2 天 | AI Mask、双图与 Reveal/PPTX 消费链 | 冻结样本报告、逐组指标、实际揭示帧 |
| R4 | 1–1.5 天 | 勾画标注、OCR、编辑、播放 | 编辑冲突测试、坐标/时间对齐报告 |
| R5 | 1 天 | 多账号、配置、Agent、迁移与安全 | 账号访问矩阵、契约差异、迁移结果 |
| R6 | 1–2 天 | 前端全流程、最终媒体、数字人、便携包 | 场景矩阵、MP4/PPTX/字幕证据、退出清单 |

每轮记录放在独立报告中，建议命名为 `docs/audits/review_2026-09-28_RN.md`。运行日志、音视频、临时项目和含用户内容的复现素材放隔离输出目录；不要提交 `runs/`、`data/`、凭据或真实用户素材。

## 4. R0：安全建立基线，复核历史遗留项

### 4.1 环境与检查入口

- 阅读当前 `AGENTS.md`，采用八个可见步骤；追踪 API 和产物时用内部阶段编号。
- 优先使用 `scripts/run_checks.py`：`full` 包含 `quick`、脚本式 Python 检查和全量 pytest；Remotion 类型检查需要 `--with-remotion`。
- `checks/conftest.py` 在 pytest 导入数据库前隔离路径，但会保留调用者已设置的环境变量。不能假定已有变量一定指向临时目录。
- 独立脚本不会自动执行 pytest 的 conftest，因此整轮检查前显式设置临时 DB 和 runs 路径；同时核对配置、凭据及其他写路径的隔离方式。
- 不导入 `server` 来“查看配置”：应用导入可能触发任务恢复等行为。先静态核对运行入口。
- 不对用户数据目录启动第二个实例。需要浏览器/渲染验收时，使用隔离数据和独立端口；验证启动参数的实际入口，不凭空假定存在 `--port` 等参数。
- 不升级依赖来让测试变绿。先记录环境差异；依赖安装按仓库锁定方案执行。

### 4.2 9 月 26 日七项调查逐条复核

入口：`docs/review_2026-09-26_investigation_gates.md`、`checks/test_investigation_gates_phase4.py`。

| 历史项 | 当时状态 | 本次验证方法 |
| --- | --- | --- |
| Step 2 并发覆写/删除正在使用的页目录 | 待修复 | 检查最新保存路径、锁、版本冲突和归档逻辑；用两个过期快照交错提交证明不会静默丢编辑 |
| 一键恢复缺少 ai_mask 阶段 | 已修复 | 复跑恢复用例，同时覆盖新标注步骤、跳过逻辑与 Agent 进度 |
| PPTX 脏会话导致任务卡 running | 已修复 | 注入 commit 失败、rollback 失败，检查独立会话写终态和重启恢复 |
| 渲染结束用旧 ORM 快照覆盖新项目状态 | 待修复 | 阻塞 worker，修改项目并提交，再放行 worker；检查视频与 PPTX 两条路径 |
| 低 RPM 下 TTS 预留超过桶容量 | 严格 xfail | 1–4 RPM、不同文本时长、不同轮询预估；证明能推进或明确拒绝不可能的配置 |
| 超大图片结果被归为可重试损坏图 | 严格 xfail | 构造真实异常类型，统计尝试次数、费用预算和错误展示；另查参数探测重放 |
| 剩余非原子文件写 | 待修复 | 搜索当前写者，注入写入/替换失败，验证旧文件完整且错误可恢复 |

本次静态查看时，两条 `xfail(strict=True)` 标记仍在源码中；没有执行它们，不能判断当前运行结果。若出现 XPASS，应先查行为为何变化，再更新测试和历史结论。

R0 退出：每条历史项都有“当前仍存在/已修复且验证/无法复现/证据不足”的明确状态；全量基线有日志，环境失败与产品失败分开记录。

## 5. R1：下游影响、成果复用与数据生命周期（最高优先级）

源码入口：`impact_registry.py`、`impact_source_version.py`、`project_impact_service.py`、`invalidation_service.py`、`storyboard_contract_diff.py`、`project_routes.py`，以及文章、分镜、图片、TTS、视频和 PPTX 的写入调用者。

规格入口：`docs/downstream-impact.md`。其中明确有“部分实现”“待完善”，逐项区分已有行为和目标行为。

已有测试入口：`test_impact_registry.py`、`test_impact_input_versions.py`、`test_project_impact_service.py`、`test_article_storyboard_reuse.py`、`test_storyboard_image_reuse.py`、`test_image_change_workflow.py`、`test_async_input_promotion.py`、`test_render_input_impact.py`、`test_narration_noop_impact.py`、`test_upstream_edit_invalidation.py`（均在 `checks/`）。

### 5.1 建立每个输入的依赖表

至少列出：正文、画面描述、旁白文字、旁白组映射、页集合/排序、源图片、Mask、勾画、音色/参考音频、字幕、视频背景、数字人配置、导出参数。每项记录：

`写入口 → 内容比较 → source_version → 影响作用域 → 保留/待核对/重建产物 → 解除条件 → 输出门禁`。

重点验证：

- 同值保存和只读导航不改变文件内容、确认记录、影响代次或输出新鲜度；不能只断言 HTTP 成功。
- 分镜 diff 是否完整覆盖真实消费者读取的字段；画面字段、文本字段、组锚点不能错误归类。
- 新增页、删页、重排按稳定 slide_id 处理；重复/空 ID 在进入 diff 前是否明确拒绝。
- 文章改变先要求核对分镜；不会无依据宣布所有旧图和音频与新正文兼容。
- 复用确认同时绑定被审查的输入版本与旧产物哈希；预览之后任一内容变化应拒绝过期确认。
- 图片确认复用只能结清图片影响，不能顺带结清 Mask/勾画；文章复用不能误消除独立存在的其他待办。
- “已查看”“稍后处理”只改变用户决策，不绕过新鲜度验证或生成门禁。
- resolve 只处理启动时对应代次、页和产物；任务期间新产生的影响不能被老任务结清。
- 音频确认记录保留后仍以真实 TTS 输入、音频和时间轴校验；不能只看文件存在。
- DB commit 失败、JSON 写失败、归档失败时，用户可恢复，不能出现 UI 显示成功但产物丢失。

### 5.2 必做场景

使用至少三页、两份已完成项目副本，记录操作前后的哈希、确认状态、待办和成品列表：

| 场景 | 核心预期 |
| --- | --- |
| 原样保存文章/分镜/旁白/Mask/勾画/配置 | 不产生新影响，不丢确认，不重复生成 |
| 只改第 2 页旁白 | 第 1/3 页图与音频不受牵连；第 2 页旧音频不能被当成新输入的有效音频 |
| 只改第 2 页画面描述 | 图片影响限于该页；原音频内容未变可复用；空间资产独立核对 |
| 重排三页 | 素材按 ID 复用；输出顺序和字幕总时间重新计算 |
| 删除第 2 页，同时该页生成在运行 | 不复活删页，不提升孤儿结果；可恢复成果按策略归档 |
| 复用预览后更换文章/分镜/图片 | 旧确认被拒绝并保留待办，前端能恢复操作 |
| 任务启动 → 用户修改输入 → 旧任务成功 | 不替换当前素材、不结清新代次影响、不将当前项目标成已完成 |
| 多次导出与相同倍率调速 | 历史成果仍可读；新文件、sidecar、注册表一一对应 |

最新复用测试包含函数直接调用和替换项目查询；需要补真实 HTTP 入口的账号、错误码及版本检查验证，不能把现有单元测试当作端到端覆盖。

R1 退出：所有生成输入都有依赖映射；单页修改、无变化保存、过期任务三类场景有证据；保留旧成果与阻止错误复用同时成立。

## 6. R2：并发、重试、一键恢复与持久任务

源码入口：`generation_governor.py`、`llm_concurrency.py`、`one_click_orchestrator.py`、`one_click_resume_policy.py`、`image_workflow_service.py`、`tts_service.py`、`tts_provider_service.py`、`video_job_store.py`、`video_render_service.py`、`pptx_service.py`、`pipeline_lifecycle.py`。

测试入口：`test_generation_governor.py`、`test_governed_llm_and_recovery.py`、`test_llm_concurrency.py`、`test_image_gateway_budget.py`、`test_image_generation_dedup.py`、`test_image_generation_page_retry.py`、`test_one_click_orchestrator.py`、`test_persistent_tts_jobs.py`、`test_persistent_video_jobs.py`、`test_video_task_status_consistency.py`、`test_video_job_idempotency.py`、`test_manifest_refresh_lock_order.py`。

审查任务：

1. 画出请求额度、项目并发、页锁、项目产物锁和任务锁的获取/释放顺序；证明没有相反锁序。
2. 同网关、不同账号和项目必须共享总额度；项目并发只能缩小全局并发；检查网关键规范化和 image/LLM/TTS 的实际计费路径。
3. 分清“真实 HTTP 请求”“参数探测”“业务页重试”“子进程轮询预留”，统计最坏总请求数，避免各层重试相乘。
4. 配额耗尽允许排队；GovernorTimeout 映射暂停；认证失败、缺参考音频、确定性超大结果等不应进入无意义重试。
5. 任务从排队、领取、执行到成功/失败/中断，每个出口持久化；成功必须清空旧 error。
6. 提交幂等键覆盖实际输入；相同输入去重，输入改变不能错误命中旧任务。
7. 断点续跑重新验证真实产物及哈希；缺一页只补必要范围，不把完成状态当成产物存在证明。
8. 检查进程重启后的 interrupted 恢复、前端重新打开后的轮询恢复、失败 session 的 rollback 和关闭。
9. 上游长请求不持有不必要的数据库事务或大范围文件锁；用模拟延迟验证其他独立页仍可推进。

竞态复现用 Event/Barrier 控制执行次序，不靠随机 sleep。最少覆盖：重复点击、同页并发生成、跨项目共享网关、保存与生成交错、超时释放槽位、失败后重试、worker 成功但终态写失败。

R2 退出：没有无限等待/无限重试；结果归属和终态一致；请求成本有上界；恢复不扩大重做范围。

## 7. R3：AI Mask、双图、揭示层及图像输出

源码入口：`ai_mask_component_detection.py`、`ai_mask_object_graph.py`、`ai_mask_semantic_matcher.py`、`ai_mask_assignment.py`、`ai_mask_manifest_apply.py`、`ai_mask_doclayout.py`、`ai_mask_engine.py`、`ai_mask_config.py`、`scripts/build_reveal_scene.py`、`pptx_export.py`。

测试入口：`test_mask_source_pair.py`、`test_ai_mask_fine_grained_detection.py`、`test_ai_mask_adaptive_background.py`、`test_ai_mask_semantic_batches.py`、`test_ai_mask_semantic_protocol.py`、`test_ai_mask_provenance.py`、`test_ai_mask_doclayout_devices.py`、`test_reveal_mask_integrity.py`、`test_white_background_workflow.py`。

审查清单：

- 生成、上传、候选应用、交换图片均维护 raw/master/marker 一致性；有效配对才读 raw，失效配对逐字节回退 master。
- 静态页面与静态 PPTX 使用 normalized；检测、候选、多模态输入、揭示裁切使用正确版本，不能各读各的图。
- 非白底自适应与生成纯白外背景的职责分开，浅灰内容、封闭白区、抗锯齿和文字边缘保持。
- 岛状卡片不提前合并成文本行；布局框是证据，不能吞掉独立组件；超过 120 候选和多批结果不能静默遗漏。
- 分批 JSON 截断/无效只按约定有界修复；重复/不存在 ID、空分配、跨批冲突可诊断。
- 残余补全与 VL 纠错采用各自约定的距离，不能错误共享算法并重新引入错绑保护。
- 手绘修正不被自动结果覆盖；揭示 builder 不重新决定语义归属。
- 配置变化、算法版本、图像内容和设备/模型相关参数正确进入缓存键；缓存不能跨项目污染或无限增长。
- 重建时拒绝旧管线与无引用资源；已 Mask 页背景使用项目背景，不能露出整张原图。

验证分三层，报告必须分开：

1. **纯检测离线基准**：候选完整性、组件合并、像素前景；含答案的最佳分配不是 AI 标注准确率。
2. **完整语义标注**：冻结图片、旁白、组 ID、模型、Prompt 和配置；保留输入/输出摘要和回退原因。
3. **实际消费结果**：从保存的 RLE 构建揭示层，检查代表性帧及 PPTX；有指标通过也要查闪白、泄漏、错时出现。

硬性门槛沿用仓库契约：前景覆盖率 ≥99.5%、未分配组件数为 0、组间像素重叠为 0。另记录每组 precision/recall/IoU，使用冻结基准既定阈值；不以均值掩盖失败组。

样本至少包含：白/非白背景、浅底容器、封闭白区、2px/8px 间隔、同尺寸卡片行、共享外框、细线、密集对象、多批旁白、横/竖屏、手工纠错、破损 raw pair。历史“11/11”“14/14”是历史证据，不能代替当前 SHA 重跑；报告要注明样本集版本。

真实供应商调用另列样本数、模型和预算；先跑离线验证。基准 CLI 的 `generate/extend` 会改数据，冻结集不能在本轮随意重生。

R3 退出：像素、语义、下游播放三层都有证据；新增参数没有破坏旧图回退和手绘保护。

## 8. R4：勾画标注的定位、编辑与时间轴

源码入口：`annotation_contracts.py`、`annotation_store.py`、`annotation_service.py`、`annotation_jobs.py`、`annotation_alignment.py`、`annotation_target_resolver.py`、`annotation_geometry.py`、`annotation_timeline.py`、`annotation_runtime.py`；前端 `static/annotations_core.js`、`annotations_workspace.js`、`annotations_editor.js`、`annotation_playback.js` 和 Remotion `AnnotationOverlay.tsx`。

测试入口：`test_annotation_store.py`、`test_annotation_jobs.py`、`test_annotation_alignment.py`、`test_annotation_target_resolver.py`、`test_annotation_geometry.py`、`test_annotation_timeline.py`、`test_annotation_invalidation.py`、`test_annotation_impact.py`、`test_annotation_workspace.js`、`test_annotation_playback.js`。

重点案例：

- 中文、英文、emoji、重复词、日期、百分比、跨行文本：Python codepoint 与 JS UTF-16 位置一致。
- OCR 空结果、低置信度、重复标签和图像替换：不能静默标到另一处；清楚区分自动定位与人工修正。
- 横竖屏、缩放、滚动、高 DPI、边缘区域：编辑坐标正确映射回源图。
- A 页编辑→B 页→撤销，不改 A 页；A 项目请求晚于 B 项目返回，不污染 B 项目。
- 两标签页同时编辑触发 revision 冲突时保留本地草稿，不能把服务器新内容静默覆盖。
- OCR/AI 计划运行中手工修改：旧计划不覆盖新标注；取消、重试、页面删除、项目关闭均正确收尾。
- 旁白/TTS 改动后，勾画时间与空间失效分别处理；相同保存不生成新代次。
- 勾画启用、关闭、未决定三种状态的完成条件明确；一键模式、侧栏、导出和 Agent 进度一致。
- 浏览器预览与 Remotion 在相同时间点输出相同笔画进度，特别测试 t=0、起止边界、页尾、调速和 seek。

`annotation_service.py` 本次新增规模超过千行，是阅读与边界审查信号；是否应拆分要看职责泄漏、循环依赖和可测性，不能仅因行数判缺陷。人工比较实际帧；`docs/annotation-validation/` 是历史验收材料，需核对对应实现版本。

R4 退出：不串页、不丢编辑、不被旧任务覆盖；定位和播放在两种画布下可核对；完成状态遵循保存的用户决策。

## 9. R5：多账号、配置、Agent 契约、迁移与安全

源码入口：`account_context.py`、`creation_config_service.py`、`creation_config_models.py`、`model_connection_service.py`、`config_portability_service.py`、`settings_service.py`、`app_security.py`、`agent_contract/`、`agent_api/`、`cli/`、`database_migrations.py`、新增迁移 `0006`–`0015`。

测试入口：`checks/agent/`、`test_creative_accounts.py`、`test_course_account_isolation.py`、`test_creation_config.py`、`test_creation_config_defaults.py`、`test_project_config_runtime.py`、`test_config_export_security.py`、`test_config_import_limits.py`、`test_config_portability_multi_account.py`、`test_database_migrations.py`、`test_app_security.py`、`test_tts_secret_transport.py`。

审查内容：

1. 建账号 A/B，逐项测试项目、课程、配置包、风格模板、模型连接、任务状态和产物下载；知道对象 ID 不能跨账号读取/修改。
2. 后台任务启动时固化账号/配置上下文，切换前台账号或默认配置不会改变在途任务归属。
3. 全局、账号默认、项目覆盖、配置包版本的优先级与空值语义统一；掩码密码保存不覆盖真实密钥，显式清空有明确语义。
4. 配置导入先完整验证再写入；损坏文件、超大包、路径穿越、重复引用、缺参考音频均不得半导入。
5. 上传/下载、压缩包路径、图片远程地址、重定向、输出路径、子进程参数和日志分别检查信任边界；依据实际允许的本地供应商规则验证，不一刀切禁用合法本地地址。
6. 内部请求模型新增字段必须在 parity 映射中明确公开或隐藏；公开字段穿过 API/MCP/CLI 后值不丢失。
7. 新复用接口、影响查询、勾画功能等逐条核对注册表；并非所有内部路由都必须公开，但应有明确映射或豁免理由。
8. 版本、contract hash、生成文档、OpenAPI 与真实路由一致；读取公共路由使用 `route_inventory.py`。
9. 空库升级、旧版库升级、已是新 schema 但空 ledger、重复启动、错误 checksum、中途迁移失败分别验证；已应用迁移不得修改。
10. 检查 Python 和 npm 锁文件差异；依赖升级单独查官方 changelog、兼容变化和公开安全公告，记录查询日期。不能只报告安装成功。

Agent 契约出现修改时，按 `AGENTS.md` 更新能力版本/API 版本、字段映射和生成文档；不要通过放宽 parity 断言隐藏不同步。

R5 退出：跨账号访问矩阵通过，凭据没有进入日志/导出非授权字段；契约可验证；迁移失败不会被泛化吞掉。

## 10. R6：前端、媒体成品与完整场景验收

前端入口：`static/workspace_navigation.js`、`workflow_state.js`、`flow.js`、`creation_config_management.js`、`output_render.js`、`event_bindings.js`。视觉对照使用 Stitch 源码和当前末尾样式层。

媒体入口：`narration_audio_service.py`、`tts_artifacts.py`、`scripts/build_remotion_props.py`、Remotion 组件、`video_artifact_service.py`、`pptx_service.py`、数字人服务和便携包构建脚本。

必须人工走通的场景：

| 编号 | 场景 | 观察点 |
| --- | --- | --- |
| E01 | 横屏三页，引导模式，Mask 开、勾画开、数字人关 | 八步顺序、音频确认、揭示、勾画、视频/PPTX |
| E02 | 竖屏三页，Mask 关、勾画关、数字人关 | 静态整页、字幕安全区、跳过状态与完成进度 |
| E03 | 一键模式，部分页生图失败后继续 | 只补缺页、额度排队与暂停、进度单调且可信 |
| E04 | 已完成项目，按 R1 矩阵修改上游 | 影响范围、复用确认、旧成品可看、新输出门禁 |
| E05 | 数字人开启并完成一次输出，再关闭/更换音频 | 可选 Step 7 保留位置；关掉不阻塞；旧口型不复用 |
| E06 | 两项目、两标签页、切账号、刷新、关闭重开 | 异步归属、草稿、持续任务与错误恢复 |
| E07 | 连续两次导出、同倍率调速、删除某一版本 | MP4/sidecar/注册表一致，历史版本不误删 |
| E08 | 旧数据升级与便携包干净目录启动 | 模型路径、字体、参考音频、依赖、端口占用处理 |

对每个 MP4 检查：分辨率、帧率、总时长、音轨、字幕换页与累计漂移、页尾留白、首尾帧、Mask 时序、勾画时序。抽查中间页边界，不能只播放开头。

PPTX 检查页数、顺序、画布比例、图片完整性及预期揭示裁切；字体/字幕和数字人不应触发重新绘制 PPT 正文。Remotion 可以渲染已允许的覆盖层，PPT 主体仍来自批准的位图。

性能记录建议用相同机器/配置比较三档页数（3/10/30 页，资源不足时注明），分别记录请求排队、检测、模型、合成、渲染、内存峰值和磁盘增长。先定可接受预算再验收，不编造统一毫秒门槛；真实付费阶段先以少量样本验证。

R6 退出：重点场景有可复查证据；缺环境的数字人/真实供应商/便携包验证标“未验证”，不能被单元测试替代。

## 11. 可执行命令与结果记录

以下为 PowerShell，均在仓库根目录运行。先建立独立审查目录，并覆盖本轮测试环境变量；不要直接继承可能指向真实数据的变量。

```powershell
$reviewBase = '1b66bbea4a454292c289895fb15a3f90ac0993ef'
$reviewHead = '62d50522914cb60949318e064b75f85b396244c1'
$reviewRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('ppt-review-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $reviewRoot | Out-Null
git diff --name-status $reviewBase $reviewHead | Set-Content (Join-Path $reviewRoot 'changed-files.txt')
git log --oneline "$reviewBase..$reviewHead" | Set-Content (Join-Path $reviewRoot 'commits.txt')
git status --short
git rev-parse HEAD
Write-Output $reviewRoot
```

确认当前检出代码与记录的目标版本一致。变更后的复验使用新 SHA，明确与原审查目标的关系。

```powershell
$reviewPreviousDb = $env:PPT_STUDIO_DB_PATH
$reviewPreviousRuns = $env:PPT_STUDIO_RUNS_DIR
try {
    $env:PPT_STUDIO_DB_PATH = Join-Path $reviewRoot 'projects.db'
    $env:PPT_STUDIO_RUNS_DIR = Join-Path $reviewRoot 'runs'

    python scripts/run_checks.py --level full --with-remotion 2>&1 |
        Tee-Object -FilePath (Join-Path $reviewRoot 'full-checks.log')
    $reviewCheckExit = $LASTEXITCODE
    if ($reviewCheckExit -ne 0) {
        throw "Full checks failed with exit code $reviewCheckExit; inspect full-checks.log"
    }
}
finally {
    $env:PPT_STUDIO_DB_PATH = $reviewPreviousDb
    $env:PPT_STUDIO_RUNS_DIR = $reviewPreviousRuns
}
```

`--with-remotion` 会执行 `npm ci`，重建依赖目录；这是运行步骤说明，本方案制定时没有执行。检查器遇到首个失败会停止，因此有失败时不能声称后续检查通过。修复/解释首个失败后继续记录未执行项。

以下命令用于定位失败或专项复验，应在相同隔离环境下运行；已经由 full 成功覆盖的部分不必无原因重复：

```powershell
python -m pytest checks/test_investigation_gates_phase4.py -q -rxXs
python -m pytest checks/test_article_storyboard_reuse.py checks/test_storyboard_image_reuse.py checks/test_project_impact_service.py checks/test_async_input_promotion.py checks/test_render_input_impact.py -q
python -m pytest checks/test_generation_governor.py checks/test_governed_llm_and_recovery.py checks/test_image_gateway_budget.py checks/test_video_task_status_consistency.py -q
python -m pytest checks/agent/ -q
python scripts/generate_agent_contracts.py --check
node checks/test_narration_project_scope.js
node checks/test_annotation_workspace.js
node checks/test_annotation_playback.js
node checks/test_mask_zoom_coordinates.js
```

脚本式检查、pytest 测试、Node 检查与真实渲染是不同层级。核对 `run_checks.py` 的实际包含项，补跑未登记的新测试；不要把所有 `test_*.py` 都假定为 pytest 可收集用例。

对已准备好的隔离样本运行产物验证，参数指向该样本的实际 run 目录：

```powershell
# 先将 $reviewRunDir 设置为隔离环境中已生成完整产物的具体项目目录。
python scripts/validate_reveal_scene.py --run-dir $reviewRunDir --repo-root .
python scripts/validate_run_assets.py --run-dir $reviewRunDir --repo-root . --require-layered
```

`--require-layered` 仅用于需要分层揭示的样本；关闭 Mask 的静态样本按其模式验收。真实 E2E 脚本先审查配置来源和创建项目行为，再执行，不直接对用户当前服务运行。

## 12. 合并、Prompt 与架构专项

合并提交单列审查：`8da90f6`、`12aae0a`、`21eacda`、`5670f0e`。比较每个父版本与合并结果，重点看并发双轨、AI Mask 默认值、配置字段和注册入口；没有文本冲突也可能丢一侧语义。使用 `git show --cc <commit>`，必要时补 `git diff <commit>^1 <commit>` 与第二父版本比较。

架构审查执行已有 composition/size/ownership 检查，并抽样追踪实际依赖：

- `server.py` 保持组合根；服务不接收整个应用模块。
- 配置、Prompt、纯规划、LLM 请求与持久化各归其所有者。
- 业务失效由指定服务处理，调用者负责一次提交；新影响先登记。
- 前端新模块显式加载，生命周期与事件绑定次序正确，跨模块通过明确桥接。
- 新兼容层、重复规范化和静默 fallback 必须有行为依据；不要为了行数把复杂性原封不动搬到另一文件。

对实际修改过的生产 Prompt 单列输入输出链审计：System、用户输入、图像、解析、修复、降级和消费方。遵循 `.agents/skills/optimize-prompts/SKILL.md`；若实施 Prompt 修改，必须先使用该技能。检查默认 Prompt 迁移只命中旧内置模板，不覆盖用户自定义内容；预览与真实请求一致。

## 13. 问题模板、优先级与最终放行条件

每条问题采用以下模板：

```text
编号 / 优先级：R1-001 / P1
标题：具体触发条件下出现的具体错误
审查目标 SHA：
文件与准确行号：
关联提交（能确定时填写）：
前提与最小复现步骤：
预期 / 实际：
证据：失败测试、调用链、日志或产物哈希
影响范围：项目/页/账号/产物，是否可恢复
根因与建议修复归属：
修复前失败的回归测试：
修复 SHA / 复验结果：
状态：已证实 / 待调查 / 已解决 / 接受延期
```

优先级规则：

| 等级 | 定义与处置 |
| --- | --- |
| P0 | 严重凭据泄漏、广泛不可恢复的数据破坏等：停止相关发布/操作，立即处理 |
| P1 | 常见路径数据丢失、跨账号访问、旧任务覆盖新结果、核心流程不可用：放行前修复 |
| P2 | 有范围限制且可恢复的行为错误、明显性能或维护性退化：明确修复计划或记录接受理由 |
| P3 | 可选可读性/样式建议：单独列出，不遮盖真实缺陷 |

最终放行清单：

- [ ] 目标版本、范围、环境、未验证项明确；所有高风险变更组都已覆盖。
- [ ] 没有未解决 P0/P1；P2 延期有影响说明、负责人与后续事项。
- [ ] 已证实问题有复现和复验记录；新测试能够检出原错误。
- [ ] full 检查与 Remotion 类型检查完成；skip/xfail 单独解释，未知失败未被消音。
- [ ] 单页变化、无变化保存、跨项目异步、过期任务、重启恢复通过。
- [ ] Mask 像素与语义门槛通过，标注预览与实际视频一致。
- [ ] 账号/Agent/迁移/配置导入矩阵通过。
- [ ] 代表性 MP4、PPTX、字幕和历史输出生命周期已人工验证。
- [ ] 未修改用户真实数据，没有提交运行产物或敏感信息。

推荐从 R0 开始，随后优先完成 R1 与 R2。它们决定其他模块的成果是否会被正确保留、正确判定为过期，并被正确的任务和项目消费。
