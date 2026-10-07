# AI Mask 精准度优化方案

日期：2026-09-27
前置调研：`docs/RESEARCH_2026-09-27_ai_mask_accuracy.md`（痛点根因与开源选型）
目标：在不推翻现有管线、不引入硬性重依赖的前提下，系统性提升 AI Mask 的拆分精度与匹配精度，并解除"纯白底"限制。

---

## 0. 方案总览

### 0.1 依据（来自调研的三条事实）

1. **像素层已达标，损失集中在检测召回与归属层**：16 图离线集 ink_recall 0.9697、跨组重叠 0，但 group recall 仅 0.63–0.73；w7 基准最差项为 pale_recall 0.03–0.53（浅色）、IoU 0.323（2–8px 间隙）、0.161（嵌套容器）。
2. **白底是第一性假设**：`white_threshold=245 / color_tolerance=12` 的绝对白色判定（`ai_mask_component_detection.py:969`）使任何非纯白底在 flood fill 第一步即失效。
3. **代码已预留接缝**：检测器按 payload 契约 + row_runs_v1 RLE 输出，下游（归属图/语义对象/质量门/reveal builder）零改动即可换检测臂；`fine_grained_detection` 开关 + 独立缓存版本号是现成先例。

### 0.2 阶段与工作包

| 阶段 | 工作包 | 内容 | 新依赖 | 优先级 |
| --- | --- | --- | --- | --- |
| Phase 0 | WP0 | 真实业务评测集（≥30 页）+ 基线冻结 | 无 | **必须先行** |
| Phase 1 | WP1 | 检测层背景色自适应（解非白底） | 无 | P0 |
| Phase 1 | WP2 | 浅色召回（pale ink 支持） | 无 | P0 |
| Phase 1 | WP3 | 粘连切分（细粒度 A/B + 桥接带证据切分） | 无 | P0 |
| Phase 1 | WP4 | 嵌套容器感知切分 | 无 | P0 |
| Phase 1 | WP5 | 软阴影策略显式化 | 无 | P1 |
| Phase 2 | WP6 | grounding 型匹配协议 v5 | 无（走现有 VL API） | P0 |
| Phase 2 | WP7 | 置信度校准 + 组级重试 + 切片上下文 | 无 | P1 |
| Phase 2 | WP8 | VL 匹配结果缓存 | 无 | P2 |
| Phase 3 | WP9 | 上传图白底规范化 | 可选 onnxruntime+模型 | P1 |
| Phase 3 | WP10 | 生成图白底兜底校验 | 无 | P1 |
| Phase 4 | WP11 | BiRefNet-lite 显著性兜底臂（可选） | 可选 onnxruntime+模型 | 视证据 |
| Phase 4 | WP12 | SAM box-prompt 边界精修（可选） | 可选 onnxruntime+模型 | 视证据 |

### 0.3 量化验收总目标（以 Phase 0 基准集衡量）

| 指标 | 现状 | 目标 |
| --- | --- | --- |
| pale_recall（浅色内容） | 0.03–0.53 | ≥ 0.90 |
| 2–8px 间隙案例 macro IoU | 0.323 | ≥ 0.80 |
| 嵌套容器案例 macro IoU | 0.161 | ≥ 0.70 |
| 16 图离线集 group recall | 0.7316 | ≥ 0.80 |
| 16 图离线集 ownership IoU | 0.6843 | ≥ 0.75 |
| 30 页新基准 group recall | 待 Phase 0 测定 | ≥ 基线 + 0.10 |
| 三道像素门（0.995 覆盖/零未分配/零重叠） | 全过 | **全过（红线，不许退）** |
| 阶段 D 端到端盲测 11 页 | 11/11 | 11/11 不回退 |

### 0.4 明确不做（Non-goals）

- 不换掉整条管线、不重写为"重建式"（OCR→矢量→重排会丢位图还原度，与 Reveal 动画冲突）。
- 不引入 torch 硬依赖；一切 NN 能力走 `ai_mask_doclayout.py` 式可选依赖 + 缺模型降级。
- 不全局调 `closing_radius`（T4 红线：半径 2 会把 case_01 切成 7 块、case_09 切到 25 块）。
- 不提交 `runs/**`、`outputs/**` 大体积产物；基准 fixture 与冻结指标走 `checks/`。

