# 可重复捕获、素材恢复与生产需求预检交接

2026-10-18，契约0.9.89 / API1.48 / produce1.11 / Skill1.21。按用户顺序先完成两项，再恢复四页课程。

## 已实现与验证

- 原正式审核、取帧、逐句语义帧与视频工具统一使用captureLaunchOptions的软件合成策略，进入生成/渲染快照、批准与输出指纹。交互GPU分数缩放的抗锯齿限制仍独立，不宣称所有GPU像素一致。
- 相同已接受设计按准确need、设计图hash、模型、参数、参考与返工指令复用已验证素材；重复理解的appearance措辞不再触发付费生成。损坏/缺失匹配缓存明确停止。旧无身份素材不猜测迁移，旧unknown请求不补发。
- visual_requirements进入实际planning_context与修复轮task；normalize/A02原门禁在生图前阻断缺coverage。四页权威需求出站已离线检查，不以计数代替科学语义/视觉签收。
- 71项缓存/语义/四页渲染与需求回归通过；75项快照/生产/恢复回归通过；27项正式导出/音频对齐/快照回归通过。三组文件互异，不将快速检查的重叠用例再累加。原视觉5场景14项通过，无页面错误。canonical quick通过。
- 回归中途一次源闭包变化导致恢复fixture提前失败；完成代码冻结后75项全过。新增快照断言曾误读files结构，修正后通过；保留首跑日志，不冒充首跑全绿。
- 代码按correctness/readability/architecture/security/performance五轴复核：共享正式策略、无重复付费恢复、严格输入与原审批门禁保留，无新增秘密或依赖。

## 本机证据

outputs/capture-preflight-final-regression.txt；capture-recovery-stable-regression.txt；capture-formal-export-regression.txt；capture-policy-visual-test.txt；capture-recovery-quick.txt。
outputs/capture-recovery-preflight/保存原合同备份、拟写需求和来源回执、工程汇总。原四页audio/text/metadata/srt/timeline共20个hash保持用户接受版本。

## 恢复生产边界

原项目ec60bbd4_010236，四页实际HTML仍未保存；001/002原失败与unknown保持历史，003/004未形成正式设计。新需求改变旧设计key，必须原流程重新规划并停在设计审阅；不得给旧候选重签。复用四条原旁白，不重新TTS。真实模型结果、HTML批准、A04、声音当前绑定、整课视频及发布均独立待验。生产恢复状态见本机outputs/capture-recovery-preflight/production-restoration.json，不能把提交任务视为交付完成。


## 真实生产跟进：0.9.90

第一轮恢复后：001设计1fd3604c已返回，但实际计划的端点按舞台比例写入对象内坐标，部分箭头向量和声明方向不一致，不接受/不还原。002两轮分别PLAN_SLOT_KIND、PLAN_VISUAL_COVERAGE，未发生图片调用；实际输出提示漏列visual_coverage。003规划有0℃平台，但图片任务tsk_img_01M56X38ZSZBFVPYT9RQ30SDYK失败；只读原ID查询确认upstream_task_failed，阶段仍unknown、费用null，不补发。004在queued且无stage时取消，零供应商调用。

修复唯一规划Prompt为0.3.5：schema_hint列覆盖字段、说明对象box归一化公式/四边中点；没有放宽解析或增加两轮预算。回归新增用例在旧实现1失败1通过，修正后2通过；相关89项和兼容7项通过。尚未证明真实模型修正成功。所有外部请求收齐后才更改源码。

仅恢复002/004的一次修正版正常生产，保留旧记录。001需要权威计划修正，不能手写本例计划冒充Agent；003原失败/费用待定不重发。当前状态仍不是课程交付完成。


## 保留原图修复：0.9.91 / API1.49 / produce1.12

002修正版任务html_d8e3dddc93bb4b119f74已返回设计d42db565，004任务html_d756c9411924450ca8ed已返回73f89323，均未被用户接受。关系清单分别4条与3条，阶段3个；设计图已本地查看，原旁白不变。

新增repair_relation_points必须与reuse_design_candidate_key及plan_version=0.2.0配对，只允许模型返回原point关系的坐标；端点对象ID/模板/正文/图表/动作不变，人工覆盖阻断。单次600秒，不自动重试，不生图/TTS/作者写入。原候选保留，原图字节相同，新key仍需用户接受。默认复用继续零模型调用。Web/Agent共享请求模型，CLI --file自动承接；MCP改为转发模型声明字段，避免漏掉reuse/plan_version等参数。

最终相关105项回归通过（204.20秒），包含模型坏响应、原生产路径保留图像与内容、人工保护、任务恢复和MCP/CLI；canonical quick通过。之前一次57通过后失败为Web/Agent默认字段断言未更新，已同步并补显式请求转发验证，未放宽业务验证。原型26项与最终105项重叠，不累加。

