# 设计审核依据、能力路由与等待 0.2.0

受影响规则：HPS-010/011/013—017/023—030/035—037。定义与本增量实现完成；离线验证、真实同案例决策、端到端生产和人工验收分别记录。

## 定义卡：依据和输入

准确对象内容、生产主题、人工保护和已注册能力高于参考图。neutral-baseline 的灰阶映射不因原图彩色而判错；原图错字不复制到代码。所有语义文字、图内标签及关系归代码，image 只承载非语义插图。图中缺标签不能因为顶层节点为 image 就交生图补字。

`html_design_policy.py` 统一 production_policy 和各节点 editable；能力来自实际 PARTS/STYLE_KEYS 与适用注册变体。set_text_style 只编辑完整 part 的字号、字重、行高、对齐，不提供分段加粗、颜色、新子部件或装饰。annotation 没有本阶段静态编辑工具。其他主题仅声明 registered_theme，未声称已给模型提供所有主题完整色值。

现有 `card` 对象的注册图标由场景字段直接绘制。设计理解输入以 `capabilities.currentRender.icon` 明示该已存在呈现，`capabilities.icons` 只列出本阶段可通过适用变体选择的新图标；空列表不等于卡片没有图标。保留当前图标的分工使用 `variant:null, icon:null`，不得借此开放未注册的图标切换。九页真实案例均规划三张卡片；第 4 页三个图标已在计划中注册为 `document`、`speech`、`lightbulb`。这项修正只解决能力说明误导，实际模型决策与 HTML 保真仍需同候选复验。

| 输入 | 消费者与用途 |
| --- | --- |
| production_policy、objects | 三个设计 Agent 的权威内容与主题边界 |
| capabilities.editable、variants/icons | 分工、还原和审核判断操作是否真实可执行 |
| 原设计图片 | 理解与构图参考，不覆盖准确对象内容 |
| 实际截图、geometry/measurements、manual_protected_paths | 独立审核和受控修复的可见证据与保护 |

独立审核不接收上一个理解 Agent 的完整结论；受控还原移除重复理解结果和第二份全量变体目录，保留实际几何、对象及适用能力。稳定规则只在受控 runtime fragment 声明，实例不夹带指令。

## 定义卡：输出及路由

设计理解、受控还原不支持响应和独立审核的问题必须带结构化 requirement；缺少或非法枚举时失败关闭。category/模型建议 route 只是证据，不能直接决定执行路径。

| requirement | 最终路径 |
| --- | --- |
| semantic_text / semantic_relation | planning，包括 image 内部的语义标签和关系 |
| asset_identity / asset_rendering | image 才能 assets；代码对象为 capabilities |
| geometry / typography | 该节点存在相应注册操作才 reconstruction，否则 capabilities |
| registered_variant | 给出明确且适用 variant_id 才 reconstruction，否则 capabilities |
| theme_conflict | design_review，保留冲突待审 |
| unsupported_presentation | capabilities |

每项只表达一种需求。路由保存 requirement、原分类/原建议、解析后路径与原因。不支持或上游返工时 automatic_retry=false，不自动发起模型解释、图片重生、作者保存或批准。结构化分类仍由模型判断，程序路由不能证明模型没有漏检或误分类。

三份 runtime fragment 与输入/输出合同升级为 0.2.0，registry 登记实际文件 hash。旧 0.1.0 响应保持历史证据，不补 requirement、不改原任务成功或候选新鲜度；新生产须建立当前定义的快照。源闭包加入 html_design_policy.py。

## 定义卡：等待与兼容

ProductionStages 对支持流进度的生成器开启 streaming，但必须保留调用方明确的 request_timeout；仅缺失/None 时默认 1800 秒。理解、还原、独立审核明确为 600 秒；规划的既有 1800 秒不变。metrics 记录实际传入 request_timeout_seconds。模型、温度、max_tokens 保持供应商绑定配置；一般阶段的 reasoning_effort 也保持绑定配置。2026-10-16 起，仅 GLM-5.3 系列的 `design_understanding` 使用请求级 `reasoning_effort=low`，thinking 继续开启，不写回绑定；还原和独立审核仍用绑定配置。

