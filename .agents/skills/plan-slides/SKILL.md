---
name: plan-slides
description: Plan PPT Studio narration and visual intent from the full article, preserving source wording and beat coverage. Use for 分镜规划、演讲稿分页、讲稿视觉映射; HTML object planning remains a separate registered stage.
---

# 讲稿与视觉分镜

读取 [共用边界](../workflow-contracts.md)。本Skill负责完整文章→逐页讲稿→视觉意图，不把Step2视觉意图当最终HTML对象计划。

## 路径与来源

通过原分镜script/visual/compose服务按阶段执行，产出slide_script_plan.json、slide_visual_plan.json与visual_contract.json。stage映射、Schema和实际字段以storyboard_planning.py、storyboard_profiles.py及当前模板为准。

1. 讲稿阶段读完整article.md及用户受众/页数要求，每页推进一个认知动作；保留事实、条件、否定和范围，不能把“没有统一适用标准”弱化为任意“没有标准”。不为凑时长/页数补造事实。
2. 视觉阶段读本页完整讲稿，只切连续非空片段；按顺序拼接必须逐字复原旁白，不改页序/标题，不重复或丢标点。让每个需独立出现的语义有明确意图，不预设正文数量。
3. 图片backend按当前原子Mask/Reveal合同组织元素：标题一个组，独立视觉岛不合并；HTMLbackend保留当前分镜意图，后续produce再生成plan0.2的对象/角色/多actionId，图内标签和关系归代码。
4. compose后核对覆盖、顺序、来源和真实下游状态。结构通过不证明语义正确；限定词检查失败回讲稿，不靠后续配音修正文案。

遇到script_review时读取原候选和原文对照，通过原script/result附当前review_id保存修正；不自动接受、补发或改正式文件。过期候选不能提交。保存通过后继续原课程，复用已修正讲稿进入visual/compose，不重新生成script；原intent/unknown仍按原门禁核实。

取消/占用停在原阶段核实；不重复已未知请求。例：一个正文元素可合法，复杂表达可拆页；不为格式补空旁白。
