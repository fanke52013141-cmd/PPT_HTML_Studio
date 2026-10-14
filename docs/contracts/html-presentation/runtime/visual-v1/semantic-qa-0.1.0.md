# A04 逐句语义 QA 0.1.0

2026-10-14，HPS-007/009–017/023/028/030。定义先于实现；工程、模型实测、听审、人工状态分别验收。

## 输入与身份

输入为保存的scene0.6/0.7、scene_plan0.2、binding0.2、当前visual_contract原句、原TTS服务的真实voice.mp3和audio_timeline。校验原句字节/hash、完整有序语块、对象/动作身份及绑定，按既有binder求真实时间，不按作者等分或比例猜测。音频可先审未确认版本，生成和确认分别记录；音频解码/时长由ffprobe验证，QA不生成或确认TTS。旧scene0.1–0.5明确legacy_not_evaluated，保留既有输出门禁，不冒充语义通过。

每个语块采样[start,(start+end)/2,end-1ms]；过短窗口、重复/乱序/缺失语块或越界拒绝。起点入场透明允许；预期visible在末帧必须可见，动作事件必须落在原语块窗口并保持身份。抽取帧复用生产播放器、字体、资源与音频bound scene；至少每句三帧，完整页预算40句/120帧。有限采样不证明帧间全部状态或词级精准同步。

## 独立模型与最小输入

一请求一语块、三张图片按start/mid/end顺序；仅传原句、视觉意图、目标/预期状态、当前相关对象内容/角色、动作/可见性和图片时间索引。其他页、整文、重复摘要、凭据和整条动画轨迹不传。声明为待检验假设；不能因为ID齐全或终态漂亮而认为表达正确。模型不规划、不修改、不批准。

输出verdict related/omitted/contradiction/uncertain，confidence0–1，至少一条对应实际帧索引/实际对象ID或null的可观察证据；结构严格校验，未知目标/帧、缺证据或重复引用拒绝。任何遗漏/矛盾阻断；related须confidence≥0.8；uncertain/低置信待人工审阅。旁白无画面理由也需核对，不能默认逃逸。

## 报告、复用与恢复

原句/plan/scene/binding/audio/timeline/实际资源/播放器/QA源/Prompt字节形成输入指纹，独立模型参数进入请求身份。每句实际帧字节、模型原始结果、请求和回执保留；报告绑定输入与证据hash。缺帧、改写报告、重用旧素材或只交终态不能通过。状态读取重新算当前输入、检查完整三帧时间及文件hash并从严格模型结果重算结论，不信任passed标记。源码/内容/音频变化标stale，不删除旧审计。

任务复用现有LocalJob/html_task_store，submit时冻结多模态模型及输入；各句intent/returned回执支持复用。unknown无ID不自动补发；停止后迟到响应可留审计但不发布当前成功。恢复原任务需同输入和模型；无新任务库/数据库迁移。

## 四类结论与批准

engineering是引用/音频/实际帧/可见性检查；semantic是逐句模型结论；audio是既有人工音频确认；human是明确语义审阅决定，与原视觉批准独立。模型pass不写human/audio批准。人工approve要求当前工程通过、无omitted/contradiction且逐句证据完整；低置信uncertain可由明确人工说明签收，不覆写原模型结论。人工reject阻断。决定绑定report key和当前revision；过期409。

scene0.6/0.7讲解视频新增语义门禁：当前工程通过，semantic相关或经人工解决不确定，human明确批准，原音频与视觉批准仍有效。静态快照PPTX保持无需真实音频的既有门禁，不能把其可导出等同讲解课程语义完成。状态在原七阶段附semantic_qa事实，不增用户可见工作区步骤。正式视频快照固定当前QA报告与决定。

Web/Agent/MCP/CLI共用submit/status/decision合同；UI展示逐句证据、四类状态与当前/过期结果。真实模型QA必须另留证；工程夹具不能冒充真实TTS语义验收。
