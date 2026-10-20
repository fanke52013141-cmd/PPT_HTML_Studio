# 2026-10-21 源码发布与后续优化 handoff

## 发布回执

- 仓库：[PPT_HTML_Studio](https://github.com/fanke52013141-cmd/PPT_HTML_Studio)，分支`main`，只推送`origin`。
- 原基线：`00fb81d43c77968a9e0bc734a75a2fd44689457c`。
- 本次源码：[662b725257a86cd59e564a1e28025c571438c64d](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/commit/662b725257a86cd59e564a1e28025c571438c64d)，北京时间2026-10-21 00:10:45，86个文件；已推送并以`git ls-remote origin refs/heads/main`核对。本文件和README入口另作后续文档提交。
- 契约包**0.9.113**、Agent API **1.60.0**、`html_repair.generate` **1.5**。无数据库迁移，默认仍为Legacy；旧generate客户端不传strategy仍走model。
- 这是源码与文档更新，正式应用未重启、未部署；未上传data/runs/outputs、模型凭据、课程媒体或node_modules。更早handoff中的“尚未提交/未发布”保留为当时状态，以本发布回执为准。

GitHub已触发源码提交的[CI #67](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/actions/runs/39455177085)，写作时为in_progress、结论未产生。它运行canonical full；本机快速检查与专项通过不能代签远端CI或本批全量通过。

## 本次完成

1. **重叠判定**：以实际线性SVG描边和文字Range判断穿字，带出处的合法端点非文字接触单独留证。不支持的图元保留原保守检查；不豁免真实穿字、穿越其他对象或安全区问题。helper进入QA及源码身份闭包。
2. **模型修复与观测**：按scope裁减无关上下文，保留完整邻居边界；第二轮使用上一候选的真实测量/截图，仍提交相对原页的完整补丁。记录Legacy流式和Pi SDK进度、耗时及异常状态，不输出推理正文。旧unknown不自动重放，模型参数及调用预算保持。
3. **几何优先入口**：编辑器“箭头与文字避让”先试有限位置/卡片尺寸候选，经原sampled及完整30fps检查；没有合法解才惰性读取模型配置、进入原模型修复。回退同样仅允许位置与尺寸，并强制全页registered检查。正常页保持unchanged，候选不自动保存或批准。
4. **候选审阅与恢复**：显示同一时刻的前后截图、参数变化、来源、范围及检查数量。明确点击保存才走原候选键/音频/人工保护复验与下游失效。历史恢复先进入草稿，再另存新修订；脏草稿拒绝、页面切换迟到响应丢弃。
5. **跨机闭包修正**：重建编辑器指纹，并登记新JS的快照白名单；固定编辑器源及容量基准JSON的LF，保留manifest逐字节身份和原严格路径限制。

## 数据依据与边界

详细记录：[几何候选扩样](handoff-geometry-repair-2026-10-20.md)、[实际入口与浏览器](handoff-geometry-entry-2026-10-20.md)、[分级真实模型测试](handoff-staged-live-diagnostics-2026-10-20.md)。

| 证据 | 结果 | 解释边界 |
|---|---|---|
| 新入口：原slide_001 | offsetY -48→16，13.032秒，633时刻通过，0问题 | 仅移动标注；0模型调用，原作者未改 |
| 新入口：原slide_003 | 卡片实测宽630→486，10.005秒，606时刻通过，0问题 | 仅宽度；0模型调用，原作者未改 |
| 几何扩样 | 2/2原故障页、4/4同内容扰动通过；2正常无操作、2不支持反例正确停止 | 不是10个独立课程；不将正常/反例计入修复成功率 |
| JSON→单图→整页真实对照 | Legacy/Pi共6次调用全部通过；整页224.043/272.192秒，均通过606时刻检查 | 每侧一页一次，不能推断长期排名或切换默认；费用未知 |

工程通过与完整输出帧检查不等于连续时间证明、审美批准或音频听审。旧180秒/600秒unknown保留；新分级成功不能反签旧请求。新geometry_first入口的真实模型回退没有追加付费调用，当前仅验证其共享原模型路径的工程行为。

原始数据仅在本机`outputs/geometry-entry-20261020-v1/`、`outputs/geometry-expanded-20261020-v3/`、`outputs/repair-staged-20261020-v1/`；Git不包含这些数据或`runs/ec60bbd4_010236`。换机没有课程时先运行版本化fixtures，不能伪称复现了原课程。

## 发布前验证

- canonical quick通过，`.tmp/publication-20261021-quick.log`。
- 相关Python回归**158 passed**，132.67秒；覆盖容量、对照工具、几何/反馈/组合入口、流式、实际浏览器测量、Pi生产、动态QA、快照及Web/Agent/MCP/CLI；`.tmp/publication-20261021-regression-v2.log`。
- 首轮为132 passed、1 failed、11 errors，原因是新面板漏登记快照白名单；保留原`.tmp/publication-20261021-regression.log`。已明确登记单个源码并新增快照闭包断言，未放宽任意路径校验。修正后才取得158项通过。
- SVG线段、DOM几何及动态策略3个Node检查通过；编辑器**17项**通过，包含autocrlf开/关及构建源/输出指纹。
- 仅将容量基准manifest的CRLF规范为LF后，4项容量基准及编辑器17项再次通过；scene文件记录hash保持。
- 前一批真实浏览器入口测试通过：实际原渲染器、完整检查、候选键、显式保存、版本恢复、脏草稿及迟到响应；仅提案选择为脚本替身。详见入口handoff，不能当真实模型成功。
- 按code-review-and-quality检查正确性、职责、输入/输出边界及有界搜索；发布暂存路径、凭据模式扫描无发现，`git diff --cached --check`通过。没有运行本批本机canonical full，不引用历史全量数字。

## 接手位置与换机步骤

先读根README → 本文 → [0.9.113契约](../../contracts/html-presentation/runtime/visual-v1/geometry-repair-entry-0.1.0.md) → 对应专项handoff。主要owner：

- `html_geometry_repair.py`：纯几何候选，最多6次sampled、至多3次完整检查；无provider或作者写入。
- `html_repair_orchestration.py`：固定目标、身份冻结、几何优先及惰性回退；`html_scene_repair.py`继续拥有模型两轮、候选键、保护、检查与保存。
- `html_engine/tools/vector-overlap.cjs`和`temporal-review.cjs`：原动态QA；`html_repair_feedback.py`：测量及反馈投影。
- `static/html_local_repair.js`：候选审阅；编辑器只提供选择、草稿和生命周期桥接。编辑器源码变更后必须重建`editor_ui`，同步manifest与快照路径白名单。

在本机实际checkout内先妥善保存未提交工作，再执行`git fetch origin`、`git merge --ff-only origin/main`；不要hard reset或复用历史机器的绝对目录。新机依赖与单实例启动详见[上批安装步骤](handoff-release-2026-10-20.md#换机安装与启动)，使用Python3.13、Node22.19或兼容更高版本、锁定npm依赖、Playwright Chromium及现有FFmpeg/微软雅黑字体。已有环境先校验依赖，不要自动重装或启动第二个服务。

运行时从实际checkout派生`PPT_STUDIO_DB_PATH`、`PPT_STUDIO_RUNS_DIR`，显式设置`PPT_STUDIO_HOST=127.0.0.1`及`PPT_STUDIO_PORT=8010`，由`start_server.py`启动。模型连接及凭据在本机安全配置，不能从文档复制；不要指向原图片项目数据库。同机已有data/runs保持原样。

## 后续优先顺序

1. **扩充独立真实页覆盖**：收集更多不同课程的穿字、无解、密集关系和正常页；分别统计几何命中率、耗时、误修/漏修、回退原因和保留范围。不要把同页扰动当独立课程样本。
2. **有数据再扩展几何能力**：当前限线性箭头及受影响文字/端点对象；根据无解分布决定是否支持多对象联合避让。所有候选仍走原保护及整页复验，不通过缩字号或规则豁免掩盖问题。
3. **验证真实回退与人工接受**：在有新输入/新身份和明确调用授权时，用少量真实无解案例确认当前模型回退；区分供应商完成、工程通过、用户视觉接受和正式输出。旧unknown先核实，不自动重放。
4. **检查远端CI终态**：若出现新失败，保留日志、定位后另加提交；不把推送成功当全量CI通过。达到重复质量门槛后，再讨论默认执行器变化或旧路径清理。
