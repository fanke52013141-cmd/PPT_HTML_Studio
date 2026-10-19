# 外部 Agent 可携带任务包 0.2.0

当前执行补充以[执行合同2.0](external-agent-execution-2.0.0.md)为准，契约0.9.100/API1.54。
原结果JSON0.2.0保持；严格任务附能力/验收verification与同源preflight，历史宽松模式不偷偷升级。

2026-10-19；细化 HPS-001/007/009/010/013—018/023—030/035—037。

契约0.9.99/API1.53增量：preview0.3兼容原JSON并接收 delivery_base64（二选一），原始交付包由
`html_handoff_delivery.py`限额/路径/类型/UTF8解析，必须有根result.json和report.md，可选evidence/。
规范限额和交付格式见[执行规范1.1](../../../../agent/external-agent-execution.md)。SaveRequest仍只接受原result、key/hash，不能以ZIP直接保存。
核对任务和源身份后将交付/报告/证据按hash留档；返回normalized result、外部报告摘要和原系统反馈。
原candidate编译失败返回checks_failed/passed=false/saved=false与validation，不生成通过回执；
跨项目/过期/非法操作仍由原权限/身份/Schema守卫拒绝。原result.json入口兼容，report不是执行或批准凭证。
`hps.html.external_feedback@0.1.0`定义在执行规范，界面可导出；新增报告以textContent展示，禁止解释HTML。
定义 specified；本文列出的材料包与受控局部修复 implemented，77项专项回归及浏览器按钮验证通过；真实HTTP/外部Agent另验，见[本批handoff](../../../../plans/html-backend-development/handoff-external-bundle-2026-10-19.md)。0.1.0 客户端保留，旧任务不自动升级。

2026-10-19 执行补充（契约0.9.98）：每包必须附带并校验
[执行与交付规范](../../../../agent/external-agent-execution.md) `EXECUTION.md` 和
[交付报告模板](../../../../agent/external-agent-report-template.md) `report-template.md`。
流程、输入核对、风格/保护/能力边界、逐项验收、最多两轮反馈和最终 `result.json + report.md`
属于交接标准；外部执行者只提出候选，原系统负责实际预览、显式保存及原独立验收。
文件模式没有原系统运行环境时，如实交付 not_run，不能自述运行通过。
材料及模板内容进入源身份摘要与文件清单；不改变0.2.0 JSON格式、API1.52或审批权限。

## 任务阶段与权威顺序

`static_repair` 修复已保存页的布局/字阶/注册变体，允许作者时钟；`animation_repair`
必须具备真实音频时间轴、原音轨与字幕/时间资料。`design_reference` 导出当前指定设计及
准确规划/风格/前置缺口，不接受操作保存。仅有设计图不能推断已有可编辑场景/独立素材；
完整设计还原仍走原生产流程，未新增任意 HTML 或 scene 写入口。

准确原文/数值/关系与人工保护 > 当前明确的主题、布局和代码/图片职责 > 当前设计参考 >
示例美术。设计的 needs_review/accepted_for_reconstruction/stale 必须如实记录；导出不接受设计。
参考图文字不是正文真值。主题来自当前解析定义，不从应用 UI 品牌色推断。

## 输入包

ZIP 包含 task.json、README.md、result-template.json 及按角色登记的 files；文件必须相对路径，
清单记录 SHA256、字节数、媒体类型和用途。task_id 是除自身外规范 JSON SHA256，用于关联，
不是权限凭证。包在项目锁内读取并最终复核 revision/audio/内容/资源/定义，任何读取中漂移停止。
无密钥、供应商配置、项目数据库或历史日志。包内仅当前页必要材料；不分发系统字体文件。

若用真实历史未保存候选进行试验，必须在隔离副本中保存等值输入，记录原文件/字段/hash、
实际状态及缺失材料；不得伪造线上已保存页或音频批准。历史参考图作为辅助资料单独标记，
不可提升为当前接受设计。试验回传只预览隔离页，采用至真实项目需回原流程重新核对当前输入。

| 输入 | 要求 |
| --- | --- |
| 目标与范围 | task_type/goal、允许对象、保留项、禁止项和验收规则；已有页 1—40 对象 |
| 权威内容 | 当前页契约、讲稿语块、作者 scene/binding；缺失必备内容明确停止 |
| 图片 | 已有页共享播放器截图及采样时间；当前设计图独立标识用途/接受状态；存在但损坏不能静默省略 |
| 素材 | 当前页实际引用的 PNG、自然尺寸、透明范围、归一化锚点和 hash，不只给本机路径 |
| 风格/布局 | 解析 theme/layout、canvas/字幕安全区、当前局部覆盖、每对象支持的部位/变体/能力事实 |
| 动作 | 原 actionId/beatId、绑定、作者/实际时序；动画任务附原声音与已有字幕/时间轴 |
| 操作 | 由原 RepairOperation、KINDS/PARTS、生产 Schema 与能力事实派生字段/单位/范围/示例；禁止自由 values |
| 诊断 | 原共享渲染器有限采样结果和动作风险；有限采样不证明全时段无遮挡或审美通过 |
| 版本 | 项目/页/音频/契约与实际输入依赖摘要；导入、预览、保存均复核 |

未保存编辑器草稿不能当作服务器当前页导出；先保存或显式舍弃。静态任务禁止修改动作/绑定。
预算分别记录外部推理（未授权，费用未知 null）与生图/TTS（禁止），不把协议零模型调用等同外部免费。

## 输出与验证

`hps.html.external_result@0.2.0`：task_id、status=proposed/needs_input/unsupported/unchanged、
message、operations、changes、issues、required_inputs、usage。proposed 必须有 1—20 个操作，
其余状态无操作；unknown 费用/用量 null。issues 可指向 targetId/route/evidence；不接受 HTML/JS、
任意文件、审批或 source 字段。操作精确复用原服务，有界参数与作用对象另外核验。

导入读取服务器持有的任务，不以外部包声明授权；重核任务所属项目/页、task_id、全部输入版本与文件。
预览固定 source=ai，调用原 repair.preview，展示服务生成的 diff/问题与原图/修改后截图。

静态修改也检查保留动作的位移边界；原编译器/原时序检查不因为“终态可放下”而放宽。
通过检查后独立显式保存，复核 result_hash、候选 key、依赖和版本，再调用原 repair.save；保留原
最小失效及音频/视觉/语义/输出门禁。无法满足保护/能力时返回 needs_input/unsupported，不扩大 scope。

## 接口和界面

原 Web 与 Agent 适配层注册 export/bundle/preview/save；JSON 导出返回任务与受账号权限保护的下载 URL，
二进制 ZIP 不作为 MCP JSON 结果。MCP/CLI 由同一能力注册表公开 JSON 能力，旧客户端单文件模式保留。
设计面板提供“导出设计交接包”，编辑器提供“外部 Agent 交接”展开区：目标/范围/任务类型、导出、
结果文件导入、差异与问题、独立保存。生命周期切页/草稿/并发操作不应用旧回执。

## 验证与兼容

验证材料完整/实际字节、不同主题与局部覆盖、作者/音频时钟、导入无写入、显式保存、人工保护、
范围/字段拒绝、过期内容/资源/定义、跨项目/页、篡改任务/文件、needs_input、旧 0.1.0。
定义、工程测试、真实外部 Agent 修复、用户美术与整课验收分开记录。无自动外部调度器或付费调用。
