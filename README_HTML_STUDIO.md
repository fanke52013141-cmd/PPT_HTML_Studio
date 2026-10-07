# PPT HTML Studio

这是 HTML 课程演示与视频系统的独立开发副本。目前运行的是原图片工作流基线；HTML 场景生成、DOM 标注和原生可编辑 PPTX 尚未实现。

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
契约包当前为 0.3.0，已作为项目规则登记；HTML 内核和自动校验尚未实现。

## 实施路线与历史资料

先建设独立 HTML 演示内核，再接入现有应用，具体顺序见
[HTML 基础构建方案](docs/plans/html-foundation-roadmap.md)。原定义与审查作为历史资料
保留，审查依据见 [基础体系审查记录](docs/plans/html-foundation-review-20261007.md)。模块复用边界见
[HTML 改造与复用方案](docs/plans/html-studio-adaptation.md)。现有界面品牌仍是原项目基线；新名称用于开发副本与启动入口，产品界面将在确定实施方案后统一调整。
