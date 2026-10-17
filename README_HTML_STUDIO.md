# HTML Studio

当前交接：[编辑器与视频优化验收](docs/plans/html-backend-development/handoff-editor-validation-2026-10-18.md)，契约0.9.85/API1.44。真实单页视频及模型/设备验证通过；真实整课与全库门禁pending。

2026-10-17 当前本地入口：[单页视频输出验证](docs/plans/html-backend-development/handoff-single-page-video-2026-10-17.md)。工程对应帧及编辑后批准/重建检查通过；真实页面待视觉批准，未发布。

2026-10-17 最新本地增量：[真实旁白与音频新鲜度](docs/plans/html-backend-development/handoff-editor-audio-freshness-2026-10-17.md)。真实MP3隔离副本编辑/跳转/重开通过；增加音频指纹过期409、保留草稿刷新配音/时序。契约0.9.83、Agent API1.43；未提交或发布。

2026-10-17 最新本地优化：[P3人工字段保护与保存边界](docs/plans/html-backend-development/handoff-editor-protection-p3-2026-10-17.md)。AI候选/最终保存共用叶字段保护，允许未保护兄弟字段，拒绝间接资源覆盖并定位冲突；契约0.9.82，未提交或发布。

2026-10-17 最新本地开发：[P2动作时间轴交接](docs/plans/html-backend-development/handoff-editor-timeline-p2-2026-10-17.md)。正式编辑器接入已有动作偏移/拉伸、只读讲稿与同一音频时钟；合成音频浏览器通过，真实旁白/输出待验。契约0.9.81，尚未提交或发布。

2026-10-17 本地开发：正式编辑器已接入 P1 布局编辑，支持移动、缩放、多选移动、撤销及原服务保存；工程与隔离浏览器通过范围、未验收项见[最新开发交接](docs/plans/html-backend-development/handoff-editor-layout-p1-2026-10-17.md)。契约0.9.80；尚未提交、推送或部署。

最新换机入口：[开源编辑与Agent优化handoff](docs/plans/html-backend-development/handoff-open-source-editor-2026-10-17.md)及[本批发布备注](docs/releases/2026-10-17-edge-reports-editor-handoff.md)。契约0.9.78；98项本批隔离测试通过，开源画布/时间轴尚未集成。以下历史状态不替代最新交接。

2026-10-17当前开发/换机入口：[流程优化与文字边缘核验发布](docs/releases/2026-10-17-review-and-handoff.md)及[跨机开发交接](docs/plans/html-backend-development/handoff-cross-machine-optimization-2026-10-17.md)。当前远端`main`已包含应用源码与guided HTML后端；原图片工作流继续保留。下方10月14日及更早记录属于历史快照，不代表当前代码、分支或验收状态。

2026-10-14 当前交接：[A04—A06 开发与线上同步备注](docs/plans/html-backend-development/handoff-2026-10-14-publication.md)。正常应用已完成五页分镜和第一页整页设计/独立素材；未保存候选的人工审阅入口可追溯原任务，但最终版式容量失败，只能驳回。真实整课、试听/签收与正式输出仍待完成。A06 过程证据见 [专项交接](docs/plans/html-backend-development/handoff-a06-2026-10-14.md)。

2026-10-14 最新增量：[A05 系统内部课程调度与跨进程恢复](docs/plans/html-backend-development/handoff-a05-2026-10-14.md)。原一键入口串联HTML生产/TTS/A04/当前签收/视频任务，课程及原子任务ID持久恢复；真实正常应用整课验收与用户试听/签收留待A06。

前序增量：[A04 逐句语义 QA、真实正反例与 A05 入口](docs/plans/html-backend-development/handoff-a04-2026-10-14.md)。逐句三帧与原句独立审核已实现；真实正常例通过、输入/输出矛盾负例被阻止。音频/人工批准仍独立。

前序增量：[共享呈现细节、GLM截图审阅与下一批入口](docs/plans/html-backend-development/handoff-presentation-details-2026-10-14.md)。文字/多模态模型分开，新增能力工程及截图验证通过，旧原图保真仍待验。

本地最新增量：[设计Agent理解、素材分工与还原审核](docs/plans/html-backend-development/handoff-design-agent-2026-10-13.md)。下方设计先行/A03为前序交接；真实模型、视觉批准与应用整课验收分别记录。

前序增量：[整页设计先行、真实豆包还原与逐句试听](docs/plans/html-backend-development/handoff-design-first-2026-10-13.md)。该轮单页通过工程检查；后续独立视觉审核发现差异并阻止正式保存，以当前设计 Agent 交接为准。A03 仍为历史增量记录。

上一批开发交接（2026-10-13）：[当前已交付、待验证及讲稿同步/系统自动制作后续方案](docs/plans/html-backend-development/handoff-2026-10-13.md)。用户已认可整体审美；语义同步和完整产品自动制作尚未通过，历史工程通过记录不表示这两项已实现。