---

## 1. Phase 0：评测基准扩充（WP0，一切改动的前置）

**为什么先做**：handoff §6 T6 本就是未完成项；没有基准的算法更换违反 §10 红线"不许用漏像素换速度"。且 WP3 的 A/B（`--fine-grained`）不写一行代码就能跑，应与建集并行。

### 1.1 建集（WP0.1）

- **来源**：从 `runs/` 挑 ≥30 页真实项目页，覆盖配额——非白底/浅色底 ≥5 页、异形/镂空图形 ≥5 页、嵌套卡片 ≥5 页、密集文本 ≥5 页、常规页 ≥10 页。
- **真值格式**：直接复用现有手动掩码编辑器产出 `manual_mask.rle`（row_runs_v1）作为 ground truth——真值格式与生产格式天然一致，零新工具。
- **组织**：沿用 `checks/ai_mask_benchmark/` 既有 bundle 机制（`project_fixture.py`、`freeze_baseline.py`）；fixture 与冻结期望指标提交进 `checks/`，渲染出的报告留在临时目录不提交。
- **双臂基线**：default 与 `--fine-grained` 各跑一遍并冻结，作为 WP3 决策依据（runner 已支持 `--fine-grained`、`--layout on/off`、`--settings-json`，`checks/ai_mask_benchmark/runner.py:428-430`）。

### 1.2 指标与门（WP0.2）

沿用既有口径：macro IoU、coverage、pale_recall、overlap、group recall、ownership IoU。新增两个过程指标：`rejected_id_rate`（模型编造 id 比率，服务 WP6 验收）、`fallback_group_ratio`（规则兜底占比，服务 WP7）。

**工作量**：3–5 人日（主要是标注）。
**产出**：`checks/ai_mask_benchmark/` 下新 bundle + 冻结基线 + 一条 README 说明如何复跑。

---

## 2. Phase 1：确定性检测增强（零新依赖）

所有新设置项统一落点（四处，缺一不可）：

1. `ai_mask_engine.py:39-70` `DEFAULT_SETTINGS` 增加键与默认值；
2. `ai_mask_component_detection.py:909-926` 检测设置指纹清单加入新键（否则改设置不触发重检测）；
3. `static/ai_mask_extension.js` 设置表单加字段（参照 `white_threshold` 的 label/type/min/max 写法，`static/ai_mask_extension.js:7-15`）；
4. 若该设置对 Agent API 可见：按 AGENTS.md Agent Contract 表登记 parity 映射并 bump 能力版本。

缓存版本策略：Phase 1 合入时统一把默认路径版本串从 `auto_elements_v5_box_label_only`（`ai_mask_component_detection.py:27`）bump 到 `auto_elements_v6_*`；新设置入指纹后旧缓存自然 miss，无需数据迁移（`auto_elements.json` 重算即可）。

### 2.1 WP1 背景色自适应（解"非白底"）

**现状锚点**：白色判定 `white = (lo >= 245) & (hi - lo <= 12)`（`ai_mask_component_detection.py:969`）；垫边纯白（:957-964）；flood fill 从四边 seed（:978-995）。

**改动**：新设置 `background_mode`（`"white" | "auto"`，默认 `"white"` 即现状行为）。`auto` 模式下：

1. **背景估计**（垫边前）：采样四边各 3% 宽的 border 带（每边 ≥2000 采样点，均匀下采样），逐通道取中位数得 `bg_color`；逐通道中位绝对差得 `bg_mad`（纹理强度）。
2. **相对白色判定**：`is_background = 通道最大距离(pixel, bg_color) <= max(color_tolerance, bg_mad * k)`（k=2 起步）。判定从"绝对白"变为"与估计背景足够近"，浅灰/米色/轻纹理底直接成立。
3. **垫边颜色**：从纯白改为 `bg_color`（保证 flood fill 种子连通）。
4. **渐变保护**：若 border 带 `bg_mad` 超阈值（渐变/强纹理），不硬拆，产出 review issue `gradient_background_detected` 路由人工复核——与现有 review 机制（`ai_mask_manifest_apply.py:112-146`）一致。
5. **诊断透出**：估计出的 `bg_color`/`bg_mad` 写入 `auto_elements.json` payload，并入 VL 请求元数据。

