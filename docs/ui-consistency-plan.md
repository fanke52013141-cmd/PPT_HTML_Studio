# 页面 UI 整体一致性优化方案（v2，经 subagent 评审修订）

> 历史规划：工作区 shell 的颜色、图标、按钮与几何规格以 `docs/ui-spec.md` 为准。本文冲突条款已被该规范取代，不能作为恢复旧样式的依据。

日期：2026-09-30。范围：仅布局与样式；**严禁修改功能**。基准：`docs/ui-spec.md`（工作区 shell 唯一规范，与其冲突时 ui-spec 优先）+ Stitch 设计稿（项目 `2320242300014903453`）。

> v2 变更：修正 P0-3 状态值（'confirmed'→'completed'）；按钮/卡片规格回归 ui-spec（30px/8px/保留 14px 图标、卡片 16/12 两级、描边 #e2e8f0）；补 JS 运行时文案同步清单；补 workspace_content.css 第二处覆盖；Step2 页签改 role="tab" 方案；重写 z-index 一节（stitch.css !important 压平是现行事实）；新增 Phase 0 与窄屏滚动机制；补守卫约束与「不做」清单。

## 0. 不改功能的硬边界（所有条目共同遵守）

1. **不改任何 `id` / `name` / `data-*`**（JS 全部按 id 绑定）。已知语义错位的 id（`#step2-btn-save` 实为批量删除）只加代码注释，不改名。唯一例外：P2-1 重复 id 修复。
2. **不改 API 路径、事件语义、显隐逻辑**。按钮文案可缩短，但必须保留完整词在 `title` 与 `aria-label` 里。
3. JS 文件只允许三类改动：**拼装 class、拼装展示文案（含 JS 模板串里的按钮 label/svg）、移动/删除无绑定的空包装 DOM 节点**。不新增/删除事件绑定（P2-1 除外）。
4. 不动 `storyboard.js:11-14` 的 `.btn-label` 文案协议（文案写 span、避免覆盖 SVG）。
5. 每阶段收尾跑：`node --check`（改动的 js）、`node checks/test_visible_flow.js`、`python checks/test_frontend_quality.js`，并在 **2560px 与 1280px** 双口径实测标题栏单行；用 `grep -o 'id="[^"]*"' static/index.html | sort | uniq -d` 输出为空证明零 id 变更。
6. 已核实：`checks/` 下无任何测试断言本方案要改的文案/id（grep 零命中），文案缩短无测试风险。

## 1. 统一基线（Phase 0 先行：stitch.css 末尾新增 "UI consistency layer"，全部选择器加 `body.workspace-open` 作用域；全局弹窗 token 改动须与 Stitch 首页层对齐后再动）

| 项 | 统一值 | 依据 / 现状冲突 |
| --- | --- | --- |
| 主橙 | `#EE5D36`（chrome）/ `#F46A38`（品牌） | 双 token `--workspace-chrome-*` vs `--content-*` 收敛为前者 |
| 侧栏 | 256px、8×40px 行、`#FFF5F0` 当前行 | style.css:4505（270px）/4537-4543（64px 四列）与 stitch.css:4379-4381（256px !important）并存；现行胜者为 stitch，删 style.css 败方规则 |
| 标题栏 | 59px 单行 `flex nowrap` + **工具组 `overflow-x:auto`（隐藏滚动条）** | ui-spec:25-27 窄屏单行强制；现有三种模式（--titlebar/--stacked/--tabs）+ Step3 无容器 |
| 标题栏按钮 | **30px 高、12px 字、8px 圆角、间距 8px、保留 14px 图标**（ui-spec:17/123-131；图标微动效规范 ui-spec:136-139 一并保留） | 原方案 28px/6px/去图标与 ui-spec 冲突，撤回；换行问题靠「缩文案 + overflow-x」解决 |
| 页签 | 文字胶囊「第 N 页」（含空格）、active 橙底白字、completed 绿色状态；**⠿ 拖拽把手与批量删除徽标仅 Step2**（ui-spec §5，Step4/Step6 页签不带） | 四种形式并存（见 §2） |
| 卡片 | **外层卡 16px / 子卡 12px 两级圆角**、1px `#e2e8f0`（--spec-line）、无硬阴影 | ui-spec:56-57/167/190；原方案 12px/#E2E3E7 平铺撤回 |
| 弹窗 | 圆角统一 **16px**（对齐 ui-spec 外层卡体系；Stitch 稿为 14px，此处取 spec 族内值并记录该偏差）、1px 边、按钮组右对齐（secondary/success/danger 三件套） | 现 16/20px 混用（stitch.css:499 vs style.css:12123） |
| 空态 | 统一类 `ws-empty`（虚线卡），并列追加到现有五处：step6-empty-state、step-audio-empty、mask-empty-state、step5-narration-empty、step2-empty-storyboard | 现五类各自命名 |
| 加载 | 统一 `.loading-spinner` + `ws-loading-card`（28px 橙色环 + 主/次文案） | 各步自制 |

