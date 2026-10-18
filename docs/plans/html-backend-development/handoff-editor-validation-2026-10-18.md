# 编辑器与视频优化验收交接（2026-10-18）

承接单页输出交接；契约0.9.85、Agent API1.44、repair.generate1.3、操作Skill1.17。本批包含此前P0—P3未发布增量。工程、真实模型、用户批准和整课状态分别记录。

## 已有实际证据

1. 用户明确批准《水为什么结冰》当前画面，并授权保留已有旁白、恢复项目原音色。原服务记录视觉批准；复制MiniMax连接供该项目使用原voice_id，不改共享连接或全局音色，不执行TTS。当前配置与原确认指纹完全一致。
2. 原持久视频任务首次输出发现42.7ms AAC priming延迟。修复合成：单页保留已验证分段，多页独立解码音轨、按页帧预算trim/pad后拼接。修复后任务4fd7605775ce4c34855969269f61c8ab成功，588帧/30fps/19.6秒，全量解码通过；32个动作/字幕对应帧通过，音频零偏移相关系数0.999991、延迟0ms。视频`runs/c16bc2b3_203534/videos/render_a1f3978d657d42d1b82bfa4bd7dbaa2a.mp4`，实际hash2952cec0314f3a5341eb82ee006e896577366f0c7ca6afc369934dd829eb4f71。旧延迟视频保留并标stale。
3. 真实页面/旁白隔离副本做基线、工具、Skill三组模型对照，各四例：布局、原句偏移、人工保护冲突、缺能力停止。每组4/4、误改0、均1轮/4HTTP，原内容/配音hash不变。总耗时78.88/42.10/45.34秒，报告token27324/25931/26287，费用未知null；单次小样本不能证明稳定提速或降低费用。没有生图或TTS调用。
4. 修复模型现在消费scope相关人工叶路径及祖先路径，包含布局、动作、绑定；旧保护从同一manual_protected_paths推导，候选/保存门禁不变。工具与Skill摘要分别比较，实际出站内容/响应留在忽略输出，不提交用户数据。
5. 实际cua浏览器：正式0.7编辑器六组窗口/DPR坐标回写+undo，十次重开，单iframe/辅助层通过。40代理适配层24组：窗口1280×900/1920×1080，DPR1/1.5/2，缩放0.5/1/1.5/2，坐标误差≤1作者像素；48样本输入到下一动画帧p95=12.6ms。当前生产注册模板最多33槽，40代理测试不宣称新增生产模板或40槽整页能力。
6. 多页：原正式导出检查覆盖第三页失败、前两页缓存复用、恢复、重排、缓存损坏重建；调度检查覆盖实际子进程恢复、unknown不重发、人工签收阻断。新增单/三页非静音chirp回归核验起点/各页边界/顺序，2项通过；有限采样不代替听感。

本地证据：`outputs/single-page-video/2026-10-17/real-comparison-fixed/report.json`、`outputs/editor-benchmark/2026-10-17/comparison.json`、`outputs/editor-stability/2026-10-17/`。这些运行数据、数据库备份和媒体不得提交Git。

## 验证和限制

最终组合回归590项通过（164.35秒，1条既有Starlette弃用提示）；另局部Prompt/Skill60项、新增指纹/修复17项通过。Node16项、bundle构建、前端质量、Agent同步、Python/JS语法及Remotion本地TypeScript通过。完整输出见`outputs/final-editor-regression.txt`。这些重叠测试数不相加。

canonical quick检查发现原仓库门禁失败：storyboard_service.py1368非空行>1350，文件未被本批修改。未提高阈值，未宣称全库CI通过。清理了发布检查发现的未使用导入，fixture导入改显式同名导出以保留pytest发现。

归档上游许可证及esbuild生成LEGAL/NOTICES保留原字节（含CRLF/尾空白），不为git whitespace检查改写许可证据或失配构建hash；手写代码的排除式diff检查单独执行。

**整体目标仍partial**：本机没有已生成多页HTML真实课程，已向用户请求课程主题/项目；不能把合成静音/信号或单页重复当作真实整课。真实0.7语义课程的A04模型/人工签收亦独立待验。分支发布不等于main合并或部署；整课输入和全库门禁未完成前不宣称五项全部完成。

## 发布门禁后续修复（2026-10-18）

已将手工标题/旁白页面的纯组装移入既有storyboard_planning.compose_manual_skeleton_slides，请求服务继续持有权限、数据库、最终校验和失效。视频启动依赖装配归入video_runtime.configure_video_runtime，server显式注入同一配置/回调；不移动业务政策、不改路由或公开Schema，不提高行数阈值。storyboard_service和server架构门禁均通过。新增手工组装字段/空输入反例；分镜与正式输出相关31项、架构/装配/路由等9项通过。

