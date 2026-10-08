# N03 模型绑定交接（模块验证完成，待公共接入）

仅修改分工 A 文件；未启动服务、未读写真实 DB/runs、未改 distribution 文件。定义完成、模块实现与定向验证完成；真实模型和完整产品尚未验证。源码基线 HEAD `83f658b9d138e1dd2a10640047ec5021b0dc05ad`，工作区有其他对话增量，未提交。

## 当前接口与接入建议

- `project_model_binding_service.freeze_project_models(project, required=("text",))`：在 **submit 时** 调用，返回不可变 text/image 模型对象及 `.summary()`。运行对象仅内存传递，严禁 asdict/持久化；summary 可放任务 payload、submission_key、生成证据、图片缓存参数。缺图片配置可提交纯代码任务，实际图片回调必须 `.require_ready()`。配置损坏必须失败，不回退。
- 生产 worker 接收冻结对象；文字 `functools.partial(generate_json_with_configured_llm, model_binding=frozen.text)`，用 dataclasses.replace 生成本任务 HtmlReviewDependencies，不能修改共享 deps。图片 `functools.partial(configured_image, model_binding=frozen.image)`。重试显式新提交获得新快照，运行中全局或项目改动不影响本次模型/凭据。
- `GET/PUT /api/projects/{project_id}/model-binding` 已由 project_routes.py include_router 接入，无需 server 再注册。账户鉴权 project_or_404；仅 HTML。PUT：`expected_revision`, `text/image: {mode: inherit|fixed|legacy, connection_id?: str, rebind?: bool}`。fixed 需要 ID；legacy 沿用现有创作包/全局优先级。返回 changed/revision；冲突 409。GET 返回 revision/bindings/effective，不含端点、public_config 或凭据引用。
- 固定内容保存在 planning/project_model_binding.json；没有数据库迁移，没有改变创作包或连接的实时编辑行为。未绑定旧项目先用创作包 storyboard/image_generation 再全局。相同 fixed ID 是 no-op；rebind=true 才刷新连接快照。凭据引用可轮换，下次任务生效。修改仅影响将来生成，不直接取消旧批准或 TTS。

## 主对话待集成（精确范围）

1. html_workflow_jobs submit 冻结模型，summary 纳入 submission key 与 payload；将 frozen 传 run；run 为本任务构造 deps/provider。不要在 run 内重新读项目配置。
2. html_production_service/asset service 将 frozen image config_hash 纳入图片缓存 key 及生成记录；素材板、设计参考和独立资产都消费同一已冻结图片 provider；确定性拆分另记工具版本。
3. static/index.html 引入 `/static/project_model_binding.css` 与 `/static/project_model_binding.js`（API client 之后）。产品配置入口容器调用 `ProjectModelBinding.mount(container, currentProject)`；只在显式打开/重载调用，非每帧或观察器。HTML review panel 属 B，主对话协调入口。扩展 frontend quality ownership guard。
4. Agent 新注册读取/保存绑定能力，复用请求结构与服务，映射同一账号/HTML门禁及 409；添加 parity 和 transport 覆盖，更新版本与生成文档。新服务不修改 ProjectCreate/Project 数据库字段。
5. impact registry/docs 加未来生成配置变更说明：保留场景/批准/音频，配置 hash 只控制新的生成缓存，不进入已批准作品的渲染 manifest；实际新生成成功沿用 html_scene_changed。
6. 规范入口/index/CHANGELOG 登记新增定义卡 project-model-binding-0.1.0.md；HPS-014–017/026/030；四维兼容均保留既有作品。
7. 现有 json_llm_service 的 model_binding 已固定 endpoint/key/model，但 max_tokens 仍读取全局。若要冻结全部生成参数，主对话需授权/接入该共享模块参数（当前 A 不可改）。不要把当前模型快照声称为全部生成参数固定。

## 修改清单

新增 project_model_binding_models.py / service.py / routes.py；新增 static/project_model_binding.js / .css；新增 checks/test_project_model_binding.py / .cjs；新增本交接、定义卡、model-binding-browser.png。修改 project_routes.py 仅 include router；html_image_provider.py 增加可选 model_binding 参数和对初始化/请求/关闭异常的脱敏边界。

## 验证

2026-10-08 实际命令与结果：

