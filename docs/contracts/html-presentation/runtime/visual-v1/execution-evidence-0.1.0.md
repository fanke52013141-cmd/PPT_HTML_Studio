# 生产执行证据 0.1.0

受影响规则：HPS-010、013—017、023—025、035—037。定义完成；本增量实现范围是既有生产任务的外部适配器边界、受控返工停点和只读展示。真实提供者效率、完整课程与审美验收分别记录。

## 输入、输出与所有权

输入是 ProductionStages 的 json/image 请求记录及其已有回执。html_execution_metrics.py 是纯汇总所有者；html_task_store.py 的任务字典增加 execution，沿原 Web/Agent/CLI/MCP 返回。原 production_stages 与回执增加 metrics，不新增数据表、作者场景字段或请求权限。

metrics 记录 role、adapter_calls、reuses、started_at（UTC）、elapsed_ms、adapter_input_bytes、attachment_bytes、output_bytes、usage 和 cost。role 从内部阶段标识/透明背景参数识别，不能从用户提示词猜测。输入字节是序列化的业务适配器 args/kwargs 大小，附件单独计数；不是供应商 HTTP 请求大小或 token 数。输出是持久化 JSON/图片字节数。指标内不保存 Prompt 明文、密钥或思考文本。

计时使用单调时钟，包含适配器函数内部的等待、兼容请求与解析；一次 adapter_calls 不是一次 HTTP 请求，也不证明供应商接单或扣费。返回或捕获异常后才能确认一次调用及其耗时。只有 intent 而无回执时调用数和耗时未知，不能补成零成本。重用 returned 产物增加 reuses，保留原调用数和耗时；旧记录复用不能推断历史调用。usage/cost 没有供应商证据时为 null。

execution 汇总 recorded_requests、measured_adapter_calls、recorded_reuses、unmeasured_requests、elapsed_ms、untimed_requests、输入/附件/输出字节及 roles。elapsed_ms 是可测调用时长之和，非整任务墙钟；未知计数必须同时展示。复用次数是读取复用事实，不是节省费用估算。新模块纳入生成快照源码闭包；旧快照不自动迁移或追认为当前。

## 停止与交接

progress.next_action 提供 stage、reason、routes、automatic_retry=false，仅为诊断和建议，不能触发自动重发、批准或保存。设计理解/独立对照中的 assets 路由要校验对象归属：代码控制对象转 capabilities，保留原分类和依据；图片对象才可交 assets。unsupported、重复候选、受控还原耗尽及容量修复退出分别持久化原因。非容量工程错误保持阻断，不能进入字号/位置修补。

容量决策最多三轮、受控还原最多两轮、原生产外部调用上限保持。达到预算后停止，不能新增一次调用解释失败。成功结果 stop_reason 为空；原任务显式进入新 attempt 或成功时清除旧 next_action/repair_status/stop_reason，保留阶段与复用证据。其他异常依旧按原类型处理，本增量不承诺所有错误都具备 next_action。

## 兼容与验证卡

- 数据：旧阶段可缺 metrics；汇总必须表明不完整，不改历史回执。
- 行为：未知结果禁重发、attempt 隔离、取消、人工保护、批准/作者提交边界保持。
- 展示：原审阅详情增加测量事实和介入原因；不得把耗时或工程通过展示成质量批准。
- 导出：无场景、资源或导出格式变更。
- 验证：使用隔离数据库和明确模型替身覆盖返回/异常/进程退出意图/复用/预算停止/代码归属；真实模型费用、时延和整课语义质量需另行实测。


2026-10-15 增量：[审核依据、能力路由与等待 0.2.0](design-review-authority-0.2.0.md) 为当前约束；设计 runtime 输入/输出升级 0.2.0，显式请求预算不被流包装覆盖。固定清单现为 20 项/0.2.0；旧 18 项报告保留，不跨清单直接比较。
