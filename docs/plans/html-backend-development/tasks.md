# 可直接执行的任务分解

所有新增名称均是本计划的建议落点，不代表文件或 API 已存在。执行前核实仓库当前实现，复用已有等价模块并记录调整。每项完成须提供代码提交、测试结果、证据路径及未解决项；同步契约/Agent 接口是该功能的一部分，不能全部拖到 F01。

## A00 源码、环境与基线

依赖：无。验收 AC01。

1. 阅读 AGENTS.md、README_HTML_STUDIO.md、规范入口及本交接包。记录分支、HEAD、工作区改动、远端、数据库/runs 配置和运行端口；禁止输出密钥。
2. 对照 `docs/baseline/source-snapshot.json` 确认原应用完整存在。保存基线测试结果，区分既存失败与新增失败。
3. 同机器执行使用唯一目录；远程执行若缺少 `server.py`、`database.py`、`static/` 等，先取得经审计的源码基线。应用源码发布是独立变更：排除配置密钥、真实数据库、runs、缓存、依赖目录，登记原提交和复制时差异，不能把 docs-only main 当成完整应用。
4. 固定 Node/Python/Chromium/FFmpeg 版本及字体清单。建立隔离测试 DB/runs，正常启动仍沿用快捷方式。

产物：`docs/baseline/html-adaptation-baseline.md`（建议新增），环境与基线报告。缺源码则该任务 blocked，不编造后续实现；可以继续规范工作。

## A01 契约与版本

依赖 A00。参考 OSS-01。验收 AC02。

对照 `html_engine/visual/` 0.1.0 和 style-review，补新能力定义卡：panel/gradient/icon、布局槽位、过程对象、动作、资源就绪、样式注册和模型输出边界。建议新版本 0.2.0，最终以定义卡确定；不得静默扩宽旧 Schema。

规定主题属性集合、公共组件参数、实例字段和派生字段。每个字段记录默认值、范围、所有者、序列化、兼容/迁移、影响下游、失败诊断。设计 `visual_backend=image|html`，与 `production_mode`、`presentation_mode` 正交；首发 HTML 仅 guided+16:9，不支持的组合明确拒绝。明确 ready/renderAt/getGeometry 类接口的输入单位和坐标空间。

产物：新运行时定义卡/Schema 版本卡、兼容表、后端状态图。旧 E1/E2/visual-v1 保留版本语义。

## A02 科普风格进入公共组件

依赖 A01。参考 OSS-01。验收 AC02、AC04。

从 `visual/style-review/{components.css,icons.cjs,style.json,layout.json,sample.cjs}` 提取公共组件能力，进入共享 compiler/renderer 与主题注册。先做标题、知识卡、图标气泡、插图容器、关系条、数据强调；主题数据声明渐变、边线、层次、图标尺度，不保留一个仅能运行样板的分叉渲染器。

用原水/冷杯内容生成与样板相同的固定时间截图；逐项对照参考特征。保持来源元数据，辅助栏目默认关闭。字体明确打包/授权来源和实际加载，禁止静默字体回退。旧格式用显式适配器或旧播放器读取。

产物：注册组件、科普主题、迁移 fixture、视觉对照报告；用户未看过记录 pending_review。

## A03 受约束模板与效果图缓存

依赖 A02。参考 OSS-01/02。验收 AC03、AC06。

至少建设三种语义结构：图文讲解、原生数据/关系说明、对象过程舞台；左右互换不算两类。标题可选、容量上下界、主体槽位、字幕安全区均可校验。过长内容返回拆页/改稿诊断，不自动缩小至不可读。

注册 CSS/SVG/Canvas 效果的 ID、用途、backend、可调参数、确定性时间接口、适用/禁用条件。实际渲染效果图，标明 ID/backend/用途；按 theme/layout/effect/font 版本与渲染器 hash 缓存。选取本场景需要的子集；引用同一缓存图，无需每页重画。约束同步写入后续提示词上下文。

