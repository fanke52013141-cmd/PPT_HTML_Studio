# 设计能力事实与请求效率 0.1.0

影响规则：HPS-010/011/013–017/023–025/037。契约包0.9.67；这是现有HTML生产链的兼容修正，不新增公开视觉能力。

## 定义与实现

`html_design_policy.presentation_facts`提供当前变体与各适用变体的结构事实，`component_context`统一供理解、还原和审核消费。文字节点仍是inline runs；text-card-label只强调同行前缀，不支持标签/内容强制分行。summary-panel的term在线下方、takeaway在侧列，不支持药丸压箭头与下方结论。不得从变体名称推断能力。

理解分工可用兼容可选字段`required_features`声明label_value_stacked、term_overlay_on_arrow、takeaway_below_flow。明确要求而当前/所选变体不支持时，确定性转换为unsupported并路由capabilities，在素材、排版、还原与审核调用之前停止。未识别的视觉需求仍依赖模型发现，不宣称完整能力覆盖。

审核建议切换到已启用变体时，保留缺陷、标记fact_conflict，转capabilities核实，不当作有效还原修复，不清空问题或升级为通过。合法的其它变体仍可进入还原。

理解、还原和审核的GLM请求采用low effort，thinking继续启用；模型绑定、输出额度、600秒等待、结构/工程门禁及原有轮次不变。局部容量修复沿用0.9.66的独立规则。三个运行片段登记0.4.0及内容hash。未知结果依旧禁止自动补发。

## 验证边界

同一真实设计、原始场景和HTML截图的诊断比较见[实测报告](../../../../plans/html-backend-development/design-agent-optimization-2026-10-17.md)。理解提前停止证明止损；独立还原请求仅用于耗时测量，不能越过生产门禁，不保存作者。低耗时不构成HTML视觉验收。
