# 首轮审核覆盖与重复验证 0.1.0

2026-10-21失败可诊断定义（HPS-010/011/013/015—017/023—025）：默认facts严格解析失败保留原错误码与阻断，不补事实、不重试。完整且合法表中的uncertain/空证据/对齐不确定，派生逐对象/维度/原因、原模型证据与人工核验事项；缺/重/未知项派生对应键清单。诊断以response_repair（响应结构）、evidence_review（观察不确定）区分核验工作，不能把不确定自动认定为assets/planning/capabilities缺陷。前者回查原请求清单，后者核对原图/当前截图/素材身份。完整原始响应保持，诊断绑定scene/reference/screenshot/response hash，progress发出automatic_retry=false；不保存作者、不签发通过或人工批准。增强内部审计，不新增响应格式或改变默认审核片段。

关联HPS-010/011/013–017/023–025/037，契约0.9.70。先定义检查清单和验证口径，不以模型填写清单等同视觉正确。

程序按实际对象生成review_checklist：所有节点geometry；文字承载节点content/typography；代码呈现节点structure；summary/arrow/annotation另有semantic_relation；image另有asset_identity/asset_rendering。每个targetId+dimension必须恰好返回一次coverage，status=pass/issue/uncertain，附简短具体evidence。不得以“其它页同上”省略。

每个issue必须对应同对象且匹配requirement维度的检查项，分类与原始问题下标由程序计算，不让模型管理确定性索引。新出站Schema不要求category/issue_indices，旧合法字段仍兼容；旧显式下标错误仍拒绝。检查pass不能遗漏必修问题；仅装饰观察可以与pass检查共存。缺项、重复、额外对象/维度、不一致引用或uncertain均阻止签发通过，保留原始响应和诊断；不额外重试模型。旧归档响应可用历史非强制校验读取，不把缺coverage的旧pass升级为当前完整审核。生产review_fidelity必须强制覆盖。

针对普通text对象，text_alignment_contract从准确layoutRef版本及presentation.typography.text.align推导当前CSS继承/覆盖的对齐依据，明确标为注册合同值，非OCR测量。模型必须在typography项给出参考图reference_alignment；缺失/不确定、或者与当前合同值不符却没有同对象typography问题，均停止。程序不假装能从此判断参考图识别是否正确，实际识别错误仍单独计漏检。

适配观察、跨轮问题保留、保护字段和工程/人工批准按0.9.69不变；模型、low/thinking、等待、预算不变。清单满足只证明声明覆盖，仍可能视觉漏检。首轮能力用固定未修改截图、明确已核实的缺陷和重复实验分别衡量：清单完成率、已知问题召回、全召回轮次、问题集合一致性、耗时。不同图或停止阶段不作性能因果比较，未标注的额外问题不武断算误报。

审核运行片段最终0.8.0；0.7.0的真实失败用于发现分类/维度及索引混淆，保留原记录。真实固定对照见[验证报告](../../../../plans/html-backend-development/first-review-stability-2026-10-17.md)，召回有所改善但全召回稳定性未提高，不视为最终验收。

0.9.71增量以[局部证据与类型兼容](local-review-evidence-0.1.0.md)为准：默认审核片段0.10.0、实验局部证据片段0.9.0独立；已知重复对齐字段须与唯一coverage严格一致才可接受，绝不替代完整覆盖或自动补齐问题。旧真实实验及失败状态保留，不回写成成功。
