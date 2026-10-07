# AI Mask 拆分与匹配精准度调研报告

日期：2026-09-27
调研目标：回答两个问题——① 是否有对应的开源项目能解决"幻灯片图拆解 + 旁白匹配"的问题；② 如何实现更精准的拆分与匹配。重点针对两个已知难点：**异形图形**与**非白底背景**。

---

## 0. 结论速览（TL;DR）

1. **没有任何现成开源项目能"整体替换"AI Mask。** 本项目的需求是"幻灯片位图 → 逐元素精确像素掩码（row_runs_v1 RLE）+ 与旁白语义组的归属关系"，这是为 Reveal 动画播放定制的专用管线。最接近的 image2ppt 类开源项目（nature-image2ppt、SlideCoder、Edit-Banana 等）目标是"还原可编辑 PPT 文档"，不产出 reveal 掩码、不接旁白时间轴，无法直接使用。**但存在一组成熟的开源"积木"，可以分阶段嵌入现有管线，且与 AGENTS.md 固化的模块边界完全兼容。**

2. **精准度提升不必推翻现有算法——诊断显示损失集中在三处，而非"整体不精准"：**
   - 像素层（掩码本身）早已达标：16 图离线集 ink_recall 0.9697、跨组重叠 0、受保护白底 1.0（`docs/HANDOFF_2026-09-20_ai_mask.md` §3.4）。**损失全部在归属层与召回层**：group recall 0.63（W3-W5 后 0.73）、ownership IoU 0.52→0.68；
   - w7 检测基准最差项：浅色内容召回 pale_recall 仅 0.03–0.53；2–8px 间隙粘连 IoU 0.323；嵌套容器 0.161；密集内容 0.085（`outputs/ai_mask_w7_current_detector/report.json`）。

3. **两个痛点各有明确解法（详见第 5 节路线图）：**
   - **非白底**：三层防线——(a) 确定性自适应背景估计（把 245/12 硬编码改为相对估计背景色的容差），(b) 上传/生成端把非白底图"显著性抠图→贴白底画布"规范化，(c) 可选 ONNX 显著性分割（BiRefNet-lite，MIT，约 224MB）作为兜底检测臂；
   - **异形图形**：现有逐像素 RLE 本身已能表达任意轮廓（含镂空、凹形），真正的缺口是**软阴影归属、浅色/抗锯齿边缘召回、相邻元素粘连、嵌套容器欠拆**四类——确定性路径修阈值与切分策略；NN 路径用 SAM 系模型做 box-prompt 边界精修。

4. **部署约束（关键事实）**：本机当前只有 numpy + PIL（无 torch、无 onnxruntime、无 cv2）。任何神经网络方案都必须沿用 DocLayout 已确立的模式：**可选依赖 + 模型文件缺失即优雅降级到现有确定性路径**（`ai_mask_doclayout.py:12-23`）。

5. **动手前必须先建可复现评测基准**（≥30 页真实业务集，handoff §6 T6 已列为未完成项）。没有基准的算法更换违反 handoff §10 红线：不许用漏像素换速度或"精度"。

---

## 1. 现状剖析

### 1.1 拆分管线（元素检测）当前算法

入口 `ai_mask_component_detection.py:900-1203`（`detect_elements`，默认 v5 闭运算路径）：

1. 读图 RGB，四周垫 2px 纯白边（:957-964）；
2. 白色判定：`white = (min_channel >= white_threshold) & ((max_channel - min_channel) <= color_tolerance)`（:969）；
3. 从四条边各 seed 一轮 BFS flood fill，与画布外连通的"白"判为背景，其余为墨水前景（:978-995）；
4. 13×13 闭运算（radius=6）产出 `grouping_mask` 连通性假设，但 `pixel_evidence_separation=True` 时墨水证据不被闭运算覆盖（:1030-1043）；
5. 8 连通连通域标记（:1049-1075）；
6. 投影切分（仅对满足苛刻条件的连通域）（`_projection_split` :1206-1329）；
7. 逐组件构造精确 row_runs_v1 掩码（`mask_rle` + 实心化前 `source_ink_rle`）（:1094-1123）；
8. DocLayout 版面框只"标注"原子（el_atom_NNNN），不融合（`_finalize_binding_v2` :729-857）；
9. 面积 <120px 者降级为 `residual_elements`（:1133-1142）；
10. 结果写 `auto_mask/auto_elements.json`，命中条件 = 算法版本 + 图片 sha256 + 13 项设置指纹 + 版面框指纹，四者任一变化即重检测（:939-954）。

