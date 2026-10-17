---
name: produce-editable-html
description: Produce and verify editable HTML in PPT Studio using registered scene plans, design checkpoints and protected editing. Use for HTML生成、设计还原、未保存候选修复、讲稿画面诊断; exclude image-only Mask/reveal production and generic websites.
---

# 可编辑HTML生产与修复

版本1.17.0，2026-10-17。先读 [共用边界](../workflow-contracts.md) 和仓库docs/contracts/html-presentation/README.md；从agent_contract.capabilities读取当前能力，不把此操作说明整篇传模型。

## 选择任务

| 当前状态/意图 | 路径 |
| --- | --- |
| 新页/新设计/明确设计修订 | html_review.produce，先设计后接受，沿原候选身份 |
| 未保存容量失败 | 原candidate Agent/严格证据；其他资源/Schema错不进排版循环 |
| 已保存页的布局/动作修改 | html_editor.read→原repair preview/generate→验证→授权内save |
| 文案/节点增删/换模板 | 回权威规划，不用局部样式补丁替代 |
| 声音/逐句QA/正式输出 | 原服务和独立签收门禁 |

新生产/失败恢复读 [references/production-and-recovery.md](references/production-and-recovery.md)；局部编辑、音频/A04或输出读 [references/edit-and-deliver.md](references/edit-and-deliver.md)。讲稿到对象的语义问题再读 [references/semantic-planning.md](references/semantic-planning.md)，重复失败定位用 [references/failure-lessons.md](references/failure-lessons.md)。

## 不变的判断

准确内容/主题/人工保护高于参考图。模型决定合法计划和操作，程序共享组件渲染；代码拥有所有语义文字、标签和关系。缺对象回planning，缺工具回capabilities，独立非语义图片问题才assets。工程、静态保真、逐句语义、声音和人工签收分开。

不手写本例plan/HTML后声称系统Agent成功；不自由CSS、不整页位图替代正文、不以改source绕人工保护。尊重当前revision、候选key、源闭包和实际hash；文件存在不代表当前可用。原unknown不补发，暂停不等于供应商已取消。

## 检查与交付

读取实际任务进度、runtime_skill身份、调用/HTTP与复用事实、read/total等待预算；unknown用量/费用为null。查看当前scene、实际截图和声音/动作证据，给实际产物路径、revision、状态和未验证项。几何通过不等于审美批准。

例：灰阶HTML不抄原图彩色；图内缺字应补规划对象，不让主体图补字；cancelled子任务不复活；仅改布局的同值保存不重TTS。

按局部编辑Skill执行：核对受保护叶字段，绝对赋值；已有动作只改原句偏移；缺能力或冲突明确停止，不改source、不生图、不合成声音。

保护祖先适用于整个子树，manual_protection=true不等于整页禁止编辑。固定效果对照使用 `scripts/benchmark_html_editor.py`，Skill组只传上面的操作摘要；只有显式--live才请求模型，四例和失败/unknown均计入分母，费用未知保留null，单次耗时差不宣称稳定提升。

本Skill演进读 [references/evolution.md](references/evolution.md)，案例在 [evaluation/cases.json](evaluation/cases.json)。历史案例声明需与当前合同核对，不能当作新能力或签收。
