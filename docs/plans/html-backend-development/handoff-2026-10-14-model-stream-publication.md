# 2026-10-14 模型流式修复与本机 A06 发布交接

这是本轮发布的接续入口，接替 [上一份线上交接](handoff-2026-10-14-publication.md) 的当前停点说明；原记录保留历史。用户已明确授权发布到 `origin` 的 `fanke52013141-cmd/PPT_HTML_Studio` / `main`。禁止推送原图片项目 `upstream`。

规范唯一来源：[HTML 演示契约](../../contracts/html-presentation/README.md)，当前契约包 **0.9.44**。起点 `56c52b0d789fa47df0de4334eb487b1447af1fb9`。代码提交版本在发布验证完成后登记。本文件自身的提交身份可用 `git log -1 -- <本文件路径>` 核验，不能把文档更新误作新的供应商运行证据。

## 当前结论

本机真实课程已从正常 UI 新建、导入正文，完成五页分镜；修复版第一页 GLM 规划一次通过，真实设计图返回。**课程停在第一页设计人工确认，A06 整课仍为 partial / pending_review。** 没有写人工批准，实际 HTML、剩余四页、TTS、A04 语义 QA、试听与视频输出都未验收。

丽梅电脑上的旧项目 `d1f5885a_122521` 及原运行文件没有迁移到本机。新项目不是原任务恢复；不能把两台机器的任务、输入句数或候选混记。

## 本次代码改动与问题对应

| 改动 | 解决的问题 | 边界与备注 |
|---|---|---|
| 设计理解应用后严格检查；容量失败调用既有有界排版修复并重验 | 总结面板选中变体后超出槽位，但此前检查的是变体应用前的场景 | 非容量错误直接停止；完整修复审计进入来源；不修改旧候选或人工批准 |
| 三项设计策略登记散列改为现有 LF 正文真实字节 | 线上登记 CRLF 散列与实际文件不符，策略加载器拒绝 | 不改正文，不放宽散列检查 |
| HTML 项目不物化图片后端风格模板 | 正常 HTML 新建被本机缺失的旧图片模板阻断 | 保留完整创作配置；image 后端保持原物化行为 |
| 正常 contract 的标题、画面描述及屏幕文字投影到模型输入 | main_title / visual_anchor / display_text / visible_text 未被旧投影消费 | 旧显式字段优先，权威原句保持，只有精确重复全文才去除 |
| 共享 JSON 可选流式聚合，HTML 规划/生产接入进度 | 非流式等待完整响应，界面无法区分思考与无响应 | 默认图片后端 JSON 调用仍非流式；只存思考字符数，不保存思考文本 |
| HTML 请求预算1800秒，流式 socket 等待最多120秒，正文100万字符上限 | 复杂深度思考容易超过原120/600秒等待 | 1800秒在接收chunk时检查；底层阻塞读可能额外占用一个socket等待窗口，并非硬实时截止 |
| stop 且完整正文后解析；截断/断流不发 JSON 修复 | 部分结果被当成完整 JSON 或补发外部请求的风险 | 完整但语法错误的既有一次修复、明确格式不兼容回退保留，仍逐请求治理 |
| unknown 与 returned 原始回执独立于源码新鲜度登记 | 快照变化错误掩盖已提交外部请求的失败 | 原 attempt/运行状态仍检查；作者执行仍严格 checkpoint；unknown 不当成成功、不盲重发 |
| 冻结模型与 JSON 上限同步到65536，新传输进入快照依赖 | 64000上限截断用户要求、传输代码未纳入身份 | 旧冻结请求不追改；固定连接修改需明确重新绑定；源码变化可能使旧候选过期 |

新增模块 `json_llm_transport.py`，其余改动留在既有服务归属。没有数据库迁移、新第三方依赖、公共请求/响应 Schema 变更或额外作者提交路径。

## 真实供应商证据（本机）

- 项目 `8ce1222f_194645`，课程 `html_903b91bbf2ec43c1b64b`，第一页 `html_c137f14ae393487fa54f`；本机五页 / 17语块，来源是重新整理的正文，不冒称旧20句字节一致。
- 项目绑定 revision3：规划 GLM-5.3，视觉用途 GLM-5.3-Flash，图片为已有 Sunburst VIP low/2K；凭据只保存在本机既有凭据存储，仓库没有可迁移密钥。
- 20:41:00规划开始，真实请求 max_tokens65536、thinking enabled、reasoning_effort=max，输入9139字符。首chunk1.249秒，首正文513.147秒，总535.124秒，finish_reason=stop，正文7787字符。输入3598 tokens，输出40555（reasoning37777，约93%），总44153；费用未知。
- 第一轮结构/语义设计校验通过，无结构修复请求；plan、brief、原始模型结果和回执均已保存。新输入与传输同时改变，不能单独归因，也不能回溯确认旧GLM600秒异常的底层类型。
- 20:50:44图片返回，供应商任务 `tsk_img_01M4X7CQ1KNMXZ37T7KPYSAV0B`；第一页 succeeded/design_review，父课程 waiting_for_review，记录时 active jobs=0。
- 设计key `11607bd977c274366750a11e69122e7874da25339284b29412e46909f57e86b0`，图片SHA-256 `e4e2560bf92e81fdc49c47e0e3c33795c1f5521ea99c52c957b59a73b24915c0`，approval_status=not_recorded。任务 succeeded 只代表设计参考阶段结束。