quick继续发现设置脱敏自检仅填充旧密钥清单，新增字段触发KeyError；夹具现在为完整SETTINGS_SECRET_KEYS填入测试值，仍要求每一项掩码。独立真实服务脱敏自检通过。最终quick日志为outputs/editor-quick-checks-final.txt，门禁最终状态以该日志为准。此前“架构失败”描述保留为发现历史，以本段后续证据更新。

canonical quick最终通过。首次完整检查为2500 passed/6 failed/8 skipped：失败集中于历史验收夹具没有提供当前设计理解/重建响应、缺正文/run_dir、旧UI错误文案和旧runtime Skill清单。夹具按现合同补齐，正式校验与预算未放宽；相关39项复验通过。浏览器夹具服务器从无参数独立脚本发现中排除，仍由真实编辑器验收启动；新增发现器回归。视频测试证据改写忽略outputs，避免修改历史已跟踪媒体。

CI环境先因Python3.11不兼容锁定NumPy而失败，改为3.13；随后暴露未安装引擎npm依赖。CI现为Windows完整渲染检查，安装三个锁定npm包、Chromium，显式核对Windows字体和FFmpeg。实际CI已通过这些前置，下一失败为Node20不展开测试通配符；editor_ui测试命令改显式文件名，本地16项通过并重建manifest。最新完整pytest输出为outputs/editor-pytest-final-v2.txt，未完成时不可声明全库通过。

## 真实整课候选已启动

未收到课程主题回复后，沿用已有《水为什么结冰》原文章，通过原项目/文章服务建立独立guided HTML验收项目ec60bbd4_010236，原单页不变。原课程任务html_c184f91c3fdc4ffeacb6实际调用已配置模型生成四页讲稿，随后进入画面规划。项目与任务ID写入outputs/real-course-acceptance/2026-10-18；继续前须检查原任务，不因等待或观察超时自动重发。新设计和最终作品仍需明确批准，当前不声明真实整课已完成。此段替代先前“没有整课输入”的阻塞描述。

## 最新核验

本地完整pytest最终为2506 passed、8 skipped、2 warnings（716.84秒），输出editor-pytest-final-v2.txt。远端b6dcbce完整检查为2505 passed、1 failed、8 skipped：PPTX任务构造测试启动真实后台工作线程，读取时状态已由queued变成running。测试现在隔离submit并核对唯一提交的任务ID，仍严格校验queued、账号权限和输入指纹；不改生产状态机。

真实整课的四页讲稿和画面规划已由原服务生成，但第一页语义计划两轮均被原校验拒绝，最终为SEMANTIC_ANNOTATION_TARGET（前轮为SEMANTIC_ANNOTATION_ANCHOR）。父任务html_c184f91c3fdc4ffeacb6与子任务html_996b82a3b8654636880c均failed；没有设计图、旁白或整课视频可供签收，未绕过门禁或再次发起付费尝试。中途观察脚本退出造成的本地子任务回执关联已据唯一子任务及一致快照窄修复，审计见outputs/real-course-acceptance/2026-10-18/local-child-link-recovery.json；修复后通过原HTTP入口续行，未重复第一轮请求。继续优化应先检查annotation目标/焦点约束在规划提示中的覆盖，不能把两个失败响应作为批准内容。

后续已追踪真实响应：首轮annotation.anchorId误引用文字对象，第二轮targetId也误指文字标签。运行Prompt0.3.3补清图片目标、图片内焦点及文字标签三种引用，不自动修补响应。新增实际provider入口两轮负载/诊断测试，相关34项通过，canonical quick、Agent同步与ruff通过。旧冻结任务因源码变化不能续为同一请求；原produce入口创建新任务html_7a4c3b72614c4e80be1c，快照811bcda6afa1eade0d7e0f55552aa02cd2fb910bb6ac0e080712af9fcbb191b0，06:41发起新规划。必须查此原任务当前状态，不能因为观察等待再次提交；新任务通过与否另记。旧父任务尚未完成。

该新任务已succeeded并停在design_review，input_state=current、saved.changed=false。新版真实规划首轮通过，不触发结构修复；323.17秒，供应商报告25480 tokens。随后原设计生成约51.19秒，合计2次adapter调用，图像调用未返回完整用量，整个任务费用/总token保持null，不能拿规划用量冒充总用量。没有生成旁白或替换正式场景。