**语义不变项**："封闭白保留"契约不变——相对背景的连通性判定天然继承该语义（AGENTS.md "White areas enclosed by content are preserved"）。

**测试**（新增 `checks/test_ai_mask_adaptive_background.py`）：合成浅灰底(235)、米色(通道差 20)、轻噪纹理底各一例，断言不再整幅判前景、组件数在期望区间；`white` 模式全量回归不变；改 `background_mode` 击穿缓存（仿 `checks/test_ai_mask_fine_grained_detection.py:218` 的写法）。

**风险与回滚**：设置默认 `white`，一键回滚；auto 误估（图片边缘贴满内容）时 border 带被内容污染 → 采样前先剔除与带内众数距离 >3×MAD 的离群像素。

**工作量**：2–3 人日。

### 2.2 WP2 浅色召回（pale ink 支持）

**现状锚点**：pale 层判定 `pale = white & (lo < 254)` 与波前归属 `_wavefront_fill_region` 已存在但只在默认关闭的细粒度路径生效（`ai_mask_component_detection.py:279-316, :382, :405`）；raw pair 机制（`ai_mask_contracts.py:26-73`）只救抠图阶段的浅色，检测层浅色元素仍整体判背景——这是 pale_recall 0.03–0.53 的直接原因。

**改动**：新设置 `pale_ink_support`（bool，默认 True）。默认 v5 路径中，当 raw pair 有效（`resolve_mask_source_master` 命中）时：

1. 构造 pale 层：`is_background 判定为白 && lo < pale_support_threshold(254)` 的像素；
2. 受限波前归属：pale 像素并入 8 连通接触或距离 ≤2px 的墨水组件——写入 `mask_rle`（掩码变宽）但不写入 `source_ink_rle`（墨水证据不变，人工修正保护与溯源语义不受影响）；
3. 归属门槛：组件侧墨水面积必须 ≥ `min_element_area`，防止把背景噪点吸进组件；
4. 独立 pale 岛（无相邻墨水、面积达标，如整块浅色板）独立成组件。

实现上把 `_wavefront_fill_region` 与 pale 判定从细粒度路径抽出共用（模块内私有函数重组，不违反 AGENTS.md 边界——检测实现仍全在 `ai_mask_component_detection.py`）。

**测试**（新增 `checks/test_ai_mask_pale_support.py`）：05_pale 合成案例 pale_recall ≥0.90；纯白图 pale 层为空集（零行为变化断言）；raw pair 失效（marker 不匹配）时自动退回现状路径。

**风险**：pale 附属吞浅色阴影 → 与 WP5 联动（阴影策略优先级高于 pale 吸附）。

**工作量**：2 人日。

### 2.3 WP3 粘连切分

**第一步：零代码 A/B（本周即可跑）**——用 Phase 0 基准跑三臂：default / `--fine-grained` / `--fine-grained --layout on`。判定：若细粒度臂在 02/03（间隙）、10_dense（密集）改善且 case_01/09（T4 记录的易碎案例）不劣化，则走"启用既有检测器"路线，把 `fine_grained_detection` 默认值决策落到数据上（handoff §6 遗留的两个默认值决策之一）。

**第二步：桥接带证据切分**（若细粒度全局不优）：新设置 `bridge_split_mode`（`"off" | "auto"`，默认 `auto`）。对 `bridge_pixel_count > 0` 的组件（闭运算桥接记录于 `ai_mask_component_detection.py:1116`）：

1. 桥接带 = `grouping_mask 有 && ink_foreground 无` 的像素；
2. 在桥接带上做距离变换，取谷点候选切缝；
3. **保守双门槛**：切缝两侧墨水投影必须呈双峰，且切后子件各自墨水面积 ≥ `min_element_area`，否则不切；
4. 产出 `split_evidence` 记录进 payload（切了几刀、依据），供复核。

**红线遵守**：不改全局 `closing_radius`；切分是"证据驱动的事后拆"，闭运算仍负责连通性假设。

