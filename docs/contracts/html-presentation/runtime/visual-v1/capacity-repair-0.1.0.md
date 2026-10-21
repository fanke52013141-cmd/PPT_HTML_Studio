# 容量修复 0.1.0：确定性尺寸/排版候选

契约包 0.9.115；HPS-007/009/010/013/015–018/023–025。新增 `capacity_first` 策略：容量溢出不再只能走模型，
先由代码生成**有界、可读下限内**的候选，再由原容量/时间检查验收。

## 适用范围

- 修复 `scope` 内 1–4 个已存在对象；annotation 不参与尺寸覆盖。
- 只生成两类操作：
  - `set_presentation`：按原容量触发维度计算建议尺寸（`box_width`/`box_height`），限制在画布 20–1600 / 20–800
    与注册变体最小尺寸内，并给出槽位内可行的 `offsetX/offsetY`；
  - `set_text_style`：仅对**已显式设置字号**的公开文字部位按 0.9→0.3 步进缩小，**不低于 24px 可读下限**。
- 不改文字内容、对象身份、关系、动作、绑定、主题或人工保护字段；不新增对象或样式。
- 原编译器、容量测量、30fps/registered 动态检查仍是唯一验收者；候选必须显式保存，不自动批准。

## 决策与停止

1. 当前整页检查已通过 → `unchanged`，不生成候选。
2. 没有容量问题（例如只是结构/字体缺失）→ `needs_revision` + `NO_CAPACITY_ISSUE`，不调用模型。
3. 按顺序尝试候选（先尺寸、后字号步进），每次用原 `candidate_from_document` 校验并重跑原检查；
   第一个通过者即为候选。
4. 全部失败 → `needs_revision` + `NO_DETERMINISTIC_CAPACITY_FIT`，保留每次尝试的操作/错误，
   **不调用模型、不返回 unknown、不修改原页面**。
5. `capacity_first` 只接受固定指令，其他目标必须使用 `model` 策略；模型路径行为不变。

## 验证

- 离线候选基准 `scripts/benchmark_capacity_repair.py`：文字行数超限用例 0→13 个候选（字号 72→24），
  16.65 canvas px 底部越界用例 0→5 个候选（1 个尺寸 + 字号步进），合计 **0→18**；模型调用 0；耗时约 0.0001 秒。
- `checks/test_capacity_repair.py` 5 项：边界/可读下限/不改文字与身份/scope 过滤/策略指令校验/基准快照。
- `checks/test_capacity_first_strategy.py`（CI 真实浏览器）：溢出页确定性修复通过且 0 模型调用；
  120 字超长文本在 24px 下限内仍溢出时显式 `NO_DETERMINISTIC_CAPACITY_FIT`，不调用模型。

## Agent 同步

- `html_repair.generate` → 1.7（策略枚举新增 `capacity_first`）；`AGENT_API_VERSION` → 1.62.0；
  capability matrix 已重新生成。
- 无数据库迁移、无新 HTTP 路由；`model`/`geometry_first` 客户端不受影响。

## 未决

真实第 3 页三卡片 16.65px 越界的原始 scene 仍在另一台机，需按 hash 封存移交后复验；
本契约只证明候选生成与明确停止，不证明真实页已通过视觉/音频/输出验收。
