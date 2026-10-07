# HTML 后端改造基线报告（A00）

日期：2026-10-08。任务依据：`docs/plans/html-backend-development/README.md` 与 `tasks.md` A00。
本报告记录执行起点，供后续执行者复现；不宣称任何计划能力已实现。

## 源码与版本状态

| 项 | 值 |
| --- | --- |
| 开发分支 | `html-studio`（完整应用检出，1372+ 文件） |
| 基线同步提交 | `3d52135` "sync: align html_engine and docs with published html-backend baseline" |
| 发布基线 | `origin/main` = `21c1aa0`（docs + html_engine 精选发布，独立历史）；本地同源分支 `project-specifications` |
| 引擎/文档对齐 | `html_engine/` 与 `docs/` 已与 `origin/main` 逐文件一致；差异仅为本地独有的应用侧文档 |
| 遗留未提交改动 | 应用源码约 144 个文件（副本时继承，清单与逐文件 SHA-256 见 `docs/baseline/source-snapshot.json`）。按计划要求保持原样、不重置、不混入本轮提交 |
| 远端 | `origin` = `github.com/fanke52013141-cmd/PPT_HTML_Studio`（唯一发布目标）；`upstream` = 原图片项目，禁止推送 |
| 提交身份 | `fanke <fanke52013141@gmail.com>`（沿用仓库历史身份，仓库级配置） |

## 环境与工具版本

| 工具 | 版本 | 备注 |
| --- | --- | --- |
| Windows | 10.0.26200 x64 | 唯一运行目录 `D:\Program Files (x86)\PPT_HTML_Studio` |
| Python | 3.13.5 | |
| Node.js | 24.12.0（npm 11.6.2） | 引擎要求 20+，满足 |
| FFmpeg / ffprobe | 8.1 essentials（PATH 可用） | 视频导出验证可用 |
| Chromium/Playwright | `html_engine` 内 playwright 1.62.1；`CHROME_PATH` 未设，浏览器探测由引擎脚本自完成 | `test:visual` 实测通过 |
| 字体 | Microsoft YaHei（引擎显式依赖，缺字体阻断） | |

## 隔离数据配置

- 测试隔离依赖 `checks/conftest.py` 在导入 `database` 前设置 `PPT_STUDIO_DB_PATH`、`PPT_STUDIO_RUNS_DIR`；pytest 一律经项目隔离配置运行。
- 真实运行数据：`data/projects.db`、`runs/` 存在且不纳入 Git；本轮全部测试走隔离目录，未写入真实数据。
- 应用端口 8010；数字人端点独立 9011（本轮未部署数字人服务，相关实测记 blocked）。

## 基线测试结果（区分既存状态）

执行命令（工作目录 `html_engine`）：

| 命令 | 结果 |
| --- | --- |
| `npm test`（E1 引擎） | 通过：29 单元用例、2 场景、像素可重复、资源/容量失败被阻断、几何验证通过 |
| `npm run test:e2`（配方层） | 通过：10 单元、3 场景 |
| `npm run test:course`（Token 课程） | 通过：9 单元、5 场景、25 关键帧 |
| `npm run test:visual`（共享视觉 V1） | 通过：12 项、2 场景、无页面错误（首跑曾因陈旧生成产物报断言差异，复跑两次稳定通过；已恢复被测试重写的证据截图） |
| `node visual/style-review/build.cjs` + `verify.cjs` | 技术检查通过；`user-visual-review-pending`（用户视觉审阅待做，属 AC04 范围） |

Python 侧迁移/失效/Agent 等基线将在发布前统一运行并记录（见验收 manifest）。

## 关键引擎现状（决定 A02–A04 起点）

- `html_engine/visual/`（V1 0.1.0）：共享 compiler/renderer/player/build，注册组件 `text/badge/label/image/arrow/annotation`，2 布局（object-left/right）、2 主题（soft-science/neutral-science）、2 实例。**用户已否定其简化视觉（changes_requested）**；技术结果保留。
- `html_engine/visual/style-review/`：按原参考补齐的科普风格实际样板（components.css、icons.cjs、content.cjs、sample.cjs），**尚未并入共享渲染器**——这正是 A02 的主体工作。
- `html_engine/visual/themes/`：已有 soft-science / neutral-science 主题包。
- `html_engine/effects/`：仅存 handdrawn 实验目录（历史证据，禁止风格，不进入生产注册）。
- E1/E2/Token 课程（`hps.e1.scene` 系）为独立旧格式，保留版本语义，不在本轮改写。

## 执行约定（本轮遵循）

1. 每项任务：实现 → 测试 → 证据 → 更新 `task-ledger.json` → 范围内提交。
2. 应用源码发布是独立变更：排除密钥、真实数据库、runs、缓存、依赖目录；不把遗留改动混入提交。
3. 视觉验收（AC04）留待用户审阅，状态记 `pending_review`；工程状态与视觉状态分开报告。
4. 只向 `origin` 发布；绝不触碰 `upstream`。
