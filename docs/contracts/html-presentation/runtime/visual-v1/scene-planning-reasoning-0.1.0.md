# HTML 场景规划推理预算 0.1.0

2026-10-16。关联 HPS-014—017、011/013。范围仅为 `html_visual_review_service.generate_scene_plan` 发出的结构化 HTML 场景规划请求；不改变项目模型绑定或其它规划、写作、设计理解、还原、审核、图片和音频阶段。

## 定义卡

| 项目 | 规则 |
|---|---|
| 目标 | 避免受严格结构校验的场景 JSON 请求把固定 completion 上限耗尽在冗长推理中。真实 GLM-5.3 规划曾以 `finish_reason=length` 结束：completion 64,000 tokens 中 62,196 为 reasoning tokens，输出 JSON 不完整。 |
| 请求策略 | 对 GLM-5.3、GLM-5.3-Flash 与 GLM-5.3-FlashX 的 HTML 场景规划请求显式发送 `reasoning_effort=low`，仍发送 `thinking.type=enabled`。不得将 override 写回项目绑定或冻结配置。其它模型不接收 GLM 专属 override。 |
| 保持项 | 使用原选定 planning 模型、冻结输入、温度、max_tokens（当前用户配置上限 65,536）、JSON 模式、规划 Prompt、超时、严格校验与最多一次完整响应结构修复。格式兼容回退及完整但语法错误 JSON 的修复沿用本请求的实际推理级别。 |
| 隔离 | 仅 HTML 场景规划调用使用该策略。讲稿生成、其它全局/项目文字调用以及设计理解、还原、图片、TTS 和审核继续使用各自模型绑定的配置。 |
| 证据 | 场景规划 request.json、适配器调用日志及流状态记录可显示实际请求推理级别；仅记录 low/high/max 标量，不保存思考文本、密钥或端点。 |
| 失败 | 不完整流继续归类为 incomplete_response/unknown，不进入 JSON 修复，不自动重发。已有未知请求与新请求身份严格隔离。 |
| 接口/数据 | 无公共 API、数据库、作者格式、Agent schema 或模型绑定 schema 变化；旧任务和项目绑定不迁移。 |

## 验收与限制

离线检查验证：场景规划传入 low override；thinking 保持 enabled；65,536 max_tokens 不变；绑定对象原值仍为 max；流证据记录实际 low；未指定 override 的常规 JSON 请求仍使用冻结绑定的 max；规划结构校验和未知结果禁重发保持。离线检查不证明真实供应商会更快完成或一定返回合法 JSON。失败的真实任务仍保留为 unknown；任何新实时供应商验证都必须作为独立新实验明确发起。