实际001端点模型修复仍待独立核验；002/004将按新定义零调用复用原图/原计划进入待审。003供应商原失败不补发、费用null，仍阻断整课。当前不是视频交付或发布完成。


## 视觉模型就绪修正：0.9.92 / API1.50 / produce1.13

002/004已在0.9.91完成零模型/零生图/TTS的原图复用（f4df29f0、d1f3d8da），未签收。001端点请求html_bba27d6495674b10aafa实调HTTP400，阶段unknown、lookup不支持、费用null；未重发。根因是项目此前没有独立视觉绑定，text与planning都回落doubao文本模型，并非图像损坏。已通过原项目model-binding入口把text固定到已有glm-5.3-flash（supports_images=true）、planning固定原doubao，image用legacy保留原创作包解析，前后image摘要完全相同。此配置写入零模型请求，声音不改。

修复：任务提交在新端点模型请求前检查图像能力；新请求角色relation_point_repair单列；HtmlTaskError的unknown不再被通用复用错误遮盖。显式复用允许在图片模型摘要不变、原合同/内容/作者验证均通过时刷新text/planning，存source_model_summary，仍须新接受。不靠更改模型绕过unknown重发授权。

源模块/模型/复用/请求边界相关67项通过（63.36秒）；31项聚焦与之重叠。增加冻结worker使用视觉模型进行端点修复的路由及独立指标断言，单独复跑见vision-routing日志。早一版105项仍是0.9.91工程结果，不能替代本次真实调用失败。后续001若需一次独立新请求必须由用户明确授权；003仍保留原供应商失败及未知费用。002/004优先集中设计接受并还原。


## 已授权还原收齐与首次输出修正：0.9.93

用户明确接受002当前25e70e83与004当前6e4bc6e3，授权001一次独立坐标请求。实际任务001 html_b23690307eb940a1a2fe返回关系键映射，被严格Schema拒绝；002 html_ff575d786e264190ba16素材返回、还原审核失败（标题、底栏遮挡、图内拥挤）；004 html_8be695dddf1b49088b65还原审核要求内容/能力核实（标签对齐、强调、分隔），均未保存正式页。003原失败不动；本轮无TTS。完整回执与集中阻断表在本机outputs/capture-recovery-preflight/authorized-production-20261018.json及concentrated-blockers-20261018.md。

定位001接口缺陷：共享json_llm_service的schema_hint只用于JSON语法恢复，并不进入首次消息。Prompt0.1.1在首次system提供严格Schema及明确字段；不放宽验证，不转换旧响应，不重发。相关33项离线回归通过（10.25秒），ruff通过。源文件变更未加载运行服务；未进行新真实调用，不能宣称生产修复成功。


## 第二、四页集中候选修正：0.9.94

用户授权集中修复现有候选布局/文字。未请求供应商；以原candidate_from_document注册操作及原共享renderer完成明确开发修正，隔离在outputs/candidate-layout-fix-20261018/isolated-run，生产作者和旧失败不写。002三卡移至285/395/505、各高100，底栏从618开始；标题40px，主体与标签分离，原锚点通过私有anchor variant调整至冰块内部，原图hash不变。004三标签居中、新text-card-outline-emphasis（700/400与强调前0.25em视觉间距）保持原runs和卡片，正文20px消除单字换行。原文字、关系、动作、binding逐项相等。

两页静态严格检查、原音频绑定后250ms指定遮挡采样均通过。新变体DOM正负例与legacy验证通过；npm run test:visual的5场景14项通过，无页面错误。证据review.md、correction.json、strict-review.json、temporal/report.json、verification.json在本机outputs/candidate-layout-fix-20261018。五轴自审：注册声明复用现有渲染、不加业务分支或新API、旧变体不变、资源hash与路径守卫保持。源闭包变化后旧候选仍不能当当前批准；尚未保存正式作者、执行A04或导出视频，不将离线开发修正冒充系统Agent真实成功。


## 用户接受后正式保存与两页音画核对

用户明确“接受两页修正画面，继续保存和验收”。核对formal-save-preflight中已展示PNG/候选hash后，将已验证素材（含原图不变的私有anchor变体）、原binding/plan以既有原子metadata owner准备，通过原Agent scene_write PUT正式保存002（revision1）及004（revision2）；两个原approve接口均valid，旧失败任务不改写。原语义prepare验证对象、动作、语块身份通过。

独立A04：002 html_fc19fbf0818a42e881a8，report8674d26fc9ef78c4da7ad91616826b179a4802c45bf61ef92fa0e2617fac2649；004 html_8e578a539bfd441aa6c9，report65daef32cba8b836922ea4f473050706627f63ab0ba0eef3aa73ff2efb9f2056。均succeeded/engineering passed/semantic passed/human pending，不代签。

