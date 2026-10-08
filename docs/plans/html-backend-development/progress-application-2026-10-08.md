# 第三轮：素材板应用接入与任务验证

用户继续开发授权范围内完成公共接入；复用实际checkout、已有HTML executor和LocalJob，不启动用户应用、不读写真实DB/runs、不commit/push。无新数据库迁移，其他对话及继承修改保留。

## 本轮交付

- html_asset_sheet_jobs.py：提交验证plan，冻结image模型后入队；plan、安全模型摘要、Prompt/提取版本组成幂等key。凭据仅在冻结对象内存传worker，不入库。复用现有HTML两worker executor，避免另起服务器/无界新worker池。新增任务类型由原恢复函数标记interrupted，最多3次显式提交尝试；停止在模型调用前后和候选边界检查，拒绝旧尝试或迟到成功。
- html_asset_sheet_routes.py与共享models：账号/HTML门禁，候选list/read、generate、review/accept和受保护PNG预览；严格请求、409修订、no-op、不可覆盖资源由同一内部服务执行。list返回最近活动素材板任务以恢复轮询，read/PNG核验实际来源。新增候选仍pending，接受才进入resources；不会自动改scene/批准/音频。
- Agent API1.14.0登记五个html_sheet能力；MCP实际dispatch与CLI sheet-list/generate/read/review/accept，新增sheet_id/request_key/asset_id路径参数；写命令--file必需。Web和Agent使用同请求class和处理函数，不额外放宽字段或审批。
- static/html_asset_sheets.js/css：显式面板、1–4条对象需求、1536×1024固定板与独立槽位，V05允许方向；透明或声明白色背景处理。任务轮询/停止/重开恢复、候选版本、对象预览、身份与边缘双人工审阅、保存后接受、已接受锁定、409保留选择、项目切换及image后端隐藏。通过已有API transport发请求，不直接fetch、不使用DOM观察器。

生成/提取/注册单位是独立资产；板数量不改变每页资产预算。当前不自动替换scene中的图片、推断语义锚点或重画正文。接受后重新打开对象编辑器可选择资源；若图片需要批注，用户仍需设置真实语义锚点和适用动作。

## 验证证据

| 命令/范围 | 实际结果 |
|---|---|
| pytest checks/test_html_sheet_application.py | 9项通过：实际FastAPI、LocalJob、冻结模型、生成/提取/审阅/接受服务，图片提供者受控替身；含提交后配置变化、幂等、queued停止、in-flight停止、中断重提、旧attempt拒绝、账号/后端/严格字段、五能力MCP/CLI真实HTTP分派 |
| pytest checks/test_html_sheet_application.py checks/agent -q | 440 passed，1既有Starlette warning，12.66秒；与下面120项有重叠，不相加 |
| 最终HTML回归（workflow acceptance/task store/model/editor/assets/sheet/annotations/server boundaries） | 120 passed，1相同既有warning，32.44秒；使用真实浏览器和独立fixture产物，模型替身 |
| node checks/test_html_asset_sheets.cjs | 10浏览器场景：generate/poll、gates、review/accept、locked、XSS、409草稿、项目隔离、重开恢复、stop、image隐藏；pageErrors=[] |
| node checks/test_html_review_panel.cjs | 11项通过 |
| node checks/test_html_scene_editor.cjs | 实际共享player/存储/编译器、保存重开、409草稿、锚点、乱序seek通过，无pageErrors |
| frontend quality、定向Ruff、generate_agent_contracts --check、diff --check | 退出0；矩阵51项capability，contract hash314ca9737c916272 |

首次全量Agent检查430 passed/1 failed：旧dispatch覆盖测试对新能力传空参数，触发严格路径校验。补齐合法请求数据后全量通过；没有放宽服务或dispatch。首次新增应用测试import了不存在的project_manager，修正为repository_paths后通过。浏览器路径通过HPS_CHROME显式使用本机chromium-1228。

## 尚未验证和后续顺序

本轮没有发送真实生图请求，没有实际AI识别/分割提供者，mask模式未配置segmenter时在生图前返回SHEET_SEGMENTER_REQUIRED。透明背景/纯色边界处理有明确范围，不能当通用精细抠图。当前注册表稳定指工程接口，不代表视觉正确、生成成本或课程签收通过。

重启恢复用真实持久表加恢复函数模拟验证，没有实际杀进程/重开桌面的故障证据；AS05保持partial。单对象重生回退、复杂边缘、多背景视觉对照、三路线实际调用/成本、用户视觉审阅、五页课程音频与导出仍待完成，AS01—06不整体passed。历史AC与原acceptance manifest结论保留，仅追加增量记录。

下一轮先验证当前图片模型真实素材板，再接准确分割提供者和单槽重生回退；最后完成三路线对照和课程签收。相同服务负责Web/Agent写入，素材替换若涉及现有场景必须继续走scene保存/失效服务，不绕过人工修改保护。