此数值由共享传输控制单次 completion 的总流等待，不是整任务、排队或含所有格式兼容/JSON 修复请求的绝对墙钟上限；无输出时仍受 SDK 读超时约束。未知外部结果保持原有禁止自动重发规则。底层兼容和 JSON 修复可能多于一次 HTTP，须与适配器调用分开计数。

第 4 页旧请求在 5,752 个流块、25,294 字符推理且正文为零后发生 `RemoteProtocolError`，没有 finish_reason 或 usage；供应商接口无按请求 ID 查单能力。只能确认本地未收到完整结果，不能推断供应商未处理或未计费。旧任务保留 unknown，不自动 resume；同一已确认设计候选的新实验使用新任务及请求 ID，单独记录调用、流证据和结果。low 策略用于降低冗长流的暴露时间，真实可靠性仍需新实验验证。

正常重复提交继续受旧 unknown 门禁阻断。若操作者在本地核实后明确选择新实验，请求须带 `prior_unknown_task_id` 和相同的 `design_candidate_key`；服务核对该任务属同一项目且已失败/中断、原合同与模型绑定及作者修订未变、新旧选项仅差此引用、未发现可恢复响应回执或作者提交，并确认唯一未决阶段是无法查单的 JSON 请求。仅此情况生成新的快照与任务身份，不改变原任务状态，也不宣称供应商结果已核实为失败。任何证据不符继续阻断。

新实验仍须使用原设计图及候选 key。因运行策略修复改变了设计定义指纹，服务只在上述旧任务核验通过后，对比旧快照中 `html_design_agent.py`、`html_production_service.py` 的原始哈希，并使用已钉住的历史候选存储器哈希重算候选的完整定义指纹；其它定义任一变化仍视为 stale。候选 JSON key、图像字节与源合同保持精确一致，运行中继续检查当前源码不变。该兼容只针对已核实的未知结果新实验，不改变普通设计审批或重用规则。

真实 low 请求 6.1 秒正常完成且返回安全用量，但首次对象分工 JSON 未通过严格结构校验。仅对**已完整返回**且结构/分工不合法的设计理解响应允许一次同设计图、同对象输入的完整 JSON 修复请求；记录原响应、诊断、修复请求及结果，仍必须通过相同校验。断流/未知结果不进入修复，不自动重发；二次不合法停止并保留证据。

后续完整分工曾选择 `summary-relationship-panel` 给缺少 heading 的 summary，编译器直到素材生成后才报 `PRESENTATION_HEADING_REQUIRED`。设计理解能力输入及返回校验现按注册编译器前置条件筛掉该类不适用变体（包括关系摘要 heading、分隔符及必需 icon），避免把不可能执行的分工交给素材/还原阶段；模型不得以其它素材补缺失 heading。

Agent API 1.33.0：produce 1.7、task_status 1.3、task_current 1.2，沿现有 next_action/execution 返回新语义和请求超时；无新请求字段、数据库迁移、作者或导出 Schema。Web 显示 design_review 为“设计与生产规则审阅”。

## 验证与同案例复验

固定事故清单升级 0.2.0，共 20 项，新增语义归属、真实可编辑能力、独立审核输入和显式等待预算案例。不同清单不与旧 18 项百分比直接比较。

`scripts/evaluate_html_design_review.py` 的 --live 使用项目当前系统模型绑定、共享 JSON 多模态适配器及上述真实 runtime fragment；分别重放原始理解场景和原失败还原截图的独立审核。先验证原 scene/image/report hash，保留原失败、原模型响应和新响应。数据库/运行目录隔离，生产配置只读，输出必须为新目录；未知结果不自动补发。

两臂是独立诊断实验：即使理解提前停止，仍可单独审核历史失败截图，不代表生产越过停止门禁。原候选因定义变化保持过期，实验不签发当前设计接受回执、不写作者、不新生图、不生成视频；结果不等于完整生产链复验。HTTP 开流记录不冒充完整耗时，适配器完成计时单独记录，usage/cost 无证据为 null。

## 0.9.69共用规则增量

纯参考装饰与必须保真缺陷的共同边界、显式reference_detail与观察留档，以及跨轮未变区域问题保留，以[参考工作流规则](reference-workflow-policy-0.1.0.md)为唯一当前增量；不得沿用早期“所有未注册装饰都返工”的解释，也不得因minor或模型新pass删除仍未变化的问题。独立审核仍不把理解阶段结论当事实，前轮仅传未解决问题和证据变化。
