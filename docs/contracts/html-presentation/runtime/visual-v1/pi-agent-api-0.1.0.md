# Pi 无人候选执行 API 0.1.0

此卡记录M0–M3初版。契约0.9.106/API1.59.0新增预授权另存、原新页Pi选择及项目候选，见[后续正式卡](pi-production-api-0.1.0.md)；初版默认candidate和外部交换兼容保留，不将历史“无作者保存”描述扩展成对新save_revision选项的禁止。

适用 HPS-007/009/010/013/015–018；M0 定义卡，M1–M3 实现和验证证据单独记录。

实现/验证见[交付handoff](../../../../plans/html-backend-development/handoff-pi-agent-m0-m3-2026-10-20.md)：功能与工程检查完成，真实简单任务完整交付通过，复杂任务失败保留；真实重复样本发布门槛尚未达到。

输入：项目/页、幂等键、原 ExportRequest（仅 static_repair / animation_repair）、执行限制。固定 schema_version=agent-job/1.0；交付策略仅 candidate。不接收任意路径、代码、密钥或供应商覆盖。沿原人工保护、风格、原文、操作 Schema、真实音频和任务身份。

输出：job_id、status、progress、result、error、usage；queued/running 为活动状态，succeeded/failed/cancelled/interrupted 为终态。成功须由宿主确认完整严格 ZIP 与原预览通过、模型实际审阅 before/after，并在返回前复核基线；不等于人工批准。失败不返回可采用 delivery。错误提供稳定 code/message。未知 cost=null。

执行：Pi SDK 独立无交互子进程，仅开放包内文字读取、图片查看、原候选检查、最终提交四个工具；无 shell、写文件、项目作者保存、审批工具。不自动发现用户配置/扩展。模型取项目冻结 text 连接，要求显式 supports_images=true；首版支持 OpenAI-compatible chat-completions，其他协议明确 unsupported。最多两轮候选，模型请求/工具/墙钟独立限额；默认不支持自动重发未知请求。系统检查反馈自动返回，用户无需中途确认。图片工具发送真实字节。

持久状态沿 local_jobs，新增 job_type=html_pi_agent，无新表；确定性项目/幂等键ID防重复。同键不同请求409；不同账户、页、后端不可读取/取消结果。启动恢复仅本类型遗留活动任务为 interrupted，不恢复未知模型请求。客户端离线不取消；取消是协作请求，远端请求能否取消不承诺。

Web 与认证 Agent API 共用服务。Agent/MCP/CLI登记同一能力；用户明确提交任务即授权预算内模型调用。每个API调用原项目权限守卫。候选成功可自动展示、原显式保存仍独立；人工接手保留原工作台。执行中人工修改导致任务 stale_input，候选不可保存。

兼容：原外部任务/结果0.2.0、执行2.1.1和原导入导出保持；无旧任务重签。新增源不进入旧合同哈希，任务材料依旧按原源校验。自动正式保存、新页生成、文章/配音不在本卡能力范围。

验收：真实 SDK 对本地模拟供应商验证工具循环、图像传输、原检查及二轮修复；API越权、幂等/并发、取消/中断/超时/超额、基线变化、人工保护、未知费用；实际共享浏览器单独验。模拟供应商不计真实模型自主成功率。真实配置缺失时明确记录未测。
