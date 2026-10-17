# 摘要内部容量与局部修复效率 0.1.0

2026-10-17；HPS-010/011/013—017/023—025。兼容修复，不改作者Schema、文字、动作身份或人工门禁。

`summary-panel`的from/to列保留120px下限，允许在既有摘要预算内按内容最大宽度展开；中间关系列132px和间距保持。旧短文案仍满足原下限，长文案不再被固定120px格截断。整体槽位和scroll/文字边界严格检查不变，不通过溢出裁切或缩字号掩盖问题。版式可能变宽，现有设计需重新检查，不自动获得视觉批准。

摘要容量诊断增加internalParts（公开part、实际宽度、scroll/client宽度、字号、内边距）及flowColumns。候选Agent输入增加presentationSizeEditable、capacitySizeHint和previousDecisions。尺寸提示只由canvas_px的box_height/box_width触发项推导：当前外尺寸减有效限值得到内边距，再加实测尺寸；不是自动应用的操作或新容量阈值。模型仍须核对邻居、人工保护和浏览器结果。

容量修复请求显式180秒共享流总预算；仅GLM识别的request级reasoning_effort_override=low，thinking保持开启。max_tokens、温度、供应商绑定和三轮预算不变；其它Agent请求不变。超时仍unknown，禁止自动重发。该超时不等于整任务含排队/格式兼容请求的绝对上限。

runtime片段candidate-layout-repair升级0.2.0并登记真实hash；旧0.1.0保留。新输入为内部兼容补充，原输出patch/stop及编辑操作保持。节点类型和工具以真实type/能力为准，不从marker等ID猜annotation；当前有效高度为0不代表可编辑外尺寸无法增加。

实际同候选诊断：原生产3次排版决策累计674.95秒后summary宽404>400+1失败；修复后原末轮场景去掉摘要缩字号，严格重放通过。完整原初态、原binding和visual_contract在隔离目录进行系统Agent诊断，2次决策、包含浏览器检查共21.05秒通过；不保存作者，不重置原任务，不宣称完整HTML还原/视觉验收通过。模型随机性、组件修复、输入变化与low配置共同变化，不能单独归因或推断长期成功率/费用。

诊断准备中两次缺绑定/讲稿合同，第三次模型停止、第四次无进展停止均保留为失败证据；最终第五次通过，不以最后成功覆盖之前调用。详细运行证据在忽略目录outputs/summary-agent-low-replay*-20261017。另一条独立回归neutral-science seek连续两次失败保持待定位。
