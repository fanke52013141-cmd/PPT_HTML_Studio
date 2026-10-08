# 共享视觉定义 0.2.0 版本卡（A01）

状态：实现完成（工程验证通过）；视觉验收 `pending_review`（AC04 待用户审阅）。
本卡是 `html_engine/visual/` 运行时 0.2.0 的归属定义，细化 HPS-001—005、007、
013、023—030、033—037。0.1.0 定义卡的公共/风格/实例/派生归属不变，本卡只记录
增量、兼容与执行状态。

## 版本与兼容

| 项 | 0.1.0 | 0.2.0 |
| --- | --- | --- |
| scene/theme/layout `version` | 0.1.0 | 0.2.0 |
| 节点类型 | text/badge/label/image/arrow/annotation | 上述全部 + header/card/figure/summary |
| theme 可选扩展 | — | colors.paper/purple/yellow/pink；gradients（五色对）；text.headline/intro/cardTitle/cardBody/caption/summary；shapes.cardRadius/figureRadius/iconRadius/iconStroke/shadowRGB |
| 模板层 | 无 | `hps.visual.template` 0.1.0（templateRef 可选引用） |
| 效果层 | 无 | `visual/effects/registry.json`（7 个已注册效果，backend=CSS/SVG） |
| 兼容策略 | — | 0.1.0 场景文档经编译器显式适配器升版读取（`fixtures/legacy-0.1.0/` 为验证夹具）；theme/layout 注册表升版 0.2.0，字段为 0.1.0 严格超集 |

适配器只改 `version` 与 theme/layout 引用版本，不改内容字段；适配事实记录在
编译快照 `adaptedFrom`。未知版本拒绝（`UNSUPPORTED_VERSION`）。

## 新增公共能力（组件消费主题参数，不含课程内容）

主题增量：2026-10-08 登记 `amber-science@0.2.0`，按既有外观字段复用公共能力，不改变本格式或原主题；定义、兼容与 Token 单页限定批准见[主题卡](../../../../styles/science-explainer/amber-science.md)。构建与实际测试结果单独记录，注册不等于全部结构已获视觉批准。

- `header`：页码+标题+分隔线；number≤4 字符、title≤40 字符；标题单行。
- `card`：知识卡=渐变图标气泡+标题+正文；tone 五色、icon 必须是注册图标
  （`UNKNOWN_ICON` 拒绝）；title≤40、body≤120；标题单行、正文按槽位行数。
- `figure`：插图容器=渐变面板+光环+可选 tag/note（各含注册图标与文本）。
- `summary`：关系条=可选 heading+from/to 状态胶囊+箭头+术语+takeaway；
  各字段长度受 Schema 限制；复合行用溢出检查，不做行计数。

图标注册表 `visual/icons.cjs` 是唯一图标来源；`icons.browser.cjs` 仅负责绘制。
字幕安全区、资产预算（单主体）、annotation 语义（target 必须 image、标签必须
text、圈心不越内容区）沿用 0.1.0，未放宽。

## 模板层（受约束结构，A03）

模板 = `结构 structure + layoutRef + 槽位规则（kinds/required）`。编译时校验：
未声明槽位、类型不符（`TEMPLATE_SLOT_KIND`）、必填缺失
（`TEMPLATE_SLOT_REQUIRED`）、布局不匹配（`TEMPLATE_LAYOUT_MISMATCH`）。
已注册三个结构：

| 模板 | 结构 | 布局 | 用途 |
| --- | --- | --- | --- |
| explanation-cards-v1 | explanation-cards | science-explanation-v1 | 图文讲解（header+headline+三卡+figure+主体+标注+关系条） |
| data-relation-v1 | data-relation | data-relation-v1 | 数据/关系说明（三数据位+说明+关系条，无图片资产） |
| process-stage-v1 | process-stage | process-stage-v1 | 对象过程舞台（单主体+箭头+条件徽章+标注+关系条） |

左右互换不算不同结构。左右换位/换色不改变对象 ID、讲稿语义与时间绑定（AC02）。
过长内容在编译/测量阶段失败并给对象诊断，不自动缩字号（AC03）。

## 效果注册与参考图缓存（A03/AC06）

`visual/effects/registry.json` 登记每个效果的 ID、backend、用途、参数来源、
使用组件。场景与模型输出不得引用未注册效果。`visual/tools/effect-cache.cjs`
以 sha256(theme@version + layout + 效果集 + 字体 + 渲染器 bundle) 为键渲染
参考图到 `visual/effects/cache/`；输入不变时第二次运行命中缓存、不生成新图
（实测 miss→hit）；任一输入版本变化产生新键并清理旧条目。

## 播放器接口与导出 harness（A04/AC05）

- `window.visualPlayer`：apply/play/pause/seek/setSubtitleFont/timeMs/ready/
  scene。`renderAt(ms)` 为唯一求值路径：无 Date.now、无自运行时钟、动画只由
  t 与固定输入决定；字体/资产就绪失败必须阻断，不留空白画面。
- `visual/tools/export-frames.cjs`：预览与导出共用同一 `preview/player.js`
  bundle；manifest 记录 bundle sha256、theme/layout/template、fps、逐帧哈希；
  逐帧 `seek(i/fps)`。重复乱序 seek 像素一致由 `visual/tests/verify.cjs`
  持续验证（13 项检查含 4 场景、3 结构、2 主题、容量、恶意文本、适配器、
  模板拒绝、哈希阻断、播放暂停、字幕区）。

## visual_backend 设计（B01 实施依据，尚未实现）

`visual_backend: image | html` 为项目级字段，与 `production_mode`、
`presentation_mode` 正交。首发约束：HTML 后端仅 guided 模式 + 16:9；不支持的
组合显式拒绝。旧项目回填 `image`，已有作品禁止切换后端。该字段的迁移、Agent
同步与失效规则在 B01/B02 落地，本卡仅固定设计口径。

## 验收状态

| AC | 状态 | 证据 |
| --- | --- | --- |
| AC02 公共/风格分离 | passed（工程） | verify 主题切换几何/测量不变；renderer 无课程名/色值分支 |
| AC03 布局覆盖与容量 | passed（工程，3 结构） | 4 场景截图 + 容量失败诊断；真实课程五场景待 C01 |
| AC04 视觉验收 | pending_review | `visual/evidence/*-final.png` 待用户对照 `user-style-reference.png` 审阅 |
| AC05 时间与运行时一致 | passed（工程） | 乱序 seek 像素一致；export-frames 逐帧 seek |
| AC06 效果图缓存 | passed（工程） | effect-cache miss→hit 记录 |
