# 设计生产与恢复

处理新生成、局部设计修订或失败恢复时读取。规则唯一源是仓库 `docs/contracts/html-presentation/runtime/visual-v1/` 下 application-production、design-review-authority、production-recovery、course-pause 和 stream-failure-evidence 对应版本卡。

- 新生产使用html_review.produce；当前语义生产明确plan_version=0.2.0。独立plan_generate是诊断，不会自动被produce复用。代码页/复用主体也先生成完整设计并停在待审。
- candidate key＋design_instruction是基于原计划/原图的修订；key单独表示用户明确接受该具体设计后继续还原。不能用“继续”替任意新图签收，更不能把设计接受等于HTML视觉批准。
- 设计理解用准确内容、主题和实际工具做分工；图内标签/关系归代码，image仅非语义插图。原图错字和彩色不覆盖正文/灰阶主题。缺对象回planning、缺工具回capabilities，非语义图片才assets，实际可改字段才reconstruction。
- 模型只返回注册静态操作，共享组件生成画面；不自由写CSS、不修改讲稿/节点身份/动作。新多标签和变体读labeled-explanation卡；超预算停止，不让图片补字。
- 容量修复至多3轮、受控还原至多2轮；实际预算/轮次从阶段记录查，不另起任务清零。理解/还原/审核显式600秒、规划1800秒；SDK单次读取等待另计，以实际progress为准。GLM设计理解、还原与审核采用请求级low思考，thinking仍开启；仅完整返回但分工不合法时允许一次带诊断的修复，未知结果不重发。
- 独立审核使用原设计与实际截图，pass仍待人工；布局工程通过不等于静态保真、逐句QA或音频通过。

恢复读task_current/task_status。对原冻结请求使用task_resume，仅当输入、attempt、预算、回执及产物允许。原task intent/unknown或同步无ID超时禁止补发；可查任务只查原ID。源变化或过期候选不重签为当前。

manual_candidate只读重演未保存证据，真实评审者可沿manual_candidate_decision记录决定；它不提交作者、不恢复任务、不批准正式视觉。工程失败只能驳回，原失败保持。课程父任务取消/占用回原分镜核实，已取消子任务不复活。

能力早停与审核事实核验读design-agent-facts-0.1.0：当前/适用变体结构事实优先；不支持的required_features在下游调用前停止。审核建议重复切换已启用变体时保留缺陷、转capabilities核实，不视为有效修复。

参考适配与跨轮审核读reference-workflow-policy-0.1.0：纯装饰必须显式类型与适用对象匹配后保留为观察，不因minor忽略语义/结构/排版问题。缺装饰图标优先省略；不再逐页补装饰能力。审核必须核对前轮未解决问题，未变对象区域不能凭新pass清除。

首轮审核覆盖读first-review-coverage-0.1.0：逐实际对象/维度检查，coverage缺项/重复/不确定/问题引用不符都不能通过，不以空issues推定审全。重复验证固定同一截图，分别报告检查声明完成、已知问题召回与一致性；不据此增加修页轮次。

首轮局部证据读local-review-evidence-0.1.0：同坐标参考窗口不是已识别对象框，必须核对整图身份；每对象窗口/缺失原因及派生hash可查。原全量覆盖、单次请求/4图预算与uncertain阻断保持，不据此声称视觉稳定。

局部对照真实实验未达标，默认关闭，仅显式实验可用；默认0.10.0只消费与唯一typography coverage一致的已知重复对齐元数据。原失败与新解析离线回放分开，不把回放召回记为新模型验收。

当前默认首轮审核见review-facts-localization-0.1.0：模型只返回逐对象/维度facts，程序生成issues/coverage/status，普通text参考对齐与当前合同自动比较，不再要求模型另写同一对齐问题。事实不确定仍停止；旧归档可读不等于新生产接受旧协议。独立参考定位不接收HTML坐标，区域只标model_proposed_unverified，先验证完整框/身份/负例，不能直接接回生产当已确认区域。

独立定位当前0.2.1使用image_size/绝对像素和region_scope，不靠type=text猜是否整卡片；未定位文字可null，located文字须实际转录。真实原响应回放15/18区域过阈值，来源文字仍误取背景条，暂不接生产。明确finish_reason=length属于已知输出额度耗尽，与unknown分开核实，原误分类不回写，禁止靠盲目重发补齐样本。

正文/背景区分以reference-text-regions-0.1.0为准：定位0.3.0分别返回container_box与text_boxes，程序按scope选范围，缺正文不能拿背景代替。固定案例真实18/18选定区域通过，但背景容器报告仍有遗漏；正文范围、容器召回、身份和审核接入分别验收，不能用单图评分替代泛化或人工批准。

分层验收见reference-layer-evaluation-0.1.0：定位0.4.1显式报告container_presence，正文完整和容器召回独立打分。not_found可无identity_evidence但必须absence/无框/无转录；located/ambiguous依据仍必需。真实0.4三次一份协议失败，原响应经0.4.1回放联合2/3；标题编号漏框仍失败。回放、真实模型和人工批准分开，不以背景15/15升级整体通过。

定位0.5.0按内容路径核对number/title/正文/关系词的逐片段转录与像素区域，程序派生文字包围盒；见reference-part-mapping-0.1.0定义卡。缺字/异文不照抄输入伪造定位。结构完整不代表像素正确；跨版式夹具与真实页、重复稳定性分别报告，不自动接入正式审核。

文字边缘核验见reference-text-edges-0.1.0：定位结果edge_verification是本地像素诊断。possible_clip需复核，uncertain不能当通过；no_detected_clip也不证明OCR/完整性。保留原框/转录，不自动扩框或触发新提供者请求；旧响应另存诊断，正式审核准入仍关闭。
