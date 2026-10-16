---
name: produce-editable-html
description: Produce and verify editable HTML slides from this repository's slide contracts, diagnose narration-to-visual mismatches, repair unsaved layout candidates or saved scene typography/layout/motion, and diagnose failed HTML production. Use for 生成可编辑HTML、讲稿画面不对应、初稿溢出、调整文字位置字号、验证自动生产与二次修改. Use registered components and shared APIs; exclude image-only production, standalone websites, and generic framework advice.
---

# 可编辑 HTML 生产与局部修复

Skill 版本：1.15.0（2026-10-15）。目标是交付实际可打开、可编辑、来源可追溯的作品。

本文代码与文档路径均相对仓库根目录；`references/`、`evaluation/` 相对本 Skill 目录。
先读 `docs/contracts/html-presentation/README.md`，再读其下 `runtime/visual-v1/application-production-0.3.0.md`、`scene-repair-0.1.0.md` 和 `candidate-layout-agent-0.1.0.md`。从 `agent_contract.capabilities` 获取实际可调用能力和请求 Schema。参考图谱不等于运行组件目录。保持内容、场景、资源、绑定为唯一源；DOM/截图/视频为派生物。

先遵循 `docs/contracts/html-presentation/runtime/visual-v1/design-review-authority-0.2.0.md`：准确内容/主题高于设计图，图内标签归代码，需求与注册工具决定返工路径；显式阶段请求预算不得被流包装覆盖。旧设计响应不自动迁移或重签当前身份。

多标签插图先读 `docs/contracts/html-presentation/runtime/visual-v1/labeled-explanation-0.1.0.md`：独立marker/relation槽走正常规划，超六标签/三箭头仍停止；新变体走原受保护编辑。旧设计批准不迁移为新计划批准。

## 执行主体与任务路由

- 说明哪些是程序渲染、哪些是模型规划或修复、哪些是人工编辑。模型返回计划、共享组件渲染 HTML，不能说成模型直接编写了最终 HTML。
- 候选排版 Agent 通过 `html_runtime_skills.py` 加载 config 中受控的 candidate-layout-repair 片段；不加载整篇本文件。正文与引用须登记版本/hash，输入/输出合同和代码权限固定。修改本文件仍不等于修改豆包策略；运行片段更新须同步注册与对照评估。
- 初稿使用生产入口；未保存的容量失败使用内部候选 Agent；已保存作品使用局部修复入口。资源、网络、Schema 错误先定位失败边界，不能用排版循环掩盖。
- 文案语义重写、增删节点或换模板回到权威内容和新规划；新图片走素材服务。禁止运行时 Agent 任意修改组件源码或生产 CSS。
- 默认黑灰白基线；保留用户已选风格和人工修改。通过字号层次、间距、对齐、线条与灰阶改善美感，不以不断缩小文字作为通用解法。

## 运行时策略与对照

设计先行流程读 `docs/contracts/html-presentation/runtime/visual-v1/design-agent-0.1.0.md`：设计确认后，Agent先理解逐对象外观及代码/图片、复用/生成分工，再调用素材服务和受控还原，最后用原图＋实际候选截图独立审核。模型审核pass仍需用户签收；layout问题可进入剩余还原预算，content/assets/capabilities回对应阶段。理解一次、还原/审核各最多两次，不重复无改善候选；保留正常思考，每次等待600秒，unknown不补发。三个新片段由config注册且实际消费，连同原容量修复共四个运行Skill；不将本Codex操作说明整篇传入模型。终态审核不替代A04逐句语义QA，多元素图片拆分不由此自动开放。下方S06单片段说明为原批次记录，以本增量为准。

讲稿/画面含义不对应、多对象分步解释或规划上下文审核，先读 [语义规划与设计分工](references/semantic-planning.md)。显式0.2.0规划与生产已支持初态、多动作和原句校验的音频绑定；语义QA和整课调度仍待后续。重复动作编辑必须选 actionId，不走排版循环掩盖表达问题。本操作Skill版本与config中的运行片段版本独立。

先读 `docs/contracts/html-presentation/runtime/visual-v1/runtime-skills-0.1.0.md`。当前只给未保存容量候选加载一个运行片段，其他职责及已保存修复保持原工具入口。检查 layout_agent.runtime_skill、每轮 request.json 和实际 system_prompt hash；registry/body/reference 不匹配、合同不兼容或运行中变化时停止，不把外部文档注册成高优先级指令。正文与引用在 `config/html_runtime_skills/`，注册在 `config/html_runtime_skills.json`，无需 `.agents` 目录才能运行。

