# N02 编辑器交接

2026-10-08，对话 B。工作目录 D:\software\PPT_HTML_Studio；保留所有既存修改。
定义见 runtime/visual-v1/scene-editor-0.1.0.md。实施中；尚未宣称产品集成通过。

已核对生产 scene 0.3.0：enter/exit/emphasize；relation_draw 仅实验纯函数，禁止暴露。
shared player.apply(scene, resources)、seek(ms) 与 geometry 是唯一预览路径。

## 已实现模块

- `html_scene_editing.py`：生产 compiler/schema 校验；scene/binding/anchors 保存；私有锚点资产；普通异常多文件回滚；人工覆盖差异合并。模块不访问数据库、不调用模型。
- `html_visual_routes.py`：已有 router 增加 GET/PUT editor、POST editor/preview，以及只允许 data.js/player.js 的固定 runtime 路由。项目权限仍由 `_html_project` / `project_or_404` 检查。保存持有原项目锁，changed 时仅本页调用 `html_scene_changed`，一次 commit。
- `html_visual_store.py`：旧接口保持参数与 no-op 行为；有 edits 记录的非 no-op 写入默认拒绝，报 MANUAL_EDIT_CONFLICT。新增内部关键字 `allow_manual_replace=False`，只有经过覆盖合并、检查和原修订校验的生产路径可显式使用 True。
- `static/html_scene_editor.js` / `static/html_scene_edit.css`：生产 Schema 生成属性控件，身份/type/slot 固定；文字分段与强调、复合组件属性、独立资源选择；enter/exit/emphasize 参数与 beatId/edge/offsetMs；列表/画面双向选择；私有图片锚点新增/命名/坐标/指针定位；播放/暂停/重播/帧步进/seek；DOM Range 实测；会话撤销/重做；409 本地草稿、服务器比较与显式重载。
- `static/html_review_panel.js`：新增“编辑对象与动作”按钮与宿主；按项目/页切换关闭播放器并保留会话草稿。无编辑器脚本时明确提示尚未接入。
- 测试：`checks/test_html_scene_editing.py`、`checks/test_html_scene_editor.cjs`、`checks/test_html_scene_editor_fixture.py`。未修改现有测试来隐藏失败。

## 新接口的精确合同

`GET /api/projects/{project_id}/html-visual/{slide_id}/editor` 返回：
`scene/sha256/revision/binding/anchor_overrides/beats/resources/capabilities/manual/preview_clock/audio_status`，加 `success`。
资源 pack 为经过现有 project-resources.cjs 检查的 PNG base64；无凭据。

`PUT 同路径` 严格请求：`scene:dict, binding:dict|null, expected_revision:int>=0,
anchor_overrides:dict[nodeId,list[{id,x,y}]]={}`。未知请求字段拒绝。
返回既有保存结果 `success/slide_id/revision/changed/sha256`。
409 detail：`code=REVISION_CONFLICT/message/expected_revision/current_revision`。
422 detail：`code/message`（Schema、通道/时间/资源、beat、锚点诊断）。

`POST 同路径/preview` 使用相同请求结构，返回 `success/scene/resources/clock/audio_status`。
若已有 audio_timeline，用原 `bind_scene_to_audio` 后再生产 compile；否则作者时钟。
此接口不改文件、不合成音频、不批准。

`GET /api/html-scene-editor/runtime/{name}` 仅 `data.js/player.js`；no-store；不存在的文件名404。
不读取任意路径、不含项目私有数据。已有 html_visual_router 在 server 中注册，因此这些路由不需要另一个 server include。

存储：`planning/html_visual/edits-{slide}.json`，format/version =
`hps.html.scene_edits/0.1.0`；`slide_id/base_revision/base_scene/base_binding/scene/binding`。
所有基线保留第一次人工保存时的值，后续保存累积覆盖。私有资源在
`planning/html_visual/editor-assets/edit-{hash}.png`，manifest 沿用 resources.json；
source 保留原资产与其 source 追溯。共享原图与同板其他资源不删除。

## 主对话待集成（仍是放行前必需项）

1. **static/index.html**：增加 `<link rel="stylesheet" href="/static/html_scene_edit.css">`；
   `html_scene_editor.js` 在 api_client.js 后、html_review_panel.js 前加载。
   **checks/test_frontend_quality.js**：新增 HtmlSceneEditor、属性/动作/锚点编辑归属 guard，确保逻辑不回流 workflow_state/storyboard。
2. **生产重新规划**：在当前项目锁与 expected_revision 校验内读取 `edits-{slide}.json`，
   调用 `merge_manual_edits(candidate_scene,candidate_binding,manual)`；非空 conflicts 阻断并保留候选。
   合并输出必须经现有生产 review 与 binding beat 校验；引用人工资源时保留现有资源。
   成功后 `save_scene(..., allow_manual_replace=True)`，保存合并 binding，并保持 edits 记录。
   旧生产入口目前会明确拒绝覆盖人工页，不会静默丢失；尚未完成端到端自动合并接入。
