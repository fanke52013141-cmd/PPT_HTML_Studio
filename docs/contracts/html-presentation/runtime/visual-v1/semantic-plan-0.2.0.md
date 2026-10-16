# A01 讲稿—视觉表达规划合同 0.2.0

2026-10-13。关联 HPS-011/013/028/030。身份 hps.html.scene_plan@0.2.0；Agent API 1.22.0。这是独立规划增量，不升级 scene/motion_binding，不等于语义 QA 或课程自动制作。

## 定义卡

| 项目 | 定义 |
|---|---|
| 所有权 | html_storyboard_planning 负责版本/注册验证与纯归一化；html_semantic_plan 负责严格语义字段和来源引用验证；html_visual_review_service 编排配置模型与最多一次结构修复 |
| 输入 | 当前页权威 narration_beats，注册模板/槽位/图标与内容字段；可选既有 brief |
| 输出 | 已规范的对象、原句及其散列、意图、目标、动作、预期状态；plan_evidence 的结构、含义和运行实现状态分开 |
| 身份 | slide_id、beat ID 来自权威输入，object ID 来自对象表；actionId 由规划者指定、整页唯一，修复时保留；模型不生成原句散列 |
| 角色 | 每个对象声明 instructional/context/decorative 与 initialVisible；初始可见只允许有理由的 context/decorative；instructional 必须由语块明确进入 |
| 几何与能力 | 每个活动槽位恰好一个已注册对象；不增加模板、自由 HTML 或图片内部虚构锚点。对象表达范围仍由注册能力决定 |
| 验证 | 严格字段、引用、覆盖/顺序、文本散列、唯一动作与进入声明；不从字符串判断任意表达的事实真伪，不签发 semantic approval |
| 兼容 | 旧 0.1.0 保持默认与原行为；新语义字段不得静默降级，未知版本拒绝。旧作品不回填角色、动作或批准 |

## 输入与输出

公共 plan_generate 请求新增 `plan_version: "0.1.0" | "0.2.0"`，默认旧版。Web/Agent/MCP/CLI 复用 HtmlPlanGenerateRequest，未知字段拒绝。CLI `html plan-generate --project <id> --slide <id> --file <request.json>`，文件可为 `{"plan_version":"0.2.0"}`。这是独立规划诊断入口，produce 尚按旧版工作；A03 前不能将新版计划送入生产编译，返回 SEMANTIC_RUNTIME_NOT_IMPLEMENTED。不因新版规划通过宣称现有生产语义缺陷已解决。

新对象在原 id/slot/kind/icon/exit/transitional 基础上声明：

```json
{"id":"output-reserve","slot":"stat-2","kind":"text","role":"instructional","initialVisible":false}
```

语块字段：

```json
{
  "id":"输入中的语块ID",
  "visualIntent":"解释输出需要预留上下文空间",
  "targets":[{"objectId":"output-reserve","purpose":"展示输出预留的具体说明"}],
  "actions":[{"actionId":"该语块-reserve-enter","objectId":"output-reserve","type":"enter"}],
  "expectedState":[{"objectId":"output-reserve","visible":true,"expression":"能看到输出预留空间的准确文字说明"}]
}
```

例子是字段说明，不注册示例对象或槽位。targets/actions/expectedState 均为数组，目标和状态无重复，每个目标恰有一个预期状态；动作只能引用该语块的目标。当前规划动作支持 enter/emphasize，可在不同语块用独立 actionId 反复强调同对象；只允许一次 enter。A03 尚未核对强调与进入的真实时刻、生存周期与音频，这些不由此文档宣称支持。

每个 beat 必须按权威讲稿原顺序出现一次，不允许新增、删除、重复、换序。语义归一化从 spoken_text（缺失时 text）取原字节，注入 spoken_text 和 UTF-8 SHA-256；不会裁剪原句。模型若回传原句或散列则必须完全相同，不能用视觉摘要改写朗读源。模型不提供这些字段更好。

纯旁白须 `narration_only:true` 和非空 narrationOnlyReason，三个视觉数组为空，仍须 visualIntent 说明语义任务。它不能自动获得讲稿—画面对应批准。无理由纯旁白、旧 target 字段混入、新版本降级或缺少视觉可检查状态拒绝；空泛 figure/focus 的自述即使形式合法也不表示解释完成。

## Prompt 与有界修复

新版 PromptVersion html-semantic-plan/0.1.0 只负责语义规划。稳定规则位于 system；本页讲稿/视觉组与已有 brief 位于 user，不发送其它页面或要求生成内部 hash。模型必须解释具体对象分工，不能把“为回复预留空间/检查实际用量”绑定到一个泛化插图强调就自称完成。

出站日志保留实际 Prompt、响应及版本/hash。缺少新版本号视为降级，最多一次结构修复；第二次失败保存原诊断并停止，不自动退回旧版。generation 快照闭包新增纯合同模块，来源修改使旧快照不可直接继续；不修改已有账本来绕过。

## 验收与后续依赖

A01 structural passed 仅指声明、来源与引用正确。evidence.semantic.meaning=pending_review、runtime=not_implemented；模型自己返回 expectedState 不能批准画面。20 个旧 Token 语块的合同回归只验证来源可追溯，不表示这些案例已由模型重新规划、已渲染或语义签收。

A02 消费这些意图和角色拆分代码/素材与生图状态；A03 才接多 actionId 的实际编译与配音时间轴；A04 检验真实帧和旁白，允许发现形式合法但内容脱节的声明；A05 接统一产品调度。正式导出、听审、人工保护、素材和付费结果恢复门禁原样保持。


2026-10-15 增量：[多标签讲解与注册呈现](labeled-explanation-0.1.0.md)提供独立代码标签/关系槽和四个新变体，旧定义保持。语义规划Prompt0.3.0实际可选择；Agent API1.34.0。固定清单0.3.0现为21项，旧18/20项报告保留，不跨清单比较。