这是 HTML 课程演示与视频系统的独立开发仓库。应用保留原图片工作流，并已接入guided HTML设计、还原、审核与受约束导出；standalone E1仍是独立工具，不等同应用后端。真实模型可靠性、九页完整验收、用户视觉签收及PPTX原生可编辑能力仍分别待验。

## 本地来源

- 来源目录：`D:\Program Files (x86)\PPT_presentation_video`。
- 来源提交：`8efecc1`（2026-10-06）。
- 副本包含建立快照时的未提交源码改动，具体清单与逐文件 SHA-256 位于 `docs/baseline/source-snapshot.json`。
- 开发分支：`html-studio`；原 GitHub 地址只登记为 `upstream`，没有自动推送。
- 仅复制源码与版本管理中的参考资产；历史课程、用户数据库、模型凭据、原虚拟环境及生成作品没有复制。
- 新虚拟环境按 `requirements.lock` 安装；视频工程使用 `npm ci`。

## 启动

当前机器工作目录是 `D:\software\PPT_HTML_Studio`；另一台使用实际clone目录，所有命令从仓库根执行，不照搬旧绝对目录或桌面快捷方式。

仓库包含 `start_server.py` 和 `start_here.bat`。历史 `open-html-studio.ps1`、`start-html-studio.ps1`、`stop-html-studio.ps1` 不在本次版本库中；不要把它们作为换机必要入口。

按锁文件准备虚拟环境后，在独立终端执行：

```powershell
$studioCheckout = (Get-Location).Path
$env:PPT_STUDIO_HOST = '127.0.0.1'
$env:PPT_STUDIO_PORT = '8010'
$env:PPT_STUDIO_DB_PATH = Join-Path $studioCheckout 'data/projects.db'
$env:PPT_STUDIO_RUNS_DIR = Join-Path $studioCheckout 'runs'
.\.venv\Scripts\python.exe start_server.py
```

访问 `http://127.0.0.1:8010`，前台按Ctrl+C停止。启动器默认8000，8010需要显式设置；端口占用会拒绝启动，禁止第二实例共享同一数据目录。不要指向原图片项目的数据库/runs。模型连接、可选数字人端点和依赖在目标机单独配置。

本机数据库、原图片/响应、凭据、字体和虚拟环境不随Git迁移；可复现测试和原案例私下迁移边界见最新handoff。本次未部署或重启任何应用服务。静态资源仍按既有无缓存策略提供。

## HTML 体系的正式契约入口

后续定义、开发、素材生产与验收统一依据
[HTML 演示体系契约](docs/contracts/html-presentation/README.md)。
详细理解构建方式及公共/风格归属，请先读
[构建方式与归属说明](docs/contracts/html-presentation/01-building-and-ownership.md)；
修改规则和兼容旧作品依照
[生产与兼容规则](docs/contracts/html-presentation/04-production-and-compatibility.md)。
契约包当前为 0.7.1；E1 独立单场景内核已实现，应用内 HTML 后端仍待接入。详见 [E1 交付](docs/plans/e1-data-driven-engine-completion.md)。

## 实施路线与历史资料

先建设独立 HTML 演示内核，再接入现有应用，具体顺序见
[HTML 基础构建方案](docs/plans/html-foundation-roadmap.md)。原定义与审查作为历史资料
保留，审查依据见 [基础体系审查记录](docs/plans/html-foundation-review-20261007.md)。模块复用边界见
[HTML 改造与复用方案](docs/plans/html-studio-adaptation.md)。现有界面品牌仍是原项目基线；新名称用于开发副本与启动入口，产品界面将在确定实施方案后统一调整。

## HTML 后端改造进展（2026-10-08 第一轮）

按 [html-backend-development 方案包](docs/plans/html-backend-development/README.md) 完成 A00–F03 全部任务的工程实施：
科普风格进入共享渲染器（schema 0.3.0，三结构模板/效果缓存/帧导出）、visual_backend 字段贯通与 Agent 能力注册（7 项）、
场景存储/修订冲突/失效、语义分镜/设计 brief/资产服务/静态审阅（真实 LLM 入口）、音频绑定、视频导出（真实冒烟
1600×900 H.264/AAC）、快照/分步 PPTX、HTML 批注定位（无 OCR）、任务持久化与总验收 manifest
（[acceptance-manifest.json](docs/plans/html-backend-development/acceptance-manifest.json)）。
视觉验收（AC04）与真实课程验收（AC20）为 pending_review，待用户审阅；真实模型端到端待服务绑定。

## E2 进展

两个受约束配方和资产工具已实现，见 [交付记录](docs/plans/e2-constrained-template-completion.md)。仍是独立设计探索工具，原应用未接入；视觉/素材生产批准待审阅。
