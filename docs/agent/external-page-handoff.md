# 外部 Agent 如何接手页面局部修复

当前勘误：执行2.1.1/契约0.9.102/API1.55.1。缺本任务必需能力必须交needs_input/unsupported、operations=[]，不能以“参数候选”或not_run豁免。要求看图的候选须完成有实际证据的原图审阅；文件模式after/原播放器可交系统接续。manifest及存在的trial-manifest是本轮校验材料，冷启动也须读取。规范/源码变化后重新导出，旧试验包和失败结果保持历史。

当前功能：[执行2.1.1与人工接手](../contracts/html-presentation/runtime/visual-v1/external-agent-workbench-0.1.0.md)。先读ENTRY/decision-input；原图和after分开，容量actual/limit分开。网页可填字号/对象对并从合法候选创建持久人工工作草稿，更新/撤销后重验；来源与叶保护由主机管理。API1.55.1，外部Agent只有work_read只读能力。

## 新任务：执行规范2.1.1

当前Agent API1.55.1；正式[执行合同基础](../contracts/html-presentation/runtime/visual-v1/external-agent-execution-2.0.0.md)与[2.1.1勘误](../contracts/html-presentation/runtime/visual-v1/external-agent-workbench-0.1.0.md)共同适用。
界面默认严格交接，输入带constraints.json、verification Schema/模板及tools/check_task.py和原生产compiler的独立Node工具。
按EXECUTION读真实图/内容/风格、声明能力；生成静态候选后运行官方便携预检。
交付ZIP根目录result.json/report.md/verification.json，静态proposed附preflight.json；导入后原系统独立复核，再显式保存。
预检不覆盖DOM文字容量、实际遮挡、音频或审美，不把not_run当通过。下文旧JSON入口兼容，严格任务不能只交单文件。

## 推荐入口：可携带任务包 0.2.0

当前协议见[0.2.0 定义卡](../contracts/html-presentation/runtime/visual-v1/external-agent-handoff-0.2.0.md)，当前执行规范2.1.1/Agent API1.55.1。下文0.1.0命令保留兼容，不包含图片/素材打包能力。

每包必须包含[执行与交付规范](external-agent-execution.md)与[报告模板](external-agent-report-template.md)：
先核对真实输入/图片/风格和权限，再诊断、最小修改、自检、最多两轮真实反馈，最终交付
`result.json + report.md`（旧JSON模式；严格模式按上文交完整ZIP）。外部逐项状态不得自填system_passed；真实原系统回执单独引用。仅文件执行的原播放器/修改后画面项写not_run，不豁免必需能力和原图理解。
实际验收、显式保存和人审由交接方继续完成。[本次真实 Token 试验任务](real-trial-token-2026-10-19.md)
记录来源、隔离副本、具体目标和回传方法。

在“调整页面与动画”中展开“外部 Agent · 导出输入 / 导入输出”，填写目标、选中对象，选择布局/风格修复或真实配音/动画修复，点击“导出输入包”。有未保存草稿时先处理草稿。设计图页的“导出设计交接包”提供原图、权威规划与风格；不是已经生成的可编辑页面，不能直接保存修复操作。

将整个 ZIP 交给 Agent，先读ENTRY.md、decision-input.json与constraints.json的能力门槛，再按引用读取task.json及其余材料。包内content.json是准确内容，reference/design.png是标注状态的设计参考，evidence是共享播放器实际截图，assets是原独立素材。当前theme/layout、人工保护、操作Schema和原时间资料随包提供。图片不可覆盖原文/主题约束，禁止任意HTML/JS/整页位图替代文字。

Agent 根据 result-template.json 返回 result.json：保留 task_id/version，填写 status、message、operations；可附 changes、issues、required_inputs、usage，费用未知写 null。需新对象/能力/素材或资料缺失时返回 needs_input/unsupported。静态任务只接受布局/字阶/变体；动画任务可以改既有动作/绑定，必须保留真实音轨和稳定身份。

点击“导入 Agent 输出”，严格任务选择delivery.zip（根result.json、report.md、verification.json；静态proposed另附preflight.json，可选真实evidence/）。单独result.json仅用于旧兼容模式，不满足严格交付。
报告作为外部自述纯文本展示，原交付按hash留档；系统复核材料/版本/保护并生成前后画面、差异与检查。
编译失败时展示真实错误、保存按钮保持禁用，不伪造修改后图；点击“导出检查反馈”返回同一Agent修订。
导入不保存；通过检查后由“保存本次候选”显式保存。保存不代表画面/逐句语义签收，继续原验收流程。
来源、素材、主题、音频、API或运行定义变化后重新导出，不能改旧结果ID冒充新任务。