第一页候选key为3aeb952adf68928daae85812d0bc1c1f7b3465352c4cb3fb915beb7ac1b09bb1，图片SHA256为96de0f0265a5e21e6906acbc43ba5d4b55c669c9c30bf5d6f15f36f6174cdb71；实际文件哈希匹配，approval_status=not_recorded。已向用户展示此图并询问设计接受，尚未收到决定。批准后须携该key沿原produce入口继续还原；普通自动继续和旧单页批准均不等于新设计接受，也不等于后续HTML/声音/A04批准。任务与费用证据保存在outputs/real-course-acceptance/2026-10-18/prompt-033-design-task.json。

源码88226fd已推送PR #2（草稿），最新核对CI 117523515123仍in_progress；日志临时HTTP502不改变任务状态，不代表测试失败或成功。后续以最新head实际检查为准。生产服务PID3904、127.0.0.1:8010在本次核验时存活，继续前核查单实例，不能仅凭历史PID启动第二份。

## 接受设计后的真实还原与 CI 结果

用户已明确接受候选3aeb952a用于继续还原。原produce入口携完整key启动html_aee5b4c3778e469a995b（快照f7547ed5748adf10f1480bf5dfedaa82e581c4b88c35169dd4e590124c44f773）。设计理解282.13秒通过，独立主体素材144.89秒返回，还原首轮496.37秒返回并通过容量/几何检查。随后独立审核328.34秒完整返回，但六处differences.requirement误写为dimension值structure，严格Schema拒绝，任务failed；没有保存正式场景、生成旁白或签发视觉批准。实际未保存截图和原响应位于该页design-reconstruction/cf5f67d3a9450d525740ef4e5837b3c6ac8d852db952461c864795ebf91dd95d/0/，不把用户接受设计等同此候选通过。

已按optimize-prompts追踪实际出站Schema及消费者，新增运行审核片段1.0.1，显式列出既有九种requirement并禁止content/structure混用；注册路径/hash同步，新片段进入新源闭包，旧1.0.0保留。Schema、覆盖、原请求预算和人工门禁不变，不自动猜测修正六处分类。相关64项及Agent同步通过；新片段实际模型结果待验，不能重签旧冻结失败任务。

曾误提前提交其余页面，核查发现设计候选绑定全局revision，第一页保存可能使其失效，已通过原cancel入口撤销：slide_002的html_71bbfc95a27947df8a2f有一次已发出的规划请求，20.9秒时因取消关闭流，供应商终态未知；不得宣称上游已取消或自动补发。slide_003的html_4ae13803bc624fbbbe4c、slide_004的html_6b8994b181a942f4a000在排队状态撤销，零模型调用；这些取消任务不复活。记录在outputs/real-course-acceptance/2026-10-18/，后续回逐页原服务推进。

ffed5df的远端Windows CI已实际成功：检查117525006980、run39076626748，canonical full含2507 passed/8 skipped/2 warnings（1139.73秒）、16项Node及Remotion TypeScript。该结果覆盖1.0.1修改前版本，不能声称后续新head也已通过。PR #2已更新该实际证据并保持草稿；整课与正式发布仍partial。

1.0.1固定图复验位于outputs/real-course-acceptance/2026-10-18/review-101-fixed-case-v2：实际用户负载、Schema、图片hash、600秒预算及思考参数均与失败审核相同，模型冻结摘要也逐项匹配，只改系统提示。两次HTTP为已知400格式拒绝及原兼容入口的一次流式请求；407.38秒后完整返回。九种requirement枚举合法，56/56事实无缺漏/重复；obj-summary.typography的reference_alignment=uncertain使原守卫继续停止（DESIGN_REVIEW_COVERAGE_INCOMPLETE）。未保存、未生图/配音、未批准，费用null；前一单HTTP预算诊断因阻止原格式回退而停止，不能算有效模型对照，原记录保留。

核查text_alignment_contract仅列headline/intro/anchor-label/marker-1普通text，summary是含多种对齐的复合模块，整体reference_alignment本来不适用。运行片段1.0.2明确只有所列普通text的typography需要该字段，其余null；复合组件真实字体差异仍须报告，certainty或reference_alignment为uncertain的原拒绝规则不变。旧响应不改写、不签发通过；新片段另验。源定义变化后旧候选不能自动重签为当前，后续应沿原生产入口生成当前版本候选与审阅，不能把该独立诊断当成正式恢复。

## 五项优化的追加证据与当前停点

