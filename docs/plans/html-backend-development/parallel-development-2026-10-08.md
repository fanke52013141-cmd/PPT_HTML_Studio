# 并行开发分工与验证 — 2026-10-08

用户已授权主对话拆分开发并由 Codex 创建对应对话。两个开发对话使用本项目当前本地目录 `D:\software\PPT_HTML_Studio`；不创建新运行副本、不搬迁目录、不启动真实服务。旧文档中的路径差异仍在 N00 中核查。每个开发对话完成本模块验证，主对话负责共同文件接入和最终集成回归。

## 共同工作规则

- 同目录修改立即对其他对话可见。不得还原、删除、stash 或覆盖他人改动，不执行 git checkout/reset/clean/commit/push、创建 PR、部署或启动应用服务；不得自行扩大文件范围。
- 读取 AGENTS.md、现行规范、完整后续计划及对应运行合同。先对照实际实现，复用现有等价能力，不重复建设已存在的配置/编辑服务。
- 任何生产 Prompt 改动先使用 `.agents/skills/optimize-prompts/SKILL.md`。实际模型配置、资源路径、秘密输出与原 image 行为遵守已有规则。
- Python 使用 `.venv/Scripts/python.exe`，测试依赖已按 requirements-dev.txt 安装。HTML 引擎 node_modules 已通过 npm ci 安装。pytest 使用 checks/conftest.py 隔离 DB/runs；额外浏览器/子进程验收也必须临时数据隔离。
- 定义、实现、工程验证、真实服务验证、用户视觉签收分别记录。stub 不算真实服务；缺服务只阻止对应验证，不阻止可完成的工程工作。
- 每个模块先完成自己的定义说明与实现，再执行有意义的 test/lint/浏览器验证并修复新增失败。共享修改需求写入各自交接报告，主对话接入后模块须再次验证；不能把报告中“需要主对话接入”当作完整产品通过。
- 新请求字段/能力、数据库变化、业务失效必须满足 Agent/迁移/影响同步；共同文件由主对话统一修改。报告要给出确切字段、兼容理由和可应用的改动建议，不绕过同步检查。

## 主对话：素材板、公共接口与集成

独占：`html_asset_sheet.py`、`html_asset_service.py`、`html_production_service.py`、`html_workflow_jobs.py`、`html_task_store.py`、`html_visual_review_service.py`、`html_visual_review_routes.py`、`html_audio_binder.py`、`html_design_brief.py`、`html_storyboard_planning.py`、`html_input_manifest.py`、`html_engine/**`、素材板专属测试与定义卡。

共同文件仅主对话修改：`server.py`、`static/index.html`、`static/workflow_state.js`、`static/workspace_navigation.js`、`static/flow.js`、`static/stitch.css`、`static/style.css`、`checks/test_frontend_quality.js`、`checks/conftest.py`、`invalidation_service.py`、`impact_registry.py`、`project_impact_service.py`、`agent_contract/**`、`agent_api/**`、`docs/agent/**`、规范入口/index/CHANGELOG、总开发计划/task-ledger/acceptance-manifest、`docs/downstream-impact.md`。

已有未提交用户/主对话改动须保留：开发计划相关 docs；`distribution_profile.py`、`static/distribution_profile.js`；素材板定义卡与 `html_asset_sheet.py`。原 image/TTS/数字人和 data/runs/outputs/logs 不在开发对话写入范围。

## 对话 A：N03 项目独立模型绑定

目标：沿用 model connections 与 creation config 包，实现项目级文字/图片模型绑定、默认继承、任务启动时配置摘要、无明文凭据的界面与持久配置。先检查当前项目 creation_config 是否已有可用绑定能力；已存在部分必须复用，补 HTML 实际消费及产品入口。

可修改：`model_connection_models.py`、`model_connection_service.py`、`model_connection_routes.py`、`creation_config_models.py`、`creation_config_service.py`、`creation_config_routes.py`、`creation_config_defaults.py`、`project_service.py`、`project_routes.py`、`database.py`、`html_image_provider.py`、`static/creation_config_management.js`。可新增 `project_model_binding*.py`、`static/project_model_binding*.js`、`static/project_model_binding.css`、`checks/test_project_model_binding*.py`、`checks/test_project_model_binding*.cjs`。可调整对应现有 model_connections/creation_config/project_service 测试。若确实必须新增迁移，A 独占下一个 `0018_*.sql`，先重新核对序号；不可修改旧迁移。