- `.venv/Scripts/python.exe -m pytest checks/test_project_model_binding.py checks/test_model_connections.py checks/test_creation_config.py checks/test_creation_config_defaults.py checks/test_project_service.py checks/test_database_migrations.py -q`：退出 0，59 passed。新增模块 12 项，涵盖两项目、固定/继承、运行快照、引用密钥、并发 revision、no-op/作品保留、旧包、损坏文件、HTTP 访问门禁/409/后端边界、真实附件传递的 SDK 替身、错误脱敏。
- 最后字段校验加固后重跑 `.venv/Scripts/python.exe -m pytest checks/test_project_model_binding.py -q`：退出 0，12 passed。Starlette/anyio 有 1 条既有弃用 warning。
- `.venv/Scripts/python.exe -m ruff check project_model_binding_models.py project_model_binding_service.py project_model_binding_routes.py html_image_provider.py project_routes.py checks/test_project_model_binding.py`：退出 0。
- `node --check static/project_model_binding.js`、`node --check checks/test_project_model_binding.cjs`：退出 0。
- `node checks/test_project_model_binding.cjs`：退出 0，真实 Chromium 1228 操作选择→保存→重开、409 保留草稿、名称转义、image 项目隐藏；使用当前 style.css/stitch.css 和新增 CSS。浏览器 API 为测试替身，不是应用端到端。证据：[model-binding-browser.png](model-binding-browser.png)。运行环境显式 `$env:HPS_CHROME='C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe'`；可选截图变量 `$env:HPS_MODEL_BINDING_SCREENSHOT='docs/plans/html-backend-development/model-binding-browser.png'`。首次默认路径 1247/包期望 1234 不存在，已用机器实际安装的 1228 跑通；不安装/启动应用。
- `.venv/Scripts/python.exe -m pytest checks/agent/test_contract_model_parity.py checks/agent/test_transport_contract_sync.py -q`：退出 0，10 passed；这验证既有能力未漂移，不代表新增能力已登记。
- `.venv/Scripts/python.exe scripts/generate_agent_contracts.py --check`：退出 0，现有矩阵一致；新增 Agent 接入仍在上方待集成。
- `git diff --check -- project_routes.py html_image_provider.py`：退出 0。

生产 Prompt 未修改，未调用真实模型。没有数据库字段/迁移和 ProjectCreate 字段变化。代码消费者只支持现有 HTML transport 的 provider/model/endpoint/key；public_config 随固定快照保留并参与 hash，但不宣称全部高级提供者参数已接入。

真实提供者 not_run；应用服务与完整产品入口 not_run；用户视觉 pending_review；不等于完整 N03 passed。

## 公共集成轮增量 — 2026-10-08

主对话授权的新范围：html_workflow_jobs.py、json_llm_service.py、project_model_binding_service.py / models.py、新增 checks/test_html_model_binding_integration.py 和本报告。按授权完成：

- submit 使用 freeze_project_models；生产 root 传既有 configured_image 时自动启用，其他注入 fixture 保持可运行，也可显式 freeze_models 注入。summary 在 LocalJob payload 的 `input.model_summary` 下，参与 submission_key；冻结对象只通过 executor 参数在内存传递。
- worker 使用 dataclasses.replace 本任务 deps 和 partial 的文字/图片回调，保持共享 deps/provider；传 `model_summary=frozen.summary()` 到主对话新增的 produce_scene 参数。
- 当前真实消费的文字 max_tokens 在提交时冻结、限制 1024–64000 并参与 hash；固定连接 public_config.max_tokens 缺省 12000，继承使用 llm_max_tokens。JSON fallback 与 repair 复用同一 model/key/endpoint/max_tokens。temperature/request_timeout 由生产调用显式设置，不读全局，保持调用方语义。图片尺寸由设计/资产调用显式传参，未虚构 public_config 全部参数支持。
- 新增任务测试使用真实 Job/LocalJob 路径、隔离 DB/runs 和真实 JSON/图片适配代码，上游 SDK/场景生产为受控替身，验证提交→改配置→执行使用旧配置、新提交得到新 key、共享依赖未被修改、持久摘要无密钥。JSON 初始化/请求/关闭错误有公共脱敏边界，错误日志不输出上游异常正文。

验证：`$env:HPS_CHROME='C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe'` 后 `.venv/Scripts/python.exe -m pytest checks/test_html_model_binding_integration.py checks/test_project_model_binding.py checks/test_html_task_store.py checks/test_annotation_llm_budget.py checks/test_html_workflow_acceptance.py -q`：退出 0，32 passed，1 既有 warning；定向 Ruff 退出 0。首次 task 测试误读 payload 层级，已改为 input.model_summary 后通过；第一次大回归未设置实际浏览器路径导致 5 项失败，设置路径后全部通过。

额外 `checks/test_server_composition_boundaries.py` 2 passed / 1 failed：HEAD 的 server.py 存在顶层 `def html_review_service_deps`，违反其“无顶层业务定义”断言。该源码在 HEAD 已存在，本轮未改 server.py，也未放宽测试；主对话需处理。扩大回归更新了原有 production-benchmark.json 和 effects/cache/manifest.json（运行验收输出），已留给主对话核查，未自行还原/提交。

任务与 JSON 配置工程接线已完成，不替代真实提供者验证。主对话仍负责生产缓存/记录、前端入口、Agent/规范同步。用户随后直接授权发布本对话代码；只发布独立模型模块与 JSON 消费，任务接线 html_workflow_jobs.py / integration test 因依赖主对话的 produce_scene 新参数，保留本地供公共集成统一提交，避免独立线上提交产生不存在的生产参数依赖。
