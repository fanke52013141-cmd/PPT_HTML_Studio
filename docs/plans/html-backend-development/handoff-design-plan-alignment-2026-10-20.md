# 设计图与计划对应修复及新对照任务

契约0.9.108，API1.59.0保持。当前源码未发布，正式服务未重启。前序参数验证见[GLM原生参数交接](handoff-glm-native-parameters-2026-10-20.md)。

## 核查结论

原A06 Token课程slide_003有5句讲稿、6个视觉对象、8个动作；讲稿主张均有对象承载。原参考图自行增加两处输入/输出药丸标签及引导箭头，并在底栏增加“费用怎么算”和改述。这些不在冻结slots中。缺少的是设计生成阶段的严格对应约束；不能据此判定原讲稿计划漏义，也不能靠放宽理解门禁接受计划外语义。

| 讲稿语块 | 准确视觉对象 |
| --- | --- |
| 分开看输入和输出 | header-usage-split |
| 输入由提示和上下文构成 | stat-input-token |
| 输出为回复单位 | stat-output-token |
| 不同单价及缓存/推理类别 | stat-input-token、stat-output-token强调；stat-pricing-cat、caption-pricing入场 |
| 实际用量结合价目表 | summary-billing |

原讲稿、原文、对象ID、动作ID、计划和原图历史不改写。修复归属是设计参考生产，不是局部静态修复或手写计划。

## 系统修改

html_reference_package新增screen_text_sources，准确记录逐槽位可见字段路径，runs按顺序组合，同文多来源仍保留各自出现。实际生图Prompt0.3.1/0.4.1禁止额外标签、重复结论、补heading和引导箭头。历史包修订从其冻结slots同源派生清单，不修改历史manifest。该文件本来已进入设计定义及生产快照闭包，无新增Schema/迁移/运行Skill片段。

对应规则见[设计图与计划对应卡](../../contracts/html-presentation/runtime/visual-v1/design-plan-correspondence-0.1.0.md)。必要标签、关系和独立审核仍有阻断资格；不把图内文字降级为装饰。

## 新图与签发

本机证据outputs/pi-design-alignment-20261020。实际通过原HtmlWorkflowJobs生产修订入口调用图片模型一次，任务html_eae1142a1bc24150a014；生成新key：
`e03846936666898de72b031f6581235dc9ea99992bb0adebe66c065be61b54cd`。

当前Agent实际看图核对：两处多余标签/箭头及底栏新增文案已去掉；计划正文、from/to、term、takeaway均保留。原图字形/空格/标点仍不得覆盖代码准确内容。此项是输入对应核查，不是用户审美签收、OCR逐字认证、HTML或音频验收。

新对照任务token-slide003-design-alignment-20261020已写入comparison-task.json并带manifest_sha256；plan-reference-audit.json保存逐句对象/动作对应。Legacy/Pi使用相同冻结计划、新设计PNG、模型及参数：glm-5.3-flash、thinking enabled、65536、temperature1.0、供应商默认推理强度（与上一轮原生参数实验一致）。每边900秒总预算、600秒阶段预算、至多12次外部调用（Pi10次文字+2次图片）、24次Pi工具、两轮还原。原unknown请求不重发。

流程：校验来源hash/当前设计→设计理解→原组件编译和工程检查→真实截图独立审核→既有有界修复→允许时仅写隔离实验作者。不得写源课程、声音或人工批准。输入阶段合法停止与新页成功分别统计。

交付：m4-legacy.json、m4-pi.json、m4-pair-summary.json、原local_jobs及阶段回执。成功须有合法分工、原工程检查和实际截图审核；不能以job succeeded或HTTP200代替业务验收。未知usage/cost记录null。

## 本轮验证

checks/test_html_semantic_design.py与checks/test_html_e_production.py：63 passed（已有Starlette弃用警告）；另对历史包修订不改字节的新增断言定向重验通过。Ruff和定向git diff --check通过。原Web/Agent请求一致性断言同步当前已存在的runner/pi_limits/max_image_calls默认值。新图已经实际生成并核查；新页对照终态见本机结果文件，声音及成片未测。

签发后首个真实进展：Legacy任务html_ffc19da60288495f9a70在247.9秒后完成设计理解，status=ready、6个合法对象、issues=[]。当前进入原容量修复，不能当作整页成功。Pi由同一对照脚本顺序派发；如果前路出现unknown，脚本会停止并保留尚未执行项，禁止原样重放。运行状态可读outputs/pi-design-alignment-20261020/execution-state.json；最终结果以原数据库和m4结果文件为准。

## 本轮最终对照状态

后续确认：Legacy设计理解ready（247.9秒）后，原容量修复请求180秒超时，任务终态failed，外部结果EXTERNAL_OUTCOME_UNKNOWN。两次文字适配调用，独立素材0次；作者revision=0、无scene、无批准，原课程hash保持。总运行449.062秒。统计usage/cost不完整，保持null；试验脚本metered_tokens=0只是未获取到完整usage，不是零消耗。

容量修复未知请求身份为`7c37345a6876a7553140ac2c5fa7fa93dc1c611497f697f97839f60dc31d3677`（应用侧身份，不保证可供服务商查询）。原对照脚本触发未知结果停止策略，Pi未启动；本次没有完整双边结果，不能计算Pi相对提升或宣布新页成功。不要直接重新运行run_pair.py。先核实原未知回执，再对已知失败输入作实质修订并另签任务；如单独执行未启动Pi，须明确独立实验与原冻结输入身份，不能冒充本轮配对完成。

证据位于本机outputs/pi-design-alignment-20261020/m4-legacy.json及m4-pair-summary.json；这些运行文件不随Git发布。仓库交接以本节终态为准，上文“当前进入容量修复”为早先过程记录。
