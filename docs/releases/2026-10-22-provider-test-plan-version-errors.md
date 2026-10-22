# 图片连接测试 / 计划版本 / 错误透出修复 · 2026-10-22

真实“什么是 token”流程实测发现的三个产品问题修复。不改变渲染器、审批或作者写入边界。

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

## 验证

- `checks/test_settings_services.py`：普通与 ToAPIs 连接探测参数断言；
- `checks/test_html_e_production.py`：默认 0.2.0、版本不一致 `409 PLAN_VERSION_MISMATCH`；
- `checks/test_html_visual_review.py`：审阅脚本失败时错误包含报告原因与路径；
- `python scripts/generate_agent_contracts.py --check` 通过。

## 边界

- 完整 HTML 审核仍需要可用的 Chromium；本次本机 DSH 沙箱仍无法启动浏览器，真实页级审核未完成。
- 未改变审批、作者写入、动态检查口径或任何通过条件。
