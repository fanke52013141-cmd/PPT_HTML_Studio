# 修复调用链优化：输入收敛与流式观测 · 2026-10-20

基于main 00fb81d4及本机累计未提交优化。实际应用源码`D:\Program Files (x86)\PPT_HTML_Studio`，附件工作区`C:\Users\Administrator\Desktop\html动画\PPT_HTML_Studio`。包0.9.111/API1.59.0，内部Prompt0.3.4/0.4.3。

两次真实请求超时不能判定两个执行器质量均差。此次先处理实际发现的可修问题，不追加模型请求，不重发unknown。此前真实结果与本批离线验证分别留证。

## 已落地

- 普通局部repair入口此前未开启已有流式能力，Legacy只能等最终返回；现在对支持能力的原生成器/partial开启stream_output并持久进度。第三方无标记生成器保持原签名，不修改模型、thinking、温度、65536额度、等待时间或调用轮数。
- PiJSON之前只汇报整轮结束的usage。现在原SDK事件经过progress.mjs只发长度/状态/时点，宿主记录首个可见事件、首次正文/工具参数、最后活动、静默及阶段/任务预算；静默每5秒更新。本地stream-N.json和原ProductionStages回调同源。宿主使用同一时钟计时，SDK首事件不冒充网络首字节。
- Legacy原流传输记录HTTP响应头时点及合法x-request-id；不复制其他头。完整stop后返回安全usage，截断/中断仍不能进入JSON修复。request ID不自动表示供应商支持终态查询。
- 模型输入只保留scope、实际冲突、显式关系端点的细测量和适用呈现目录/绑定；每张图全部邻居boxes、全部箭头与标注几何保留，避免移动后撞到别的箭头。原全页检查、截图与保护保持，原完整报告留盘。
- 回调异常也会回收Pi子进程和管道；日志不保存推理、正文、工具参数或原始异常。unknown不重发，usage/cost缺失仍null。新增模块进入runner_identity及生成快照源码闭包。

## 输入重放数据

同此前冻结原稿/指令/截图，未调用模型；新结果在`outputs/repair-input-stream-audit-20261020-v2/input-audit.json`，逐页Prompt在该目录。原报告hash随每行记录，源码身份为该次时点，不反签后续记录。

| 页面 | 原user输入UTF-8字节 | 最终输入字节 | 减少 | 保留 |
| --- | --- | --- | --- | --- |
| slide_001 | 54230 | 29708 | 45.22% | 1组冲突、4张对应图、全部邻居边界/箭头几何 |
| slide_003 | 35614 | 17120 | 51.93% | 1组冲突、4张对应图、全部邻居边界/箭头几何 |

v1曾裁减更多箭头几何，随后复核将全部其他箭头/标注几何保留；最终以v2为准。邻居boxes及箭头几何均逐值核对一致，不是仅检查数量。字节减少不等价token/费用减少，也未测真实延迟改善。

## 验证

- 58项专项通过，77.19秒：原局部候选/保护/反馈、流式聚合、真实SDK对本地HTTP/SSE、图片与原生thinking/65536/温度、截断、stage timeout、无重试、计数不泄露内容。`.tmp/repair-stream-input-tests.log`。
- 53项源码闭包/原Pi工具任务/ProductionStages/比较分母/架构检查通过，107.80秒。`.tmp/repair-stream-closure-tests.log`。
- 新增回调异常子进程回收1项通过；最终投影29项回归通过，18.87秒；宿主时钟、timeout及回收3项复查通过。日志分别为`.tmp/repair-stream-cleanup-test.log`、`.tmp/repair-stream-projection-final.log`、`.tmp/repair-stream-clock-final.log`。重复复查不累加为新独立样本。
- canonical quick及最终复查均通过、退出0，最终日志`.tmp/repair-stream-quick-final.log`。Ruff、Node语法及git diff --check通过；不引用旧2775项全量作为本批证据。

按optimize-prompts追踪原repair实际调用、保护、附件、解析与保存后再投影；按code-review-and-quality检查隐私、同帧来源、全邻居保留、总/阶段预算、回调失败清理与源码闭包。合同定义见repair-stream-context-0.1.0.md，无数据库/公开请求Schema变更。

## 后续方向

新任务按最小JSON→单图→整页逐级验收，记录首响应/首输出/完成时间、实际调用/usage、完整候选通过率及源保护。明确失败开始于哪一级后，再调整对应供应商连接、请求任务或输入；不预先承诺本轮已解决服务响应。几何避让类问题后续适合确定性候选试算加原检查，让模型只处理确需语义判断的部分；该自动试算尚未实现。

原作者、音频、批准、生产数据库及默认Legacy保持；未启动正式服务，未追加真实供应商调用，未提交/推送。两处本地源码同步，运行数据仅留实际应用目录。