原 legacy_prompt 保留为内部明确对照；当前默认 runtime_skill 依据三模板豆包固定输入对照启用。评估使用 `scripts/evaluate_html_runtime_skills.py --out <new-directory>` 预览计划，带 `--live` 才使用已有文字模型；只读原配置，运行数据库/文件隔离，不导入 server。首轮实际模型输入与截图必须一致，保留失败并按 AB/BA 顺序运行，不手改输出或择优重跑。适配器调用、HTTP 请求、usage、耗时和人工介入分别记录，未知费用为 null。结构化事实路由测试不证明自然语言自动选 Skill 的准确率；三例通过不能推广为所有页面或视觉批准。

## 用户状态与任务恢复

先读 `docs/contracts/html-presentation/runtime/visual-v1/workflow-status-0.1.0.md`。使用 html_review.task_current（MCP ppt_html_task_current / CLI html task-current --project --slide）按页恢复原任务；项目最近记录只是概览，不以其条数推断某页没有任务。task_status 核对冻结输入、实际依赖、内容与 revision，旧任务缺信息为 unknown；succeeded/design_review 不表示 HTML 已完成或批准。查看 progress 的实际修复轮次、Skill版本与原结果复用，失败/未知结果不得汇总为成功。

显式继续使用 html_review.task_resume（MCP ppt_html_task_resume / CLI html task-resume --project --job），由原快照恢复 contract/options；不要改参数规避原任务预算或供应商未知结果。取消、坏回执、耗尽、源码/模型/内容变化仍阻断。Web刷新自动恢复轮询，项目切换清空旧状态。编辑器先展示真实 preview 的重建影响再保存；当前交付同时检查 artifact_state 和 historical，旧成功不升级为新版完成。

## A04 逐句语义 QA

先读 `docs/contracts/html-presentation/runtime/visual-v1/semantic-qa-0.1.0.md`。对已保存scene0.6/0.7，使用 html_semantic.submit/status/decision（MCP ppt_html_semantic_* / CLI html semantic-*）。submit仅expected_revision，真实voice.mp3与时间轴必须就绪；原句/对象/动作与plan0.2核对后复用共享播放器每句start/mid/end三帧。没有真实音频不能用作者等分代替。

任务使用原LocalJob，可读/停止/显式继续原任务；冻结模型，已返回帧与模型回执复用，unknown不补发。读取结果分别核对engineering、semantic、audio、human与原visual批准。模型pass只提供语义建议；用户明确签收当前report_key且note记录依据才写decision。omitted/contradiction或工程失败不能批准；uncertain/低置信明确待审。页面/声音/动作/代码变化会使报告stale。

视频输出需要新版当前语义签收；静态PPTX仍独立，不把静态可导出称为课程讲解通过。原句、三帧与证据须展示；不以终态替代逐句检查，不把模型规划的visualIntent当事实证据。生产Prompt唯一源为config/html_semantic_qa_prompt.md，不把本操作Skill整篇传模型。

## 正式导出

A05课程调度先读`docs/contracts/html-presentation/runtime/visual-v1/course-orchestration-0.1.0.md`。HTML项目沿原pipeline.run/status/resume（CLI run start/status/resume、MCP ppt_pipeline_*）或Web一键入口调用。resume保持课程LocalJob和阶段子任务ID；设计仍在逐页原入口确认，视觉/音频/A04签收独立，不用通用checkpoint.approve代写。restart/start_from不能绕过。刷新查询backend、job_id、children、historical；实际旧子任务unknown或提交ID丢失时停止，不换参数补发。正常生产与故障注入测试分开报告；完整真实整课仍需用户在既有停点审阅。

正式 PPTX/视频先读 `docs/contracts/html-presentation/runtime/visual-v1/formal-export-0.1.0.md`，沿用原导出任务入口。任务固定整课有序快照，视频以页内缓存和整数帧重组；不得手动搬移缓存或强开 allow_legacy_unbound 绕过批准/音频/binding 门禁。检查作品 metadata.export_evidence 和实际可下载文件：分段命中也必须 hash/格式/全解码通过，数字人合成后再次校验最终文件。PPTX 仍为图片式页面，不能宣称可逐对象编辑。historical=true 是旧输入的有效历史结果，不能说成当前项目已完成；检查当前 artifact_state，不以成功任务代替当前输入签收。源码/工具/字体变化须重验，工程通过不代表视觉或真实供应商验收。

