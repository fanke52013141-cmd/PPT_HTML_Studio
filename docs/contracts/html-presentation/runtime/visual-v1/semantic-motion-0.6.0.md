# A03 语义动作编译与真实配音绑定

2026-10-13；HPS-009/010/011/013/028/030。新增scene0.6.0、motion_binding0.2.0；消费A02 scene_plan0.3.0。A01独立plan0.2.0仍不能直接编译，须有A02对象分工；所有旧场景/绑定保留原读取，不自动升级或重新批准。

## 模型、归属与编译

`html_semantic_motion.py`负责新计划动作编译、显式绑定合同和纯音频求值；`html_audio_binder.py`按scene版本分派，旧算法不改。`html_production_service.compile_plan`消费0.3.0，重新核对冻结对象/讲稿及来源摘要，产生注册节点，不生成任意HTML/JS。共享视觉schema/compiler/renderer负责新scene的机器校验和实际渲染。scene对象/页ID仍须满足运行时小写字母、数字、点/短横线规范；不能静默重命名破坏引用。

scene0.6.0增加nodeStates：完整覆盖实际节点，每项`{role,initialVisible}`；背景/装饰按A02显式初始状态，instructional必须隐藏。motion每项增加唯一actionId，仍使用enter/emphasize及显式持续时间/位移，不支持exit。同对象enter唯一，强调可多次且区间不重叠；同一actionId不能重复。初始可见对象不制造0ms进入动作，永久隐藏非讲解对象可不含动作，instructional必须由显式enter驱动。

编译产生作者预览时钟，默认3500ms语块槽且至少12000ms，动作500ms；同对象多动作按顺序分配、标注等待主体及标签完成进入。此时钟仅供无音频预览，不能当正式课程配音。真实时间绑定不使用该槽位间距或比例系数。

## 绑定0.2.0

严格字段`{format:"hps.html.motion_binding",version:"0.2.0",mode:"beat_action_ids",actions,narration}`。actions以稳定actionId为key，每项`{beatId,edge:"start",offsetMs}`；所有动作必须且只能有一个绑定。offsetMs为0—120000整数，但执行时必须落在对应语块真实窗口。narration逐句存`{id,spoken_text,spoken_text_sha256}`，原句/hash从计划保留，引用集合及顺序与实际音频一致。

当前新合同只提供start边界；旧0.1.0允许的end/负偏移保留在旧路线。新语义场景缺绑定、旧版本绑定、悬空/缺失actionId或未知beat一律拒绝，不回退作者时间或比例缩放。重复强调各有独立ID，不能用object:type掩盖另一动作。

## 真实音频时钟

沿用原TTS与确认时间轴，不重新选型或重合成。音频segments秒数在binder边界转毫秒，按beat_id（缺省id）合并连续分句窗口；重复语块不能隔段回归。原句逐片段核对，只允许已有字幕分句器在明确片段边界省略句末标点及空白；内部标点、词句、数字更改必须拒绝。音频片段顺序、集合、有限时间、无重叠、完整时长均校验。

动作开始=真实语块开始+偏移，再满足同对象前一动作和标注依赖完成时间。动作持续时间保留作者值，上限为本语块剩余窗口；剩余不足1ms拒绝，不偷偷移动到别句/尾部。标注只能在主体和文字标签完成进入后出现。持续时间和实际窗口确定所有状态；同一输入重复绑定偏移只应用一次，随机seek与顺序播放求值一致。新元数据mode明确beat_action_ids，timeScale=null。

场景时长使用audio_content_duration_sec，保留末句结束到文件结尾的尾部；字幕仍仅在句子窗口显示，尾部空白不延长字幕。实际媒体全解码/听审仍由原输出验收执行，本轮未授予audio_confirmed。

## 编辑、修改影响与公共接口

现有编辑保存/重开/预览校验新绑定及当前权威原句，不因ID没变而接受旧讲稿。人工保护与合并按actionId，保留重复强调；绑定/样式仍走原业务写入和html_scene_changed影响规则。编辑样式不能把新scene降成0.5.0。公共局部修复增加可选actionId，重复目标/动作类型未指定ID则明确拒绝；基础样式不接受动作ID。Web/Agent/MCP/CLI共享RepairOperation，preview/save能力1.2，AgentAPI1.24.0；新修复Prompt0.4.0要求从实际motion选已有ID。

0.6.0的审批/输出输入摘要包含实际binder与semantic_motion源码散列，运行绑定变化使相关旧批准失效；不触发TTS失效。无数据库迁移、不重写旧人工批准。正式输出仍要求原视觉/音频批准及快照校验；scene结构与时间通过不能替代A04语义QA或人工听审。

## 范围与验证

已实现compile_plan调用、新场景共享播放器、实际音频binder、编辑保存/重开及原输出分派消费新格式。普通produce_scene任务仍按旧计划默认运行；A05将负责系统整课调度及显式新流程入口，不能宣称输入讲稿后无人值守自动完成。独立图片的状态请求/设计确认仍按A02准备，未自动调用付费服务或接受生成锚点。

工程验证包括同对象重复强调、多动作、背景初始可见、缺绑定拒绝、原句变更、偏移越界、短句/标注依赖、保存重开/保护、真实播放器开始/中点/结束截图、往返seek、二十个保留S08真实语块窗口及尾部。实际音频只读复用，测试表达是时序fixture而非重做课程，语义QA/听审/正式输出/数字人状态仍分开登记。
