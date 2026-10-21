# 正文溢出与箭头穿字冻结评测 · 2026-10-21

## 目标与做法

把两类工程缺陷从“专项检查通过”提升为可重复的冻结评测：正文超出父卡片边界、箭头中心线穿过文字。夹具
`checks/fixtures/overflow-crossing/dataset.json`（hash `d960332e31bdfa050c89d8674228694caaeb2dfd798947c97364934c2ac916bc`）
冻结测量事实，`checks/fixtures/overflow-crossing/probe.cjs` 直接调用生产谓词
`html_engine/visual/capacity.cjs`（原 1 CSS 像素容差）与 `html_engine/tools/vector-overlap.cjs`
（`svg-linear-stroke/0.1.0`，真实线段/描边半径/文字矩形）。全程无浏览器、无供应商、无作者写入、无批准。

评测器 `scripts/evaluate_overflow_crossing.py` 拒绝覆盖旧输出，校验数据集版本/用例/期望值，
逐类输出 TP/FN/TN/FP、确定判断漏检率/误报率、漏检或未决占比、判断覆盖率、未决计数与实际耗时，
并保留每个用例的触发维度、文字矩形或端点理由。

## 用例与实测

| 类型 | 用例 | 期望 | 实测 |
|---|---|---|---|
| 正文溢出 | `real-card-bottom-overflow`（2026-10-21 真实候选约 16.65 CSS px 底部越界，按冻结测量重放） | 检出 | 检出（line_count 7>6、scroll_height、text_bottom_overflow 16.65>1） |
| 正文溢出 | `near-edge-legal`（四边均在 1 CSS px 容差内） | 不检出 | 不检出 |
| 正文溢出 | `dense-legal`（行数等于预算、无父容器越界） | 不检出 | 不检出 |
| 箭头穿字 | `arrow-crosses-text`（中心线穿过文字矩形） | 检出 | 检出 `stroke_crosses_text` |
| 箭头穿字 | `endpoint-contact-legal`（端点落在非文字对象边界，原 relationContacts 语义） | 不检出 | 不检出（声明端点接触） |
| 箭头穿字 | `dense-relations-legal`（四条关系绕行两块文字） | 不检出 | 不检出 |
| 箭头穿字 | `unsupported-vector-undetermined`（不支持的 SVG 图元，线性核心无法判定） | 未决 | 未决，保留在原检查器的保守回退边界 |

结果：`text_overflow` TP1/TN2/FN0/FP0，耗时约 0.000075 秒；`arrow_text_crossing` TP1/TN2/FN0/FP0，
未决 1、模糊/未决排除 1，耗时约 0.000649 秒；整体进程 0.029 秒。`documented_real_observation`
与 `controlled_frame` 分开统计，后者有 5 例确定目标。

## 边界

- `real-card-bottom-overflow` 是按文档记录数值重放，不是本机重新截图或重新渲染；不能据此声称真实页已复验。
- 真实箭头穿字对仍在另一台电脑的隔离候选里（第 4 页 540 时点 3 组、318/213/207 次），需按 scene/binding 与证据 hash
  封存移交后再纳入本数据集；不得用受控帧冒充真实渲染。
- 端点接触、贴边合法、密集关系负例只证明当前谓词不误报这些受控形态，不等于全部真实布局。
- 本批无契约包/Agent API/数据库变更，不改生产阈值，不放宽原检查器。

## 验证

`checks/test_overflow_crossing.py` 3 项（冻结集指标、非法用例拒绝、未决与分母分离）与标签 v0.2.0
测试合计 16 passed；新脚本 ruff、compileall、`node --check` 通过。本机仍不能运行 Playwright 用例
（DSH 沙箱拒绝浏览器 mojo 管道），浏览器/真实课程终态以远端 CI 与另一台机证据为准。
