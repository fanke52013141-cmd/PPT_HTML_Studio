# 设计生产与恢复

处理新生成、局部设计修订或失败恢复时读取。规则唯一源是仓库 `docs/contracts/html-presentation/runtime/visual-v1/` 下 application-production、design-review-authority、production-recovery、course-pause 和 stream-failure-evidence 对应版本卡。

- 新生产使用html_review.produce；当前语义生产明确plan_version=0.2.0。独立plan_generate是诊断，不会自动被produce复用。代码页/复用主体也先生成完整设计并停在待审。
- candidate key＋design_instruction是基于原计划/原图的修订；key单独表示用户明确接受该具体设计后继续还原。不能用“继续”替任意新图签收，更不能把设计接受等于HTML视觉批准。
- 设计理解用准确内容、主题和实际工具做分工；图内标签/关系归代码，image仅非语义插图。原图错字和彩色不覆盖正文/灰阶主题。缺对象回planning、缺工具回capabilities，非语义图片才assets，实际可改字段才reconstruction。
- 模型只返回注册静态操作，共享组件生成画面；不自由写CSS、不修改讲稿/节点身份/动作。新多标签和变体读labeled-explanation卡；超预算停止，不让图片补字。
- 容量修复至多3轮、受控还原至多2轮；实际预算/轮次从阶段记录查，不另起任务清零。理解/还原/审核显式600秒、规划1800秒；SDK单次读取等待另计，以实际progress为准，不降低模型思考。
- 独立审核使用原设计与实际截图，pass仍待人工；布局工程通过不等于静态保真、逐句QA或音频通过。

恢复读task_current/task_status。对原冻结请求使用task_resume，仅当输入、attempt、预算、回执及产物允许。原task intent/unknown或同步无ID超时禁止补发；可查任务只查原ID。源变化或过期候选不重签为当前。

manual_candidate只读重演未保存证据，真实评审者可沿manual_candidate_decision记录决定；它不提交作者、不恢复任务、不批准正式视觉。工程失败只能驳回，原失败保持。课程父任务取消/占用回原分镜核实，已取消子任务不复活。
