# 还原与二次处理优化方案（可执行）· 2026-10-22

## 0. 目标与北极星

用户目标：**提高设计→HTML 的还原成功率，减少生成后的二次处理**。落成三个可测指标：

| 北极星指标 | 含义 | 现状 | 目标 |
|---|---|---|---|
| 首轮可保存率 | 真实页进入“可显式保存候选”的比例 | 0/3（2026-10-21 水循环第2–4页） | ≥2/3 |
| 每页二次处理次数 | 人工修复 + 模型修复轮次 | 每页 1–3 轮，含 unknown | ≤0.5 |
| 确定性修复占比 | 缺陷由代码而非模型修复的比例 | 低（多数回模型） | ≥80% |

## 1. 判断：问题不是“模型画得不好”，而是边界与收敛

真实失败（详见[水循环试验](../plans/html-backend-development/handoff-water-cycle-trial-2026-10-21.md)、[系统问题台账](../plans/html-backend-development/system-issues-2026-10-21.md)）几乎都不是审美问题：模型在猜 ID、槽位名、端点、像素级容量与路由；这些本应由代码精确计算。同时修复链是“几何微调 → 整页模型重写”，缺陷类型没有路由、没有收敛保证。

因此优化顺序固定为：**先缩小模型职责（去几何/去ID）→ 再补确定性求解器 → 再换评测主指标 → 最后才比较 Legacy/Pi 与外部 Agent**。

## 2. 四层目标架构

```
L1 确定性编译层：ID、槽位、布局、文本测量、关系路径、容量、碰撞（现有 compiler/renderer/capacity/vector-overlap）
L2 模型层：只做语义选择（内容映射、模板/variant/icon、关系语义、需求提取），输出枚举与引用，不输出坐标/端点/ID
L3 修复求解层：缺陷 → 确定性求解器优先；无解才回模型，且只回 typed edit DSL；每缺陷独立预算
L4 验收阶梯：结构 → 静态视觉 → 动态 QA → 语义；候选可恢复，不自动批准、不写作者
```

## 3. 工作包（按依赖排序，可独立交付）

### W1 规划端点归一化（本次已完成）

- **问题**：模型用槽位名（`stage-1`）代替对象 ID（`obj-stage-1`），原校验严格拒绝，页面停在第 1 页两轮重试。
- **改动**：`html_storyboard_planning._resolve_relation_endpoints` 在严格校验前做**唯一槽位名归一化**：仅当槽位唯一、目标类型非 arrow/annotation、`point`/`anchorId` 形状与目标兼容时改写成对象 ID，并写入 `registered.endpoint_resolutions` 回执；未知、素材 ID、歧义槽位、锚点不符一律不改写，仍由原校验拒绝。
- **文件**：[html_storyboard_planning.py](../../../html_storyboard_planning.py)、[html_course_structure.py](../../../html_course_structure.py)、`scripts/benchmark_plan_endpoint_normalization.py`、`checks/test_plan_endpoint_normalization.py`。
- **数据（同一基准，`--baseline` 与默认对照）**：

| 指标 | 优化前 | 优化后 |
|---|---|---|
| 槽位名端点计划通过 | 0/32（0%） | **32/32（100%）** |
| 编译 scene/binding 完全一致 | — | **32/32** |
| 归一化回执 | 0 | 32 |
| 未知端点仍被拒 | 32/32 | **32/32** |
| 类型不符（指向 arrow）仍被拒 | 32/32 | **32/32** |
| 供应商调用 / 作者写入 / 批准 | 0 | 0 |

- **验收**：10 passed；真实页面该类错误可 0 轮重试（依据：第 1 页该错误导致 2 轮失败）。

### W2 关系路由确定性修复（本次已完成）

- **问题**：第 4 页 540 时点 3 组箭头穿字，单对象数值搜索无解，模型回退 593s、空正文、unknown。
- **方案**：新增 `geometry-repair/0.2.0` 的**端点附着点求解器**（不改语义、只改几何）：
  1. 枚举箭头两端在目标对象边界上的合法附着点（四边 × 三分位，含箭头头部方向约束）；
  2. 用真实 `vector-overlap.cjs` 判定候选是否避开所有文字矩形与对象描边；
  3. 仅在原 QA（30fps/registered）通过时产出候选；无解必须给出确定诊断（NO_LEGAL_ROUTE），不返回 unknown；
  4. 不移动作者文字、不改关系对象、不改样式；候选仍需显式保存。
- **改动**：`html_scene_repair.KINDS` 增加 `set_endpoint_point`；`html_repair_static.apply_static` 按关系节点校验；`html_geometry_repair` 新增求解器并接入 `geometry_repair` 预览循环；`html_repair_orchestration` 路由表前置。
- **数据**（冻结帧基准 `checks/fixtures/geometry-endpoint-routing/dataset.json`，hash `4e027ec3…`）：可路由穿字 0/2 → **2/2**；非路由用例（无解/anchor/隐式槽位）**3/3** 正确跳过；误生成 0；模型/供应商/作者写入 0/0/0；耗时约 0.03 秒。Agent API 1.61.0、预览/保存 1.8、generate 1.6、契约包 0.9.114。

