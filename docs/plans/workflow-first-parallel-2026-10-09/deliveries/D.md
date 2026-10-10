# D 线交付：离线视觉目录与参考装配

记录时间：2026-10-10（Asia/Shanghai）
工作目录：`D:\software\PPT_HTML_Studio`
D 线起始基线：`bb6dbbebf55b8075e439f9c1a059ae5c74b0ff31`（`main`；开始时工作树干净）
关联范围：AC06、HPS-031—033；视觉边界按 HPS-035—037 执行。

## 状态

| 工作项 | 结果 | 证据与限制 |
|---|---|---|
| D01 身份、版本和状态 | 完成 | 目录从本地标准库、静态素材清单和当前运行注册表动态生成。历史问题留有来源、哈希和当前事实；不改写源库。 |
| D02 截图、源码与生产映射 | 完成 | 24 张分类页逐张核对 ID、manifest、源 HTML 哈希、PNG SHA-256 和 1920×1080 尺寸。候选运行节点明确标成候选，全部保留生产适配缺口。 |
| D03 可读分册与已有样例 | 已有产物入库；新增生产样页待审 | 提供分类页、三套调色参考和六张 B 样页变体的哈希固定副本。course-everyday 用户审阅仍待完成；纸飞机为 E1 探索/容量实验。没有把 C 的动效结果或未生成样页编入正式能力。 |
| D04 检索和本页相关项 | 完成 | 提供只读查询、任务关键词建议、分类筛选和详情记录；请求可只携带选中页面，不把整库送入提示。 |
| D05 缓存及附件校验 | 完成 | 缓存按选中定义/版本、选中图片、准确内容、样式、模式和理由计算；完整性及损坏/缺失图片失败关闭均有专项测试。 |

## 实际目录盘点

当前 checkout 的源计数为：24 张灰阶分类图、32 个基础/固定结构条目、16 个变体、28 个静态效果、18 个组合、5 个字体样张、3 套独立配色。32 个条目中包含固定关系/数据结构示例；这不代表存在通用图表或关系图引擎。

本次同时从现有生产定义中读取到 11 种节点、8 种注册效果、6 种布局、4 种模板和 4 种主题。早期工作流卡中的“生产 7 项 / 实验 61 项”与当前源码不符，目录没有沿用这些旧数字，也没有把静态参考条目伪装成已注册生产能力。

`html_engine/visual/catalog/catalog.json` 的静态参考集有独立 ID、版本、用途、参数范围、主题许可、实现状态、审核状态、结论、来源哈希和截图哈希。标准页与运行时条目分开；标准页到运行定义只提供候选语义链接，`directAdapter` 为 false。目录中的 `available` 只表示源定义存在，不表示用户已批准。

### 历史事项

- D01 交接提到 F01 渐变错引，但未提供原文件、字节或重现步骤。当前 F01 是 Noto Sans SC 字体样张，渐变效果是 E01—E04。记录为 `not-reproduced-from-current-source`，保留源文件 SHA-256，不推测性修复旧内容。
- B 线曾报告纸飞机标题在“同/一”之间换行。B 已调整该样页的字号和标题宽度并重导截图。目录记录此修订只适用于该样页，不扩大为生产排版容量结论。
- `sample:course-everyday` 仍为 `pending-review`；`sample:paper-plane` 为 `experimental`。两者用户美术审批均为 pending，且都不是 production template。

## 文件与目录

新增 D 专属实现：

- `html_engine/visual/catalog/`：来源映射、`neutral-style.json`、生产映射缺口、历史事项、样例请求、生成目录和示例离线包。
- `html_engine/tools/catalog-lib.cjs`、`catalog-build.cjs`、`catalog-query.cjs`、`catalog-assemble.cjs`：目录校验/生成、只读检索、确定性参考附件组装。
- `html_engine/tests/catalog-assembler.test.cjs`：8 个目录、请求、缓存和失效场景用例。
- `docs/assets/code-art-references/catalog-v1/`：便于阅读的源截图分册和版本清单。

标准库 HTML、组件/效果源文件、生产 schema/renderer/registry、B 线样页源码、C 线代码、应用/API/Agent 和公共总索引均未由 D 线修改。共享工作区中可见的 C 线 `html_audio_binder.py`、`checks/html_motion_v1/`、`html_engine/motion-research/` 以及 `docs/research/README.md` 并非 D 产物，均予以保留。

## 默认视觉与请求边界