本机旧豆包 `html_653b2a4f5c7045ba8654` 与旧 GLM `html_3da3336b4f404e9a83b6` 均保留未知结果历史。无可用查单能力时，不得换快照/改超时/改输出上限后重发同一未知请求。排查推理与事实边界见 [模型停顿诊断](diagnosis-model-timeouts-2026-10-14.md)，事件时间线见 [本机运行交接](handoff-a06-local-2026-10-14.md)。

## 验证与发布备注

发布前联合 Python 回归 **579 passed / 2 failed**（124.41秒）：本轮传输、设计、规划、生产恢复、项目创建、模型绑定、数据库迁移、失效、源码保护、图片/音频隔离与全部Agent检查。两项失败为 `checks/agent/test_html_editor_binding_integration.py` 的 `test_model_binding_read_write_noop_conflict_and_redaction`、`test_mcp_dispatch_and_cli_reach_real_http[project_model_binding.read]`：既有Web绑定输出包含planning，但Agent `ProjectModelBindingResult`拒绝bindings.planning/effective.planning。以临时目录加载 **origin/main 原版** `project_model_binding_service.py` 单独重演前一例仍失败；Agent模型/路由/该测试均未改，本轮绑定服务差异只有64000→65536上限。这是既有Agent读绑定缺口，不报告全绿；后续需同步公共模型/能力版本及MCP/CLI合同，不能只关闭extra校验。

前端11项真实浏览器面板回归、visible flow、frontend quality、三个JS语法检查通过；17个改动Python文件Ruff、AGENTS指定compileall、Agent合同生成一致性、Remotion `npm install`及TypeScript检查、diff空白检查通过。无依赖锁文件变化。此前分组80/51/99等存在重叠，不累加为独立测试总数。真实模型调用与测试替身分开记录。由于未修改导出、音频和渲染器，本次没有额外生成/解码新视频；整课/MP4仍待验收。

发布只包含源码、配置、测试、契约和去敏文档。`runs/`、`outputs/`、`logs/`、`data/`、数据库、密钥、图片和生成媒体不上传。拉取代码不会自动获得本机课程或模型连接，另一台机器须沿原配置导入方式建立其自身合法连接，不能提交凭据文件。

本机运行目录 `D:/Program Files (x86)/PPT_HTML_Studio`，服务 `http://127.0.0.1:8010/`；记录时实际 PID29972，已加载本轮修复，不需因文档发布重启。原启动 ps1 未在起点仓库发布，本机实际使用现有 `start_server.py` + `.venv/Scripts/python.exe`，端口环境变量 `PPT_STUDIO_PORT=8010`。别启动第二份可运行副本或连接丽梅电脑的数据库目录。

本机证据：`outputs/a06-local-normal-20261014/progress.json`、`glm-real-plan-stream-completed.json`、`first-design-ready-full.jpg`；原始任务/候选/回执在对应 `runs/8ce1222f_194645`。流式诊断日志按 artifact_prefix 命名，后续同前缀调用可能覆盖指标文件；按任务及散列封存的 stage 产物/回执才是恢复依据。

## 下一位接手者的顺序

1. 拉取 origin/main，先读本交接及契约。确认机器、目录、项目、冻结绑定和任务状态；不要把旧交接里的“当前进程仍旧版”当作现状。
2. 在本机正常界面打开项目/第一页，展示真实设计图，等待用户决定设计方向。未确认前不点击接受、不替用户签收。
3. 用户确认后，从“确认设计并生成实际页面”继续原设计候选，生成独立素材、受控还原、严格工程/视觉审核；最终页面另需审阅。容量修复代码已测试，但此新页的真实还原尚未执行。
4. 逐页完成其余四页，核对来源与17语块改写；沿父课程/原子任务ID恢复，不复制或手写规划/作者场景来伪造正常流程。
5. 真实TTS、试听、A04每句三帧/原句对照、人工决定、正式视频输出和完整解码分别留证；全部完成前A06不改为passed。
6. 有活动外部请求时推迟生产源码修改和重启；确需修改时按现有快照/回执恢复策略处理，保留unknown，不能用“新代码版本”掩盖重复请求。
