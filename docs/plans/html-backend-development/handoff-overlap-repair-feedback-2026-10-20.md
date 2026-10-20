# 真实重叠修复与反馈闭环 · 2026-10-20

基于main 00fb81d4及本机累计未提交优化；实际应用源码目录为`D:\Program Files (x86)\PPT_HTML_Studio`，附件工作区为`C:\Users\Administrator\Desktop\html动画\PPT_HTML_Studio`。本批包0.9.110、Agent API1.59.0。

## 两组真实冲突的候选修复

使用原scene repair工具，不改变关系from/to、文本、图表数值、动作、binding或音频。第一页obj-anchor-label的offsetY从-48调整为20；第三页obj-card-2宽度调整为500，使其原派生箭头避开chart:min。未新增箭头白名单或路由特例。

完整受控集成证据：`outputs/overlap-feedback-20261020-v2/repair-summary.json`；前后截图在该目录`comparison.md`。已查看两个最终画面；几何通过不等于用户视觉批准。

| 页面 | 修改前穿字记录 | 修改后 | 30fps检查时点 | 决策轮数 | 隔离保存revision |
| --- | --- | --- | --- | --- | --- |
| slide_001 | 162 | 0 | 633 | 2 | 1 |
| slide_003 | 298 | 0 | 606 | 1 | 2 |

计数是跨时间重复记录；采样包括全部30fps输出时点及额外动作边界，frame_complete=true，continuous_time_verified=false。没有连续时间数学证明、听审或人工批准。

源码工作树指纹`2a7242993a2b84d7698ccae07277aeed9f26aa429cd63bae17f638734abb1590`固定在该次source-manifest；source_unchanged/code_unchanged均true。只有isolated-run执行save_repair，保存前候选不写作者；保存后原历史检查点可读取且与基线一致，音频身份一致。原课程、批准、数据库未修改。后续本文件记录不改变历史实验指纹。

## 原修复闭环改进

- 发现并修复generate_repair第二轮沿用原截图/测量的问题。第二轮按最新有效候选构建报告、附件与对应时间的几何/文字矩形；原targets和scope保持，操作仍是对原稿的完整绝对补丁。
- 原始时序证据保留；模型投影合并同对象/文字部位/原因的重复记录，带首末时间、次数与代表测量。冲突对象作为只读上下文，不能扩大修改范围。至多四张图优先冲突并包含最终状态；长时间序列投影为数量及hash。
- 逐轮保存实际Prompt、附件来源、候选检查结果；超时等异常只记录异常类型及unverified，不重发。原两轮预算、无进展/重复停止、保护、revision/音频守卫和显式save复验保持。
- 顺带修正语义场景Prompt版本替换未命中；当前基础0.3.3、语义0.4.2。SVG helper加入局部候选运行身份，新反馈owner进入生成源码闭包。

遵循`.agents/skills/optimize-prompts/SKILL.md`追踪实际调用输入/附件/解析/下游；`html_scene_repair.py`为原生成与预览/保存入口，`html_repair_feedback.py`只负责证据投影，不写作者、不决定通过。原renderer未修改。合同见editor-repair-context-0.1.0。

## 受控集成及诚实边界

复用脚本`scripts/evaluate_overlap_repair.py`接收每页至多两轮明确操作，冻结原课程后调用原generate/preview/save，并校验语义/动作/binding、音频及历史检查点。命令参数为`--source-run runs/ec60bbd4_010236 --output outputs/新目录 --decisions 决策JSON`；决策格式`{slide_id:[[operation,...],...]}`，output必须不存在。

v1保留：第一页真实失败候选收到新证据后第二轮通过；第三页width600中间方案没有改善实际测量，原tracker返回unchanged_measurements并停止，没有保存该页。v2对第三页使用已验证的width500单轮方案，两页保存均成功。没有为凑足两轮放宽无进展规则。

决策由开发时明确提供，没有模型请求；因此这证明真实内容、真实浏览器及生产调用链集成，不代表真实模型自主修复成功。provider_calls=0、model/cost=null、autonomous_model_acceptance=not_run，human_visual_acceptance=pending_review。

## 验证与下一步

81项相关回归通过，122.32秒，`.tmp/overlap-feedback-regression.log`。覆盖新候选反馈/截图、原稿完整补丁、无进展及异常不重发、范围/人工保护、过期音频、候选保存/快照身份、历史恢复新revision/保护保留/完整性和源变更拒绝。canonical quick通过，`.tmp/overlap-feedback-quick.log`；Ruff与git diff --check通过。未将旧2775项全量结果算作本批验证。

按code-review-and-quality五维复核：证据投影不修改原报告；不同文字部位不合并；截图列表与附件同源；未知请求异常原样向上传播；原保护/原检查/原保存owner保持。没有依赖、Schema/API或数据库迁移。

下一步是使用新任务身份做真实模型修复效果对照，并单独记录模型/输入/预算及失败分母；不重发历史unknown任务。当前仍保持Legacy默认，原课程正式采用和人工批准单独处理。本批未提交、推送或启动正式服务。