**测试**（新增 `checks/test_ai_mask_bridge_split.py`）：02/03 IoU ≥0.80；case_01 仍 1 件、case_09 组件数不变（防过拆回归，用 Phase 0 冻结基线断言）；10_dense 以 30 页集 macro IoU 不退化为线。

**工作量**：A/B 1 人日 + 实现切分 3–4 人日。

### 2.4 WP4 嵌套容器感知切分

**现状锚点**：case_06_nested IoU 0.161（单案例最差）；版面框嵌套比 `BOX_NESTING_RATIO=0.9` 已有（`ai_mask_object_graph.py:18-33`）；handoff T4 待办"容器感知切分"。

**改动**：新设置 `container_split_enabled`（默认 True，依赖 doclayout 框可用；doclayout 降级时自动 no-op）。对"单组件 bbox 同时覆盖某版面框外沿、且内部含 ≥2 个子框或墨岛"的情形：

1. 容器自身 mask = 外框 bbox 环带（外沿到内缩环宽，环宽取框线墨水厚度估计）；
2. 内部墨岛按现有连通域逻辑归子组件；
3. payload 新增 `container_children` 父子关系；归属图与语义对象（matcher 的 `container_or_illustration` 岛吸收逻辑，`ai_mask_semantic_matcher.py:87-134`）天然兼容——元素粒度变细，吸收规则不变；
4. 动画语义：语义组既可绑容器整体（整卡 reveal）也可绑子件，由匹配层决定，检测层只负责可分。

**测试**（新增 `checks/test_ai_mask_container_split.py`）：case_06 IoU ≥0.70、越界像素 < 1e5；doclayout 关闭时行为与现状完全一致。

**工作量**：3–4 人日。

### 2.5 WP5 软阴影策略显式化（含决策点 D1）

**现状**：无阴影判别逻辑——阴影像素深于阈值随主体熔合（可接受）、浅于阈值被洗掉（光晕丢失，11_halo_lines coverage 0.9614 的来源）。

**改动**：新设置 `shadow_policy`（`"attach" | "strip"`，默认 `attach` = 显式化现状）。

- `attach`：维持现状 + WP2 的 pale 吸附把浅阴影环带并入主体（阴影随主体 reveal，视觉自然）。
- `strip`：组件外围 ≤4px、低饱和、亮度低于背景估计（WP1 的 `bg_color`）的环带判背景。

**决策点 D1（需拍板）**：推荐 `attach`（真人播 PPT 时阴影随卡片动更自然，且零风险）。

**测试**：合成带软阴影卡片两态期望输出各自冻结进 Phase 0 bundle。

**工作量**：1–2 人日。

---

## 3. Phase 2：匹配升级

### 3.1 WP6 grounding 型匹配协议 v5（本阶段主攻）

**现状锚点**：每请求 = 1 张全图 + N 张带 id 切片（`_request_object_batch`，`ai_mask_semantic_matcher.py:747-822`）；模型只返回 id 列表（engine prompt v4，`ai_mask_engine.py:155-321`）；幻觉面 = 跨图对齐 id，`rejected_group_ids/rejected_object_ids` 即其代价（`_merge_batch_results` :469-637）；整页失败即放弃 VL（engine :941-944）。

**改动**：新设置 `matching_protocol`（`"id_v4"` 默认 | `"grounding_v5"`）。`grounding_v5` 协议：

1. **请求**：单张完整原图（≤1280px，不再发 N 张切片——省 token，消除 id 对齐幻觉面）+ `visual_groups`/`narration_beats` 元数据。
2. **输出**：模型对每个 group 直接返回 `region: {x, y, w, h}`（归一化 0–1000 坐标）+ `confidence` + 可选 `reason`。
3. **确定性对齐（代码侧，不让模型做）**：region → 语义对象集合（对象中心点入框，或 bbox IoU ≥0.5）；复用 `_clean_match` 白名单过滤与 `_merge_match_results` 合并（`ai_mask_assignment.py:163-255`）；对齐为空的 group 回退：先按 id_v4 对该组单独补问一次，仍空则几何 fallback。
4. **解析防御**：Qwen 系模型有"归一化 vs 绝对像素"两种坐标习惯——解析层双格式兼容并统一归一（这是已知的真实坑，必须测）。
5. **能力探测**：走 `step2_llm_vendor_options` 声明当前 vision 模型是否支持 grounding；不支持时 `grounding_v5` 自动降级 `id_v4` 并记 warning，不硬失败。
6. **Prompt 流程（强制）**：按 AGENTS.md Prompt Optimization Policy，先走 `.agents/skills/optimize-prompts/SKILL.md` 全流程——trace 真实 payload/输出解析/fallback/下游消费者；坐标展开、对象对齐、排序全部在代码做，模型只输出它看得见的区域判断。Prompt 版本 `ai_mask_semantic_mapping_v5`；`ai_mask_config.py:53` 的迁移语义保证只迁内置默认、不动用户自定义。
7. **几何后处理与门不变**：标题固化/稀疏框改绑/锚点保底/补全、溯源门、复核路由全部保留。