产物：模板定义、效果注册、缓存 manifest、可重复生成工具。

## A04 共享离线播放器接口

依赖 A02。参考 OSS-03/05。验收 AC05。

在 `visual/player.cjs`、`renderer.cjs`、`build.cjs` 统一包的资源就绪、确定性 seek、几何查询、诊断接口。字体/图片未就绪必须失败而非截空白。Canvas 随机状态固定 seed，不能依赖 Date.now、增量累加或 CSS 自运行时钟决定导出状态。

新增预览/导出 harness，二者使用同 bundle。允许项目内注册资源；拒绝模型脚本、任意路径、外链资源和未注册效果。保留旧包，不重写 E1。

产物：版本化播放器 API、独立 harness 和重复 seek 测试。

## B01 后端类型入库与项目配置

依赖 A01。验收 AC08。

修改 `database.py`、`project_service.py` 的 ProjectCreate/Update/输出、`project_routes.py`、creation_config 系列及项目 UI。新增迁移文件建议 `0017_project_visual_backend.sql`，执行时检查最新序号；遵守 `database_migrations.py` 校验与回放，不修改已应用迁移。旧项目回填 image。

已有作品不可直接切换后端导致旧产物误用；首发禁止已有生产内容项目切换，UI 说明新建项目。同步 `agent_contract/models.py`、capabilities、versions、API 映射及生成文档。

产物：迁移、后端字段完整链路、配置兼容测试。

## B02 HTML 存储、版本与失效

依赖 B01、A04。验收 AC09、AC18。

新 `html_visual_store.py`（建议）使用 `repository_paths.py`、`project_storage.py` 安全路径。每个场景分别保存语义计划、设计引用、scene definition、资产 manifest、review 状态、动作及绑定结果；所有中间产物标注生成输入 hash、版本和来源，不覆盖唯一已确认版本。

复用 `artifact_registry.py`、`artifact_fingerprint.py`、`impact_registry.py`、`project_impact_service.py`、`invalidation_service.py`。新增 HTML 影响规则并同步 downstream-impact 文档；主题变更不重新合成未改的音频，讲稿变更不得保留旧音频确认。

现有 revision 注释偏 Agent 可见更新；明确 HTML 编辑无论 Web/Agent 都必须 expected_revision 并在同一事务比较和更新。冲突返回 409，不丢人工修改。服务不自行提交调用方事务。

产物：数据目录约定、修改/失效矩阵、并发与回滚测试。

## B03 按后端分派原流程

依赖 B01、B02。验收 AC08、AC20。

修改 `static/flow.js`、`project_runtime_service.py` 和 UI 状态映射。沿用原八步外壳：导入、分镜、视觉生产、对象/动作、音频、批注、数字人、输出。HTML 第四步不能继续要求 AIMask/OCR。原内部 key：图片 3/4，Mask 5，音频 6/7，批注 10，数字人 9，输出 8；不可直接按显示序号改后端 key。

HTML readiness 独立判断 scene/assets/review/audio 等真实状态，不造 mask 文件骗过旧门槛。数字人可选；分发配置隐藏步骤继续工作。新增 UI 模块使用 `workflow_state.js`、`api_client.js`、`ui_foundation.js`，事件注册遵守现有顺序，不新建总控 app.js。

## C01 语义分镜适配

依赖 B02、A03。参考 OSS-04。验收 AC07。

复用 `storyboard_planning.py`、`visual_contract_service.py`、`storyboard_contract_diff.py` 的 ID/讲稿关联，扩展 HTML 分镜 schema/profile；编排交给 storyboard_service，模型调用仍经 storyboard_llm。规划内容形式、模板、对象、渲染归属、资产需求、出现/退出和讲稿 beat 引用，不输出自由 HTML。

修改生产提示词前阅读 `.agents/skills/optimize-prompts/SKILL.md`。保持提示词默认值/自定义迁移/UI 预览一致。使用有限修复次数；结构失败保存诊断，不自动改验证器迎合模型。