## 初稿

1. 读取当前页权威visual_contract和注册模板。检查项目文字/图片模型绑定，默认neutral-baseline黑灰白。已有素材先验证 assetRef、身份、版本及文件内容并显式复用；不能因已有图片而误入新生图分支。
2. 用html_review.produce进入生产，由服务调用模型返回plan；结构错误由服务一次重试；容量失败的未保存候选由服务内部 LangGraph 排版 Agent 最多三轮，实际截图/测量驱动，严格重验才保存。资源/Schema 错误不进入循环。失败停止，不手写计划后声称自动成功。html_review.plan_generate仅用于独立规划诊断，其输出不会自动被produce复用。
3. 所有新生产任务都先生成整页设计并停在design_review，纯代码和复用主体页也执行。缺图片连接停止；不跳过设计。展示候选并沿用已授权的批准范围；审批使用实际design candidate key。
4. 接受后复用同一任务继续独立主体与场景生成，按 `design-first-reconstruction-0.1.0.md` 进行受控还原。首轮设计图加必要对象/实测输入；仅结构修复轮附失败截图，最多两次。模型返回注册操作，由共享组件渲染；禁止整页图片替代HTML正文或修改原文/动作。scene0.6可经注册set_variant显式升级0.7；没有的能力返回unsupported，不生成自由CSS。
5. 读html_editor.read，再用html_repair.evidence检查实际渲染。展示本次实际保存的HTML与设计图对比，不以旧样板替代。诊断预览 passed=false 不能当作成功。审计请求、图片数、思考参数、耗时及人工介入；工程通过仍需美感/语义/音频批准。网络unknown不盲目重试。用户界面请求plan0.2，旧公共默认0.1保留；不要把兼容默认误当多动作生产。

## 局部修复

先读 `docs/contracts/html-presentation/runtime/visual-v1/minimal-rebuild-0.1.0.md`。editor/repair preview 的 rebuild_plan 是当前修改的 dry-run：检查目标页、rebuild/reuse 和原因，再沿用已授权范围保存。只改屏幕字/字号/位置时保留现有朗读和素材；仅动作/绑定不重新 TTS。保存重算计划并绑定当前作者内容，editor.read 的旧计划不匹配时返回 null。计划中的 reuse 是候选，仍须资源散列、音频确认和视觉门禁有效；不凭计划跳过检查或批准。字体/共享运行输入变化必须重测。无需新 Agent 能力；MCP/CLI 沿用 editor/repair 的预览与保存。多页输入可用 scripts/html_rebuild_check.py capture/plan 做只读分析，不能将分析报告宣称为已执行所有重建阶段。

在需要复现一页输入或核对检查版本时，先读 `docs/contracts/html-presentation/runtime/visual-v1/input-snapshot-0.1.0.md`。使用 `scripts/html_snapshot_check.py freeze-render --run-dir <run> --slide <id> --expected-revision <revision>`，随后 `review --snapshot <path>` 检查固定输入，展示返回的实际 HTML。generation 快照已由生产任务消费；恢复规则见 `docs/contracts/html-presentation/runtime/visual-v1/production-recovery-0.1.0.md`。同输入失败/中断可显式重提交，已返回响应复用但归一化与实际检查重做。intent/unknown、坏产物或过期 revision 必须先诊断；不要修改阶段账本或换一个无意义参数绕过阻断重复生图。取消不恢复；作者已保存而任务中断时先读取现有作品核实。QA 校验必须匹配期望快照和证据目录，不能只看报告的 passed。静态 review 检查终态；review-temporal --snapshot <path> --fps 30 --overlap-policy registered 检查全部输出帧和动作边界。先读 temporal-qa-0.1.0.md，核对原请求、coverage、clock、排除依据和证据哈希；帧间连续时间未数学证明，不能代替视觉/音频批准或正式导出门禁。重复补丁/候选或实际无改善提前停止，保留原作品和 stop_reason。不能替代下述作者编辑 API。

恢复对账另读 `docs/contracts/html-presentation/runtime/visual-v1/production-recovery-0.2.0.md`。启动/同输入提交会先检查响应与作者 prepared/sealed 回执；完整作者提交直接补回原任务成功，无须重新规划。ToAPIs 有原 task_id 时只查旧任务；无 ID 的同步超时不补发。回执损坏、文件缺失、新版本或连接变化时停止，不编辑阶段账本或换参数绕过阻断。恢复成功仍不是视觉批准；检查返回的 reconciliation 和实际 editor 内容。

