# S02 外部结果对账与作者提交恢复 0.2.0

2026-10-12；HPS-010/011/014/015/017。[0.1.0](production-recovery-0.1.0.md) 的兼容增量；不改作者 Schema、批准格式和生产 API 路径。

| 项目 | 定义与实际接线 |
|---|---|
| 外部回执 | 原始结果落盘后，在登记 LocalJob returned 前写请求回执；绑定 job_id、snapshot_id、阶段 key、attempt、request_id、产物路径及 SHA-256。登记失败可对账回写，不能使用任意同名文件 |
| 供应商任务 | ToAPIs 创建成功后、第一次轮询前调用持久登记回调，保存 upstream_task_id；上游 ID 自有回执覆盖文件已写而数据库未提交的窗口 |
| ToAPIs 对账 | HTML 执行器读取原任务 ID，重新解析当前凭据，校验 image config_hash 与原连接一致后使用已有 resume_task_id 路径。恢复不上传参考图、不 POST 生图；查询回来的图片仍须经过实际解码与散列验证 |
| 其他接口 | 支持 invoke_with_request_id / lookup 的适配器可明确提交和查询同一请求身份；普通同步文字/图片接口没有可用 ID 时维持 unknown，不能伪装成支持远端查单，也不能自动补发 |
| 查询预算 | 每个请求最多三次查询会话，计数查询前提交、跨进程保留；ToAPIs 单次恢复轮询窗口为30秒，保留既有网关治理/退避。会话内可能多次 GET，此计数不是 HTTP 次数或费用统计 |
| 作者写前日志 | 保存作者文件前在项目锁内写 prepared 回执，列出最终预期的 scene、revision、binding、plan、provenance、资源清单、设计接受记录、涉及的项目图片、参考来源及实际检查截图散列；另携带完整生产 result |
| 作者写后封存 | 所有作者文件完成后在同一锁内写 sealed 回执。prepared 和 sealed 均不能单独证明成功；恢复必须检查文件齐全、每项散列、scene/result 身份、review passed 与当前 revision 全部匹配 |
| 恢复入口 | 服务启动先将活跃任务标记 interrupted，再做对账；相同输入再次提交也先对账，再决定是否建立新任务身份。已有作者提交恢复为原任务 succeeded，不重新规划、生成或写作者文件 |
| 数据库完成 | 下游失效的数据库修改与任务 succeeded 在同一次提交中完成；对账走原失效服务，保留音频确认，不创建视觉批准 |
| 保护 | cancelled 不复活、旧 attempt 不接受、换供应商连接不查询、缺文件/坏回执/新版作者文件不报成功、不自动写回缺文件。恢复阻断在既有任务 error/stages 显示；task 额外提供 reconciliation 字段，Agent/Web 继续共享 dict 结果 |
| 兼容 | LocalJob 仍为唯一状态源，回执是恢复证据。无需新表或 migration；旧任务缺新回执保持原阻断策略。不改旧图片工作流，公共 ToAPIs 回调参数默认为 None |

实现：html_production_recovery.py、html_production_stages.py、html_workflow_jobs.py、html_production_service.py、html_image_provider.py；ai_provider_service.py 增加可选任务 ID 回调，并修正 resume 时不应再上传参考图。

首版限制：供应商已接收请求但创建响应和任务 ID 都未到达本地时，无法可靠查单，仍阻断重复调用。prepared 日志显示部分文件写入时也明确阻断，不能自动当作完整作者提交或覆盖可能已有人工修改。远端成功但结果链接失效同样不能虚报恢复。无强制重新请求 UI、无底层 HTTP 累计预算或断电事务承诺。

验证分别记录：故障注入、真实浏览器静态检查、供应商 HTTP 模拟；本轮没有真实付费供应商查单，不代表真实远端端到端验收或用户审美批准。具体证据见 [收束交接](../../../../plans/workflow-first-parallel-2026-10-09/deliveries/S02-RECONCILIATION.md)。
