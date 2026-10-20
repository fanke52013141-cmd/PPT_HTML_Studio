# 2026-10-20 源码发布与跨机 handoff

## 仓库与交付范围

目标仓库：https://github.com/fanke52013141-cmd/PPT_HTML_Studio，main分支。发布基线5964561（2026-10-19外部交接/工作区）；本次提交包含其后已授权的应用、规范、测试及文档。发布提交可从Git日志中的`feat: publish candidate editing and Pi agent workflows`定位，随后的备注提交记录实际源码提交及远端状态。

契约0.9.108、Agent API1.59.0、produce1.14、外部任务/结果0.2.0、执行合同2.1.1。无数据库迁移；原应用单进程、图像/TTS/音频与批准门禁保持。

- 候选画布直接编辑、中文属性、持久撤销/重做；正式保存检查点与旧版本恢复为新修订。
- 实际容量/安全区中文说明、可预览后确认的联动调整、保守关联组局部采用与整页复验。
- Pi完整SDK1.3.0固定输入输出和白名单工具；幂等/恢复/取消/预算；局部修复可预授权另存AI版本；新页显式runner=pi；文章/讲稿/可视化和共享预算批量只交候选。
- GLM-5.3系列按用户配置启用原生thinking、65536上限与温度1.0；文章/讲稿使用planning连接，视觉修复使用明确支持图像的text连接。其他模型保持原兼容参数。
- 生图Prompt0.3.1/0.4.1按冻结slots登记文字来源，约束计划外标签、结论与箭头；历史包修订同源派生，不改历史文件。
- CI使用Node22.19.0并安装锁定agent_runner依赖；没有运行时自动安装、全局Pi或额外账号要求。

更早文档的“未提交/未发布”、初版8192/off及“试验运行中”均是对应阶段的历史状态；本交接和后续发布回执优先。Git源码同步不代表运行服务已重启或已部署。

## 入口与职责

人工候选接手见[画布与历史](handoff-candidate-canvas-history-2026-10-20.md)、[联动与关联组](handoff-repair-assistance-2026-10-20.md)。Pi接口、原请求样例、候选交付与恢复见[M0–M3](handoff-pi-agent-m0-m3-2026-10-20.md)、[M4–M5](handoff-pi-agent-m4-m5-2026-10-20.md)、[原生参数修复](handoff-glm-native-parameters-2026-10-20.md)。

`html_handoff_workbench.py`持有人工作草稿，`html_scene_editing.py`持有作者版本/保护；`html_handoff_assistance.py`只派生有限建议，原检查器始终权威。`html_agent_jobs.py`/`html_agent_workflows.py`持有任务；`agent_runner`无shell、作者写入或批准权限；`html_pi_json.py`仅适配原生产JSON阶段。不要复制第二套renderer或把人工接手来源冒充AI自主成功。

## 真实验证状态

[设计图与计划修复](handoff-design-plan-alignment-2026-10-20.md)：真实Token第三页原计划5句/6对象/8动作完整覆盖；设计图额外语义已由原生图修订入口移除并实际看图核对。新图key `e03846936666898de72b031f6581235dc9ea99992bb0adebe66c065be61b54cd`。

Legacy新任务`html_ffc19da60288495f9a70`设计理解ready；随后容量修复180秒超时，供应商结果未知，双方作者未改。对照脚本停止，Pi未启动。本轮未完成公平双边对照。旧Pi600秒未知结果同样保留；不得重发原未知输入，不把原HTTP200、结构通过或本地脚本供应商当作课程验收。

M5此前Pi讲稿/可视化候选覆盖五页；文章和复杂新页仍有超时或质量失败，批量无完整Legacy基线。Legacy保持默认，不移除旧编排。人工视觉、逐句听审、正式音频与成片验收独立，当前不签发通过。

## 换机安装与启动

在实际checkout内操作，先正常停止旧服务、核实无进行中任务并备份本机data/runs，再拉取main。不要重置他人的未提交修改或创建第二个桌面副本；数据和凭据不在仓库，需用现有安全配置方式在本机设置。

```powershell
# 当前所在目录应为本机实际checkout
$studioCheckout = (Get-Location).Path
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
npm ci --prefix html_engine
npm ci --prefix editor_ui
npm ci --prefix scripts/remotion
npm ci --prefix agent_runner --ignore-scripts --no-audit --no-fund
npm exec --prefix html_engine playwright install chromium
npm test --prefix editor_ui
$env:PPT_STUDIO_HOST = '127.0.0.1'
$env:PPT_STUDIO_PORT = '8010'
$env:PPT_STUDIO_DB_PATH = Join-Path $studioCheckout 'data/projects.db'
$env:PPT_STUDIO_RUNS_DIR = Join-Path $studioCheckout 'runs'
& .\.venv\Scripts\python.exe start_server.py
```