## 2. P0 — 用户点名与最高优先

### P0-1 Step6 勾画标注：缩略图条 → 「第 N 页」文字页签（用户点名）
- `annotations_workspace.js:432-458 renderAnnotationThumbnails()`：`<img>` 换成 `<button class="annotation-page-tab{active}"><span class="page-label">第 N 页</span><span class="page-count">n</span></button>`；数量角标保留（0 隐藏）；点击仍调 `selectAnnotationPage(index)`（已核实按索引绑定、不依赖 img、无 onload 预热）；补 `aria-label="切换到第 N 页"`。
- 废弃 CSS 需删**两处**：`annotations.css:62-110` 的 `.annotation-thumb` 族 **和 `workspace_content.css:170-177` 的 108px 宽覆盖**（漏删则新页签被撑成 108px）。
- 行为附注：去 img 后每页少一次 `/slides/{id}/image` 请求（缓存预热消失），属预期。

### P0-2 页码文案全站统一「第 N 页」
- `mask_workspace.js:623`「第N页」→「第 N 页」；`narration_audio.js:249` 行头改「第 N 页」主 + `slide_id` 12px 灰色副文案。Step2 已合规不动；Step3 为卡片网格无页签，不适用。

### P0-3 Step4 页签补挂完成态（修正取值）
- `mask_workspace.js:618` 拼 class 加 `s.status === 'completed' ? ' completed' : ''`。
- **取值必须是 `'completed'`**（原稿 'confirmed' 全仓不存在）：确认流程 `mask_editor.js:1029-1031` 把全部页写 `"completed"`；前端兜底 `mask_workspace.js:588-597`（needsAdjustment→pending 否则 completed）；后端 `mask_manifest_service.py:443-444` 只写 `status or "pending"`。语义正确：未确认页保持 pending 不标绿。

### P0-4 标题栏单行化（拆两步走）
**4a 文案缩短 + JS 同步**（先行，低风险）：
- 缩短词：检查并补齐音频→**补齐音频**、强制重生成全部→**强制重生成**、确认并进入勾画标注→**确认进入勾画**、图片风格设置→**图片风格**、确认标注，进入下一步→**确认进入下一步**。完整词保留在 title/aria-label。
- **必须同步 JS 运行时模板**（只改 index.html 会被打回，均属「拼装展示文案」允许类）：
  - `narration_audio.js:511-513`（`#step6-audio-confirm-label` 动态写「进入勾画标注/确认并进入勾画标注」）
  - `mask_workspace.js:984`（`#step5-btn-confirm-next` innerHTML 整体重写）、`:959`（AI 语义分块 + svg）
  - `storyboard.js:993-1001`（`#step2-btn-save`「保存/批量删除」+ svg）
- Step5 两行工具条（index.html:448/461）合并一行：按钮搬入同一 toolbar；`#step7-loading` 与 `#step6-autosave-status` 随行保留、id 不动；删除空包装 div（`.step6-toolbar` 无任何绑定，已核实）。
- Step3 按钮补 `.workflow-toolbar` 包裹 div。

**4b 按钮规格统一**（依 Phase 0 token）：30px/8px 间距/14px 图标保留 + `.workflow-toolbar` 加 `overflow-x:auto`。
- 宽度口径：Step5 缩短后 8 按钮 ≈705px + spinner + autosave ≈900px，2K/1920 无压力，1280 贴边由 overflow-x 兜底（ui-spec:25-27）。
- **Step4 单行宽度必须计入运行时注入控件**：`ai_mask_extension.js:141-149` 注入「AI 标注设置」「运行 AI 标注」、`:257` 注入 preview-modes 控件。

### P0-5 Step8 错误卡片移出标题栏
- `#step8-error-box`（index.html:718-722）整体移到内容区顶部。id/显隐逻辑不动（output_render.js:310/371-374/518 全按 id）。移出后**顺手删除 style.css:6055-6059 的 `flex:1 0 100%`**（为 flex header 整行换行而设，失效）。附注：不再随 sticky header 吸顶，属预期。

### P0-6 Step7 标题去重
- 内部卡片标题（index.html:573「数字人讲解」）改「数字人配置」；顺带对齐第三处 `:583`「数字人讲解设置」措辞。

## 3. P1 — 弹窗与浮层统一

