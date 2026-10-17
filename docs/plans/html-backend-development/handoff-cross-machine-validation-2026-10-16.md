# 换机测试交接：HTML Studio，2026-10-16

## 结论与交付边界

另一台电脑要验证**当前代码能否从新项目完整运行**，不需要本机 `data/`、`runs/`、`outputs/`。从 `origin/main` 获取源码、单独配置依赖与模型凭据、创建新测试项目即可。这是本轮推荐的测试方式，也能揭示对本机缓存或旧任务的隐性依赖。

若目标改为**继续本机第 4 页的同一设计候选或核查原供应商请求**，则需要本机项目数据库、对应 `runs/` 产物和原设计图的完整身份链；仅有源码或一张图片不足以恢复原任务。这些数据不得提交到仓库：`config/git_policy.yaml` 明确禁止运行输入和生成媒体，`.gitignore` 也排除 `data/`、`runs/`、`outputs/`、`.env`。需要迁移时另走受控的离线传输，并在目标机核对哈希、路径、数据库与任务回执后再操作；不要在 Git 中强制加入、公开发布或直接合并两个数据库。

当前 handoff 只提交无凭据的流程事实与测试说明。原始测试产物、供应商响应、设计图片、模型配置及凭据仍留在本机；本文件不能作为原候选的人工批准回执。

## 本机测试转化成了什么

不是所有发现都已经修好。已经修复的部分通过源码、注册规则和回归测试进入仓库；尚未修复的真实供应商结果则作为明确停点保留，换机时重新验证其发生率和原因。

| 本机实测发现 | 当前处理 | 带到新电脑的回归证据 | 仍需真实验证 |
| --- | --- | --- | --- |
| 场景规划长推理耗尽输出额度，末尾 JSON 截断 | GLM 场景规划请求级 low；完整 `length` 归类为输出额度耗尽；结构修复保持有界 | `checks/test_json_llm_transport.py` 的 effort/输出额度测试及 `checks/test_html_semantic_design.py` 的规划修复测试 | 九页在新机器、新供应商会话中的完成率与语义质量 |
| 标注目标误用图片焦点名，直到设计后才失败 | 规划阶段前移 `targetId`、`anchorId`、`labelId` 身份校验 | `checks/test_html_semantic_design.py` 的无效/合法标注引用测试 | 新真实计划是否一次提供正确引用 |
| 设计理解流长时间只有推理，断流后结果未知 | 仅该阶段使用请求级 low；区分读静默、总预算与未知结果，禁止盲重发 | `checks/test_html_design_agent.py` 的推理档测试，`checks/test_json_llm_transport.py` 与 `checks/test_html_production_stages.py` 的断流/禁重试测试 | 真实供应商长期传输可靠性；旧请求是否计费仍未知 |
| 模型给无 heading 的 summary 选择需 heading 的变体，浪费下游素材调用 | 按编译前置条件过滤不适用变体，并校验分工返回 | `checks/test_html_design_agent.py::test_variant_with_required_heading_is_not_offered_or_accepted` | 其他变体在真实内容容量下是否合适 |
| 第 4 页三张已有图标的卡片被误报为缺组件 | 输入增加只读 `currentRender.icon`，保留严格图标编辑限制 | `checks/test_html_design_agent.py::test_existing_card_icons_are_rendered_without_editable_icon_choice`；同一设计真实请求已返回 `ready` | 后续 HTML/视觉是否忠实呈现图标和版式 |
| 独立素材调用 102.5 秒后本地 `ValueError`，无图片或完成标志 | **未修复供应商/网关根因**；任务按外部结果未知停止，没有自动重发 | `checks/test_html_production_stages.py` 的未知结果与禁重发、`checks/test_html_production_recovery.py` 的回执/查单恢复测试仅验证安全边界 | 精确异常来源、供应商侧结果、可查单/回执、再次调用的成功率与费用 |

上表中的自动化测试是从事故中提炼的可重复输入和断言，不依赖本机数据库。真实图像质量、第三方传输和未知请求的供应商侧状态不能靠这些替身测试证明；这正是换机真实测试要补的证据。

## 当前源码与真实案例

