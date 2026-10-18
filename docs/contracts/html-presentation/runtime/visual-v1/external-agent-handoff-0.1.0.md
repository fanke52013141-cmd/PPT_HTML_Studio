# 外部 Agent 页面交接与动作诊断 0.1.0

2026-10-18；HPS-007/009/013/014/015/017/018。定义 specified、实现 implemented；协议离线/本地传输与真实外部 Agent 效果分别验证。

| 项目 | 规则 |
| --- | --- |
| 归属 | `agent_client/html_handoff.py` 是现有能力的客户端组合；不是新后端、队列或模型调用服务。HTTP/MCP/CLI 原能力注册表仍唯一。HTTP API1.51，repair preview/save1.7、evidence1.2、generate1.4 |
| 输入 | `hps.html.external_task@0.1.0`：task_id为去掉自身后的规范JSON SHA256；project_id/slide_id、goal、scope、contract_hash、expected_revision、audio_revision；context含原作者scene/binding、原人工protected_paths及真实音频bound_scene/timing。含原RepairOperation与ExternalResult派生JSON Schema；不导出API密钥或项目配置 |
| 范围 | 第一版仅已保存且具真实音频时间轴的页面局部修复。1—40个唯一现有对象，1—20个原注册操作。缺对象/需重规划/需生图或TTS返回unsupported或needs_input；不接受任意HTML/JS、全页替换或模型自己的成功声明 |
| 输出 | `hps.html.external_result@0.1.0`：task_id、status=proposed/needs_input/unsupported、message、operations。proposed必须有操作，其他状态不得带操作；额外字段拒绝。操作Schema复用原RepairOperation，服务保留字段/语义验证 |
| 预览 | 客户端重核packet散列、契约、当前页/音频版本与scope；固定source=ai，通过原repair.preview返回candidate_key/动态检查，独立回执绑定task_id和结果hash。原人工保护/目标动作/合法字段服务守卫为权威。输入hash用于关联和误改检测，不是签名或权限凭证 |
| 保存 | 单独显式save命令，要求匹配结果与通过检查的预览回执，仍走原repair.save。请求带expected_audio_revision，冲突按原AUDIO_REVISION_CONFLICT返回409；候选key额外绑定实际音频revision，最终save_editor重核同一音频。无自动重试、无自动审批 |
| 复用 | 不调用provider/生图/TTS；无作者修改的export/preview不失效现有作品。真正save仍走现有最小失效服务；声音、语义、视觉、正式输出门禁保持 |
| 兼容 | 既有请求的expected_audio_revision可省略。旧候选key因补入音频身份需重新preview，不自动保存；旧scene/音频/renderer不变。API版本与生成Schema同步；SDK交换格式独立版本化 |

`html_motion_activity.py`只读分析已绑定scene：按beat合并实际动作时间区间，给active_ms、static_fraction和longest_static_interval_ms。至少三个目标的讲解段，静止区间≥max(4秒,段长60%)提示long_static_interval；至少三个enter起点差≤100ms、均≤1秒、讲解段≥4秒提示simultaneous_short_entrances。单一引导标题不触发群组警告。

这是**时间安排诊断**，不证明像素有移动、语义正确或动画好看；不加入正式渲染阻断、不自动补运动。复杂长动作也可能无实际视觉变化，需共享播放器/成片证据。JSON/模型叙述均作为数据；身份、scope和原服务边界不由外部结果更改。

原repair.evidence/preview/save报告也提供motion_activity，原内置修复Prompt0.3.2的实际temporal_report保留这一诊断，输出解析与两轮预算不变。动画诊断与修复模型作为生成源码闭包冻结；不改渲染器或既有画面批准指纹。匿名字幕段按beat_index定位，不伪造语义beat_id。

验证包括：原同时500ms入场被标记、错峰draw-on不触发这两条风险、重叠区间不重复计时、无动作/跨语块裁切、过期版本/音频/契约、篡改任务、越scope、source=human及错结果回执拒绝；原人工保护与API/MCP/CLI回归仍需通过。真实外部Agent的独立成功率/轮数/费用未验证，不能把人工构造的协议回传称为外部Agent自主完成。
