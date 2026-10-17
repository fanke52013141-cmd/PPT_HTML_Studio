# 统一审核事实与独立参考定位 0.1.0

关联HPS-010/011/013–017/023–025/037，契约0.9.72。替代默认审核的双写模型协议；派生对外结果与独立批准保持。

## 唯一事实表

默认审核受控片段1.0.0，输入design-review-input/0.3.0，输出design-review-facts/0.1.0。模型唯一顶层facts，每个review_checklist中的targetId+dimension恰好一项，包含certainty、一次evidence、适用的reference_alignment和differences。差异仅含requirement/severity/suggestion/variant_id/reference_detail，不重复对象ID、证据、对齐、状态、分类或问题下标。没有差异使用空列表；uncertain/缺/重/额外项/空证据/维度错绑一律停止，不自动补发。不能把旧status/issues/coverage响应悄悄转换成新请求事实。

html_review_facts.py拥有严格解析与派生：同一事实产生问题和coverage，最终pass/changes_requested及分类/下标由程序决定。普通text参考对齐明确时，与准确layoutRef/编辑覆盖合同的当前值比较，差异自动产生typography问题；这是显式事实比较，不是程序识别参考图或补造视觉判断。参考不明确仍停止。其它语义/几何/字体/结构问题必须由模型difference提出，不猜测。纯装饰适配仍按原规则处理。

原消费者继续使用result.issues/coverage/status/routed_issues；原始facts与fact_projection来源索引保留。前轮未变问题仍独立保留，continuity标识这种继承，不宣称本轮新识别。旧归档validate_fidelity仍可按历史合同读取；新生产require_facts严格拒绝旧格式。实验同坐标窗口仍关闭默认，其旧协议与默认新协议分开。

## 参考图独立定位

html_reference_localization.py通过受控内部design_reference_localization阶段执行，只给完整参考图、原始image_size与对象type/内容身份及region_scope；不提供候选截图、HTML几何、slot、layout、presentation或动作。region_scope由对象/呈现类型确定complete_card、title_and_number、complete_relation_module或visible_content，不含位置。text加text-card变体也必须按整卡片定义，不能仅凭type=text取文字。

初版0.1.0的0..1000坐标发生混用，保留历史验证函数和记录，不能按越界数值猜单位。当前定位片段0.2.1、输入/输出0.2.0使用绝对像素xPx/yPx/widthPx/heightPx，边界与实际image_size严格比较，不截断、不换算或猜测旧结果单位。逐targetId仍有status=located/not_found/ambiguous、identity_evidence和图上visible_text。located须有合法范围框，文字承载对象须非空转录；其它状态须box=null，not_found无可见文字允许null或空串，不允许编造非空转录。ambiguous可无可见文字。0.2.0真实模型的缺失对象null曾被旧类型拒绝，0.2.1将这种语义明确为nullable，回放与新模型请求分别报告。结构正确只证明协议合法，不证明定位正确。

每次保留原始请求/响应、原图与scene/身份hash、模型建议裁剪和红框总图。quality=model_proposed_unverified，人工批准pending，不自动接生产审核或提升成参考事实。来源路径/等待/low/thinking及未知不重发沿用设计Agent；本任务的独立三次重复是明确验证实验，不增加原生产还原轮次。

## 验证与当前性

先固定原图和独立可见对象边界标注，再计算对象命中、完整覆盖和IoU；框存在或转录与输入相同不足以证明身份。加不存在对象负例，要求不产生虚假框；重复三次报告一致性。对象移位不能沿HTML坐标猜位置。标签基准不得由本次模型框反推。新的跨布局泛化、真正文字身份核验及定位接入效果在实测账本分别记录，不以小样本通过替代整课验收。

新解析/定位模块、运行片段与注册合同加入生产snapshot源闭包；旧冻结快照保持不可变，不重签为已执行新协议。无作者保存、视觉批准、声音或输出格式改变。

同次审核实验因旧版length输出上限在8次后提前停止；已确认终态与初版评估器unknown误分类分开留档，不自动重发。定位0.2.0三份原响应按0.2.1离线回放区域15/18达阈值，来源文字三次均错取灰色整条，故仍不接入生产。完整证据见[实测记录](../../../../plans/html-backend-development/review-facts-localization-2026-10-17.md)。