- 目标仓库：`https://github.com/fanke52013141-cmd/PPT_HTML_Studio` 的 `origin`。禁止推送到原图片项目的 `upstream`。
- 截至写入本文件，本机 `main` 的最近提交为 `241b980`，另有未提交的设计理解、传输、恢复、测试和契约修改。**新电脑测试前必须先提交并推送这些修改，再记下实际远端提交 SHA；只克隆当前远端会漏掉本轮修复。**本文件本身也需包含在该提交内。
- 固定真实案例：“什么是遴选考试”，九页规划，每页三张卡片。第 4 页计划中的图标为 `document`、`speech`、`lightbulb`。原设计候选 key 为 `13d26b2eac59badc869d46df37e4922c0cb72d226c81ece65797a0671c90e7f8`，图片 SHA-256 为 `51beb1199dd7205a1b3eb9a7d2a4693076ae40eb4ed1765923d72e0e17a3af42`；它只获准用于本机系统还原测试，不是最终视觉批准。该图**不在仓库里**，新电脑不能声称复用了它。
- 原设计理解请求 `html_de9f9435250040c5a5fd` 在推理流中断后结果未知；最后新任务 `html_c64721ec3f3a4b549564` 的设计理解已通过，随后独立素材请求约 102.5 秒后在本地以 `ValueError` 停止，并标记 `EXTERNAL_OUTCOME_UNKNOWN`。素材请求 ID `1aa69ec3d45545ac6d667a3f9a3ecda3dd5e2019ff038be32fedb39201fec1a2`；供应商不可按该 ID 查单，没有返回图片、用量或完成标志。**不要在新电脑把该请求当失败而自动重发，也不要伪装为原任务续跑。**当前没有第 4 页 HTML 或保真截图。
- 本机更详细的原始报告位于忽略目录 `outputs/live-linxuan-runtime-20261016-131819/nine-page-planning/slide-004-html-reconstruction-test.md`；换机后默认不可访问。此处记录了复验所需的无敏感结论。

## 新电脑操作顺序

1. 在本机完成代码提交与 `origin` 推送，记录 `git rev-parse HEAD`。在目标机克隆同一仓库并核对 `git rev-parse HEAD` 与远端提交一致；不要从历史 handoff 的旧提交直接开测。
2. 在目标机创建自己的 Python 虚拟环境，按 `requirements.lock` 安装依赖；需要视频工程时在 `scripts/remotion` 执行 `npm ci`。Windows 启动路径以目标机的实际 checkout 为准，不照抄本机 `D:` 路径。仓库里的旧 README 启动脚本说明可能不对应当前 checkout；先确认实际文件存在，再用 `start_server.py` 启动。
3. 创建目标机独立的 `data/projects.db` 和 `runs/`，启动前显式设置 `PPT_STUDIO_DB_PATH`、`PPT_STUDIO_RUNS_DIR`、`PPT_STUDIO_PORT`。不要指向本机原图片项目的数据目录，不复制 `.venv`、`node_modules` 或进程锁。模型供应商凭据只在目标机本地设置，不进 Git；按应用现有设置界面重新绑定所需模型。无需把本机 `.env`、数据库或模型配置包上传仓库。
4. 先跑隔离回归：`python -m pytest checks/test_html_design_agent.py checks/test_html_production_recovery.py checks/test_html_runtime_skills.py -q`。再启动服务，确认当前源码页面和项目创建、模型连接；测试使用新建项目，不使用生产/原图片项目数据库。
5. 真实流程从文章/主题输入开始，核对九页讲稿与画面语义，选择并确认**新生成的具体设计候选**，再由系统 Agent 做设计理解、独立素材、HTML 还原、工程检查和视觉/逐句语义审核。每个阶段分别记录任务 ID、候选 key、请求/回执、模型调用次数、耗时、结果状态及产物哈希；不要用 Codex 手写 HTML 代替系统 Agent。
6. 任一阶段出现 `EXTERNAL_OUTCOME_UNKNOWN` 时停在原请求，先核对目标机回执/产物与供应商可查单能力；未知不能按普通失败自动重试。设计理解 `ready`、工程通过、视觉批准、讲稿画面对应和最终输出分别判定，不互相替代。

## 换机验收口径

至少记录：目标机 Git SHA、Python/Node 版本与依赖安装结果、所用隔离数据库/运行目录、应用版本、真实模型绑定（不含密钥）、九页规划结果、设计候选身份、设计理解输出、素材/HTML 产物、工程与语义审核，以及任何未知请求的查单/回执证据。与本机比较的是**固定流程和失败分类**，不是把新生成的视觉图误称为原候选的逐像素复现。

本机已经验证卡片现有图标与可切换图标的能力说明修复：设计 Agent 25 项、恢复流程相关 17 项、运行 Skill 44 项通过。真实同候选复验只证明设计理解跨过了卡片图标误判，素材阶段结果未知；HTML、视觉保真和整课输出均未通过。若新电脑要专门诊断素材供应商可靠性，须使用新任务并单独记账，不继承原未知请求的状态或人工批准。