已用原共享export-slide-video工具生成两页review_only视频（不登记正式作品），真实原音轨、原字幕与audio-bound scene：002为623帧/20.766秒，004为493帧/16.433秒，30fps H264/AAC、完整双流解码通过；原音频相关系数0.999946/0.999977且lag0ms，字幕5/4条未超视频末尾；6个同时间预览/编码抽样帧通过（MAE0.094—0.649，不宣称逐帧像素无损）。证据outputs/candidate-layout-fix-20261018/review-videos。原4页全课音频confirmation缺失，原confirm服务需全部HTML binding，因此正式输出仍被001/003未保存阻断；未手写confirmation或allow_legacy绕过。已向用户展示两段视频并请求当前两报告独立语义签收。


## 第二、四页当前语义签收已记录

用户明确“接受两页音画与逐句语义验收”。通过原semantic/decision入口在revision2将上述8674d26f与65daef32完整key批准；两页semantic/status复读valid=true、semantic=passed、human=approved、visual=approved。历史任务result中的human=pending是任务结束时快照，以当前status为准，不改原任务。user-semantic-acceptance.json留存完整回执。全课audio确认仍missing_confirmation，001/003未保存，故不宣称四页整课视频/发布完成；不需再次请求002/004相同内容的签收。


## 后续开发：第三页原代码计划复用

已复读002/004当前semantic/status：revision2、valid=true、semantic passed、human approved、visual approved，不重复请求相同签收。003原html_fdc52bd530634adfbf5c的归档模型计划79381921仅声明code资源，故零供应商请求走原normalize/A02/compile/共享renderer，形成未保存代码候选；通过既有set_variant/set_text_style统一描边卡片、标题徽章、三栏底栏，不重写原文/动作/binding。静态passed、原音频prepare通过、250ms指定遮挡采样passed；平台由min/max/points计算为0℃。这是明确开发整理的代码候选，不冒称原图片供应商任务已成功或当前设计已被接受。outputs/remaining-pages-20261018保存源计划、修改操作、实际截图及验证，未写真实项目第三页。001 Prompt0.1.1尚未新付费请求，旧失败保持。


## 第三页保存及第一页一次授权修复：0.9.95

用户接受第三页并授权001一次独立坐标请求。003候选fee9b1bb/画面d0b61ed5与原展示hash核对，原scene_write保存revision3，approve valid。为避免001被其他页保存误伤，显式reuse增加本页基础hash/无人工覆盖/当前revision一致的跨页重建判断；旧load_design接受规则不改。相关37项回归通过，ruff与diff检查通过。确认无active LocalJob后从原PID41972重启唯一8010服务，当前PID25952，明确原data/projects.db与runs，加载Prompt0.1.1及revision修复。

001新任务html_1b5982ca50c6449398b6单次请求返回正确Schema，新待审key6a4c63b47c6049dc6fb062087d04bcbef52a41c0755aa25f75a1eaf246022b6b，图片hash60faefc6与原字节一致，仅point变化。然而真实对象坐标下八方向45°扇区（±22.5°）仅3/8满足，不将任务succeeded冒充语义修复成功，不接受该候选、不追加供应商请求。新增只读diagnose_html_relation_points脚本，显式方向不作NLP推断，按矩形射线派生8份point建议并复算方向；不写原计划/候选/作者。14项离线几何正负例通过，与37项文件互异；实际诊断在outputs/remaining-pages-20261018。

003语义任务html_9051028969db432fb33f完成，report960e33fcc2efec950f2972b70411af23b269a5550cd8a19757b2f4b8e6d196a9 engineering/semantic passed，human pending。原共享工具输出review_only核对视频598帧/19.933秒，H264/AAC30fps双流完整解码通过；音轨相关系数0.999987、lag0ms，4条字幕末尾19.92秒；3个同时间抽样帧MAE0.193—0.303通过。已展示视频并请求独立语义签收。原002/004已签收，无需重问。全课正式输出仍待001与原全课音频确认，不手写confirmation、不宣称发布。


## 第三页人工语义签收完成

用户明确“接受第三页音画与逐句语义验收”。原semantic/decision以当前revision3和完整960e33fc报告key记录approved。随后复读002/003/004：valid=true、engineering/semantic passed、human/visual approved；三个原报告key保持。音频状态仍pending，因全课audio_confirmed尚未建立，不把旁白已接受等同于全课确认已完成。回执outputs/remaining-pages-20261018/page003-user-semantic-acceptance.json。下一阻断是001八方向坐标，原模型3/8、程序建议未写作者；未新增模型、生图或TTS调用。


## 第一页程序坐标修复与四页音频确认

