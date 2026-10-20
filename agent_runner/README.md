# HTML Studio Pi 执行器

M4–M5接线见[handoff](../docs/plans/html-backend-development/handoff-pi-agent-m4-m5-2026-10-20.md)。原produce入口runner=pi使用同一完整SDK的submit_json模式驱动原生产owner，图像供应商与正式批准不替换。项目agent_workflow API扩展文章、讲稿/可视化及共享预算批量候选；修复可预授权save_revision，由Python原保存owner另存，SDK没有作者写入工具。后续默认切换待真实比较。

Node >=22.19.0。在本目录执行 `npm ci --ignore-scripts --no-audit --no-fund`，然后正常启动原 Python 应用。Pi SDK 固定1.3.0及lockfile；运行时不自动安装或加载用户扩展。不启动第二个应用服务。

使用项目现有文字模型连接（OpenAI兼容聊天协议），布局/动画/新页视觉任务须明确设置supports_images=true；纯文章/分镜文字候选不强制图像能力，但任何实际图片调用仍在付费前检查能力。模型和凭据仅经父进程stdin传递，不写任务包、数据库或事件日志。无额外Pi账号/全局安装要求。原生Anthropic/Gemini协议首版明确拒绝；兼容网关需实际验证工具调用和图像。

页面：“调整页面与动画”→选择对象→“AI自动修改/外部Agent交接”→填写目标/验收条件→“开始AI修改”。结果自动展示原检查候选，保存或人工微调走原入口。“恢复任务状态”查询持久作业；HTTP结果不明用同一幂等键对账；后台任务不中途提问。

API：`POST /api/projects/{project_id}/html-visual/{slide_id}/agent/jobs`，请求见 `html_agent_models.AgentJobRequest`；GET同路径`/{job_id}`或`/{job_id}/result`；POST `/{job_id}/cancel`。认证Agent入口前缀`/api/agent/v1/projects/...`，能力`html_agent.create/read/result/cancel`自动提供MCP和CLI。

四工具：read_material只读封存文字、view_image发送真实PNG、check_candidate调用同源便携预检与原预览、submit_result封装严格ZIP并原导入复验。模型最终文本不作为业务JSON。执行期间无shell/写作者/审批/生图/TTS工具。

限制：默认最多两轮候选、12次模型请求、24次工具和600秒，GLM-5.3系列出站使用原生thinking enabled、冻结输出额度（上限65536）及项目温度；其他模型保留8192/off兼容配置，不转发项目原生reasoning_effort。取消协作停止；单进程并发1。原始模型会话不落盘，只保存宿主终态及无敏感内容工具事件。排队前固定页面/配音/保护身份，执行前后固定执行器源码指纹。重启标记interrupted，未知调用不重发。费用未知null。成功只代表指定自动检查与模型视觉自检；有限采样/模型审阅不代表人类视觉或声音批准。

图片查看与最终视觉观察必须跨模型请求：同一批工具先取图再提交，不能冒充模型已经看懂刚取回的图。最终结果须与最后一次检查完全相同。HTTP提交结果不明时页面只允许恢复原幂等任务，不直接另建一次付费任务。

验证：`../.venv/Scripts/python.exe -m pytest checks/test_html_pi_agent.py -q`（从仓库根执行时使用`.venv/Scripts/python.exe`）。本地脚本供应商配合真实SDK验证协议与工具，不当作真实模型质量数据。

依赖许可证随npm包提供；Pi SDK MIT，依赖清单由lockfile冻结。升级需重新跑任务、图像、预算、停止、权限与原编辑器兼容验证。

真实独立试验：`scripts/evaluate_pi_agent.py --source-run <原run> --output <全新隔离目录> --request <AgentJobRequest.json> --live`。不加--live仅校验输入；复用现有视觉连接，只读凭据和原设置，任务数据库与资料副本独立，既有试验目录拒绝重试。它不会把失败候选签成成功，也不恢复未知调用。
