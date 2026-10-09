# 标准组件参考库

**唯一现行方案：中性标准组件 + 独立多角色配色 + 统一风格描述 + 准确内容。**

现行交付是 [standard](standard/) 的 24 张黑白灰参考 PNG，完整用法见 [标准组件库 1.0](STANDARD-LIBRARY.md)。[总览图](standard/overview.png)展示代码复刻后的美化效果；[全页缩略图](standard/contact-sheet.png)用于选型。HTML 是内部截图与组件调用工具。组件不绑定课程或配色，代码和图片共享统一视觉语言。

全页统一美化：32 项基础组件、16 种呈现变体、28 项静态效果、18 项组合、5 种字体。`reference-input-v2` 保留独立配色和统一风格输入；其中旧组件截图由 `standard/` 分类页替代。

## 当前资产

| 资产 | 内容与用途 |
| --- | --- |
| standard-components.png | 32 项中性标准组件总览，用于选型 |
| typography/arrows/cards/shapes/annotations/relationships/data-time.png | 七类细节图，按任务只传相关分类 |
| palette-clear/editorial/science.png | 清爽多彩、温暖编辑、冷静科普；每套包含主色、辅助、强调、分类及浅色面 |
| style-description.png / .json | 清爽轻立体的统一视觉描述；颜色服从独立配色表 |
| presentations-neutral/clear.png 及 titles/emphasis/containers/labels 细节 | 同一组件的 16 种呈现，真实 DOM 截图 |
| presentation-variants.json | 变体 ID、父组件、用途与样例；查询 PV01–PV16 |
| components.json / components-extensions.json | 原 24 项稳定 ID + 8 项固定关系/数据示例 |
| effects.json / static-catalog.json | 28 项静态效果、18 项组合示例；不是新增生产能力 |

使用规则、覆盖缺口见 [输入说明](REFERENCE-INPUT-V2.md)。下一步唯一执行顺序见 [详细开发计划](../../docs/plans/html-backend-development/visual-reference-roadmap-2026-10-09.md)。

## 复现

从仓库根执行，先安装 html_engine 的锁定依赖并设置 HPS_CHROME 为实际 Chromium 路径。中文字体需安装 Noto Sans SC、Noto Serif SC；字体尚未随包交付，缺字不视为验证通过。

```powershell
node html_engine/reference-library/build-components.cjs
node html_engine/reference-library/export-standard-library.cjs
node html_engine/reference-library/verify-components.cjs
node html_engine/reference-library/export-reference-input.cjs
node html_engine/reference-library/export-style-description.cjs
node html_engine/reference-library/component-query.cjs --id R01
```

改动源文件后重建，不能只编辑生成 HTML/PNG。当前 32 项参考实现与查询可用；新增关系与数据示例不支持任意拓扑、任意数值输入。新一版美感仍待反馈，未接入生产规划器/scene。

## 历史实验与清理

[PAIR-02/03 往返记录](ROUNDTRIP-RESULT-0.4.md)保留：两个静态实例得到用户认可，不代表新组件或完整生产链路通过。prepare-experiment.cjs、reconstruct-experiment.cjs、style-pairs.* 保留用于历史实验复现，不是现行输入协议。内部 components.html 里的历史风格演示同样不作为交付入口。

已从当前库移出被否定的七页页面模板、soft-depth 三模板六页、自建动效实现及其旧入口/截图（移至忽略目录 .tmp 可恢复，不发布）；已认可实例与 outputs 中的用户成果保留。当前已使用内置生图进行设计研究，不使用用户 API 密钥；音视频与数据库不在此次静态参考库改动范围。

本轮覆盖与美感审核见 [审核记录](VISUAL-AUDIT.md)，实际 PNG 已按精修源重新导出。