## 追加测试记录：先测完，再统一优化

2026-10-16 在当前工作树上只做测试与取证，未根据以下新失败修改生产实现：

| 测试 | 结果与证据 | 后续分诊 |
| --- | --- | --- |
| `scripts/evaluate_html_workflow.py` 固定事故清单 | 30/30 通过；隔离报告在本机忽略目录 `outputs/workflow-evaluation-20261016-v10-pre-optimization/report.md` | 工程回归通过，不等于真实模型或九页成片通过 |
| `checks/test_html_production_integration.py`、`test_html_semantic_qa.py`、`test_html_audio_binder.py`、`test_html_render_runner.py` | 42 通过、2 失败。失败为 `test_replanning_keeps_manual_title_and_private_anchor`、`test_replanning_conflict_preserves_current_scene`；两项都在到达原断言前收到 `DESIGN_PROVIDER_MISSING` | 判断是新“设计先行”门禁后测试夹具缺少 provider，还是重新规划路径出现行为回归；不要仅改断言掩盖人工保护测试 |
| `html_engine/visual/tests/capacity.test.cjs` | 通过 | 仅容量诊断，不含真实设计审美 |
| `html_engine/visual/tests/verify.cjs` | 首轮 `Theme neutral-science seek must be deterministic` 失败，立即复跑 14 项、5 场景、0 页面错误通过 | 记录为可复现性/时序波动待调查，不能只报第二次通过 |
| `checks/test_html_semantic_qa.cjs`、`test_html_audio_review_runtime.cjs`、`test_html_workflow_status.cjs` | 均通过；分别为浏览器替身语义 QA、合成 WAV 音画时钟、持久任务 UI | 不代表真实 TTS、真实九页逐句审核或用户试听 |
| 第 4 页旧素材与最新未知请求核对 | 旧任务 `html_7a50f2a7d331460fae64` 返回的 `slide-004-exam-scenes-ff6a64863376.png` 文件存在且 SHA-256 匹配旧记录；最新任务 `html_c64721ec3f3a4b549564` 只有 unknown 回执，没有对应返回图片。两次请求键不同 | 旧素材可作为独立离线诊断证据，不能冒充最新未知请求返回，也不能因此解除禁重发门禁 |
| 第 4 页历史素材的隔离静态渲染 | 在忽略目录 `outputs/slide-004-historical-asset-static-diagnostic-20261016/` 用旧任务编译场景及上述有效素材运行共享 `review_scene`，`passed=true`、无页面错误并生成截图 | 证明旧素材可被当前渲染链消费；该场景在设计理解分工操作之前，截图与已确认设计的标题徽章、右侧主体尺寸/位置及底部关系布局有明显差异。既非最新任务输出，也非系统 Agent 完整还原；不得算视觉保真通过 |
| `checks/test_ai_provider_service.py`、`test_html_asset_service.py`、`test_html_visual_review.py` | 22/22 通过；覆盖提供者替身、资产与静态审核 | 不能由替身通过反推出真实素材 `ValueError` 的供应商根因 |

待统一优化的新增条目：人工编辑后重新规划测试的 provider 前置条件；视觉 seek 偶发不一致；独立素材 `ValueError` 的原始来源与供应商结果核实。前三项分别属于测试/行为分诊、渲染稳定性、外部传输/回执，不应合并成一个“HTML失败”结论。当前仍没有真实第 4 页 HTML 或九页端到端成功证据。

### 第 2 页独立真实实验

为继续测试而不重发第 4 页未知素材请求，从语义抽查对应的第 2 页通过系统 `html_review.produce` 新建任务 `html_74c1f326eb194a819700`，`plan_version=0.2.0`。首次规划有一次结构/身份修复；原整页设计生图请求被标记 unknown，但保存了可查的上游任务 ID `tsk_img_01M521TW30BK4D4BQDRK3EMC9N`。随后同输入提交触发系统**查询原上游任务并对账返回图片**，原任务进入 attempt 2，没有重新 POST 第一次图片请求。

attempt 2 复用了第一轮规划响应一次，但修复轮再次调用模型，形成不同的图片阶段 key，并发起第二个设计生图请求；两张返回图片分别绑定各自阶段身份，不能互换。最终任务在 `design_review` 成功停下，累计规划适配器调用 3 次/复用 1 次、设计生图调用 2 次；没有生成主体素材、HTML 或作者保存。当前设计候选 `ef5f82fe841a50d7ffb78171c8f274a9192a6f4393bcac4ae3f6e8959ba2290a`，图片 SHA-256 `1c54c9b48da8b42e2305302a98c0c0570e4b94fdfbf2729265392b332dc02a1c`，文件仍在本机忽略的 `runs/` 下。已展示给用户，**是否用该具体图做还原测试仍待明确确认**；设计阶段完成不等于视觉批准。

