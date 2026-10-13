# A02 语义对象分工与设计输入 0.1.0

2026-10-13；叠加 scene_plan 0.2.0，关联 HPS-011/013/028/030。Agent API1.22.0 请求形状不变，契约包0.9.33。当前新版规划尚未发布到默认生产；旧0.1.0路径保留。

## 定义卡

| 项目 | 定义 |
|---|---|
| 输入 | A01已规范化计划；原句及散列、注册对象/槽位、角色、初始可见、动作和预期状态 |
| 输出 | hps.html.semantic_design 0.1.0，分工allocations、初始/逐句/最终可见对象、原计划hash和自身hash |
| 所有权 | html_semantic_design为纯投影与约束检查；html_design_brief消费分工；html_reference_package把必要表达投影传给设计Prompt |
| 表达 | 准确文字、数据、关系和独立讲解对象属于code；kind=image属于image_asset，figure仍是代码容器 |
| 素材 | 当前语义适配最多一个独立主体。每个图片对象与image_asset需求一一对应，需求id=assetRef.id且版本非空；不是扩大原素材预算 |
| 状态 | enter/emphasize，按动作列表顺序计算声明可见集合；强调前已进入，所有非初始对象须有enter。不能承诺exit/换文案/内部变形 |
| 图片控制 | whole_asset_only；同一图片跨语块的expectedState.expression必须相同。不同描述即保守阻断，请统一其不变外观或重新分工；不作自然语言同义推断 |
| 几何 | 用真实匹配版本的注册布局box/maxLines作为规划上下文；不支持自由布局或任意新组件 |
| 验收 | 结构/顺序/身份通过不等于画面正确。semantic_review固定pending_review；真实素材身份/锚点、实际时间/截图另验 |
| 兼容 | 新版设计brief0.2.0/设计Prompt0.4.0；旧brief0.1.0/设计Prompt0.3.0保持。A03未完成前禁止将新版计划编译为旧单目标动画 |

## 规划输入及修复上下文

html-semantic-plan/0.2.0 使用白名单输入：本页id/title、每个beat的id/spoken_text、视觉组id/description/不同的屏幕content、可用素材id/version/description。brief只带templateRef/theme/asset_budget/subtitle_reserve/asset_needs的决策字段。音频路径、时间记录、散列和完整效果目录不进入user消息。

只删除与本页原句串联（含明确标题前缀）完全相同的content；独立屏幕文字保留。不得通过摘要替换原句或猜测语义等价。system提供模板/合法kind/字段、真实box/maxLines和工具范围。新增必要上下文可增加system长度，不能以更短为优先目标。

源语块缺失、重复或原句为空、无效素材声明、非法budget在调用模型前拒绝。结构修复的具体诊断只在user提供一次；Pydantic错误只保留前8条loc/type/msg及剩余数量，不回显整段输入和说明URL。原失败响应完整保留在本地；最多一次结构修复仍保留。

同一beat/object/type/出现序号的原合法且不重复actionId在结构修复中必须保留；原重复或非法ID允许修正。删除/改含义需要重新规划，不从新名字推断与旧作品等价。本门禁只限当前两轮修复，不宣称已实现跨改稿的完整ID迁移。

## 设计输入链路

新版模型规划通过A01后，再经过A02分工校验；失败可在同一有界结构修复内纠正，最后仍失败则保留诊断停止。plan_evidence返回semantic_design，build_design_brief也从当前plan重算；reference_package再次核对brief与plan一致，不复用陈旧分工。

参考包content.semanticDesign携带对象职责、起始/最终可见集、原句、视觉意图、目标和预期表达。actionId、动作操作和每步完整可见集、审计hash留在计划/证据，不重复发给静态生图。语句原文支持检查表达相关性，不要求生图把旁白印在画面上。准确屏幕文字仍只来自slots。

设计Prompt生成一张终态完整页面，要求布局支持对象独立显现，不画分镜格、不将多个讲解对象合成一张主体。required_keyframes为新版投影start/每个视觉beat/end的审阅要求；这不是已生成图片序列或音频时钟。单图片内部区域/语义锚点未经实际资产校验不能声称可控；当前设计投影只承诺整个主体。

generation和设计候选定义指纹纳入semantic_plan、semantic_design、planning_context。规则变化应重建输入及重新审阅，不能给旧候选补写新批准。

## Agent/Skill边界

候选排版Agent继续使用LangGraph evaluate→decide→apply，只有受控capacity-repair片段进入模型，固定工具合同、max3轮、人工字段和严格浏览器review保持。主题/布局按id+version唯一匹配，缺失拒绝REPAIR_REFERENCE_VERSION。不能借用另一版本的预算修复当前场景。

内容/状态/素材分工错误回到规划，不交给排版Skill。Codex操作Skill1.8.0记录此路由，但结构化facts路由测试不是自然语言分类准确率或生产自动编排证据。没有新增自主规划Agent或第六个运行Skill。A03实际编译/绑定、A04真实帧语义QA、A05课程调度仍是后续阶段。
