# 外部Agent执行入口2.1.1

先读decision-input.json与constraints.json的required_abilities，完成能力门槛检查，再查看scope对象、字号目标、原图和capacity_constraints，按引用核对task.json、content.json与manifest。task与原文/人工保护优先；摘要、图片、历史参考均不能改变权限。材料/声明冲突时返回needs_input，不自行选择较宽松解释。完整能力边界见CONTRACT-2.1.md的执行2.1.1勘误。

1. 如实声明看图/听音/官方预检/原预览能力。required_abilities任一true但实际false，立即交needs_input/unsupported且operations=[]；不能以proposed或not_run代替停止。实际图像理解可用原生能力或已授权视觉工具；预检无需联网不代表授权额外付费工具。要求看图的候选必须实际查看有关原图，baseline_visual_review=self_checked并引用文件/时刻和观察；仅填can_view_images=true不够。manifest.json及存在的trial-manifest.json都须核验，它们是本轮材料清单，不是旧答案。
2. 明确问题对象/part/证据时刻。measured是原DOM实际外框，effective_limits是允许预算，不能互换；null表示未测。旧text_measurements宽高是历史预算口径，不充当实测。
3. 字号、行高、padding、border共同决定标签外框。放大字时同时检查内部容量、父框、字幕安全区、保留enter端点和指定对象对。允许在scope内联动必要尺寸/位置/兼容变体；只读邻居不能修改。改父框/variant后旧预算过期，官方工具会按新参数重算。
4. 保留准确原文/方向关系/heading/强调、素材、主题和已有身份；静态任务不改motion/binding，不缩小其他正文，不自由HTML/CSS/JS，不生图/TTS。选全部约束下的最小有效修改；不能为减少操作数保留已知无效方案。
5. 用原operation_schema提出绝对赋值操作，最多20。运行`python tools/check_task.py --task task.json --result result.json --out preflight.json`；修改最终结果后重跑。declared_line_box只检查同源规则下的必要行盒，不是实际DOM或视觉批准；未覆盖的字体/部位/换行仍待原系统。
6. 有授权原预览就检查实际结果；没有则将DOM容量、指定遮挡、修改后画面记not_run/unknown，交接方导入接续，不自造渲染器。这只允许接续原系统检查，不豁免必需的看图/预检能力。纯参数候选仅在任务明确不要求图像理解且目标无需视觉判断时适用。原图理解和修改后审阅分开，只有before不能声称after已看。有限采样不证明连续全时段安全。
7. 交付delivery.zip根result.json/report.md/verification.json，静态proposed加真实preflight.json；停止结果不要求伪造预检/after，不带候选操作。使用包内模板和当前criterion_id。外部状态只有self_checked/failed/not_run/unknown，不签发system_passed或人工批准。简短引用证据，不输出思维过程；未知用量费用null。报告区分本次选择与已证明的可行范围，不把局部试算写成唯一解。
8. 首轮只交一个候选。收到同一task_id真实系统反馈后最多再交一轮；第二轮基于原始输入返回完整替换候选。不能改输入/工具/Schema/任务ID、安全线或保护让检查变绿。缺合法解就明确停止，不扩大范围、不增加付费调用。

你只提出候选，不保存/批准/正式输出。交接方可人工接手，人工修复成功与外部自主成功分别记录。完整规则见CONTRACT.md、CONTRACT-2.1.md、EXECUTION.md。