### 1.2 白底假设的全部硬编码（根因清单）

| 常量 | 当前值 | 位置 | 非白底下的行为 |
| --- | --- | --- | --- |
| `white_threshold` | 245（设置上限 255） | `ai_mask_engine.py:40` | 浅灰底（如 RGB 235）整幅判为前景 → flood fill 无路可走 → 全图一个巨型组件，**完全欠拆** |
| `color_tolerance`（通道极差） | 12（上限 40） | `ai_mask_engine.py:41` | 米色/暖白底（通道差 >12）同样整幅判前景 |
| `add_border` | 2px 纯白垫边 | `ai_mask_engine.py:43` | 垫边假设背景是白的，非白底时垫边本身成为"假前景" |
| `closing_radius` | 6（13×13 核） | `ai_mask_engine.py:42` | 主动桥接 ≤6px 间隙（记录在 `bridge_pixel_count`），粘连的直接来源 |
| `pale_support_threshold` | 254（仅细粒度路径） | `ai_mask_engine.py:48` | 默认路径下浅色墨水无支持层 |
| `RAW_SOURCE_CUTOUT_HARD_MIN_CHANNEL` | 254 | `ai_mask_contracts.py:36` | 只救通道 ≥254 的近白偏色，244–253 的浅灰/米色不覆盖 |
| 投影切分门槛 | bbox ≥15% 画布 **且** 长宽比 >1.5:1 | `ai_mask_component_detection.py:1231,1237-1240` | L 形/对角接触不切；密集文本谷深不够不切；哑铃形真元素被误切 |
| 覆盖率门 | 0.995 | `ai_mask_contracts.py:18` | — |

**渐变底的失效模式**：靠近白的部分过阈值、远离白的部分不过 → flood fill 推进到第一条非白环带即停，组件边界黏住渐变等值线，产生撕裂状错误掩码。**纹理底**：要么数千碎组件（过拆），要么连成大片（欠拆）。

现行补偿机制（master 洗白 + raw sidecar 配对，`ai_mask_contracts.py:26-73`）只覆盖"接近白的偏色"，本质仍是白底假设的延伸。

### 1.3 匹配管线（元素↔旁白语义组）当前算法

`ai_mask_semantic_matcher.py` + `ai_mask_assignment.py` + `ai_mask_engine.py:591-843`：

1. **语义对象准备**：元素聚成 obj_001…——文本行合并（高 5px–14%H、按行聚类，同排等高卡片被容器岛门挡住绝不并入）、大岛吸收 pad 内子元素、其余单独成对象；`residual_elements` 按框距就近吸收后一并给模型看（`_absorb_residuals_into_objects` :267-324）。
2. **多模态请求**：原子模式每批 12 个对象、每次请求 = 1 张未画框完整原图（≤1280px）+ 每对象 1 张带 id 标签的裁剪切片（pad 8-20px、最宽 400px），temperature 0.1、JSON mode，截断/坏形重试 1 次（`_request_object_batch` :747-822）。
3. **模型返回**：`matches[{group_id, narration_beat_id, object_ids, confidence, reason}]` —— **只返回 id 列表，不返回坐标**；模型编造的 id 直接拒绝（`_merge_batch_results` :469-637）。
4. **兜底与后处理**：置信度 <0.72 不作数；模型没认领的组由确定性 fallback（旧框先验几何匹配）补上；随后四道几何后处理——标题区固化、稀疏外框改绑旁白标题组、旁白组锚点保底、组件全覆盖补全（origin=completion 永不抬高置信度）。
5. **质量门**：像素门（覆盖率 ≥0.995、零未分配、零跨组重叠，`ai_mask_assignment.py:1196-1213,1354-1359`）+ 语义门（动态组进字幕安全区、拥有标题区、残余过多、原子性问题）+ 溯源门（model/rule/completion/manual 四源，无 model 参与的 body 组路由人工复核）。
6. **无缓存**：每次标注都重新请求 VL；检测与版面有缓存。