Agent 固定案例采用三轮轮换顺序复测，每阶段12例，共36例。baseline/tools/skill均12/12成功、误改0、未知请求0、平均1轮，各12次HTTP；平均每例8.179/8.368/9.599秒，报告token76584/77050/78310，费用未知。原内容与旁白hash保持，无生图/TTS。样本中未观察到工具或Skill提速，不宣称成功率提升或成本下降。完整报告为outputs/editor-benchmark/2026-10-18/repeated/comparison.json；供应商延迟和同期生产影响计时，三轮不足以得出统计结论。

只读视频比较脚本补齐逐页原声音轨、顺序、连接边界及丢失语音检查，不再将多页音轨标为未执行；保留单页报告兼容字段。16项回归覆盖实际单/三页AAC拼接、错序、整体/第二页延迟、静音、截断、预算外原声音频、静音连接杂音及非整数帧率。AAC测试参考按已知源呈现时长取样，避免把解码器暴露的尾部填充误判为原声音频被切掉；真实冻结输入仍直接解码voice.mp3核对。原正式单页视频再次32帧通过，相关系数0.999991、延迟0ms，证据outputs/single-page-video/2026-10-18/multipage-verifier-regression/report.json。该检查不代替听感、文字语义或视觉批准，也不宣称真实整课已通过。

真实整课四页原服务TTS均生成，时长18.408/20.736/19.920/16.416秒。任务825b204662b44fee99783ad68bd47e0c最终因HTML尚未保存而绑定失败（HTML_AUDIO_BINDING_INVALID:FileNotFoundError）；已生成音轨保留，后续复用缓存绑定，不再次配音。audio-status显示四页完整且配置未过期，尚未声音签收。顺序试听WAV为outputs/real-course-acceptance/2026-10-18/audio-preview/course-narration-preview.wav（75.48秒、全量解码通过），仅供试听，不是正式整课视频音轨一致性证据。

当前设计候选24ee8ed7203e608f101bae6b40b95e1ef7d20b9cb1342c26eb91de24fc9705b3已展示，用户随后明确要求直接完成五项，沿原produce入口继续html_1a8f68a0b8024d1fbe91。设计理解和独立素材返回；首轮还原因REPAIR_FIELDS停止，原预算内第二轮仍在运行。继续时首先查询原任务，不能因观察超时重发；此处未记录HTML或整课批准。

9b557f3远端CI为2511 passed/1 failed/8 skipped，唯一失败为测试仍断言审核片段1.0.0；02761a3更新到1.0.2，相关32项本地通过。最新检查117537247752/run39080833949仍in_progress，不将前一版本通过结果冒充当前head结果。整课签收、main合并和部署仍未完成。

html_1a8f68a0b8024d1fbe91随后明确failed：第二轮还原工程检查通过，独立审核301.32秒完整返回，43/43事实覆盖、Schema合法。真实差异涉及figure边框/顶部标签、标注虚线与路径、标签变体/位置以及summary三栏分隔；路由capabilities/planning/reconstruction，不能保存或签收。审核将旧plain summary的渲染前缀“这个过程叫”列为文字差异；后续须结合renderer及适用变体核对，不直接改实例正文。未发起第三轮或重配音。

首轮REPAIR_FIELDS定位为set_variant误用values.variantId。运行片段0.6.1明确variant操作字段与问题描述variant_id的区别；共享候选诊断给出操作名、未知字段、允许字段，仍拒绝别名。新提示版本不重签旧候选或扩张真实请求预算；原失败证据留存于design-reconstruction/e1844b7bc1bc6e9c0b4a393aae8b1497c39bc88e6890a8ed0f80df5a1ed0d0d9。

0.6.1实际出站、共享候选与runtime Skill闭包等65项通过。随后能力事实补齐figure无容器描边/顶部胶囊、annotation实线/静态不可编辑、summary渲染前缀与分隔线数量，设计Agent/政策43项通过，ruff及diff检查通过。两组测试存在重叠，不合计为独立覆盖；尚未启动新的真实模型实验，不宣称已提高还原成功率。当前需解决设计参考与注册组件结构差异，再逐页还原、缓存音轨绑定、A04与整课视频验收；五项整体仍partial。

## 结构差异修复（用户明确要求完成整课后续）

契约0.9.86先定义后实现figure-frame-top、annotation-dashed及summary-strip-divided。旧变体保留；annotation仅允许set_variant，Schema拒绝空间/字体/icon，原target/anchor/label及时间保持。新绘制模块presentation-structures.cjs归共享visual renderer，独立模块进入generation源闭包，bundle与Schema/注册目录重建。设计理解/还原片段0.7.0、Agent API1.45、repair.preview/save1.5、操作Skill1.18同步。