若未知的同步模型调用前已经留下可重演的未保存候选，读 `docs/contracts/html-presentation/runtime/visual-v1/manual-candidate-review-0.1.0.md`。用 `html_review.manual_candidate` 查看绑定原失败任务的设计/截图/工程问题，再由真实评审者走 `html_review.manual_candidate_decision` 明确记录接受或驳回；工程失败只能驳回。决定不会恢复原任务、提交作者scene或批准正式视觉。没有用户的具体审阅决定时不要代写。

1. 读html_editor.read，冻结revision；选定公开对象ID和scope。暂停帧仅用于定位，基础属性会影响对象整个生命周期。
2. 根据问题选set_presentation、set_text_style、set_motion或set_binding；字段以生产Schema为准。字体/布局需scene0.5，服务显式升级；annotation不能覆盖其坐标空间。
3. 已有明确参数可调用html_repair.preview；需模型推断调用html_repair.generate。请求使用实际revision、scope、instruction、time_range_ms、step_ms、overlap_pairs。不让模型生成source、candidate_key或批准。
4. 对已绑定动作调整set_binding；不要把动画变换后的屏幕位置写作基础坐标。关系引线和图片锚点由同一渲染器重算。
5. 检查candidate.review、diff、clock、截图；仅在授权范围内用html_repair.save提交原request和candidate_key。保存再验证，409重新读取不覆盖；失败保持原作品。
6. 再读editor并重看实际页面。服务最多两轮模型修复；超限或needs_input/unsupported清晰报告原因。AI保护人工字段；不能将source改human规避保护。用户明确人工操作才使用human。

## 必须区分

- generate通过配置的兼容chat接口发送最多4张实际PNG截图和测量报告；模型必须具备图像输入能力，不能静默去掉图片后声称完成视觉判断。正常 evidence 已提供末帧参考几何、文字测量和全部问题摘要；完整有限采样轨迹留在本地。仅当输入确实含原始 frames 时才涉及防御性过滤。保留真实 frame_count，不能把未传 frames 误报为零采样。实际调用与图像接受仍需真实验证。截图由程序提供时间索引，对象身份以结构化输入为准。
- 默认有限采样，未提供overlap_pairs不代表全部遮挡检查通过；高风险区间用16ms步长，超过240帧预算要缩短区间。容器/主体的合理覆盖不能误标碰撞。排除项必须来自注册关系并记录理由，保留原诊断，不能任意删掉失败对象对。
- 文案语义重写/增删节点/换模板需回到权威内容与新规划候选；独立主体重生成走素材服务，不能通过局部操作隐藏。
- 作者时钟不是确认音频。排版修复不重新TTS；输出仍需现有音频和视觉批准。
- HTML源可编辑不代表快照PPTX或MP4内部可编辑。服务不提供持久undo；会话撤销按现有编辑器执行。

## 诊断、验收与持续打磨

1. 遇到失败先读 [失败经验](references/failure-lessons.md)。区分已证实、待证实、已排除原因；检查实际请求摘要与调用日志，不能根据本地报告大小推断网络负载或 HTTP 500 原因。停止本地等待不等于取消供应商请求。
2. 修改工具调用时验证真实签名及必填参数（包括 schema_hint），不能只靠接受任意 kwargs 的 mock。模型结果仍经过代码 Schema、权限、容量与保存门槛。
3. 交付实际 HTML 链接、当前 revision 和证据路径。工程、真实模型、二次编辑、视觉审阅、正式导出分别标注 passed / failed / not_tested / pending_review。截图必须检查文字层次、可读性、留白和图文融合；几何通过不能代替审美批准。
4. 每次实验固定输入、代码与 Prompt 版本，记录调用次数、修复轮数、耗时及人工改动。中途改代码后另记实验版本；单页成功不推广为多模板可靠。缺失指标用 null，不估造数据。
5. 按 [迭代机制](references/evolution.md) 把新失败加入 [评估案例](evaluation/cases.json)，定位属于规则、Prompt、工具、资源、网络还是审美问题，再修改对应层。结构检查、人工案例走查和真实模型评估分别记录，不能互相冒充。

调用方式：MCP ppt_html_editor_read / ppt_html_repair_preview / ppt_html_repair_generate / ppt_html_repair_evidence / ppt_html_repair_save；或 `python -m cli.pptctl html repair-<mode> --project <id> --slide <id> --file <request.json>`。工具权限沿用宿主，不引入第二服务。保存密钥到既有设置，不写入Skill、Prompt、产物或Git。
