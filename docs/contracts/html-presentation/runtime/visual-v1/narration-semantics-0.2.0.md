# A01 讲稿—视觉表达规划合同 0.2.0

> 后续A02对象分工、状态与设计输入见[独立0.3.0合同](object-decomposition-0.3.0.md)。本0.2.0版本不补字段、不改语义；新生产编译仍待A03。

2026-10-13；HPS-011/013/028/030。格式 `hps.html.scene_plan` 0.2.0；不是 scene、motion_binding 或 QA 格式的升级。定义与结构校验已实现，语义正确性、对象分解、真实时间绑定及课程调度仍待 A02—A06。

## 归属与版本

`html_scene_plan_models.py` 是 Web/Agent 与语块字段的共享类型源；`html_storyboard_planning.py` 负责注册模板、对象及版本校验，`html_narration_semantics.py` 是该纯规划层的语义合同实现。`html_visual_review_service.py` 仅组装模型请求、执行至多一次结构修复并留证。宿主校验不能由验收脚本或 Prompt 自证替代。

旧 0.1.0 的读取、默认调用和生产路径保持原意；旧作品不补字段、不重解释、不重写批准。新接口请求显式选择 `plan_version:"0.2.0"`，返回必须具有该版本；旧结果或不标版本的新字段不能作为新规划通过。当前 `compile_plan` 明确拒绝 0.2.0，防止尚未实现的多动作语义被旧编译器丢弃。A03 接入前不能把新规划作为已可生产的课程。

## 字段定义

顶层 templateRef、slots、objects、assets 延用已注册能力；对象与实际内容槽位一一对应。`version` 必填 0.2.0，旧 target 单目标字段不属于新语块。每页最多 128 个语块，每语块最多 32 个目标、32 个动作。身份为 1–80 位 ASCII 字母/数字/`_.:-`，首位为字母或数字；说明字段去外侧空白后 1–1200 字符。

| 字段 | 类型、来源与约束 |
|---|---|
| beats[].id | 引用权威 narration_beats 的稳定 ID，必须完整覆盖、无重复、无未知；冻结顺序以讲稿为准 |
| spoken_text / spoken_text_sha256 | 宿主复制原句 UTF-8 字节语义并计算 SHA-256，不要求模型重写或计算；冻结计划再验时必须与当前权威原句一致 |
| visualIntent | 必填非空字符串，说明本句应解释的具体关系、状态或事实。结构合法不证明描述属实 |
| targets | `{objectId,role,meaning}` 数组；对象须已声明、每句无重复；role 为 instructional/context/decorative，同一对象跨句角色不得冲突；meaning 是对象承担的具体表达职责 |
| actions | `{actionKey,objectId,type,expectedState}` 数组；对象必须是本句目标，type 仅 enter/emphasize；装饰不承担讲解动作；每个 instructional 目标必须有自身动作 |
| actionKey / actionId | key 是作者/模型声明的整页唯一动作局部身份，重排保留 key；宿主按 slide_id＋NUL＋key 的 SHA-256 前32位构造 `act-...`。同对象同类型可反复使用，分别采用不同 key；不是 object:type 身份。改 key 改身份，复制到另一页改身份 |
| expectedState | `{visible:true,meaning:非空说明}`；声明 enter/emphasize 后可见及其含义，不是几何或运行状态证明；运行帧验证留待 A03/A04 |
| narration_only | 严格布尔，缺省 false。true 时必须有非空 narration_only_reason，targets/actions 为空；false 时不得携带理由，须有 instructional 目标及动作。理由是待审核声明，不能自动免除内容 QA |

缺少权威原句、重复源 ID 或超出页容量，在模型调用前拒绝。冻结计划的原句/散列或 actionId 不匹配时拒绝，不偷偷重算并接受作者篡改。未知动作、目标、角色和字段返回稳定诊断；不存在旧模式回退。

## 生成与接口

PromptVersion `html-plan-0.5.0`：权威讲稿决定含义，visual_groups 与可选 design_brief 只用于设计条件，不替换原句。模型输入保留原 beat ID/spoken_text，删除源语块中的旧映射、时间等无关字段；不要求输出散列、派生 actionId、像素或时长。只列实际注册的模板/词汇，不能虚构插图内部控制能力。旧 PromptVersion 0.4.0 保持旧规划路径；没有更改用户自定义 Prompt 或存量配置。

Web 与 Agent 的已有 `.../html-review/{slide_id}/plan/generate` 使用同一 `HtmlPlanGenerationRequest`，支持 `{plan_version,brief?}`。请求不写作者文件或批准，只在 records/review 留证；Agent/MCP/CLI 由能力注册同源派生，`html_review.plan_generate@1.1`，Agent API 1.22.0。无新增数据库字段或下游失效事件。

新版本证据文件使用 `records/plan-<slide>-v0.2.0.json` 和 `_v0_2_0` 实验前缀，与旧生产证据隔离，不覆盖旧规划记录。CLI 使用原 `html plan-generate --project ... --slide ... --file request.json`，请求文件显式选择版本；未提供文件仍走旧默认。

结构校验完成时，证据分别标记 `structure:passed / semantic:not_run / audio:not_run / human:pending_review`。A01 只证明合同完整、引用合法及来源可追踪；不能据此标记讲解正确、设计还原通过、音频确认或整课完成。Token 第5页第3句仅做通用 figure 强调的旧映射必须被新合同拒绝；补齐自述字段也只得到结构通过，仍需动态语义 QA。

## 修改影响与验收

讲稿改动必须重新验证相关语块的原句/散列；视觉意图、目标或动作变化需重新检查对应表达和后续场景。当前规划接口不保存生产输入，因而不制造失效账本事件；A02/A03 接入写入路径时按 HPS-011 同步真实影响与缓存身份，不能把规划证据文件当作者场景。

验收覆盖多目标/重复强调、源顺序与身份稳定、原句字节与冻结再验、无理由纯旁白、未知/重复引用、非法动作/状态、版本降级、调用前缺源拒绝、Web/Agent同源及二十个 S08 实际语块追踪。真实付费模型、新课程画面及语义通过均另验；没有复制外部代码或新增依赖。