可新增文档仅：`docs/contracts/html-presentation/runtime/visual-v1/project-model-binding-0.1.0.md`、`docs/plans/html-backend-development/model-binding-handoff.md` 及该模块命名的证据文件。不修改 B 的前端、编辑服务或主对话共同文件。

需主对话接入的 server/生产配置绑定、script 标签、Agent/影响注册，写入 model-binding-handoff.md 的“待集成”并提供精确建议。工作模块必须实现完成，不能只交设计或空壳；若可以通过已有注册入口完成接入且属于以上文件，直接实现。

验收：两个项目可不同模型；继承与固定配置行为明确；未绑定旧项目兼容；凭据引用解析无秘密泄漏；更改全局不偷偷改变固定项目任务；已启动任务用固定配置；无变化保存不失效；测试传入可控提供者，真实服务状态另外登记。

运行：相关 `checks/test_model_connections.py`、`checks/test_creation_config.py`、`checks/test_creation_config_defaults.py`、`checks/test_project_service.py`、`checks/test_database_migrations.py` 与新增测试；定向 Ruff、JS syntax、真实浏览器界面测试。Agent parity/generate check 用于发现待集成差异，交主对话修复共同文件；不得修改测试来隐藏暴露需求。

## 对话 B：N02 对象、动作与锚点编辑器

目标：在当前 shared renderer/scene/beat 契约上补产品编辑器，支持对象选择、内容/资产属性、注册动作/beat、锚点、预览 seek、修订冲突、人工覆盖与保存重开。素材板资源仍作为现有独立资源使用，勿依赖正在开发的素材板专属 API。先读取当前 scene schema/player 接口确认已支持能力。

可修改：`html_action_editing.py`、`html_annotation_targets.py`、`html_visual_store.py`、`html_visual_routes.py`、`static/html_review_panel.js`、`checks/test_html_action_editing.py`、`checks/test_html_annotation_targets.py`、`checks/test_html_visual_store.py`、`checks/test_html_review_panel.cjs`。可新增 `html_scene_edit*.py`、`static/html_scene_edit*.js`、`static/html_scene_edit.css`、`checks/test_html_scene_edit*.py`、`checks/test_html_scene_edit*.cjs`。

可新增文档仅：`docs/contracts/html-presentation/runtime/visual-v1/scene-editor-0.1.0.md`、`docs/plans/html-backend-development/scene-editor-handoff.md` 及该模块命名的证据文件。不可修改 A 文件、Agent 公共模型、server、生产/资源/音频/渲染引擎或总规范。

既有存储接口与原保存行为必须保持兼容；新增编辑数据单独定义可追溯格式并保留人工覆盖。动作范围以实际生产 schema/播放器为准，不能根据实验纯函数注册表虚构可执行动作。时间与几何继续由共享播放器和现有 binder 解释；新底层需求写入交接报告，主对话补齐后再完成整链验收。

验收：通过实际浏览器完成选对象→改内容/资源→改 beat/动作→调整锚点→保存→重开；expected_revision/409 不丢草稿；no-op 保留批准/音频；改动影响最小；重新规划保留人工覆盖或明确冲突；目标删除/越界诊断；HTML 不调用 OCR；预览重复 seek 一致。锚点缩放误差按 AC13，不以 UI 字符串测试替代操作验证。

运行：上述 B 现有与新增 pytest；`node checks/test_html_review_panel.cjs`、新增真实浏览器验收、定向 Ruff、JS syntax。共同 script 标签、ownership guard、Agent/影响与重新规划接入建议写入 scene-editor-handoff.md。

## 汇报与推进

已创建开发对话：

- A：`01a11993-9ac4-7523-9f26-9b4c39c5bfda`，本地主机 local。
- B：`01a11993-e28b-79c1-90c6-13ce42f95f1e`，本地主机 local。
- 主对话：`01a11974-285b-7333-bc30-134fffad0105`，负责公共接入与最终验证。

各对话持续在自己的交接文件记录：实际修改文件、定义/接口、验证命令与退出码、当前通过范围、未集成项、真实服务/视觉未验证项。共同文件改动请求写文件，由主对话读取；不向其他对话自行发送指令，不创建新的子对话或自动扩展 Agent。

主对话接到报告后检查改动、补公共接入、运行模块及跨模块回归。只读独立验收对话待首批模块达到可检查版本再创建，避免审阅不断变化的半成品。合并到同目录不需要 cherry-pick，但代码可见不等于完成集成。