**A/B**：runner 支持 `--vision-model/--settings-json`（`checks/ai_mask_benchmark/runner.py:433-442`），30 页集上 `id_v4` vs `grounding_v5` 双臂，验收 `rejected_id_rate`（应趋零）与 group recall。

**测试**（新增 `checks/test_ai_mask_grounding_protocol.py`）：region 双格式解析、越界/非数值清洗、对齐为空回退链、不支持 grounding 的 provider 降级。

**工作量**：4–5 人日（含 optimize-prompts 流程）。

### 3.2 WP7 置信度校准 + 组级重试 + 切片上下文

1. **校准**：Phase 0 基准上统计模型自报 confidence 与真值归属的一致率，输出分段可靠度表；据此校 `llm_confidence_threshold`（当前 0.72 是未经校准的经验值）。
2. **组级重试**：engine :941-944 的整页放弃改为"失败组重问一次，仍失败才 fallback"；重试计入 `vision_max_requests` 预算，不放大成本。
3. **切片上下文**（id_v4 协议下的低成本改进）：`_crop_object_bytes` 切片角落加 ≤160px 全图缩略（灰度 + bbox 红框标注），缓解"只看局部猜不对组"。

**工作量**：2 人日。

### 3.3 WP8 VL 匹配缓存（低优先）

键 =（slide 图 sha256，检测设置指纹，visual_groups/narration_beats 结构哈希）；命中跳过 VL 请求。重标注同图时当前是全量重问，此改动直接降本。键语义与检测缓存（`ai_mask_component_detection.py:939-954`）对齐。

**工作量**：1–2 人日。

---

## 4. Phase 3：上游白底规范化

### 4.1 WP9 上传图白底规范化（非白底的最后一环）

**现状锚点**：上传路径已有字幕安全区白度检查 `enforce_white_image_region`（`image_workflow_service.py:339-365`，`nonwhite_ratio > 0.005` 即报）；生成图入库时已做洗白 + raw pair 封存（`ai_provider_service.py:374` 调 `normalize_connected_background`）。

**改动**：新设置 `upload_background_normalization`（`"off" | "prompt" | "auto"`，默认 `"prompt"`）。

1. 上传入库时四角 + 四边带采样判背景非白（阈值与 WP1 共用一套估计函数，抽到公共位置）；
2. 非白时：可选依赖抠前景（rembg/BiRefNet-lite ONNX，集成模式完全仿 `ai_mask_doclayout.py:12-23`：零硬依赖、模型缺失降级）→ 合成到纯白 1920×1080 画布 → 洗白 + raw pair 封存（**raw 保留原始非白底图，永远可回溯**）；
3. `"prompt"` 模式给用户对比预览 + 一键规范化确认；`"auto"` 直接处理；
4. 无 onnxruntime/模型时降级为仅提示，**不阻断上传**。

**冗余防线设计**：WP1（检测层自适应）与 WP9（上游转化）互为兜底——上传规范化失败（PNG 透明通道、极端底）时由 WP1 auto 模式接住。

**测试**（新增 `checks/test_upload_background_normalization.py`）：米色底上传 → 规范化后 master 四边纯白、raw pair 有效、AI Mask 白底模式正常出件；模型缺失降级路径。

**工作量**：3–4 人日。

### 4.2 WP10 生成图白底兜底校验

