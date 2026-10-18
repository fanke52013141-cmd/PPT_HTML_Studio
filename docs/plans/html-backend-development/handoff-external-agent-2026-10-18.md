# 动作诊断与外部Agent标准交接

2026-10-18；契约0.9.96、API1.51、repair.preview/save1.7、evidence1.2、generate1.4；本地源码已激活，尚未验证真实外部Agent效果。上一阶段四页视频已正式登记current，见[课程输出交接](handoff-capture-recovery-preflight-2026-10-18.md)。

## 具体改进

此前001所有主要对象同时500ms入场，系统工程/语义通过却未识别十多秒基本静止。本轮新增html_motion_activity纯时间诊断：按实际音频绑定后字幕段合并动作区间，保留活动时长、静止比例/最长区间、同时短入场风险。接入原repair报告和内置repair Prompt0.3.2的实际temporal_report；不是像素/审美通过门禁，不自动增加动作或供应商请求。真实旧001触发long_static_interval及simultaneous_short_entrances，已接受新版两项均未触发。输出证据outputs/external-agent-handoff-20261018/motion-before-after.json。

agent_client/html_handoff.py增加基于既有能力注册表的客户端export/preview/save组合，版本化external_task/external_result/external_preview；外部执行者取得明确目标、scope、作者场景/真实绑定、人工保护路径、版本与派生操作Schema，只返回原注册操作。任务身份、结果hash、契约/场景/音频版本和scope均核对；固定source=ai，原服务保护/候选key/预览再保存为权威。不导出密钥、不直写run/DB、不提供代审批、不启动外部Agent或计费调用。使用说明[外部页面交接](../../agent/external-page-handoff.md)。

同时修复原repair候选缺音频身份：可选expected_audio_revision贯穿预览/证据；候选key绑定实际音频hash；动态检查完成及最终save_editor重核音频，防止旧旁白候选在scene revision未变时保存。缺省请求兼容，旧候选重新preview，未改scene/渲染器/批准输入。新诊断及修复模型加入生成源码闭包。

## 验证与边界

- Agent最终隔离全套443项通过，包含新交换及Web/Agent音频冲突409边界测试；最新聚焦motion/repair/external35项通过（重叠，不累加）；快照闭包及原多模态/退出9项通过。
- 原场景编辑/修复/动作43项通过；后续音频最终保存竞争正例/负例也已覆盖。原quick门禁全通过（7项既有可选benchmark跳过）；ruff、契约生成一致性通过。
- 实际8010任务包45,898字节；原HTTP导出、标准结果回传、原repair预览成功；同值操作scene/binding diff均空，没有调用save。最终预览motion_activity=no_schedule_warning；这是人工构造同值结果的传输验证，不算外部Agent自主修复。
- 复读四页revision6且valid=true，原20个音频相关文件hash保持；既有整课作品仍current、非historical。未增加模型、生图、TTS请求。
- 五轴自审：修正实际bound_scene匿名字幕无id的兼容；重叠动作按并集计时；结果无任意代码执行，source不可由外部提升；复用注册表/原服务，不新增工作队列；补齐生成源码依赖。动作诊断阈值是可解释风险提示，尚无跨课程误报率证据。

服务器换版前确认无queued/running LocalJob；当前唯一8010源码实例PID40036，原data/projects.db与runs，日志outputs/external-agent-handoff-20261018/final.*。当前meta应API1.51/hash0a4b61393bf4a5e0；旧SDK写操作需升级后重协商。实际旧音频HTTP验证发现repair适配器统一422，已修正冲突为409并加入Web/Agent回归；实际8010复验409通过。

一轮测试误与服务启动放在同一PowerShell命令中，继承生产DB/runs环境，导致15项创建项目测试失败（模板不存在），428项通过；该轮不作为通过证据。改为独立环境并显式移除两个PPT_STUDIO数据变量后443项全部通过。真实项目仍原3条、无新LocalJob；49个本轮新建且无项目记录的测试目录按创建时间/真实项目排除/绝对路径约束搬至outputs目录test-residue，可恢复；2条明确e2e测试失败幂等记录归档后定点移除。核对所有含project_id的表无对应测试残留，未删除实际项目或课程产物。后续测试不得在设置真实服务数据环境的同一命令中运行，保持checks/conftest的临时库隔离。

## 下一步

选择实际外部Agent执行同一固定页面修复任务，与内置Agent比较有效修复、误改、人工介入、轮数、耗时和费用（unknown保留null）。先验证可用性再增加预算受限的自动转交；当前没有远程Agent调度器。跨课程自动生产、设备压力/失败恢复复验和源PR发布仍独立跟踪，不因为本课程交付或协议通过而宣称全部完成。
