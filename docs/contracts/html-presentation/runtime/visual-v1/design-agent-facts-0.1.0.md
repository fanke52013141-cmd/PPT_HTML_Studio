# 设计能力事实与请求效率 0.1.0

2026-10-21逐对象观察定义（HPS-010/011/013/015—017/023—025/035—037）：最终理解0.7.5/内部输入输出0.3.0将独立插图观察与能力分工分开，同一次原请求返回feature_observations，逐输入对象恰好一条targetId、feature=independent_illustration、presence=present/absent/uncertain及短可见evidence。不论ready或unsupported均须完整；不能因对象已有image能力省略观察，不因一个缺口丢弃其他观察。观察对象自己承担的内容，不能将已有image承担的同一照片重复分配给外框/标题/标注；不按对象类型猜看图结果。程序验证覆盖、唯一性和证据，present与实际能力比较产生capabilities缺口；uncertain保留原观察及hash、以evidence_review停止，不自动重试或当作不存在。缺/重/未知对象等结构错误沿原一次修复预算，仍非法则停止。新出站Schema必需此表，旧归档Understanding仍可读取，不能据旧省略推断absent。旧required_features其余语义/原三项保持；新独立插图观察为唯一新判断源，旧显式同名需求不得与其矛盾。旧候选源码/运行片段身份须重验，不迁移数据库、不写作者或批准，公开API与包版本保持。0.7.4试验容器误拦保留；最终同图真实识别4/4、负例6/6，系统缺口拦截2/2、负例8/8，原模型问题类型仍错分。单一课程开发集不代表泛化或人工批准，见识别评测开发记录。

2026-10-21系统缺口优化定义（HPS-010/011/013/015—017/023—025/035—037）：presentation_facts明确独立插图能力与装饰图标不同；card内只有注册图标，无独立图片槽，figure是框架而非图片。理解required_features兼容新增independent_illustration，只有image对象满足，非图片对象声明此需求时在素材/排版/还原前返回capabilities；不自动增加对象、转位图或用图标代替。能力判断依赖模型明确声明，不宣称自动识别全部参考需求。旧省略字段行为不变、原三项特征保持，理解片段升级0.7.3、实际JSON Schema同步，公开API/数据库与包版本不变。原源闭包/候选身份须重验；真实识别召回另验。

影响规则：HPS-010/011/013–017/023–025/037。契约包0.9.67；这是现有HTML生产链的兼容修正，不新增公开视觉能力。

## 定义与实现

`html_design_policy.presentation_facts`提供当前变体与各适用变体的结构事实，`component_context`统一供理解、还原和审核消费。文字节点仍是inline runs；text-card-label只强调同行前缀，不支持标签/内容强制分行。summary-panel的term在线下方、takeaway在侧列，不支持药丸压箭头与下方结论。不得从变体名称推断能力。

理解分工可用兼容可选字段`required_features`声明label_value_stacked、term_overlay_on_arrow、takeaway_below_flow。明确要求而当前/所选变体不支持时，确定性转换为unsupported并路由capabilities，在素材、排版、还原与审核调用之前停止。未识别的视觉需求仍依赖模型发现，不宣称完整能力覆盖。

审核建议切换到已启用变体时，保留缺陷、标记fact_conflict，转capabilities核实，不当作有效还原修复，不清空问题或升级为通过。合法的其它变体仍可进入还原。

理解、还原和审核的GLM请求采用low effort，thinking继续启用；模型绑定、输出额度、600秒等待、结构/工程门禁及原有轮次不变。局部容量修复沿用0.9.66的独立规则。三个运行片段登记0.4.0及内容hash。未知结果依旧禁止自动补发。

## 验证边界

2026-10-21固定识别评测：见[固定参考集与漏检率基线](../../../../plans/html-backend-development/feature-recognition-benchmark-2026-10-21.md)。图像/原请求响应/独立标签hash封存；特征声明与能力缺口拦截分开统计，旧输出合同未要求的新特征记未决，不计FN。模糊弃权、未知/非法、归档/受控/新模型、标注权威与课程/页/目标分母分别记录。只读文件评测无供应商/作者/批准，不将开发集及历史响应率当新模型泛化效果。HPS-010/011/013/015—017/023—025/035—037，公开API/契约包保持。

同一真实设计、原始场景和HTML截图的诊断比较见[实测报告](../../../../plans/html-backend-development/design-agent-optimization-2026-10-17.md)。理解提前停止证明止损；独立还原请求仅用于耗时测量，不能越过生产门禁，不保存作者。低耗时不构成HTML视觉验收。
