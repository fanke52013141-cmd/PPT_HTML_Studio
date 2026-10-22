# 图片连接测试 / 计划版本 / 错误透出 / 用量与浏览器预检 · 2026-10-22

真实“什么是 token”流程实测发现的问题修复。不改变渲染器、审批或作者写入边界。

## 1. 图片连接测试（P1）

- 根因：`settings_service.test_image_connection` 调 `generate_image_response` 时没有传
  `api_key/provider`，ToAPIs 分支因此报“缺少 API Key”；固定 15 秒超时也短于异步任务。
- 修复：传入 `api_key`；按 base URL 识别 ToAPIs 并传 `provider="toapis"`、
  `public_config={toapis_resolution:1k, toapis_quality:low}`；ToAPIs 使用任务级超时
  （600 秒）；其他供应商仍为 15 秒快速探测。
- 实测：真实 ToAPIs Key 下 `POST /api/settings/test-image` 返回
  `{"success":true}`，耗时 48.9 秒（1024×1024 low）。

## 2. 计划版本默认与缓存（P2）

- Web/Agent 的 `POST .../html-review/{slide}/produce`：**省略 `plan_version` 时默认 0.2.0**
  （语义计划），0.1.0 仅在调用方显式要求时使用。
- 已接受的设计参考带有自己的计划版本；当请求版本与设计/计划版本不一致时，
  `produce_scene` 以 `409 PLAN_VERSION_MISMATCH` 失败关闭，不再静默复用旧计划。
- UI 的“接受设计”“重试资产”请求补上 `plan_version:'0.2.0'`，与“生成本页设计图”一致。
- Agent API **1.62.1**；`html_review.produce` capability **1.15**；契约矩阵已重新生成。

## 3. 审阅失败错误透出（P3）

- 根因：`review_scene` 在审阅脚本非零退出时只拼接 stderr；浏览器启动失败时 stderr 为空，
  任务错误只剩“静态审阅脚本失败：”。
- 修复：stderr 为空时读取审阅报告中的 `code/message`，并附上报告相对路径（最多 700 字符）；
  任务错误现在能看到 `browserType.launch: spawn EPERM (report=planning/.../report-slide_001.json)`。
- 仍不把环境故障当成场景通过；失败继续 fail-closed。

## 4. 供应商用量与成本依据（P4）

- 流式 JSON 调用成功时，从任务进度中的 `model_stream.usage` 取
  `prompt/completion/total tokens`，写入 stage `metrics.usage`，并标记 `usage_source=model_stream`。
- 非流式调用或供应商未返回用量时，保留显式 `usage_source=provider_not_returned`，不再静默 `null`；
  失败分支标记 `model_stream_failure`。
- ToAPIs 图片任务在 stage 指标中标记 `cost_basis=toapis_async_token_priced_unknown`，
  上游任务 ID 仍单独记录，便于按平台账单核对；不伪造金额。
- 实测某次规划调用记录到 `usage.total_tokens=20221`（prompt 11437 / completion 8784）。

## 5. 浏览器预检（P5）

- 新增 `browser_preflight(repo_root, node_bin)`：用 Playwright 启动一次 headless Chromium 后关闭，
  进程内缓存结果；不写盘、不调用供应商。
- HTML 生产任务在**任何付费设计/素材调用之前**执行预检；失败直接以
  `BROWSER_UNAVAILABLE：无法启动 Chromium，已在付费生成前停止…` 结束任务。
- 审阅阶段若仍遇到浏览器启动失败，错误码改为 `BROWSER_UNAVAILABLE`（503），
  原始错误与审阅报告路径一并保留，不再只报“静态审阅脚本失败”。
- 本机 DSH 沙箱实测预检会拒绝执行，说明该保护能阻止“先付费出图、最后浏览器不可用”的浪费。

## 验证

- `checks/test_settings_services.py`：普通与 ToAPIs 连接探测参数断言；
- `checks/test_html_e_production.py`：默认 0.2.0、版本不一致 `409 PLAN_VERSION_MISMATCH`；
- `checks/test_html_visual_review.py`：审阅脚本失败错误包含报告原因与路径、浏览器失败码；
  预检失败输出；
- `checks/test_html_production_stages.py`：流式 usage 进入 stage 指标；
- `python scripts/generate_agent_contracts.py --check` 通过。

## 边界

- 完整 HTML 审核仍需要可用的 Chromium；本次本机 DSH 沙箱仍无法启动浏览器，真实页级审核未完成。
- 未改变审批、作者写入、动态检查口径或任何通过条件。

## 交付证据

| 提交 | 内容 |
|---|---|
| `6212ad7` | P1 图片探测、P2 计划版本、P3 错误透出；Agent API 1.62.1 / capability 1.15 |
| `9cd84d1` | 仅在调用方显式请求版本时校验计划版本，修复兼容性回归 |
| `0c929d3` | P4 流式 usage 落盘、P5 付费前 Chromium 预检与 `BROWSER_UNAVAILABLE` |

- CI：`39784143662`（`9cd84d1`）success；`39793733217`（`0c929d3`）success；
  `39776927491`（`6212ad7`）failure 仅含已修复的计划版本兼容用例与已知视频截图 flake。
- 真实验证：ToAPIs 连接测试成功 48.9s；沙箱中 `browser_preflight` 返回 `ok=False`；
  一次规划调用记录 `usage.total_tokens=20221`。
- 复现：`python scripts/generate_agent_contracts.py --check`；
  `python -m pytest checks/test_settings_services.py checks/test_html_production_stages.py -q`；
  以及本文件“验证”中的审阅/e2e 用例。