真实共享浏览器回归通过：带框/顶部标题、两条分隔线、无附加term前缀、虚线圆圈/引线/箭头、乱序seek终帧一致、旧实线兼容、过小/溢出拒绝、非法annotation字段拒绝。原呈现细节8项仍通过；相关组合108项、补充人工保护18项（重叠）及canonical quick通过，完整pytest运行中，日志outputs/framed-relations-full-pytest.txt。参考目录41件重建/一致性检查通过；不以工程证据代替新课程视觉通过。

已核对无running/queued任务后，将原8010单实例3904切换为源码进程34184（start_server.py、同DB/runs），exec session50721。真实第一页新任务html_ec9c0f1795fb4fdb862e，快照2556e2b1aca12f20446c1095ac8b60f5ce46e6770ffe1a64a3a3f6cd78d8853c；提交后发现参考目录派生产物尚未重建，补齐目录使该快照依赖过期。已发请求先等待明确终态，不取消为unknown、不盲目补发；后续沿完整新定义的原入口继续。记录structures-086-design-submission.json。这不是正式还原通过或新设计批准。

用户明确回复“接受当前四页旁白”。已把该决定与试听时原始四页产物hash写入outputs/real-course-acceptance/2026-10-18/audio-preview/user-audio-acceptance.json；原确认API需等四页HTML绑定校验通过再调用。未重配音、未用此决定代签画面/A04。

旧快照任务已完整返回规划（175.17秒、报告17509 tokens），随后按原checkpoint明确failed“快照依赖已变化”；没有进入生图或作者保存。不是unknown或取消。参考目录重建且检查41件通过后，原produce入口提交html_e42edd172e9a4b1db05b，快照5bcad9d55102681d881b129a894175f80044ce0cf639f43e2b54114d8f031c55，实际记录structures-086-complete-design-submission.json。继续查询此ID，不再次提交。

## 当前结构补齐与原图复用（0.9.87）

0.9.86完整本地pytest为2529 passed/8 skipped；该结果不代表后续0.9.87。第一页44f05c66设计已由用户接受，原还原html_566ee18f79954fb89922明确失败：图标事实错误判读，以及虚线圈/实线引线缺少注册变体，未保存HTML。

0.9.87补齐三种圈/线混合变体，准确暴露figure自带tag/note图标；原可选icons列表为空不表示内容图标不存在。修复图片compositing层随seek变化造成的像素抖动，1592/1600两种宽度解码RGBA严格相等通过。新增reuse_design_candidate_key只把未改变的模型计划与原图复制为新待审参考，零模型、生图、TTS；旧key仍stale，新key不得自动接受。契约卡design-reference-reuse-0.1.0、API1.46、produce1.9、Skill1.19与运行片段0.7.1同步。修复后的两个旧回归与新增用例组合16项通过，设计相关组合92项通过（有重叠），当前全库尚未复跑。

用户明确“授权第二页新实验”；独立新规划/设计允许另计调用费用，旧取消任务html_71bbfc95a27947df8a2f供应商终态和费用仍未知，原记录保持。授权证据保存在ignored outputs，不自动恢复旧任务。须先保存第一页再新建第二页候选，避免全局作者revision使候选失效。当前整课视频、HTML/A04签收与发布仍未完成。

0.9.87 canonical quick及完整pytest通过：2544 passed、8 skipped、4 warnings，669.62秒，日志outputs/reference-reuse-087-full-pytest.txt。原图复用html_f353501d78b34793ac00成功，模型调用0，图片hash不变；新key1ea58fbd由用户明确接受。还原html_362b08a75afb453b862c设计理解和主体素材均返回，布局请求超时为unknown（供应商不支持查询、费用未知），没有保存HTML。用户随后明确授权一次独立新还原实验，原入口携带prior_unknown_task_id提交html_909008f5e0f44cb08a6c；第二页独立规划html_895eddb52ced47678ab7亦在运行。原unknown不改写；不把提交当成功。当前服务恢复为隐藏独立进程9688，同一8010/DB/runs，避免执行会话关闭连带停止服务。新候选及第一页面都尚无HTML/A04或整课批准。

## 收敛到四页统一阻断清单

用户要求只核对已有任务、不新增泛化实验，集中修复而非逐个试错。当前实施输入见[四页交付阻断清单](course-delivery-blockers-2026-10-18.md)。第一页html_909008f5e0f44cb08a6c明确failed，真实审核匹配混合标注和底栏，卡片表面及散热箭头仍不符；图标圆形底不存在的模型断言与截图/源码不一致，不作为新功能缺口。第三、四页未进入设计/还原，不冒充已审核；平台线与完整三阶段需要前置核查。第二页html_ee1e1fd91f754fb0a18f仍在原设计理解请求；本轮没有提交新规划、生图、TTS。