需要Node>=22.19.0、已有FFmpeg/ffprobe及生产Windows微软雅黑字体；服务运行使用原启动器和本checkout目录，不能指向图片项目数据或同数据启动第二进程。新机先配置planning/text/image连接及本机凭据，text视觉连接显式supports_images=true；不从日志或文档复制密钥。程序启动只做原迁移/遗留作业中断恢复，不恢复未知付费请求。

旧设计key和外部签名包因源码/能力身份变化会过期，按原显式复用/重新导出和审阅入口处理，不改task_id、hash或批准伪造当前性。历史手工字段和音频仍受原hash/保护守卫约束。

## 后续优先顺序

1. 查明原容量失败的实际字段、DOM测量与模型请求预算/时限；原未知结果先核实，不靠盲目延时重发掩盖。
2. 在实质修正输入后重新冻结同一计划/图/模型，分别验证Legacy/Pi的理解、工程、真实截图及有界修复；调用、token未知值和人工介入分别统计。
3. 获得真正可保存新页后，在原编辑器验证拖动/中文参数/局部采用/保存恢复，再做逐句听审和原正式输出。
4. 达成真实课程重复质量门槛后，再讨论默认切换与旧编排清理；网页批量向导尚未实现。

## 本次发布前验证

设计对应相关63项、Pi原生参数和路由34项此前已通过；这些是不同批次，不冒充本次全量结果。编辑器16项、Remotion TypeScript在本次发布检查通过。canonical full检查正在本机执行，最终结果与发布提交由后续发布回执明确记录。

本地验证日志位于outputs/publish-20261020-*.log，运行证据和媒体只在本机，不随Git上传。仓库不会包含data、runs、outputs、node_modules、凭据或付费生成图片。

## 实际发布回执（首批及传输修正）

源码提交`1578d32c78e099e2d6f782b414aa55e94e87a0a5`已成功推送origin/main（上一个远端5964561），92个文件。暂存路径及凭据模式检查无发现，git diff --cached --check通过。工作区在首批提交后干净。未部署或重启本机服务。

发布全量检查发现已有新增能力与传输分发不一致：MCP未将html_agent/agent_workflow纳入原严格通用分发；CLI缺项目工作流命令及局部任务创建JSON参数。补丁沿原capability Schema校验、路径编码及AgentClient._request修复，不新增业务存储/批准/模型调用。实际CLI解析并执行8种动作的回归覆盖POST/GET、参数文件、URL编码与精确请求体；MCP全能力可达性原断言保留。传输及合同回归97 passed、Ruff通过。API和合同版本保持。

canonical full中的首轮pytest已经加载修正前的MCP模块，会保留该历史失败；不得覆盖日志伪造全绿。最终全量结果及后续修订提交在最终回执记录。GitHub网页CI与本机全量状态分开；无法读取远端状态时不能报告CI已通过。

## 线上源码核对与验证状态

- 主功能提交：`1578d32c78e099e2d6f782b414aa55e94e87a0a5`。
- MCP/CLI修正提交：`7ea5e442ab79bf05f61ffe57a51f8bcb305704f5`。两次git push origin main成功，git ls-remote核对该提交与本地HEAD一致；后续只追加本文等发布备注。
- 本次canonical quick及独立脚本检查：通过（由full入口先执行）。编辑器16项通过；Remotion TypeScript退出0；传输/合同97项通过；暂存空白/路径及凭据模式检查通过。
- 本次canonical full的全量pytest仍在执行，已观察到修正前MCP分发遗漏的首轮失败；不能称全量通过。最终进程结果需读取本机outputs/publish-20261020-full.log。最先失败单独复现为1 failed/137 passed；修正后97项包含原失败用例和8种CLI实际分发回归，均通过。
- 远端GitHub工作流查询未返回本次run，未取得CI通过证据；不要用本机quick或推送成功代替远端CI通过。
- 本次是源码/规范/备注发布，正式应用未重启、未部署，课程/数据库/凭据/生成媒体未上传。运行状态和供应商unknown的处理以上文终态为准。

接手后先收齐全量日志或GitHub新CI结果；若有新失败，保持日志原样，针对原因修正并另加提交，不改写已发布历史或放宽来源/批准守卫。