生成入库（`ai_provider_service.py` 归一化处）增加 border 带非白率检查：超阈值记项目日志 + review 提示。生成 Prompt 合同已是纯白外底，这里只做兜底断言，不自动重生（避免 API 成本浪费）。

**工作量**：1 人日。

---

## 5. Phase 4：NN 兜底臂（可选，凭证据立项）

**立项条件**：Phase 1 合入后，若 Phase 0 基准仍存在确定性路径无法覆盖的场景（渐变底、极端纹理底、毛发级异形边缘），才启动。先跑证据，再写代码。

### 5.1 WP11 BiRefNet-lite 显著性兜底臂

- 新模块 `ai_mask_neural_detection.py`，完全仿 DocLayout 模式：零硬依赖、`available()` 探测、模型文件缺失/会话失败自动降级、LRU 会话、懒加载用完释放（W5 内存红线：`_connected_sets`/`_build_atom` 在 <3GB 可用内存曾 MemoryError，NN 会话按同标准评估）。
- 触发：仅当 WP1 判 `bg_mad` 超阈值（渐变/纹理底）时启用；alpha → 阈值化 → 连通域 → 与确定性组件投票融合；任一步失败回退确定性结果。
- 模型：BiRefNet-lite ONNX（MIT，约 224MB，CPU 数秒/页）。**避开 BRIA RMBG 系（非商用许可）。**
- 产出仍是 row_runs_v1 payload，下游零改动。

### 5.2 WP12 SAM box-prompt 边界精修

- 对每个确定性组件 bbox 做 box prompt（MobileSAM ONNX，编码器一次 + 逐框解码，CPU 可行；有 GPU 可换 HQ-SAM）。
- **只精修边界、不重新发现元素**——SAM 的失败模式（粘连元素合成一个掩码）不会引入新拆分错误。
- 精修掩码与现有 RLE 做一致性校验（三道像素门照常把关），通过才替换 `mask_rle`；`source_ink_rle` 证据链不动。

**工作量**：视证据 1–2 周。

---

## 6. 实施顺序与依赖

```
WP0 建集与基线冻结（先行，3-5天）
 ├──→ WP3 第一步 A/B（零代码，与 WP0 并行）
 ├──→ WP1 背景自适应（2-3天）─┐
 ├──→ WP2 浅色召回（2天）─────┤ Phase 1（约 2-3 周）
 ├──→ WP4 嵌套切分（3-4天）───┤
 └──→ WP5 阴影策略（1-2天，含 D1 决策）
        │
        ├──→ WP6 grounding 匹配（4-5天）─┐ Phase 2（约 1.5 周）
        └──→ WP7 校准与重试（2天）───────┘
                 │
                 ├──→ WP9 上传规范化（3-4天）─┐ Phase 3（约 1 周）
                 └──→ WP10 生成校验（1天）────┘
                          │
                          └──→ Phase 4 立项评审（凭 Phase 0/1 复测证据决定 WP11/WP12）
```

理由：Phase 1 全部是确定性小改动、直接命中量化最差项且互不阻塞；WP6 复用现有远程 VL 通道零部署负担、收益/成本比最高；NN 臂放最后，用基准先证明确定性天花板。

## 7. 决策点清单（需产品/用户拍板）

| 编号 | 决策 | 推荐 | 影响 |
| --- | --- | --- | --- |
| D1 | 软阴影随主体 reveal（attach）还是剥离（strip） | attach | WP5 默认值 |
| D2 | 上传规范化默认 `prompt`（确认后处理）还是 `auto` | prompt（首版更稳） | WP9 默认值 |
| D3 | grounding_v5 需要的 vision 模型：当前配置的模型是否为 Qwen 系/支持 grounding | 先探测再定 | WP6 降级策略 |
| D4 | `fine_grained_detection` 是否转默认 | 等 WP3 A/B 数据 | 检测默认路径 |
| D5 | Phase 4 NN 臂是否立项 | 等 Phase 1 复测证据 | WP11/WP12 |

## 8. 测试与回归计划

**新增测试文件**：