## C02 设计参考与关键帧冻结

依赖 C01、A03。参考 OSS-04。验收 AC06、AC07。

新增设计 brief 服务，输入主题、模板、实际效果图、效果 ID/backend、资产预算、字幕留白和内容。模型产物是候选设计参考；明确 CSS/SVG/Canvas 部分与独立图片部分。记录输入/输出 hash、模型配置、引用图版本。

按需生成关键帧：静态场景一张可够；对象过程需覆盖起点、关系变化和终点。复用已认可模板可以不再生设计图。人工选择后冻结可执行目标与差异说明，不能声称自动像素级复刻生图。

## C03 独立资产生产与质量

后续增量：用户已确认的多对象素材板/自动拆分任务以[完整开发计划 N00-A](next-development-plan-2026-10-08.md)为执行依据，补充验收见[AS01–AS06](acceptance.md)。先完成对象/槽位/提取定义与真实三路线对照，再接入本任务及 C04/F01/F02；固定槽位裁切已有工具，自动识别/精细抠图/应用编排仍待实现。单主体既有路径保留作为回退，板内多个资源不改变单页预算。

依赖 C02、B02。验收 AC10。

复用 `ai_provider_service.py`、并发治理及样式参考存储的适用能力。不要整段调用 `image_workflow_service.generate_slide_image`：其白底/画布适配/旧步骤失效为图片后端语义。新建小范围资产服务包装现有 provider。

优先资产 hash 命中；生成主体保持透明/声明背景、边界完整，登记尺寸、alpha bbox、锚点、角色和主题兼容。图集仅用于视觉一致的独立小资产，须有分区清单、间隔和独立输出核验；不能自动裁切粘连物后当成功。切失败重做该资产或人工纠正，不整课重生图。

## C04 编译、静态审阅与诊断

依赖 C03、A04、B03。参考 OSS-02。验收 AC04、AC10。

应用 UI 加 HTML 静态预览与问题列表、候选版本、重新生成指定资产/页面入口。新服务建议 `html_visual_service.py`/routes，server.py 只组装。先 schema/resource 校验，再浏览器测量、截图；静态通过之后才进入动作验收。

文字溢出、图片缺失、锚点错位、违规底部元素给对象 ID 与修复建议；失败保留原已确认画面。批准记录绑定 scene/theme/font/asset/layout/runtime hash，任一相关变化旧批准失效。

## D01 对象和动作编辑

依赖 C04。参考 OSS-04/05。验收 AC11。

增加对象列表/可见区间/关键状态/讲稿关联/重播与 seek。动作使用注册参数：显隐、位移、强调、关系描绘、数值变化等，按能力卡实现；临时对象有独立 ID、资产和生命周期。人工覆盖单独记录优先级，重规划不能静默覆盖。

复用现有纯时间插值；DOM/SVG/Canvas 使用同一作品时钟。自动播放、暂停、恢复、随机跳转必须相同状态。运动不能只做全页淡入，也不因追求动效让正文持续抖动。

## D02 已有音频时间轴绑定与字幕

依赖 D01、B02。验收 AC12。

复用 narration_audio_service、tts_service/provider/artifacts、确认/校准。新 HTML binder 读取每页 `narration_beats.json`、`audio_timeline.json` 中已验证的 segment/beat，绑定稳定对象动作 ID；明确秒/ms 转换只在接口边界做一次。`scripts/bind_reveal_timeline.py` 是旧 RLE 路线参考，不生成假 RLE。

缺失/重复 beat、未确认音频、偏移越界明确拒绝输出；手工偏移只应用一次。字幕仅占专用底部区域，字号可调、空字幕留空，换行容量检查。主题改动不触发 TTS。

## D03 HTML 精确批注

依赖 D01、D02。验收 AC13。

对接 annotation_target_resolver/geometry/timeline/runtime 与前端 annotation_playback。文字使用 DOM Range/实际字形布局，SVG 使用已登记几何，图片内部目标使用资产语义锚点与 contain 映射；不把外接框当图片内容坐标，不走 OCR。