### 1.4 量化现状（基准证据）

| 场景 | 指标 | 数值 | 出处 |
| --- | --- | --- | --- |
| 16 图离线集（默认臂） | group recall / ownership IoU | 0.6303 / 0.5206（W3-W5 后 0.7316 / 0.6843） | handoff §3 |
| 16 图离线集 | ink_recall / 重叠 / 白底保护 | 0.9697 / 0 / 1.0（**像素契约始终满足**） | handoff §3.4 |
| 2-8px 间隙 | macro IoU | 0.323（case_02/03 recall 0.6667） | handoff §3.3、w7 |
| 嵌套容器 case_06_nested | 单案例最差 | 0.161 IoU、574688 越界像素、缺 2 组 | handoff §3.3 |
| 版面框关闭 case_08_repeated | recall | 0.2000 | handoff §3.3 |
| 浅色内容 05_pale | coverage | 0.1107（pale_recall 全线 0.03–0.53） | w7 |
| 光晕线条 11_halo_lines | coverage | 0.9614（<0.995 门） | w7 |
| 端到端真实 API 盲测（阶段 D，11 页） | 11/11 过门 | 覆盖率 ≥0.9969、重叠 0、逐组 p/r ≥0.99 | git 660bec1/9202646/e0df6da |

**结论**：真实生成的白底图端到端已经很好；差的是 (a) 浅色/抗锯齿/光晕召回，(b) 小间隙粘连与嵌套容器，(c) 归属层（哪组元素归哪句旁白）。

### 1.5 痛点一"异形图形"的根因重定义

"异形图形难以精准标注"这个表述下实际混着四个不同的问题，解法完全不同：

1. **任意轮廓表达**：不是问题。row_runs_v1 是逐像素行程，凹形、镂空、曲线边界都能精确表达（封闭白域按契约保留，AGENTS.md "White areas enclosed by content are preserved"）。
2. **软阴影与光晕**：无专门判别逻辑。阴影像素深于阈值 → 与主体熔为一体随主体 reveal（视觉上尚可接受但边重）；浅于阈值 → 被当作背景洗掉（光晕丢失，11_halo_lines coverage 0.9614 的来源）。
3. **浅色/抗锯齿内容**：245/12 阈值下浅色墨水被判背景 → 整体丢失（pale_recall 0.03–0.53 是检测层最差项）。raw pair + 254 地板已在端到端盲测中把 05_pale 从 0.11 救到 0.9999，但该机制未推广到默认检测路径。
4. **相邻粘连与嵌套**：闭运算半径 6 桥接 2–8px 间隙（02/03 IoU 0.323）；投影切分只救"大长条"；嵌套容器（外框+内部卡片）欠拆为整体（case_06 IoU 0.161）。T4 已明确红线：**不要全局改 closing 半径**（半径 2 会把 case_01 切成 7 块、case_09 切到 25 块）——必须走"证据切分"而非调参。

### 1.6 痛点二"非白底"的根因

flood fill 从画布边界向内的"边界连通白色即背景"定义，是整条拆分管线的第一性假设；白底不成立时**第一步就失效**（见 1.2 表格）。上游 master 洗白（把与外边缘连通的近白像素刷成 #FFFFFF）只能处理"接近白"的底。**真正的解法方向不是继续调阈值，而是把"背景是什么"从硬编码变成估计值，或在上游把非白底图转化为白底问题。**

---

## 2. 开源项目调研

### 2.1 直接对口项目检索结论：没有

按"slide image → element decomposition / editable PPT"方向检索，最接近的项目：

