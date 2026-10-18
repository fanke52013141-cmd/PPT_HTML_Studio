# 外部 Agent 如何接手页面局部修复

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
