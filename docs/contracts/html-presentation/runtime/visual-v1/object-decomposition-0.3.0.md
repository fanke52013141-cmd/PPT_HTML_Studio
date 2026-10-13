# A02 语义对象分解与生图状态合同 0.3.0

2026-10-13；HPS-011/013/026/028/030/036。新增 `hps.html.scene_plan` 0.3.0、`hps.html.design_brief` 0.2.0；不是执行场景或 motion_binding 格式升级。A01 的0.2.0原义保留，旧0.1.0仍为未指定请求版本时的默认。新语义计划实际动作编译/配音在A03接入，独立语义QA在A04完成；不能据本合同宣称课程通过。

## 归属与独立控制边界

`html_scene_plan_models.py`是共享字段源，`html_object_decomposition.py`归属纯规划层；`html_design_brief.py`负责设计输入与独立素材需求，`html_reference_package.py`负责实际附件与内容包，`html_asset_design_prompt.py`负责独立主体请求。模型请求仍由现有review服务编排；不创建新任务池、分割服务或实际生成入口。

所有讲解文字、标签、数据/容量解释、流程、箭头和逻辑关系由已注册代码槽位独立承担。图片只承担一个独立主体，控制粒度为整张图片；图内锚点仅定位，不使其成为可单独显现的图层。需要分别出现的概念必须分成多个代码对象/已接受的独立资产；不支持图片内区域动画、动作形变、修改栅格文字、精确容量填充或未注册状态更新。当前动作词汇仍只有enter/emphasize，隐式exit/transitional在0.3.0拒绝，不能按旧编译器补动作。

既有素材板生成、拆分和接受服务保持原义；本轮不声称自动分割成熟，也不自动接受候选。已接受主体可通过现有项目resources输入引用，未接受候选不进入这些资源。模型需要拆分但资源/槽位不支持时应拆页或调整表达，不能用整张素材板绕过预算。

## 对象字段和状态

顶层新增 `objectSemantics`，逐个且仅一次覆盖实际objects；objectId复用原身份。最多64项，字符串/ID边界沿用A01。下列说明均为计划声明，结构验证不证明含义正确。

| 字段 | 约束 |
|---|---|
| role / meaning | instructional、context、decorative；非空表达职责，角色与所有语块targets一致 |
| semanticType | text/relation/data/subject/symbol；图片仅subject，文字/关系/数据/符号不能转给图片 |
| representation | code或independent_asset；与实际slot kind一致，只有image为独立资产 |
| initialState / endState | 严格布尔visible；当前只能独立显隐或强调固定内容，不声明未实现数值更新或形变 |
| initiallyVisibleReason | 背景/装饰初始可见时必填；instructional必须初始隐藏，初始隐藏时不填此理由 |
| sourceMode | 仅图片必填generate或existing；代码不填；图片必须有唯一匹配素材表及assetRef身份/版本 |
| requiredAnchors | 图片需要实际图内定位时声明具体锚点ID，不填写坐标；无定位需求时为空。focus/center、重复或未知锚点不可冒充具体定位 |

宿主按权威语块顺序推导 `visualSequence`：初始状态、每句前/后可见集合与稳定动作、结束状态。隐藏对象不能emphasize，已可见对象不能再次enter；每个instructional对象必须有自身语块驱动；endState与推导结果须一致。标注只能引用明确图片对象、文字标签和声明过的具体锚点，不能先于主体或标签显示。sequence不是实际渲染结果；A03还须验证真实帧和配音。

宿主记录 `decomposition_sha256`，绑定对象/槽位/资产、原句/动作和推导状态；对象/讲稿/状态修改后设计输入拒绝旧摘要并要求重验。摘要是复现依据，不是审阅批准；旧作者作品和批准不迁移。

## 素材预算与锚点

请求`asset_budget`严格整数0—2，默认1。最终独立主体按实际image对象数量计入预算，包括已有素材；同一asset多个对象不自动免计，素材板也不按请求次数计数。模板注册槽位仍限制图片数量；2只是预算上限，不自动扩展某模板的槽位能力。

generate记录`pending_asset`：没有实际图片，不能授予锚点/资源批准，后续生产须验证。existing只能引用本次输入已提供的项目assetRef；调用现有字节验证加载器核对PNG、散列、尺寸、alphaBBox和真实源图锚点，按identity/version选择当前页资源，不因无关资产损坏而检查本页失败。具体requiredAnchors核对唯一ID和归一化坐标，状态`resource_verified`仅表示字节与元数据通过，不代表锚点语义经过人工认可。无图内定位需求时为`whole_asset_verified`。内置/外部未登记图片须先成为有效项目资源，不能仅凭模型命名引用。

anchorChecks保存实际源图尺寸和选定归一化坐标，并进入状态摘要。组装已有主体参考时必须提供run_dir，重新核对当前字节与锚点；无变化后才复制实际PNG进入参考包附件，按assetRef和attachmentIndex指明用途，附件/缓存/manifest同时登记。锚点位置改变但图片字节未变也阻断旧规划，不能用旧定位数据制作。

## 设计与模型输入

规划PromptVersion0.6.0先声明语义对象和代码/资产分工；宿主派生sequence/状态检查，不要求模型计算散列、像素、时长或动作身份。0.2.0原Prompt0.5.0保留，用户自定义Prompt/连接配置不覆盖。

0.3.0规划返回宿主构建的design_brief0.2.0，含narration_design：对象职责、权威原句、视觉意图、初始/逐句/结束状态、主体预算和锚点状态。真实分类PNG参考包的content.json携带同一输入，其manifest/cacheKey绑定实际内容；内容与附件字节改变都拒绝。设计Prompt0.4.0只发送必要指导/内容，散列与锚点核验记录不进入模型；旧Prompt0.3.0保留。

每个独立主体的请求只携带自己的职责、initial/end状态、相关语块/预期状态与需要定位的部位，禁止将文字、数字、单位、箭头、容量条或多阶段烘焙进图片。新请求PromptVersion`html-independent-subject/0.2.0`，默认low/1024×1024/透明底；generate为`prepared_not_called`，existing为`reuse_only`。只准备provider输入，不调用付费图片服务；A03/后续调度接入时沿用设计确认停点和原服务。

## 接口、影响与验收

Web/Agent/MCP/CLI沿用同一规划路径与请求模型，显式`plan_version:0.3.0`与asset_budget；能力html_review.plan_generate@1.2，Agent API1.23.0。证据按v0.3.0隔离，不覆盖旧记录。无数据库字段、业务作者写入、批准或失效事件；新写入路径在A03同步既有影响机制。

工程验收覆盖两个Token独立代码对象案例、状态/预算/分工错误、图内控制拒绝、生成锚点待验证、实际PNG锚点与选中资源散列、包内容和状态篡改、版本和HTTP/MCP/CLI传递。案例只证明合同/资源/请求包，不证明实际视频表达、真实生图质量或用户视觉验收。不得以这些检查把S08或N02的真实课程验证改为passed。