用户要求修复001→验收→全课音频→四页正式视频与发布。用已明确八方向和通用几何函数生成point，不再请求模型；目标框顶部留80px标题区避开左上箭头穿字。normalize/A02/compile通过，八方向实际向量全部通过，只有point更改；正文/对象/动作/binding保持。显式选择已有无箭头透明水杯599363a681ea，原PNG字节不变，登记为water-cup-cooling的现有资源选择，不冒充旧生成缓存命中或模型任务成功。原设计图、历史失败与费用记录不动。

通过原注册呈现操作统一外观，独立输出outputs/page001-closure-20261018。静态/音频绑定/250ms指定遮挡采样通过后，原scene_write保存001为revision4，未代画面批准。原A04任务html_ef23e6d89be54b31b06b完成，report a191c027c48fffb9232894d02d01355e355c83655a051aa46567ed41bad7a272 engineering/semantic passed，待用户画面及语义合并确认。

复用用户此前接受四页旁白的原回执，调用原steps/7/confirm，audio_confirmed=true。确认前只读重演timeline写入，4页semantic/bytes均no-op；确认后20个原音频/文本/metadata/SRT/timeline hash全部不变。002/003/004当前valid=true、visual/human approved、audio confirmed，无需重签。

001核对视频review_only为553帧/18.433秒，H264/AAC30fps完整解码通过，原音轨零滞后相关系数0.999919，4条字幕末尾18.408秒，3个抽样帧MAE0.155—0.629通过。已展示视频并请求第一页当前画面+报告合并决定；四页正式导出尚未启动，不绕过该决定。独立结果和原作者写入来源在save-receipt、direction-verification、audio-confirmation-receipt、closure-readiness等JSON。

## 第一页动画反馈与已保存分段动作

用户明确反馈“这个根本没有什么动画呀，这个音频是OK的。”，因此旧a191c027画面/语义仍未获人工批准，声音保持接受。定位原场景所有第二句对象同时500ms入场，之后静止；复用现有关系draw-on能力，仅通过原repair.preview/save的source=ai保护事务调整既有动作。17条binding偏移与18条时长/标签位移分别保存为revision5/6，保留actionId/beatId；正文、对象、关系坐标、原素材等非motion作者内容逐项相等。首个100ms采样预览超预算422，未写入；改为现有250ms采样预算后两次预览及保存均通过，无额外模型、生图或TTS用于修复。

动作顺序为水杯/要点出现、约8.9—13.0秒八支箭头依次向外画出、降温标注、前提卡片、结论。outputs/page001-motion-20261018记录完整前后作者、原事务回执及motion-verification：八箭头在实际共享播放器多时间点的路径长度单调增加且存在中间态；五个同时间预览/编码帧比较通过。新review_only视频18.433秒/553帧/30fps H264/AAC全解码通过，音轨相关系数0.999919、lag0ms，20个已接受声音相关文件hash保持。另有motion-detail.mp4为裁切无声放大核对片段，非正式课程产物。

新独立A04任务html_7ca5aad733fa4c3ab0e5 succeeded，当前report5e61363eec54d2adf5fc9882206cf8480b08f1fc3cfe15c3ad4934c3a3c811da engineering/semantic passed，visual/human pending；不转移旧批准。002/003/004当前revision6下仍valid=true、visual/human approved、audio confirmed，不重复签收。待用户观看新版第一页并决定后，才记录当前第一页批准、走正式四页视频与发布入口。源服务当前唯一8010实例PID2536，输出日志在page001-motion目录；未新增引擎或公开API能力。

## 四页正式视频已导出并登记当前作品

用户明确“接受新版，继续整课导出”。原approve及semantic/decision在revision6记录第一页当前完整5e61363e报告批准，user-acceptance.json留存；四页当前semantic/status均valid。通过原Agent videos/render提交op_29873ef9257a / job b6ff41b7500f4c2d9c1fc0a08e0e7e0a，184.4秒完成，冻结整课2621a4694fc2661aca29641483afe3262c7ec3f026a14cfe88b32e0599636d1a。原作品服务登记videos/render_740350b9c6da466385f8deeab068eda0.mp4为current、historical=false，并更新out.mp4；这是本地项目作品发布，不表示源PR已合并或视频已上传外部平台。

最终视频1600×900、30fps、2267帧、75.5667秒、H264/AAC、bt709，完整双流解码通过，SHA256 a28ca96121dd364bac047fc215a9ee28d920a93797d03e0cd1e523952c0db952。原scripts/verify_html_video_frames.py实跑通过：冻结快照/运行身份/hash复验、四页顺序与78个指定时刻预览/成片帧比较、全部原音轨与三处页间拼接检查通过，四页及边界lag均0ms，无丢失源语音。报告outputs/page001-motion-20261018/formal-verification/report.json。有限抽帧工程检查不替代用户对完整成片的最终观看评价；不得因已交付本课程声称所有项目性能/模型优化目标均已完成。