待统一优化另记：规划修复在恢复尝试中是否应复用确定性结果，以免同一业务提交衍生新图片阶段与第二次付费生图。先核实输入/诊断/阶段 key 的实际差异，再决定是否属于实现缺陷；本轮不改代码或归咎于供应商。

### 2026-10-17 开发续进

两项“人工编辑后重新规划”旧测试在进入合并逻辑前触发 `DESIGN_PROVIDER_MISSING`，是测试夹具未提供现行设计先行门禁所需的候选。现将两项收窄为人工差量合并和冲突的纯逻辑测试；实际设计候选→生产路径仍由 `test_html_e_production.py` 覆盖。两组共 40 项通过。此修正不意味着第 2/4 页真实 HTML 已通过。

第 2 页重复生图的本地机制已定位：恢复尝试复用首轮规划响应，但修复轮再次调用模型，得到另一份合法计划；设计请求键随计划变化，因此又调用生图。生产任务原本在第一次完成规划后已经保存 `phase:plan`，现让恢复尝试先读取并校验该密封阶段产物，再沿相同计划继续。损坏或非 JSON 的阶段产物失败关闭，不能回退为重新调用规划模型。该改动只适用于同任务快照与源码仍有效的恢复；新提交、人工修改、定义变化仍按原门禁处理。新机器需用一次真实可查单的中断/恢复实验验证适配器实际调用次数；当前未对原第 2 页候选发起 HTML 还原。

2026-10-17 隔离故障注入进一步覆盖**真实任务执行器路径，但模型和图片供应商使用替身**：规划首轮故意缺失 `templateRef`，真实校验器触发一次有界修复；设计图返回后、候选写入前人为中断，再按同一任务 ID 恢复。首次运行暴露参考包装配器拒绝覆盖已存在目录，尽管规划/图片均未重调；现改为对同计划/brief/定义哈希路径上的已有包执行严格 `verify_package` 并复用。复测任务成功停在 `design_review`，规划适配器总调用 2 次（首次及修复）、图片适配器总调用 1 次，恢复阶段新增调用均为 0。损坏包会验证失败关闭，不能以目录存在冒充有效参考。该实验没有调用真实供应商；真实 ToAPIs 查单、模型计费和网络中断恢复仍待隔离实测，不能据此宣称线上问题完全关闭。

本轮相关完整回归：`checks/test_html_production_stages.py`、`test_html_production_recovery.py`、`test_html_e_production.py`、`test_html_production_integration.py` 共 **76 项通过**；`git diff --check` 无空白错误。运行时 8010 服务未启动，故本轮没有对现有九页项目或真实供应商发起新请求。

### 2026-10-17 真实供应商传输探针

在独立 `outputs/live-provider-recovery-b83c79251a1245baa5fe8cc5cdb6c648/` 数据库和运行目录中，以现有项目的只读图片模型绑定发起**一次**真实 ToAPIs 图片任务，并设置“上游任务 ID 一到即中断”的本地故障注入。约 9.6 秒后本地得到 `EXTERNAL_OUTCOME_UNKNOWN`，任务 `html_288f59aa77314ab5a622` 的 image 阶段没有收到/登记 `upstream_task_id`，`lookup_supported=false`，错误被图片边界包装为 `ValueError`。无法由此证明远端没有接收或计费；禁止再次提交该请求，也不能按任务 ID 查单。探针未写现有九页项目。忽略目录保留原数据库和回执供本机核实；不要将其或任何凭据提交仓库。

为使下一次同类故障可定位，图片服务对已结构化的 `ImageGenerationError` 现在只向任务记录传递白名单错误 `code` 和 `phase`，不传上游响应、密钥或异常文本；没有结构化错误的场景仍只记安全异常类，不臆测提交阶段。隔离测试证明 `submit/connection_reset` 元数据能写入 unknown 回执且不泄露原文。此改动不能追溯补全上述未知任务，也不放宽禁重发门禁。真实可查单恢复的端到端验收仍待**另一个明确隔离实验**；在此之前不能宣称线上传输可靠性已解决。

相关回归 `test_html_production_stages.py`、`test_html_production_recovery.py`、`test_ai_provider_service.py` 共 **45 项通过**。