- `checks/test_ai_mask_adaptive_background.py`（WP1）
- `checks/test_ai_mask_pale_support.py`（WP2）
- `checks/test_ai_mask_bridge_split.py`（WP3）
- `checks/test_ai_mask_container_split.py`（WP4）
- `checks/test_ai_mask_grounding_protocol.py`（WP6）
- `checks/test_upload_background_normalization.py`（WP9）

**回归底线**（每个工作包合入前必跑）：

- 三臂基准：`python -m checks.ai_mask_benchmark.runner --bundle <Phase0 bundle> --out <tmp> --label <arm>`，对比冻结基线；
- 既有防退化：`checks/test_ai_mask_fine_grained_detection.py`（:104 记录的"默认闭运算熔合 2px 间隙"行为预期会被 WP3 改变——该测试需随 A/B 结论同步更新，属预期修改非回归）；
- AGENTS.md Required Validation 全量（`compileall` 清单、`pytest checks/agent/`、`generate_agent_contracts.py --check` 等）——凡动了 Agent 可见设置/模型就必须同步 parity 映射并 bump 能力版本。

## 9. 工程约束与红线（合入检查单）

1. **模块边界**（AGENTS.md）：检测实现只进 `ai_mask_component_detection.py`/新模块；匹配实现只进 `ai_mask_assignment.py`/`ai_mask_semantic_matcher.py`；prompt 只进 engine 常量区 + `ai_mask_config.py` 迁移；engine 保持纯编排；不 import `server`。
2. **Prompt 改动**：WP6 必须先走 `.agents/skills/optimize-prompts/SKILL.md` 全流程，配套 runtime payload/输出契约/迁移/UI 预览四对齐测试。
3. **Agent Contract 同步**：新增任何 Agent 可见字段 → `checks/agent/test_contract_model_parity.py` 映射表登记 + capability 版本 bump + `scripts/generate_agent_contracts.py` 重新生成并提交。
4. **像素门与红线**：0.995 覆盖/零未分配/零跨组重叠不许退；不用漏像素换速度；不改全局 closing_radius。
5. **内存**：新算法 numpy 向量化；NN 会话懒加载用完释放；<3GB 可用内存场景纳入基准。
6. **设置四处落点**：DEFAULT_SETTINGS + 检测指纹清单 + `static/ai_mask_extension.js` 表单 +（如可见）Agent parity——见第 2 节开头。
7. **许可合规**：NN 权重统一 MIT/Apache-2.0，逐权重核对（库 MIT ≠ 权重可商用）；排除 BRIA RMBG 系。
8. **默认值一致性**：新增开关的 DEFAULT_SETTINGS 与 normalize 兜底保持一致（不要复制 handoff §6 记录的 `doclayout_enabled` 不一致模式）。
9. **Git**：只提交 `checks/` fixture 与代码；`runs/**`、`outputs/**`、模型权重文件不入库（权重路径走配置，同 `doclayout_model_path` 模式）。

## 10. 风险登记

| 风险 | 概率 | 缓解 |
| --- | --- | --- |
| 背景估计被边缘内容污染 | 中 | border 带离群剔除（§2.1）；`white` 模式一键回滚 |
| pale 吸附吞阴影/噪点 | 中 | 归属门槛 + WP5 策略联动 + 像素门兜底 |
| 切分过拆（重蹈 T4 覆辙） | 中 | 保守双门槛 + case_01/09 冻结断言 + `split_evidence` 可审计 |
| grounding 模型坐标格式漂移 | 高（已知坑） | 双格式解析 + 单测覆盖 + 不支持即降级 id_v4 |
| NN 会话内存（W5 复现） | 中 | 懒加载/用完释放 + <3GB 基准场景 |
| 30 页集标注工作量超预期 | 中 | 分批：先 15 页覆盖难点配额即可启动 Phase 1 A/B |

---

## 附：与调研报告的对应关系

- 调研报告 §4.1 P0-1↔本方案 WP1；P0-2↔WP2；P0-3↔WP3；P0-4↔WP4；P0-5↔WP5
- 调研报告 §4.2 M0↔WP7；M1↔WP6；M2（嵌入先验）暂缓——待 WP6 落地后按 `fallback_group_ratio` 数据决定是否值得
- 调研报告 §4.1 P1-6↔WP11；P1-7↔WP12；P2-9↔WP9；P2-10↔WP10