| 项目 | 做什么 | 为什么不能直接用 |
| --- | --- | --- |
| nature-image2ppt | 幻灯片截图 → 对象级可编辑 PPTX | 产出矢量/文本对象，不产出像素级 reveal 掩码，不接旁白 |
| SlideCoder / VIGA（学术论文线） | vision-as-inverse-graphics：图像 → 版面+元素程序 | 研究原型，目标是"重建幻灯片"而非"保留原图做动画拆解" |
| Edit-Banana | 图/PDF → 可编辑 DrawIO/PPTX | 同上 |
| dom-to-pptx、ppt-master | 结构化 DOM → PPTX | 输入就不是位图 |

本项目的关键差异：**原图必须原样保留并按掩码分层做 reveal 动画**（Remotion 不得重绘正文内容，AGENTS.md Image Rules），因此"重建式"方案（OCR→矢量→重排）从根本上不适用——它们会丢掉位图还原度。可借鉴的只有它们的子模块思路（OCR、版面框检测——其中 DocLayout-YOLO 本仓库已集成）。

### 2.2 可组装的开源积木（按用途分四类）

#### A. 高质量/通用分割（解决"边界精修"与"任意形状"）

| 项目 | 许可证 | 部署形态 | 对本项目的价值 |
| --- | --- | --- | --- |
| [SAM 2 / SAM 2.1](https://github.com/facebookresearch/sam2)（Meta） | Apache-2.0 | torch 较重；社区有 ONNX 导出 | 对现有组件 bbox 做 box-prompt，产出真实物体边界的精修掩码 |
| [HQ-SAM](https://github.com/SysCV/sam-hq)（NeurIPS 2023，arXiv:2306.01567） | 开源（代码继承 SAM 库，权重托管 HuggingFace） | 同上，仅增约 4.7M 参数融合层 | 边界细节显著优于原版 SAM（细结构、镂空、锯齿边缘），比 SAM 更适合"异形图形" |
| [MobileSAM](https://github.com/ChaoningZhang/MobileSAM) / EfficientSAM / EdgeTAM | Apache-2.0 | 编码器约 10MB 级，**CPU 可行**（编码一次、解码多次） | 无 GPU 环境下的 box-prompt 精修首选 |

使用方式（关键）：**不改变现有检测的"发现"职责，只做"精修"**——现有确定性管线给出组件 bbox（它发现元素的能力已经够用），SAM 系模型只负责把 bbox 内的掩码边界修准。这样 SAM 的失败模式（把两个粘连元素合成一个掩码）不会引入新的拆分错误，且输出可以无损转成 row_runs_v1。

#### B. 显著性前景/背景移除（解决"非白底"与"软阴影"）

| 项目 | 许可证 | 部署形态 | 对本项目的价值 |
| --- | --- | --- | --- |
| [BiRefNet](https://github.com/ZhengPeng7/BiRefNet)（高分辨率二分分割 DIS，CAAI AIR 2024） | **MIT** | ONNX 全量约 880MB；**lite 版约 224MB**，CPU 数秒/页 | 任意底色/渐变/纹理下的显著性前景 alpha；软阴影通常随主体保留；边界质量是同类最优 |
| [rembg](https://github.com/danielgatis/rembg)（u2net/isnet/BiRefNet 权重） | 库 **MIT**（权重逐一核对，避开 BRIA 系） | pip 即用，CPU | 上传图白底规范化的现成实现 |
| [PyMatting](https://github.com/pymatting/pymatting) | MIT | 纯 Python+scipy，CPU | 以现有掩码为 trimap 做软边缘 alpha 精修（阴影羽化、抗锯齿边） |
| RMBG-1.4 / RMBG-2.0（BRIA） | **非商用许可** | — | 明确排除（商用需向 BRIA 付费） |

#### C. 开放词汇检测（解决"按语义找元素"的先验）

| 项目 | 许可证 | 部署形态 | 对本项目的价值 |
| --- | --- | --- | --- |
| [Grounding DINO / Grounded-SAM 2](https://github.com/IDEA-Research/GroundingDINO) | Apache-2.0 | torch 重 | 用文本提示（"柱状图""流程图卡片"）直接出框 → 交给 SAM2 出掩码 |
| [Florence-2](https://huggingface.co/microsoft/Florence-2-base)（微软，0.2B/0.7B） | **MIT** | 轻量，可 CPU/边缘部署 | 一个模型同时做 grounding + OCR + 区域分割，是轻量替代 |
| YOLO-World / YOLOE | Apache-2.0 | ONNX CPU 友好 | 实时开放词汇框先验 |

#### D. 文档版面与 UI grounding（幻灯片≈高分辨率 UI 截图）

| 项目 | 许可证 | 现状 | 对本项目的价值 |
| --- | --- | --- | --- |
| DocLayout-YOLO / PP-DocLayout | 开源 | **已集成**（`ai_mask_doclayout.py`，可选 onnxruntime CPU，缺模型自动降级） | 版面框已用于原子标注；嵌套框信息还可用于容器感知切分（见 5.1） |
| [Qwen2.5-VL / Qwen3-VL](https://qwenlm.github.io) | Apache-2.0（API 或本地） | 匹配环节现走远程多模态 API | **grounding 原生输出 JSON bbox**（归一化/绝对坐标），是匹配环节升级的主推方案 |
| OS-Atlas / ShowUI / UGround（GUI grounding 线） | 开源（权重+数据全开源） | VLM | "指令→截图元素框"，与"旁白句→幻灯片元素"任务形态同构，可作为兜底或微调底座 |

### 2.3 许可证与部署小结

- 可安全商用：SAM 系（Apache-2.0）、BiRefNet（MIT）、rembg（MIT）、Florence-2（MIT）、Qwen2.5-VL（Apache-2.0）、PyMatting（MIT）、DocLayout-YOLO。
- 排除：RMBG-1.4/2.0（BRIA 非商用许可）。
- 部署铁律：本机无 torch，所有 NN 能力一律走 **onnxruntime 可选依赖 + 模型文件缺失自动降级** 的既有模式（DocLayout 先例：`ai_mask_doclayout.py:12-23,474-499`），不得成为硬依赖。

---

## 3. 结论一：是否有对应的开源项目？

**没有"拿来即用"的整体方案；有"按接缝组装"的成熟积木。**

- 整体替代不存在：本项目要的是"位图原样保留 + 逐元素像素掩码 + 旁白归属"，开源世界没有对这个组合的现成实现；最接近的项目目标都是"重建可编辑文档"，与本项目的动画管线目标冲突。
- 积木全部存在且许可证干净：拆分精修（SAM 系）、非白底前景（BiRefNet/rembg）、语义框先验（Florence-2/Grounding DINO）、匹配升级（Qwen2.5-VL grounding）。
- 现有代码已为组装预留了接缝（`detect_elements` 的 payload 契约 + row_runs_v1 + 版本化缓存指纹 + 基准 runner），任何新检测臂只要产出 `mask_rle`（row_runs_v1、画布坐标系）即可零改动接入下游（归属图、语义对象准备、质量门、reveal builder 全部不动）。

---

## 4. 结论二：更精准的拆分与匹配——路线图

### 4.1 拆分

#### P0：确定性增强（零新依赖，改 `ai_mask_component_detection.py`，先做）

1. **背景色自适应**（解决浅灰/米色底）：从四边 border 带（垫边前）估计背景色（中位数/众数），白色判定改为 `dist(pixel, estimated_bg) <= tol` 且通道极差仍受控；`white_threshold/color_tolerance` 从绝对值变为相对估计背景的容差。沿用设置指纹机制新增设置项 + 新缓存版本号，缓存自动隔离，可先在 w7 合成基准回归。
2. **浅色召回推广**（解决 pale_recall 0.03–0.53）：把 raw pair + 254 地板机制从"抠图阶段"推广到默认检测路径——raw 配对生效时用洗前像素以 254 地板重判墨水（这正是端到端盲测把 05_pale 从 0.11 救到 0.9999 的既有机制，只差推广）。
3. **粘连的证据切分**（解决 2–8px 间隙，替代"调 closing 半径"这条已被 T4 红线否掉的路）：对闭运算桥接的 `bridge_pixel_count` 区域，在桥接带做距离变换分水岭/墨岛分层切分；或直接启用**已建成但默认关闭的细粒度 P1 检测器**（`fine_grained_detection`，无闭运算、可分岛永不融合）做 A/B——它当年就是为此设计，只差基准验证与默认值决策。
4. **嵌套容器切分**（解决 case_06 IoU 0.161）：利用 DocLayout 框嵌套比（`BOX_NESTING_RATIO=0.9` 已有）与墨岛分层，按"容器框内墨水分层（边框环 + 内部岛）"构造子掩码，即 handoff T4 待办"容器感知切分"。
5. **软阴影策略决策**（产品决策 + 小改动）：确定"阴影是否应随主体 reveal"。若"是"，把阴影判为前景的一部分（BiRefNet 的行为）；若"否"，在锚点吸收半径外浅色低饱和区域按背景处理。当前无判别逻辑是明确缺口。

#### P1：可选 NN 检测臂（onnxruntime 可选依赖，产出仍为 row_runs_v1 RLE）

6. **BiRefNet-lite（MIT，约 224MB）显著性兜底臂**：当确定性路径检出"背景色非白/渐变/纹理"（可用 border 带方差判定）时启用；alpha 阈值化 → 连通域 → 与确定性组件求并/投票；失败或未安装模型即降级现有路径。CPU 数秒/页，与"逐页批处理"节奏兼容。
7. **SAM 系 box-prompt 边界精修**：对每个确定性组件 bbox 做 box prompt（MobileSAM/EfficientSAM CPU 可行；有 GPU 用 HQ-SAM/SAM2），精修后的掩码与现有 RLE 做一致性校验（覆盖率门与零重叠门不变）后融合。**只精修边界，不重新发现元素**，避免引入新的拆分错误。
8. 交付形态：新建 `ai_mask_neural_detection.py`（或并入 `ai_mask_component_detection.py` 按 `fine_grained_detection` 的先例加开关分支），**不得把 NN 实现放进 `ai_mask_engine.py`**（AGENTS.md 模块边界）；新缓存版本号字符串；用 `checks/ai_mask_benchmark/` runner 与 `outputs/ai_mask_w7_*` 评分口径做 A/B。

#### P2：上游转化（改 `image_workflow_service` 上传/生成路径，不动 AI Mask 核心）

9. **上传图白底规范化**：上传时角落采样判定背景非白 → rembg/BiRefNet 抠前景 → 合成到纯白 1920×1080 画布 → 走既有 raw pair 封存（洗前原图永远可回溯）。**把"非白底"问题在上游转化为"白底"问题**，AI Mask 确定性核心保持不变。这与 P0-1 的内部泛化互为冗余防线：上传规范化失效（如 PNG 透明通道、复杂底）时由 P0-1/P1-6 兜底。
10. **生成端强化**：Step 3 生成后加白底校验（四角+边界带采样），不达标自动重生成或先规范化再入库；现有"纯白外底"契约不变。

### 4.2 匹配

#### M0：现有 VLM 批次的低成本改进（改提示词与请求结构）

- 裁剪切片加**上下文环**（低透明度的全图缩略参考或 bbox 在全图中的位置示意图），缓解"只看局部猜不对组"；
- 对 `confidence` 做校准（当前是模型自报值，0.72 阈值的实际含义未经校准）；
- 失败组重问一次（当前整页失败即放弃 VL，`_annotate_project` :941-944，可改为组级重试）。
- 注意：任何 Prompt 改动必须先走 `.agents/skills/optimize-prompts/SKILL.md`（AGENTS.md Prompt Optimization Policy）。

#### M1：grounding 型输出（消除"引用切图 id"间接层，推荐主攻）

- 现匹配要求模型在"完整原图 + N 张带 id 切片"之间对齐 id，幻觉面大；Qwen2.5-VL 系/OS-Atlas 系模型原生支持"文本→JSON bbox"grounding。
- 改法：让模型对每个旁白视觉组**直接输出描述目标区域的 bbox（归一化坐标）**，代码侧用中心点/面积重叠把 bbox 对齐到已检出的语义对象，再回退到现有 id 引用协议作为兜底。坐标对齐是确定性的，模型只做它擅长的"看图说话指位置"，id 编造问题自然消失。
- 保留现有几何后处理链（标题固化/稀疏框改绑/锚点保底/补全）与溯源门不变。

#### M2：两级裁决（降本 + 提准）

- 用便宜的几何+嵌入先验（CLIP/SigLIP 图文相似度，本地小模型或 API）对"元素↔旁白句"做批量初排，VLM 只裁决歧义项；
- 匹配环节目前无缓存，嵌入索引可顺带把重标注成本降下来。

#### 评测先行（M 与 P 共同的前置）

- 按 handoff §6 T6 建 **≥30 页真实业务集**标注基准；现有 16 图离线集 + w7 合成案例继续作为回归底线；
- 指标沿用：macro IoU、coverage、pale_recall、overlap、group recall、ownership IoU；
- 任何检测器/匹配器更换必须 A/B 并守住三道像素门（0.995 覆盖 / 零未分配 / 零跨组重叠）与红线"不许用漏像素换"。

### 4.3 实施顺序建议

```
基准扩充(T6) → P0-1 背景自适应 + P0-2 浅色召回（先在合成基准回归）
→ P0-3/P0-4 粘连与嵌套（细粒度 P1 A/B + 容器感知切分）
→ M1 grounding 型匹配（收益/成本比最高的一步）
→ P2 上传规范化（补非白底最后一环）
→ P1-6/P1-7 NN 兜底臂与边界精修（有真实收益证据后再上）
```

理由：P0 全部是确定性小改动，直接命中量化最差项（浅色召回、粘连、嵌套）；M1 复用已有远程 VLM 通道，不引入本地部署负担；NN 臂放在最后，因为它引入模型分发、内存与算力成本，应等基准证明确定性路径的天花板后再决定。

---

## 5. 风险与红线

1. **NN 掩码的语义漂移**：神经掩码倾向把阴影、浅色光晕算作前景，会使"前景"定义变宽——覆盖率门数值不变但含义改变，reveal 图层的视觉观感（阴影是否随主体动）需要产品决策先行（P0-5）。
2. **内存红线**：W5 实测 `_connected_sets`/`_build_atom` 阶段在 <3GB 可用内存时 MemoryError（handoff §5）；BiRefNet/SAM 的 ONNX 会话内存需按同标准评估，懒加载 + 用完释放。
3. **模块边界**：检测实现只进 `ai_mask_component_detection.py`（或新模块），匹配实现只进 `ai_mask_assignment.py`/`ai_mask_semantic_matcher.py`；engine 保持纯编排；不得恢复任何 `server` 依赖。
4. **人工修正保护**：`ai_mask_manifest_apply.py` 的人工笔刷保护逻辑与 `source_ink_rle` 证据链必须在新检测臂下继续成立。
5. **许可合规**：统一避开 BRIA 系权重；引入每个模型前核对权重文件的独立许可（库 MIT ≠ 权重可商用）。
6. **默认值一致性**：handoff §6 已记录 `doclayout_enabled` 在 DEFAULT_SETTINGS 与 normalize 兜底间的不一致，新增检测臂开关时不要复制这个模式。

---

## 6. 参考链接

- SAM 2：https://github.com/facebookresearch/sam2
- HQ-SAM（arXiv:2306.01567）：https://github.com/SysCV/sam-hq
- MobileSAM：https://github.com/ChaoningZhang/MobileSAM
- BiRefNet（MIT，ONNX 导出含 lite 约 224MB）：https://github.com/ZhengPeng7/BiRefNet
- rembg（MIT）：https://github.com/danielgatis/rembg
- PyMatting（JOSS 2020）：https://github.com/pymatting/pymatting
- Grounding DINO / Grounded-SAM 2：https://github.com/IDEA-Research/GroundingDINO
- Florence-2（MIT）：https://huggingface.co/microsoft/Florence-2-base
- Qwen2.5-VL（grounding JSON bbox）：https://qwenlm.github.io
- OS-Atlas：https://huggingface.co/OS-Copilot/OS-Atlas-Pro-4B
- RMBG-2.0 许可说明（非商用）：https://huggingface.co/briaai/RMBG-2.0
- 内部证据：`docs/HANDOFF_2026-09-20_ai_mask.md`、`outputs/ai_mask_w7_current_detector/report.json`、`checks/ai_mask_benchmark/`
