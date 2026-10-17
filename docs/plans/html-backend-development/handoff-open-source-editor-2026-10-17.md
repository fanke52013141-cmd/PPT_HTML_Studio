# 换机开发 handoff：开源编辑组件与 Agent 还原优化

日期：2026-10-17，Asia/Shanghai。项目：[PPT_HTML_Studio](https://github.com/fanke52013141-cmd/PPT_HTML_Studio)。本次发布到`origin/main`，前一批基线为`3d84d23`；本文件所在的新提交才是本次交接基线。接收机拉取后记录`git rev-parse HEAD`并与`origin/main`核对，不固定回退到旧提交。

## 1. 最新用户目标，必须优先延续

目标是提高系统Agent把设计图还原为可编辑、可播放HTML的能力，并支持用户二次修改。用户希望充分直接复用开源组件，降低自行设计/实现通用交互的成本。

**后续第一步：按[详细优化方案](open-source-editor-optimization-2026-10-17.md)开展P0开源组件适配验证，随后P1布局编辑。** 人工逐行标注不是生产、开发或测试前置条件；不要要求用户逐页审核，也不要继续围绕一页反复打磨。

系统Agent执行还原和修正，Codex负责开发工具、规则、组件和测试；不能让Codex手写本例场景后声称系统Agent已通过。未知供应商请求维持原核实/恢复规则，不因换机盲重发。

## 2. 已实现、已验证、待实施

| 项目 | 当前事实 |
| --- | --- |
| 契约 | 0.9.78，索引以`docs/contracts/html-presentation/contract-index.json`为准 |
| 文字边缘报告 | 已接入独立定位成功结果；输出自包含只读`text-edges.html`及hash回执，逐区域身份、原框、跨界墨迹、状态筛选/放大 |
| 可选离线盲审/计分工具 | 已实现，但用户不需填写；零真实人工标注，真实误报/漏报/人工耗时仍为null |
| 本批隔离回归 | 5个测试文件98项通过，29.57秒；JS语法和Python编译已通过 |
| 同真实页历史结果展示 | 3份报告，39/39区域；23疑似/7不确定/9未见跨界，诊断结论未改变；新模型调用0、原记录修改0 |
| 本机浏览器交互 | Browser Use返回`Local browser use is disabled in Work settings`；实际报告筛选/缩放/拖框交互未核验，不能以Node最小DOM检查替代 |
| 当前场景编辑器 | 已有属性编辑、单对象选择、undo/redo、播放/暂停、seek/逐帧、已有动作参数和讲稿绑定 |
| Moveable/Selecto/可视化时间轴 | 仅完成方案及来源核对，未安装、未集成、未验收 |
| Agent自动局部修正闭环 | 仍待后续集成和固定案例效果对照；不能以只读诊断/报告表示闭环完成 |
| 完整课程/供应商/视觉签收 | 维持各自待验证状态；没有新的整体通过结论 |

前序真实定位仍为正文16/18、分层联合1/3；受控版式联合2/4。新增报告或工具不提高旧评分。人工工具包39行来自同一张原图的三次定位，不是39个独立案例或三张新真实页。

## 3. 下一实施切片与开源复用

主方案：直接采用Moveable 0.53.0、Selecto 1.26.3和@xzdarcy/react-timeline-editor 1.0.0作为候选依赖；Scena借鉴编辑器组合；Theatre仅作交互参考。锁定来源/许可/发布包integrity见[研究档案](../../research/2026-10-17-open-source-scene-editor/README.md)及[sources.json](../../research/2026-10-17-open-source-scene-editor/sources.json)。这些版本尚未经过本项目集成实验。

P0必须在本项目现有隔离场景里完成：

1. 原生JS Moveable/Selecto能在同源iframe内正确选择、拖动、resize；缩放/滚动后回写作者坐标，不只改变临时DOM。
2. 拖动生成原`set_presentation`等受控操作，本地预览通过后仍走原revision/save/人工保护。
3. 时间轴以局部React模块嵌入现有编辑器；发布包要求React/ReactDOM >=18，不整体迁移现有前端。
4. Timeline只负责编辑和时间游标，播放由原音频/共享播放器驱动，避免第二套动画引擎和时钟。
5. 绑定动作拖动修改beat相对offsetMs，不能覆盖成绝对startMs；稳定actionId/beatId、原句hash及语块窗口保持。
6. 包版本精确锁定、本地bundle、许可证登记、销毁/切页无重复监听；不引入CDN latest。

P1首个可用结果：选中“人选来源”卡片→拖动位置→调整宽度→撤销/重做→保存/重开→播放后仍在正确位置。之后P2动作轨道、P3保存保护、P4 Agent工具/Skill对照、P5整体验收。各阶段目标与模块拆分见详细方案；第一轮不引入自由关键帧/任意旋转/图片内部拆分。

## 4. 关键代码和规则入口

- `static/html_scene_editor.js`：现有编辑器及共享播放器iframe、属性、undo/redo、保存/冲突。`static/html_audio_review.js`：已有真实声音试听。
- `html_scene_editing.py`：revision、结构限制、人工保护和保存；`html_scene_repair.py`：set_presentation/set_text_style/set_motion/set_binding等受控操作。
- `html_engine/visual/schema.json`：支持字段和预算；`renderer.cjs`：按时间求值及DOM/SVG组合。当前presentation没有任意旋转/warp；节点上限40，不因库支持更多能力就绕过Schema。
- `html_semantic_runtime.py`、`html_motion_binding.py`、`html_audio_binder.py`、`html_audio_binding_service.py`：对象动作与讲稿/真实音频绑定。新版plan0.2→scene0.6/0.7、binding0.2；生产默认plan仍0.1，新语义路线需显式选择。
- `html_rebuild_plan.py`/`invalidation_service.py`：最小重建和下游影响，不在新UI重写失效业务。
- `html_text_edge_report.py`/`scripts/report_html_text_edges.py`：只读报告；`html_text_edge_benchmark.py`/`scripts/benchmark_html_text_edges.py`/`scripts/assets/text_edge_labeler.js`：可选离线校准。
- `html_build_snapshot.py`已将报告源码纳入闭包；代码升级后旧快照按原规则变stale，不能为了恢复旧实验跳过来源检查。
- `.agents/skills/produce-editable-html`和`bind-animation-timeline`：操作边界；真正runtime片段按`config/html_runtime_skills.json`登记。Skill文档数量不等于独立Agent数量。

先读根`AGENTS.md`、契约README、UI规范及相关runtime卡；参考研究不是第二套规范。新能力按HPS规则补定义/兼容、实现/消费者/source closure与验证，状态分开报告。

## 5. 另一台电脑拉取和准备

已有克隆先检查`git status`，保留本机未提交工作，不使用reset --hard或强推覆盖。干净工作区：

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
git rev-parse origin/main
```

新克隆：

```powershell
git clone https://github.com/fanke52013141-cmd/PPT_HTML_Studio.git
cd PPT_HTML_Studio
```

当前机器实际工作目录是`D:\software\PPT_HTML_Studio`。另一台使用实际clone目录，所有命令从仓库根运行；不要照搬历史`D:\Program Files (x86)`路径或另建桌面运行副本。

Python锁文件来自3.13.5环境；目标机建议Python3.13，先安装环境再执行：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip check
npm.cmd ci --prefix html_engine
```

视频相关开发再按`scripts/remotion/package-lock.json`运行`npm.cmd ci --prefix scripts/remotion`，并准备ffmpeg/ffprobe和所需浏览器/字体。字体、Node、Python虚拟环境与便携运行时不在Git中。P0的新editor_ui局部构建包尚不存在，不能先运行方案中未来脚本。

## 6. 已核对的启动入口（修正历史缺失脚本）

仓库实际包含`start_server.py`和`start_here.bat`，没有历史文档中的`open-html-studio.ps1`、`start-html-studio.ps1`、`stop-html-studio.ps1`。换机不要依赖旧桌面快捷方式。

在独立终端从当前仓库启动：

```powershell
$studioCheckout = (Get-Location).Path
$env:PPT_STUDIO_HOST = '127.0.0.1'
$env:PPT_STUDIO_PORT = '8010'
$env:PPT_STUDIO_DB_PATH = Join-Path $studioCheckout 'data/projects.db'
$env:PPT_STUDIO_RUNS_DIR = Join-Path $studioCheckout 'runs'
.\.venv\Scripts\python.exe start_server.py
```

`start_server.py`自身默认端口为8000，所以8010必须显式设置。用浏览器打开`http://127.0.0.1:8010`，前台Ctrl+C停止；端口占用会拒绝，不要启动第二实例访问同一数据库/runs。`data`下模型配置和数字人端点须在目标机重新核对，不能指向原图片项目的数据或服务。此交接未启动/重启本机服务，不声明线上应用已部署。

## 7. 回归命令与数据隔离

在另一个全新终端执行测试；先去掉可能从服务终端继承的真实路径，让`checks/conftest.py`配置临时数据库/runs：

```powershell
Remove-Item Env:PPT_STUDIO_DB_PATH -ErrorAction SilentlyContinue
Remove-Item Env:PPT_STUDIO_RUNS_DIR -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m pytest checks/test_html_text_edge_benchmark.py checks/test_html_text_edge_report.py checks/test_html_text_edge_verification.py checks/test_html_reference_localization.py checks/test_html_build_snapshot.py -q
node --check scripts/assets/text_edge_labeler.js
```

本机本批98项通过（29.57秒）；部分源闭包/快照检查需要本地Node、浏览器/字体，目标机缺依赖应先做原预检，不将环境失败伪称业务失败或直接降低标准。P0编辑器接入另需扩展`test_html_scene_editor.cjs`等真正浏览器测试，旧的98项不证明新功能通过。

## 8. 哪些数据随Git，哪些需要另外迁移

随仓库：全部本批源码、注册规则/契约、隔离测试、固定gold JSON、研究来源、详细方案、发布备注和本handoff。

不随仓库：`data/`模型/凭据/数据库、`runs/`课程/原图片、`outputs/`真实响应/HTML报告、日志、字体、虚拟环境、node_modules。原图及供应商响应不能因在gold/报告中出现hash就被当作已经随Git携带。

**开始P0/P1不需要复制本机真实课程数据库。** 用仓库现有场景和隔离夹具即可开发。如必须原样复现这次真实页，应私下迁移三份`outputs/reference-parts-realpage-20261017/localization-{0,1,2}`中的`reference.png`和`audit/result.json`，核对原图SHA-256 `326d7425690b31f32675d757cce53388469bbf58fce5fe32ae5cfb002cb9b09a`，再运行离线报告入口；不要带密钥/Authorization或把运行目录加入Git。原任务服务恢复还涉及完整runs与数据库，不能仅靠这六个离线文件冒充任务恢复。

## 9. 可直接交给新机器Agent的说明

> 请先阅读本handoff、详细开源优化方案及研究sources.json。最新目标是系统Agent还原与二次编辑：直接复用Moveable/Selecto/React Timeline Editor，先实施P0适配验证，再做P1布局编辑。现有拖动/时间轴新能力尚未实现，人工逐行盲审只是可选校准，不要求用户填写。使用当前checkout及隔离测试数据，保留现有讲稿/动作身份、真实音频绑定、人工修改保护、revision和单一播放器。不要盲重发原未知请求，不把Codex手写场景当系统Agent成功，不整体更换现有音频/渲染系统。完成每个切片时提供可复现产物、实际测试与未验证项。
