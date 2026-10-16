# 设计审核依据、能力路由与等待 0.2.0

受影响规则：HPS-010/011/013—017/023—030/035—037。定义与本增量实现完成；离线验证、真实同案例决策、端到端生产和人工验收分别记录。

## 定义卡：依据和输入

准确对象内容、生产主题、人工保护和已注册能力高于参考图。neutral-baseline 的灰阶映射不因原图彩色而判错；原图错字不复制到代码。所有语义文字、图内标签及关系归代码，image 只承载非语义插图。图中缺标签不能因为顶层节点为 image 就交生图补字。

`html_design_policy.py` 统一 production_policy 和各节点 editable；能力来自实际 PARTS/STYLE_KEYS 与适用注册变体。set_text_style 只编辑完整 part 的字号、字重、行高、对齐，不提供分段加粗、颜色、新子部件或装饰。annotation 没有本阶段静态编辑工具。其他主题仅声明 registered_theme，未声称已给模型提供所有主题完整色值。

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

ProductionStages 对支持流进度的生成器开启 streaming，但必须保留调用方明确的 request_timeout；仅缺失/None 时默认 1800 秒。理解、还原、独立审核明确为 600 秒；规划的既有 1800 秒不变。metrics 记录实际传入 request_timeout_seconds。模型、温度、max_tokens、reasoning_effort 保持供应商绑定配置，不静默关闭思考以换速度。

此数值由共享传输控制单次 completion 的总流等待，不是整任务、排队或含所有格式兼容/JSON 修复请求的绝对墙钟上限；无输出时仍受 SDK 读超时约束。未知外部结果保持原有禁止自动重发规则。底层兼容和 JSON 修复可能多于一次 HTTP，须与适配器调用分开计数。

Agent API 1.33.0：produce 1.7、task_status 1.3、task_current 1.2，沿现有 next_action/execution 返回新语义和请求超时；无新请求字段、数据库迁移、作者或导出 Schema。Web 显示 design_review 为“设计与生产规则审阅”。

## 验证与同案例复验

固定事故清单升级 0.2.0，共 20 项，新增语义归属、真实可编辑能力、独立审核输入和显式等待预算案例。不同清单不与旧 18 项百分比直接比较。

`scripts/evaluate_html_design_review.py` 的 --live 使用项目当前系统模型绑定、共享 JSON 多模态适配器及上述真实 runtime fragment；分别重放原始理解场景和原失败还原截图的独立审核。先验证原 scene/image/report hash，保留原失败、原模型响应和新响应。数据库/运行目录隔离，生产配置只读，输出必须为新目录；未知结果不自动补发。

两臂是独立诊断实验：即使理解提前停止，仍可单独审核历史失败截图，不代表生产越过停止门禁。原候选因定义变化保持过期，实验不签发当前设计接受回执、不写作者、不新生图、不生成视频；结果不等于完整生产链复验。HTTP 开流记录不冒充完整耗时，适配器完成计时单独记录，usage/cost 无证据为 null。