1. **按钮组容器归一**（CSS-only）：共享选择器组统一 `.modal-actions`/`.config-editor-actions`/`.settings-footer-actions`/`.creation-config-package-actions`/`.model-setup-actions` 及 `#modal-confirm` inline（改右对齐，danger 语义保留）。
2. **标题栏形态归一**：五种 header 形态 CSS 统一排版（标题左、辅助钮右、底部 1px 分隔线）。缺 × 的弹窗**不加 ×**（需新绑定，越界）；「关闭」文字按钮样式统一成 icon-button 视觉。
3. **圆角与遮罩**：全站弹窗 16px（token `--ws-modal-radius`，覆盖 stitch.css:499 的 20px 与 style.css:12123 的 16px）；遮罩统一 `rgba(0,0,0,.45)` —— 仅限 workspace 作用域；**首页也用的全局弹窗（modal-create/settings 等）遮罩保持 Stitch 层现状（rgba(15,23,42,.34)+blur）**，如需统一先与 Stitch parity 对齐立项。
4. **inline 样式清理**：modal-create / modal-edit-project 的 inline label/select/按钮组 style 换 `.form-field`/`.modal-actions`。
5. **z-index 收敛（重写）**：现行事实是 `stitch.css:490` 的 `.modal-overlay{z-index:100 !important}` 压平了 style.css:694（1000）、`#modal-confirm`（1100，无 !important 故失效）与 images.js:477 的内联 1200——**实际按 DOM 顺序堆叠**，`#modal-confirm`（index.html:1383）可能被 DOM 靠后的业务弹窗遮挡（潜在真 bug）。收敛动作：删 stitch.css:490 的 !important，在 consistency layer 一处定义层级表（遮罩 1000 / confirm 1100 / 账号·恢复类 1200），删 images.js:477 内联改 class。
6. **Toast**：仅 CSS 冲突清理（stitch.css 内 999px 与 12px 双 `!important` 圆角、三段宽度规则收敛为一段）。**守卫约束：必须保留 stitch.css 的 `left: 50% !important` 与 `transform: translateX(-50%)`（test_frontend_quality.js:91-93 断言）及 style.css 的 `#toast-container` 选择器（:69）**。保持仅渲染 error 的行为（test_frontend_quality.js:49-53 守卫）。

## 4. P1 — Shell 与状态组件

1. 侧栏：删 style.css:4505/4537-4543 败方规则，锁定 256px/40px 行/图例行。
2. 空态 `.ws-empty` / 加载 `.ws-loading-card` 追加并列 class（只加 class）。
3. 可访问性：**Step6 新页签用原生 button**（无嵌套按钮，合法）；**Step2 页签不做 div→button**（storyboard.js:751-757 页签内嵌删除 button，button-in-button 非法 HTML），改为 `div + role="tab" + tabindex="0"` + 键盘激活 + aria-label；Step4 保持现状。

## 5. P2 — 低风险清理

1. `#dh-slide-status` 重复 id（index.html:621/683，全文件唯一重复）：**:621（整段视频状态卡，digital_human_panel.js:638 在用）保留原名**；**:683 改新 id（如 `dh-generate-status`），同步重定向 `:762/:772` 两处引用。同时在 `checks/test_frontend_quality.js` 新增「index.html id 唯一」守卫。
2. Step5 面板 `step6-*`/`step7-*` 前缀混用：仅注释标记。
3. CSS 收敛：改动全部进 stitch.css "UI consistency layer"；style.css 冻结（只删不改）；`workspace_content.css` 的 `--content-*` 换引用 `--workspace-chrome-*`。

## 6. 实施顺序与验证

| 阶段 | 内容 | 验证 |
| --- | --- | --- |
| **0** | token 层（consistency layer + 作用域策略） | 双口径(2560/1280)无回归 |
| 1 | P0-1/2/3（页签族统一） | node --check 3 个 js；Step4/Step6 页签并排比对 |
| 2a | P0-4a 文案缩短 + JS 模板同步 | grep id 清单 diff 为空；1280/2560 单行 |
| 2b | P0-4b 按钮规格 + overflow-x；P0-5/6 | 同上 + Step4 注入按钮计入 |
| 3 | P1 弹窗层（含 z-index 真修复） | 逐个打开 16+9 弹窗截图；confirm 不被遮挡 |
| 4 | P1 shell/状态 + P2 | test_visible_flow / test_frontend_quality 全绿 |

## 7. 明确不做

- 不改 Step1 标题「准备文章」与侧栏「导入文章」差异（ui-spec 有意为之）。
- 不动 Toast error-only 行为；不增删任何按钮（× 不加）。
- 不动 `.btn-label` 文案协议（storyboard.js:11-14）。
- 不引入 dark/打印模式（全仓无 prefers-color-scheme/@media print）。
- 不为 Step6 复刻 Step4 的 `syncStep5FullscreenThumbs` 全屏搬移（Step6 无全屏态）。
- 顶栏 56px（ui-spec:16）本轮不动；Step3 卡片网格形态保留（页签族只约束页级导航）。
- 全局弹窗遮罩统一暂不做（见 P1-3 限制条件）。