没有显式选择时，组包使用 `neutral-baseline` 黑/灰/白描述，不附加彩色配色图。三套真实配色只有在 exploration/review 模式显式选择后才会作为独立资产附加。现有 `style-description.png` 含蓝色纸飞机，保留在实验条目下，不作为默认风格图。

请求将以下内容分开保存：准确标题/文字/关系、视觉指导、明确选择的分类截图，以及含来源、版本、理由、哈希、尺寸和 cache key 的 manifest。静态参考图中的示例文字只用于说明，并明确禁止照抄进内容。运行时 ID 不能用作截图附件；未登记 ID、未审样例误用、错误模式、缺失或 SHA 不符的素材均会返回稳定错误。

本地关键词规则最多建议三页，结果只是供核验的候选，不宣称语义模型匹配。没有显式引用时只按任务建议相关页；无命中则要求提供 ID。缓存身份不受未选中目录项变化影响，选中定义版本或图片变化会改变缓存键。

## 可复现证据

目录快照：`9e999fb743dabe48158bb2abd91138b15922cea2ff22cf354248f5c96cf4d3e3`。构建和 `--check` 均检查 41 个源/导出文件；`--check` 返回 `current`。截图整图解码通过，共解码标准页、文档副本和示例包中的 63 张 PNG。

离线示例包位于 `html_engine/visual/catalog/examples/water-cycle-package/`：5 个 ID 选择后合并为 4 张唯一截图，只含 8 个文件；默认调色中性，`provider.requestCreated=false`、`provider.callMade=false`。这是一份可审阅的请求素材包，不是发送给模型的请求。

| 示例附件 | SHA-256 |
|---|---|
| `attachments/classification/component-01.png` | `652b9b365c3a7544199a341dd72db1beeb4b55cd71cad5ef8cb0fd598ccb8d21` |
| `attachments/classification/component-02.png` | `ba4fa70c5a3d668058292bc1021e2a44d9869cc8db321fbd421d11ba3711730c` |
| `attachments/classification/component-03.png` | `310873ffc4465fdc9ccbfc51520ae84ed4776e6d2d877c40f2677cec20dbc4e5` |
| `attachments/classification/component-06.png` | `e237bf4200941c1deacf1da567c5dd4315a63c24b57bc1846de156bf8183b1fb` |

包 manifest SHA-256 为 `165bb35f2c8cd57db43f23de3e9b1c7aed3c6e8e6cff81dbd9ddc85c20a4e390`；cache key 为 `1348c0e8670da38f9f1e4af87f41d27b26cdbe15e7eec95805f4d3065f17ce09`。重复装配返回同 key 的 `cache-hit`。任务查询“水的状态变化过程与相反方向”只建议 component-02（箭头与连接）和 component-06（关系与组织），并标注需人工核对相关性。

验证命令及结果：

| 命令 | 结果 |
|---|---|
| `node html_engine/tools/catalog-build.cjs` | exit 0；41 个文件，目录 snapshot 与上表一致。 |
| `node html_engine/tools/catalog-build.cjs --check` | exit 0；`status: current`。 |
| `node --test html_engine/tests/catalog-assembler.test.cjs` | exit 0；8 passed，0 failed。覆盖清单/哈希、默认灰阶组包、任务建议、独立配色、非法/未审引用、缓存失效和坏图失败关闭。 |
| `.venv\Scripts\python.exe` 的 Pillow 全图解码脚本 | exit 0；63 PNG 解码。 |
| `git diff --check` | exit 0。 |

本轮未调用任何真实文本/图像供应商，也未启动应用服务。离线装配不能证明供应商接线或端到端生图。

## 交给 A 线的集成提案

D 模块提供离线装配边界，不接管生产任务、持久化、提示词、API 或 Agent。建议由 A 在其接线层接收 `task`、精确 `content`、显式 reference IDs/pages、可选 `paletteId`/`styleId`/`mode` 和每项 `rationale`，调用装配器并将经过哈希核验的 manifest/附件路径交给 E 线的供应商适配层。装配器只生成本地包，不发请求。

真实接线前，E 线需要确定 provider/model/version、endpoint 与凭证来源、图片数量/格式/大小限制、detail/resolution、timeout/retry/cost 与保留策略。真实验证需记录脱敏后的出站请求及附件 SHA、供应商 call/billing ID，确认响应并全量解码/哈希返回图像；禁止记录密钥。A 线还需决定如何把选择理由与包 manifest 纳入任务缓存和批准指纹。完成这些之前不应标记为应用集成或真实生图通过。
