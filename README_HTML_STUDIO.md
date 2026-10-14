# PPT HTML Studio

2026-10-14 当前交接：[A04—A06 开发与线上同步备注](docs/plans/html-backend-development/handoff-2026-10-14-publication.md)。正常应用已完成五页分镜和第一页整页设计/独立素材；未保存候选的人工审阅入口可追溯原任务，但最终版式容量失败，只能驳回。真实整课、试听/签收与正式输出仍待完成。A06 过程证据见 [专项交接](docs/plans/html-backend-development/handoff-a06-2026-10-14.md)。

2026-10-14 最新增量：[A05 系统内部课程调度与跨进程恢复](docs/plans/html-backend-development/handoff-a05-2026-10-14.md)。原一键入口串联HTML生产/TTS/A04/当前签收/视频任务，课程及原子任务ID持久恢复；真实正常应用整课验收与用户试听/签收留待A06。

前序增量：[A04 逐句语义 QA、真实正反例与 A05 入口](docs/plans/html-backend-development/handoff-a04-2026-10-14.md)。逐句三帧与原句独立审核已实现；真实正常例通过、输入/输出矛盾负例被阻止。音频/人工批准仍独立。

前序增量：[共享呈现细节、GLM截图审阅与下一批入口](docs/plans/html-backend-development/handoff-presentation-details-2026-10-14.md)。文字/多模态模型分开，新增能力工程及截图验证通过，旧原图保真仍待验。

本地最新增量：[设计Agent理解、素材分工与还原审核](docs/plans/html-backend-development/handoff-design-agent-2026-10-13.md)。下方设计先行/A03为前序交接；真实模型、视觉批准与应用整课验收分别记录。

前序增量：[整页设计先行、真实豆包还原与逐句试听](docs/plans/html-backend-development/handoff-design-first-2026-10-13.md)。该轮单页通过工程检查；后续独立视觉审核发现差异并阻止正式保存，以当前设计 Agent 交接为准。A03 仍为历史增量记录。

上一批开发交接（2026-10-13）：[当前已交付、待验证及讲稿同步/系统自动制作后续方案](docs/plans/html-backend-development/handoff-2026-10-13.md)。用户已认可整体审美；语义同步和完整产品自动制作尚未通过，历史工程通过记录不表示这两项已实现。

这是 HTML 课程演示与视频系统的独立开发副本。应用目前运行原图片工作流基线；E1 独立数据驱动渲染已实现，应用内 HTML 生成/标注和原生可编辑 PPTX 尚未实现。

## 本地来源

- 来源目录：`D:\Program Files (x86)\PPT_presentation_video`。
- 来源提交：`8efecc1`（2026-10-06）。
- 副本包含建立快照时的未提交源码改动，具体清单与逐文件 SHA-256 位于 `docs/baseline/source-snapshot.json`。
- 开发分支：`html-studio`；原 GitHub 地址只登记为 `upstream`，没有自动推送。
- 仅复制源码与版本管理中的参考资产；历史课程、用户数据库、模型凭据、原虚拟环境及生成作品没有复制。
- 新虚拟环境按 `requirements.lock` 安装；视频工程使用 `npm ci`。

## 启动

唯一开发与运行目录：`D:\Program Files (x86)\PPT_HTML_Studio`。

正常使用桌面上的 **PPT HTML Studio** 快捷方式。它直接执行本目录的
`open-html-studio.ps1`，每次打开都先核对并停止本项目的旧服务，再从当前源码
启动并打开浏览器。关闭浏览器不会自动停止服务，再次打开快捷方式会重启服务。
原项目的服务和数据库与此副本隔离。

代码更新规则：后续修改均发生在本目录，不另建桌面运行副本，不使用打包版本代替
源码入口。打开快捷方式会使用已保存的本地最新代码，不自动拉取远程仓库。
HTML/CSS/JS 响应禁止浏览器缓存；重启服务后重新打开页面即可使用更新。
上次启动目录、时间与进程号记录在 `logs/desktop-launch.json`，失败详情在
`logs/desktop-launch.error.log` 和 `logs/desktop-server.stderr.log`。

前台排查可运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-html-studio.ps1
```

默认访问 `http://127.0.0.1:8010`。在前台启动时按 Ctrl+C 即可停止；后台服务可以运行以下命令停止，脚本会核对进程属于当前副本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\stop-html-studio.ps1
```

该入口强制使用副本自己的 `data/projects.db` 和 `runs/`，数字人客户端默认连接独立的 `9011` 端口。复制来的旧启动脚本继续保留作为原项目参考；本副本优先使用新入口。

数字人代码已保留，但本次未部署 GPU 模型、启动数字人服务或调用付费生成接口。未来可以复用机器上的 ComfyUI 推理服务，项目配置、头像与任务数据仍需隔离。

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