对象离场/移动时批注跟随或按规范隐藏。全屏缩放、文本修改、字体变化后重新计算；旧图片批注行为保留。

## E01 视频导出后端

依赖 A04、D02、D03。参考 OSS-03/05。验收 AC14。

新增 HTML runner（建议 `html_render_runner.py`）接入 video_render_service 的 backend 分派，兼容 RemotionRenderResult 所需结果语义。图片仍用原 remotion_runner。HTML 在本地受限资源服务中加载同一播放器，等待 ready，按 i/fps 截帧，FFmpeg 编码基础视频、混入已有音频。禁止另写一套 JSX 布局或录屏等待动画。

复用视频配置、色彩元数据检查、进度/取消、输入 fingerprint 前后校验、作品登记。字幕由同一 HTML 画面渲染一次，禁止 FFmpeg 再叠同一字幕。临时帧隔离清理，不删除旧有效输出。

## E02 数字人继续沿用

依赖 E01。验收 AC15。

使用 video_render_service 已有基础视频之后的 `_apply_digital_human_composite` 及 digital_human service/client/routes。不重做对口型与音色。启用时预留经过模板声明的主体避让区域，位于字幕区上方；禁用时没有占位人像。失败策略与现有应用一致且对用户可见。

## E03 快照与分步 PPTX

依赖 E01。参考 OSS-06。验收 AC16。

扩展 pptx_service readiness/job、pptx_export 路由分派。共享播放器渲染终态或指定步骤快照后输出 16:9 PPTX；支持选择是否包含字幕，默认演示稿快照不带视频字幕。说明为图片式页面、不能逐对象编辑；步骤快照有明确页数映射和备注。

## E04 有限可编辑 PPTX（后续）

依赖 E03；不在首发完成门槛。参考 OSS-06。验收 AC16 增量。

先建文字/基础形状/图片/图表的 native/rasterized/unsupported 映射与字体/渐变/动画兼容矩阵，再实现转换。保留 node ID 和降级报告，禁止把 SVG 整页嵌入称为全部可编辑。开始此任务前核验将采用的具体转换器和许可证。

## F01 Agent 与 Web 等价操作

依赖 C04、D03、E03；相关字段在各功能开发时同步。验收 AC17。

在 agent_contract/capabilities、models、versions、operations、agent_api/routes 注册 HTML 操作和状态；HTTP/MCP/CLI 同一能力源。运行 generate_agent_contracts 并检查生成物。比较 Web/Agent 创建、编辑、生成、审阅、seek 状态、导出和冲突行为；不要仅生成文档却遗漏服务调用。

## F02 持久化任务、恢复与局部重试

依赖 B02、C04、E01。验收 AC18。

复用 LocalJob 和 generation_control/governor 的机制。video_job_store 硬编码 video_render，HTML 设计/资产任务应有自己的类型/store，不能伪装视频任务。实现重启 interrupted、幂等 key、限次重试、取消安全边界、阶段完成持久化；客户端断开不自动取消。

重做单资产只失效依赖页面和导出；并发编辑时旧任务不得覆盖新版。质量未过的作业保留失败原因，不自动标记步骤完成。首发 guided 先闭环，one_click 不自动放开视觉门槛。

## F03 总验收与交付

依赖 M0–M3、F01、F02；不依赖 E04。验收全部首发 AC。

在隔离数据上完成真实课程和故障矩阵。提交 acceptance manifest、截图/关键帧/短视频、ffprobe 及测试日志，明确用户视觉结论和未运行项。桌面关闭重开验证当前源码、版本、缓存行为；不得动原项目目录。

更新 README、契约实现状态、开发启动说明、Agent 交接记录和已知限制。按文件范围审查/提交，只向当前仓库 origin 发布；不要把原工作区遗留改动一起打包。首发未通过项不得标记已完成。
