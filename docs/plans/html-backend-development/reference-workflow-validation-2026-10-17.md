# 共用参考规则与审核连续性验证

## 本轮目标与实现

统一理解、还原、审核的判断口径，不继续为第2页添加装饰图标。规范见[参考工作流规则](../../contracts/html-presentation/runtime/visual-v1/reference-workflow-policy-0.1.0.md)，契约包0.9.69。

三个实际设计runtime片段0.6.0引用同一个reference-workflow-policy-0.1.0.md及可信hash；生产上下文和确定性分类来自html_design_policy。新增可选reference_detail显式区分纯装饰图标与容器外观。只在完整文字的text/header/summary、unsupported_presentation且非major时转为reference_observations；不按minor或模糊证据删除问题。旧模型输出缺字段仍保守阻断。真实图片、card、语义关系、结构、几何/字体和内容等不据此豁免。理解必须有完整分工，不能由程序伪造ready对象。

review_fidelity保存节点hash、几何与实际截图区域hash，并把未解决问题和前后证据交下一轮；不传理解结论或批准。程序对区域像素/盒子未变的问题强制保留，缺可比区域证据的未变节点也不自动清除。变化只允许重审，不证明已修复。模型原始响应、观察和最终规则结果各自留档。

## 数据与证据

| 检查 | 优化前 | 优化后 |
| --- | --- | --- |
| 同一真实设计因纯图标/节点造型差异回capabilities | v3旧实验3项（stat-1、stat-2、summary） | 新实验0项；三阶段均消费同一规则 |
| 已归档“摘要区域未变，却下一轮pass”事件 | 原模型pass漏掉1项箭头问题 | 程序保留1项，changes_requested；0次模型调用 |
| 新实验真实卡片对齐问题 | 首轮3项 | Agent合法操作后第二轮0项 |

旧失败和模型pass不追溯覆盖。离线连续性重放使用v2归档的原图、真实0/1候选截图、对象和几何：scripts/evaluate_html_review_continuity.py核对图片hash后重放；证据outputs/reference-workflow-policy-20261017/continuity-replay.json。本例未变区域的像素证据确实命中，不是只比较文字描述或假定操作有效。

同案例真实实验outputs/reference-workflow-agent-20261017，沿用已确认图片SHA256 b81aec5dabe40d82d9e7ce5f3ed7fe52897e4b3ba4f6bd0041e141ec847950a6及原权威计划，系统reconstruct_design完整调用。理解12.444秒；容量1轮9.741秒通过；还原6.171秒/审核15.176秒；第二轮还原7.224秒/审核12.420秒。6次实际HTTP请求全部完整返回，总模型63.176秒；无unknown补发、无新生图、无作者写入/人工批准。

新实验最终仍停止在两轮预算：第二轮发现caption出处文字居中，要求用现有typography工具改为left。这个问题未被装饰规则吞掉，也不要求扩组件。首轮未发现、第二轮才出现，说明审核覆盖稳定性仍需改进；不为追求pass增加轮数或人工补本页。新旧实验的停止原因不同，不将63.176秒与旧54.144秒当作性能优化证明。本轮证明口径一致及误放拦截，不宣称稳定性或整页验收通过。

## 回归

checks/test_html_reference_workflow.py新增18项专项通过（0.96秒），覆盖显式观察保留、8种必须阻断的需求、4种保守边界、理解完整分工、实际像素连续性、缺证据保留、原图不匹配零调用、真实审核入口保留raw pass但返回changes_requested。

整组checks/test_html_reference_workflow.py、test_html_design_agent.py、test_html_design_reconstruction.py、test_html_design_policy.py、test_html_runtime_skills.py为107项通过（102.70秒；该次收集包含新增17项），随后增加的真实入口测试在18项专项重跑通过，共108个不同测试验证。先前一轮在修改运行片段注册表期间触发1项CHANGED_DURING_RUN，保留并在固定源码后完整重跑；不放宽哈希保护。Python编译检查通过。

本轮未改渲染器，未重跑其全量浏览器测试；既有neutral-science seek非确定性仍开放。模型仍可能把语义误分类为装饰，显式分类与保守字段约束不能代替通用语义识别或人工批准。连续性只能拦截有可比证据的未变区域，不能证明所有已变区域都正确。接下来优先测首轮逐对象覆盖与问题发现稳定性，而非添加本页装饰或重做设计图。
