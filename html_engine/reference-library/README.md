# 标准组件参考库

**唯一现行方案：中性标准组件 + 独立多角色配色 + 统一风格描述 + 准确内容。**

交付是 [reference-input-v2](reference-input-v2/) 的 PNG，HTML 是内部截图渲染工具。组件不绑定某一课程，也不被一种颜色覆盖。代码和图片是实现分工，整个画面遵循同一视觉语言。

## 当前资产

| 资产 | 内容与用途 |
| --- | --- |
| standard-components.png | 32 项中性标准组件总览，用于选型 |
| typography/arrows/cards/shapes/annotations/relationships/data-time.png | 七类细节图，按任务只传相关分类 |
| palette-clear/editorial/science.png | 清爽多彩、温暖编辑、冷静科普；每套包含主色、辅助、强调、分类及浅色面 |
| style-description.png / .json | 清爽轻立体的统一视觉描述；颜色服从独立配色表 |
| components.json / components-extensions.json | 原 24 项稳定 ID + 8 项固定关系/数据示例 |
| effects.json / static-catalog.json | 28 项静态效果、18 项组合示例；不是新增生产能力 |

使用规则、覆盖缺口见 [输入说明](REFERENCE-INPUT-V2.md)。下一步唯一执行顺序见 [详细开发计划](../../docs/plans/html-backend-development/visual-reference-roadmap-2026-10-09.md)。

## 复现

从仓库根执行，先安装 html_engine 的锁定依赖并设置 HPS_CHROME 为实际 Chromium 路径。中文字体需安装 Noto Sans SC、Noto Serif SC；字体尚未随包交付，缺字不视为验证通过。

```powershell
node html_engine/reference-library/build-components.cjs
node html_engine/reference-library/verify-components.cjs
node html_engine/reference-library/export-reference-input.cjs
node html_engine/reference-library/export-style-description.cjs
node html_engine/reference-library/component-query.cjs --id R01
```

改动源文件后重建，不能只编辑生成 HTML/PNG。当前 32 项参考实现与查询可用；新增关系与数据示例不支持任意拓扑、任意数值输入。新一版美感仍待反馈，未接入生产规划器/scene。

## 历史实验与清理

[PAIR-02/03 往返记录](ROUNDTRIP-RESULT-0.4.md)保留：两个静态实例得到用户认可，不代表新组件或完整生产链路通过。prepare-experiment.cjs、reconstruct-experiment.cjs、style-pairs.* 保留用于历史实验复现，不是现行输入协议。内部 components.html 里的历史风格演示同样不作为交付入口。

已从当前库移出被否定的七页页面模板、soft-depth 三模板六页、自建动效实现及其旧入口/截图（移至忽略目录 .tmp 可恢复，不发布）；已认可实例与 outputs 中的用户成果保留。当前不做付费生图、不改音视频/数据库。