HTTP 使用 `/api/agent/v1/projects/{project_id}/html-visual/{slide_id}/handoff/{export,preview,save}`；bundle 为 `/{task_id}/bundle` 二进制下载，不是 MCP JSON 工具。JSON 三项在同一能力注册表公开为 `ppt_html_handoff_export/preview/save`。

CLI 示例（export-request.json 按当前 editor-read 提供 expected_revision、scope、task_type、goal）：

```powershell
python -m cli.pptctl html handoff-export --project PROJECT --slide SLIDE --file export-request.json
python -m cli.pptctl html handoff-bundle --project PROJECT --slide SLIDE --task-id TASK_SHA256 --out task.zip
python -m cli.pptctl html handoff-preview --project PROJECT --slide SLIDE --file import-request.json
python -m cli.pptctl html handoff-save --project PROJECT --slide SLIDE --file save-request.json
```

import-request.json 为 `{"result": <result.json内容>}`；save-request.json 为同一 result 加预览返回的 candidate_key/result_hash。服务器持有原任务，不接受调用者改写任务范围或身份。原 API 认证仍在本机/环境配置，不放进 ZIP。协议不调用外部 Agent，不把导出或人工构造结果当作自主修复成功。

ZIP传输在同一preview入口使用 `{"delivery_base64":"<原delivery.zip的base64>"}`，与result二选一；
归档报告/证据的限额和安全路径见执行规范。返回feedback可保存为JSON交给外部Agent，导入不等于采用。

## 旧客户端单文件协议 0.1.0

现有Agent API/MCP可由其他Agent直接使用。本客户端把已有调用组合成可交换JSON，适合可调用HTTP/MCP的Agent，也适合只能读取任务文件、输出JSON的Agent。不会自行启动或计费调用外部Agent。协议见[定义卡](../contracts/html-presentation/runtime/visual-v1/external-agent-handoff-0.1.0.md)。

内置Agent负责自动编排；系统服务负责原文、人工修改、素材、音频、检查、保存和验收。外部Agent可以提出修改，不能用自述结果替代验证和人审。这次课程中的程序修复不算内置Agent自主成功，外部Agent也采用同一评判标准。

先导出任务（命令参数`--output`为根参数，放在子命令之前）：

```powershell
$env:PPT_AGENT_API_URL = 'http://127.0.0.1:8010'
# 需要认证时，仅在本机环境设置 PPT_AGENT_API_KEY，不交给任务文件。
python -m agent_client.html_handoff --output task.json export --project PROJECT --slide slide_001 --goal '让热量传递动作随讲解展开，保持原文与人工调整' --scope obj-relation-1 obj-relation-2
```

将task.json交给选定Agent。它按文件内`result_schema`与`operation_schema`返回result.json；这里的内容只是操作建议，没有保存行为。例如：

```json
{
  "format": "hps.html.external_result",
  "version": "0.1.0",
  "task_id": "复制任务包中的64位task_id",
  "status": "proposed",
  "message": "拉长原箭头绘制动作；保持原关系与文字。",
  "operations": [{
    "targetId": "obj-relation-1",
    "kind": "set_motion",
    "action": "enter",
    "actionId": "复制任务包中的既有actionId",
    "values": {"durationMs": 2400}
  }]
}
```

先运行原服务预览，审阅回执中的review/issues；不满足检查时修正结果或返回无法完成原因：

```powershell
python -m agent_client.html_handoff --output preview.json preview --task task.json --result result.json
# 仅在决定采用修改后执行；这一步保存作者，会使相关旧批准失效。
python -m agent_client.html_handoff --output saved.json save --task task.json --result result.json --receipt preview.json
```

同一个结果只保存一次。版本/音频/契约变化后重新导出任务，不盲目重试写入。保存后继续原独立语义审核、用户画面决定与正式输出流程。客户端不提供审批、TTS、生图或任意文件写入给结果执行者。

第一版没有远程调度器、外部服务商配置或自动故障转交。后续若接入具体Agent，先用相同固定任务比较内置/外部：有效修复率、误改率、人工介入、轮数、耗时与费用；没有报账的费用记null，失败/unknown计入分母。只有外部实际更好时才增加有预算上限的自动转交。图片审美仍需实际画面证据；结构化任务包不代替图片/视频访问。

## 最小输入视图（2026-10-22 追加）

任务包同时提供 `task-minimal.json`（hps.html.external_minimal_task 0.1.0）：只含 scope 内对象、类型化缺陷、确定性候选、相关文件引用、操作 schema 与结果契约、幂等键/回执要求。`task.json` 仍是权威且不可修改；最小视图是派生输入，候选仍须原编译器与 QA 验收，unknown 不得盲目重发。
