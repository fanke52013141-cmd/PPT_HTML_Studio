# 代码美术参考资产登记

2026-10-09。规范入口：[资产形成与使用](../../contracts/html-presentation/framework/12-code-art-reference-assets.md)。

**先用真实代码做出足够美的样板，再作为生图模型的主要美术依据。** 本目录记录现有资产如何形成、用途、实际材料和未完成项；归档不等于美术通过。

## 形成方法

美术目标→效果定义审查→代码细节/局部组合/完整页打磨→固定字体资源与参数→真实截图→技术检查和人工美术审阅→登记采用版本→生图与HTML对照→第二主题复用。

每个资产保留稳定ID、版本、源码/截图/参数/资源、哈希、渲染环境、生成或编辑来源、反馈、使用范围和修订。细节、组合、完整页共同传递代码的审美水准；普通能力测试图另标technical_demo。

## 当前归档

| 材料 | 形成过程与作用 | 当前美术状态 |
| --- | --- | --- |
| [61项效果板](../../reviews/2026-10-08-capability-workflow-demo/effects-demo.html) | 真实HTML/CSS/SVG/Canvas演示与五张截图；技术能力分类和初始证据 | 未作为正式美术参考审阅；存在编号/参数一致性待审项 |
| [早期可复用风格板](../../styles/science-explainer/reusable-style-board-v1/README.md) | 真实代码风格板，供探索固定参考输入方式 | 历史试作；不能沿用为本轮已认可美术资产 |
| [水为什么结冰生成提案](../../reviews/2026-10-08-capability-workflow-demo/generated.png) | 真实模型依据代码截图、风格图、规则及对象表生成 | 视觉提案；不是代码实现证据 |
| [水杯](../../reviews/2026-10-08-capability-workflow-demo/reconstruction/water-cup.png)与[冰块](../../reviews/2026-10-08-capability-workflow-demo/reconstruction/ice-block.png) | 参考提案分别模型编辑为2048²透明PNG；原始文件与可见边界保留 | 细节重绘；未证明无损提取或独立美术批准 |
| [实际HTML对照](../../reviews/2026-10-08-capability-workflow-demo/reconstruction/review.html) | 11个代码对象、2张独立插画，保留13个原对象身份；由实际代码组装 | 用户认为方案比较OK，但明确美感仍不足；生产视觉未通过 |

逐文件来源、用途、sha256、字节数和审阅范围见 [manifest.json](manifest.json)。过程及纠偏见 [形成备注](formation-notes-2026-10-09.md)。

## 下一类待形成的资产

经过打磨和审阅的 `code_art_detail`、`code_art_composition`、`code_art_page` 固定参考集，必须具备真实可见美感及完整可实现范围；本轮只登记形成要求，不虚构这些资产已经通过。

背景、中文排版、渐变、阴影、线条、图文协调都需进入实际样板审阅。先选一套漂亮的代码美术方向，再让模型依其为新内容组合；正式参考图不能只展示几种普通形状。

## 版本与备注

原文件保留用于问题追溯。F01在目录表示纯色，历史还原记录却引用它表示渐变；实际标题80px也超过旧目录18–48px。两项都登记待修，未改旧截图或旧定义掩盖差异。修正后应新建采用修订并重新截图/审阅。

`manifest.json`是文档资产清单，不是应用注册表。仓库预览不包含系统字体文件、API凭据、语音及课程数据库；依赖本机字体的范围已注明。

归档检查：[文件/链接与哈希记录](archive-validation-2026-10-09.json)、[便携HTML和流程实际打开记录](archive-browser-2026-10-09.json)。清单的sha256按Git规范化后的仓库字节计算；Windows文本原始字节不同的保留original_worktree字段，PNG字节保持不变。历史任务记录中的哈希仍指当时实际输入，不静默改写。