### W3 容量溢出确定性修复（本次已完成）

- **问题**：第 3 页三卡片 16.65 CSS px 底部越界，页面被正确拦截但无自动修复路径。
- **方案**：有界候选生成（卡片宽/高在模板槽位内扩展 → 兄弟间距/文本换行 → 最后建议拆页），全部交原容量/重叠检查判定；字号只允许在可读下限以上。
- **数据**（离线候选基准 `scripts/benchmark_capacity_repair.py`）：文字行数超限 0→13 个候选（72→24px，下限24），16.65px 越界 0→5 个候选（尺寸+字号），合计 **0→18**；模型/供应商/作者写入 0；候选生成约 0.0001 秒。真实浏览器 CI 用例验证“确定性修复通过且0模型调用”与“可读下限内仍溢出时显式无解”。generate1.7、Agent API1.62.0、契约包0.9.115。

### W4 外部 Agent 最小输入（本次已完成）

- **问题**：任务包体积大、仍要求 Agent 自行推几何；unknown 无回执/幂等。
- **方案**：`html_external_handoff` 增加 compact 模式：
  - 只给：参考图、当前 scene 差异、类型化缺陷清单（含测量值）、允许操作白名单、**确定性候选 ID 列表**；
  - 不给：自由坐标、可推导的 ID 空间、全量 scene 历史；
  - 输出只接受 typed edit DSL（含候选 ID 或 `set_endpoint_point` 枚举值）；
  - 任务包带幂等键、供应商任务回执字段、unknown 查询入口。
- **数据**（代表性任务包，同一构建）：全量 `task.json` 113,922 字节 → `task-minimal.json` **26,403 字节（-76.8%）**；保留 scoped targets、2 条类型化缺陷、文件引用与 hash、候选与 QA 边界、幂等键与回执要求；`task.json` 仍为权威。测试 4 passed。真实 Agent 完成率/候选采用率待外部环境配对实测。

### W5 真实失败语料与离线 CI 门槛

- 冻结真实页的 scene/binding/测量/报告（hash 封存，不公开课程媒体），把四类真实失败做成离线夹具；CI 跑“检出 + 求解 + 无解识别 + 耗时”，缺陷逃逸必须为 0。
  - 已交付跨机迁移工具 `scripts/feature_recognition_bundle.py`（0.1.0）：只传 dataset 引用的图片/请求/响应/标签，逐文件 SHA-256/路径/符号链接/体积校验，导入先验证后落盘并拒绝覆盖；受控夹具往返 8 文件/2 页/69,258 字节且计分一致（4 项测试）。
  - 真实材料仍未在本机：需要另一台机用该工具导出未曝光课程样本，导入后按 0.2.0 标注再评估。
- 现有基础：`scripts/evaluate_overflow_crossing.py`、`scripts/evaluate_geometry_corpus.py`、`scripts/benchmark_plan_endpoint_normalization.py`、`scripts/feature_recognition_bundle.py`。

### W6 模型接口瘦身与跨课程泛化

- 规划/理解只输出枚举选择与引用；覆盖键/端点由代码派生；输出预算与 `finish_reason` 硬门禁。
- ≥3 门未曝光课程 × 3–4 页，标签 v0.2.0+（容器/图标/标注/模糊），模型指标与程序派生指标分开。

### W7 Legacy / Pi / 外部 Agent 配对实验

- 同一真实输入配对比较：首轮可保存率、修复轮次、耗时、成本、unknown 率；不先用默认切换。

## 4. 验收门槛（写进发布检查）

| 门槛 | 目标 |
|---|---|
| 冻结语料缺陷逃逸 | 0 |
| 几何类模型调用 | 0（W2 后） |
| 无解结论明确率 | 100%（NO_LEGAL_ROUTE / NO_CAPACITY_FIT） |
| 每页墙钟 | 确定性路径 <120s |
| 首轮可保存率 | ≥2/3（真实页） |
| 输入体积（外部 Agent） | 下降 ≥50% 且候选覆盖 ≥80% 缺陷 |

## 5. 风险与边界

- 不自动批准、不写作者、不第二渲染器；候选必须显式保存。
- 归一化只处理“唯一且类型兼容”的槽位名，不猜测未知引用；回执可审计。
- 求解器只在原始 QA 通过时产候选；无解必须显式，不返回 unknown。
- 契约包 0.9.113 / Agent API 1.60.0 在本次 W1 中不变；W2 若新增操作需同步契约、CHANGELOG 与 Schema 测试。
- 本机沙箱不能运行浏览器用例；浏览器/真实课程终态以远端 CI 与另一台机证据为准。

## 6. 执行节奏

1. **W1（已完成并推送）**：归一化 + 基准 + 测试 + 文档。
2. **W2/W3**：确定性求解器 + 冻结帧 + 0 模型调用数据。
3. **W4**：外部 Agent 最小输入 + 体积/候选数据。
4. **W5/W6**：真实语料 + 跨课程门槛。
5. **W7**：Agent 配对实验与默认切换评估。
