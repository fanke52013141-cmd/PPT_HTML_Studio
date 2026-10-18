# 可重复捕获、素材恢复与生产需求预检交接

2026-10-18，契约0.9.89 / API1.48 / produce1.11 / Skill1.21。按用户顺序先完成两项，再恢复四页课程。

## 已实现与验证

- 原正式审核、取帧、逐句语义帧与视频工具统一使用captureLaunchOptions的软件合成策略，进入生成/渲染快照、批准与输出指纹。交互GPU分数缩放的抗锯齿限制仍独立，不宣称所有GPU像素一致。
- 相同已接受设计按准确need、设计图hash、模型、参数、参考与返工指令复用已验证素材；重复理解的appearance措辞不再触发付费生成。损坏/缺失匹配缓存明确停止。旧无身份素材不猜测迁移，旧unknown请求不补发。
- visual_requirements进入实际planning_context与修复轮task；normalize/A02原门禁在生图前阻断缺coverage。四页权威需求出站已离线检查，不以计数代替科学语义/视觉签收。
- 71项缓存/语义/四页渲染与需求回归通过；75项快照/生产/恢复回归通过；27项正式导出/音频对齐/快照回归通过。三组文件互异，不将快速检查的重叠用例再累加。原视觉5场景14项通过，无页面错误。canonical quick通过。
- 回归中途一次源闭包变化导致恢复fixture提前失败；完成代码冻结后75项全过。新增快照断言曾误读files结构，修正后通过；保留首跑日志，不冒充首跑全绿。
- 代码按correctness/readability/architecture/security/performance五轴复核：共享正式策略、无重复付费恢复、严格输入与原审批门禁保留，无新增秘密或依赖。

## 本机证据

outputs/capture-preflight-final-regression.txt；capture-recovery-stable-regression.txt；capture-formal-export-regression.txt；capture-policy-visual-test.txt；capture-recovery-quick.txt。
outputs/capture-recovery-preflight/保存原合同备份、拟写需求和来源回执、工程汇总。原四页audio/text/metadata/srt/timeline共20个hash保持用户接受版本。

## 恢复生产边界

原项目ec60bbd4_010236，四页实际HTML仍未保存；001/002原失败与unknown保持历史，003/004未形成正式设计。新需求改变旧设计key，必须原流程重新规划并停在设计审阅；不得给旧候选重签。复用四条原旁白，不重新TTS。真实模型结果、HTML批准、A04、声音当前绑定、整课视频及发布均独立待验。生产恢复状态见本机outputs/capture-recovery-preflight/production-restoration.json，不能把提交任务视为交付完成。


## 真实生产跟进：0.9.90

第一轮恢复后：001设计1fd3604c已返回，但实际计划的端点按舞台比例写入对象内坐标，部分箭头向量和声明方向不一致，不接受/不还原。002两轮分别PLAN_SLOT_KIND、PLAN_VISUAL_COVERAGE，未发生图片调用；实际输出提示漏列visual_coverage。003规划有0℃平台，但图片任务tsk_img_01M56X38ZSZBFVPYT9RQ30SDYK失败；只读原ID查询确认upstream_task_failed，阶段仍unknown、费用null，不补发。004在queued且无stage时取消，零供应商调用。

修复唯一规划Prompt为0.3.5：schema_hint列覆盖字段、说明对象box归一化公式/四边中点；没有放宽解析或增加两轮预算。回归新增用例在旧实现1失败1通过，修正后2通过；相关89项和兼容7项通过。尚未证明真实模型修正成功。所有外部请求收齐后才更改源码。

仅恢复002/004的一次修正版正常生产，保留旧记录。001需要权威计划修正，不能手写本例计划冒充Agent；003原失败/费用待定不重发。当前状态仍不是课程交付完成。