3. **Agent/API/MCP/CLI**：新增场景编辑读取/保存/预览能力，request/response 精确映射上述字段；
   图像锚点使用源图归一化坐标。新增能力版本、API版本、parity映射与生成文档按 AGENTS 同步。
   原 Agent parity 当前通过仅说明旧映射未破坏，不能代表新增能力已同步。
4. **影响登记/总规范**：编辑 scene、binding 与私有锚点资源均复用本页 html_scene_changed；
   在现有规则登记中明确 binding-only 与 anchor-only 为视觉/输出失效，不触发 TTS；同步 downstream-impact、规范索引/CHANGELOG 和任务账本。B 未写这些共同文件。
5. **素材板资源选择**：当前只消费普通 resources.json 和固定 runtime 能力。
   现有独立资源格式没有接受状态，不能猜测 accepted；主对话加入素材板 acceptance 时，在资源读/选/保存路径同步验证接受状态，避免把 pending_review 槽位当成已接受。
   裁切/遮罩修改、新资产生成入口归主对话，不在此编辑器重建。

## 实际验证（2026-10-08）

Python 均为 `.venv/Scripts/python.exe`。pytest 经 checks/conftest.py 隔离 DB/runs。
浏览器 fixture 为 OS 临时目录、127.0.0.1 随机端口独立 http.server，未启动应用服务；
不导入 server/database，不访问真实项目。结束关闭 Chromium/fixture 并删除临时目录。

| 命令 | 结果 |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest checks/test_html_scene_editing.py checks/test_html_action_editing.py checks/test_html_annotation_targets.py checks/test_html_visual_store.py -q` | 30 passed，退出0；Starlette 既有 deprecation warning |
| `node checks/test_html_scene_editor.cjs` | 退出0；真实 Chromium + 原 shared bundle + 真实存储/编译器；操作、保存重开、绑定、换资源、锚点、409保留/比较/重新打开草稿、DOM Range均通过；pageerror=[] |
| `node checks/test_html_review_panel.cjs` | 6 checks，退出0；正确 Step3 宿主、生命周期与重复刷新无额外变更 |
| `.venv/Scripts/python.exe -m pytest checks/agent/test_contract_model_parity.py checks/agent/test_transport_contract_sync.py -q` | 10 passed，退出0；新增能力同步仍待主对话 |
| `.venv/Scripts/python.exe scripts/generate_agent_contracts.py --check` | 退出0；现有 capability-matrix up to date |
| 定向 Ruff：html_scene_editing/html_visual_routes/html_visual_store 及两新增 Python 测试 | All checks passed，退出0 |
| `node --check static/html_scene_editor.js` 与 `node --check static/html_review_panel.js` | 退出0 |
| `git diff --check -- html_visual_store.py html_visual_routes.py static/html_review_panel.js` | 退出0 |

浏览器需指定实际安装路径：
`$env:HPS_CHROME='C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe'`。
第一次未指定时旧1247路径不存在导致5项锚点测试 setup error；定位环境后重跑30项通过，未改引擎/现有断言。

证据：`scene-editor-browser-evidence.json`；实际 fixture 截图 `scene-editor-evidence.png`（当前全局 ignore 图片，文件仍本地可查看；主对话决定是否纳入发布）。
1500/1200/900 宽度指针定位最大原图误差0.01209像素；改用 pointerup 保留小数坐标解决 click 取整误差。
重复乱序 seek 的 geometry/DOM 完全相同；1600原生画布截图 hash 相同。
分数 CSS 缩放下最初出现3个像素的浏览器合成差异，未将其改写为零差异；原生尺度像素检查通过。

## 状态与边界

定义 specified；B 模块 implemented、工程验证 passed；公共接入 partial。
真实模型/真实课程/应用完整操作/重审输出/用户视觉签收 not_run，待主对话集成验证。
图片语义锚点可实际输出；文字/SVG 测量可用，生产 annotation 仍只支持图片，文字选区明确 output_supported=false。
会话历史不是持久版本恢复；进程崩溃事务恢复不在本轮保证；关闭页面有未保存提醒。
没有调用 OCR、模型或真实服务，没有 commit/push/PR/部署，没有修改 distribution 文件或 A/主对话模块。

## 本轮仓库更新备注 — 2026-10-08

用户在模块交付后明确授权更新线上仓库，本节覆盖上一节开发阶段的“不 commit/push”限制。
本次提交仅包含对话 B 的 N02 代码、测试、定义卡和工程证据；目标为
`origin/main`（fanke52013141-cmd/PPT_HTML_Studio），不包含 A 的模型绑定或主对话尚未提交的素材板/规划改动。
发布状态为“编辑器模块工程验证通过，公共集成仍待完成”；不标记真实服务、课程或用户视觉签收通过。
推送前重新执行30项模块测试、隔离真实浏览器操作和6项 review panel 浏览器检查。
截图使用隔离测试资源；它是操作证据，不是批准的生产设计。
