# 外部 Agent 完整材料包与受控结果导入交接

最新增量：契约0.9.99/API1.53，preview0.3接收result JSON或delivery_base64（二选一），
`html_handoff_delivery.py`拥有受限ZIP解析，原主owner核对任务后留档报告/证据并调用原预览。
页面提供导出输入、导入输出、原系统检查反馈下载和显式保存。新报告以纯文本展示，外部自述不等于系统通过。

真实返回来自用户桌面“agent辅助html转动画”：delivery.zip与独立result.json/report.md逐字节一致，
task_id=295289f7…6cd40，6项操作符合原结果Schema与scope。原0.9.98封存任务仍有效时已运行原preview_result，
实际失败为SCENE_INVALID / CONTENT_SAFE_ZONE:obj-summary：677-40+156=793，再加保留的enter.offsetY=12为805，超过800。
原任务/交付/失败留存于outputs/external-agent-real-token-20261019/returned-first-round，未保存、未批准、未改原项目。
Agent明确无法看图且无原系统接口，报告运行项not_run；不得将像素扫描当视觉验收或直接声称外部已成功。
新规范强调静态修复保留动作位移。API与源定义更新后旧任务须重导出，不能改旧结果ID冒充新任务。

后续增量：契约0.9.98，[真实Token任务与来源](../../agent/real-trial-token-2026-10-19.md)和
[执行验收交付规范](../../agent/external-agent-execution.md)已补齐。规范/报告模板每包带hash，
Agent只交付候选与报告，文件模式运行项写not_run；真实源资源Windows分隔符已兼容且包路径守卫保持。
历史Token未保存候选等值复制至outputs隔离页，原图/原文/绑定留存并实际重新取帧；无真实音频，
不宣称线上已保存页、整页语义/美术通过或外部Agent修复成功。此前77项是0.9.97历史证据，新增验证见文末。

2026-10-19，本地源码增量；契约0.9.97 / Agent API1.52 / 交换格式0.2.0。
未推送、未切换真实8010服务、未调用外部Agent/模型/生图/TTS；真实项目数据与原作品未修改。

## 交付与使用

- `html_external_handoff.py` 汇集权威内容、实际播放器截图、当前独立素材、真实时间资料、解析theme/layout及全部输入身份，生成可携带ZIP。`manifest.json`核对所有payload；task.json清单只列输入，避免task_id循环依赖。
- `html_handoff_contract.py` 从原生产Schema、KINDS/PARTS和component_context生成逐对象/部位/动作/变体操作Schema；复用锁定AJV。既有repair服务仍是字段、人工保护、动态检查、保存和最小失效的权威。
- 已保存页：编辑器展开“外部 Agent 交接”，填写目标、选中范围、选择静态或真实配音动画任务并导出。将ZIP交Agent，返回result.json；导入显示真实前后截图、diff和检查，独立“保存本次候选”。未保存草稿、过期修订或材料停止，不隐式覆盖。
- 设计图：设计面板“导出设计交接包”。携带原图、准确规划、brief风格及接受/过期状态，明确缺少可编辑scene/素材；不把设计参考包当作可直接保存的还原操作。完整新页还原继续原produce流程。
- Web/Agent共享薄适配；MCP/CLI从同一注册表转发JSON，ZIP单独下载。API认证留在本机，不写包；结果固定AI保护，来源用量作为未独立核实的外部报告留存，未知费用null。旧0.1客户端保留。

入口与命令见[接入说明](../../agent/external-page-handoff.md)，规范见[0.2定义卡](../../contracts/html-presentation/runtime/visual-v1/external-agent-handoff-0.2.0.md)。

## 状态与边界

| 轴 | 当前状态 |
| --- | --- |
| 定义 | specified：阶段、材料/风格/操作/输出、版本、保护、预算和验收职责明确 |
| 实现 | implemented：静态/音频动画局部修复包、设计材料包、导入预览及原服务保存、三种JSON适配及ZIP下载 |
| 工程验证 | 本轮隔离测试与真实浏览器证据见下方最终核验；HTTP处理函数/权限与网络传输分开 |
| 真实外部Agent | unverified：未执行自主修复、费用/效果对照或自动调度 |
| 真实设计/音画/整课 | 本批未修改或重新批准；历史课程结果仍按前次交接 |

现有端点仅已有对象的受控修改；缺对象/需新组件/需生图或TTS返回needs_input/unsupported。未实现任意HTML导入、远程调度、自动审批或仅凭一张图创建完整作者scene。

## 验证环境与发现

- 测试DB/runs均为outputs下独立临时根；没有导入server或连接真实DB，浏览器使用已安装的Chromium headless shell与共享捕获策略。
- 当前受限环境阻断回环网络；常规TestClient在Windows事件循环socketpair处等待，浏览器HTTP访问也被拒绝。本批适配测试直接调用真实Web/Agent处理函数并运行原权限/模型/数据库/服务，MCP/CLI实际转发到同一处理函数；这不等于真实HTTP网络传输复验。
- 浏览器通过本地管道提供fixture请求，实际加载编辑器/共享播放器，点击导出、上传result、检查前后图、显式保存、重开、过期结果及草稿保护。无外部网络，无供应商替身冒称真实模型。
- 首次真实设计checkpoint测试发现两个未修改的已跟踪runtime片段仍为CRLF，而注册hash对应Git中的LF。仅在“规范化后等于HEAD且HEAD SHA256等于注册值”时恢复candidate-layout-repair-0.3.0和design-reference-localization-0.5.1的原Git字节；未改文字/Prompt或登记hash，无新增这两文件Git差异。
- 原设计面板DOM检查未打开既有折叠区即填写隐藏输入，现修正为真实点击展开后填写；生产交互和门禁未放宽。
- 未完成全库CI或真实网络环境复验，不把专项通过扩写为全库通过。

## 后续

在正常网络/目标运行环境对上述注册API做HTTP烟测，再选同一固定页面让真实外部Agent返回标准结果，比较有效修复、误改、人工介入、轮数、耗时和费用。保留版本/素材/音频/人工保护及独立验收；先证明实际可用，再考虑有预算的自动转交。

## 最终核验

- 冻结本批服务源码后的9个相关测试文件 **77 passed / 1 warning，86.74秒**：完整任务包、真实浏览器按钮、Web/Agent处理函数与MCP/CLI、旧0.1交换、原修复保护、架构和路由检查。warning为既有anyio别名弃用提示。日志：`outputs/handoff-097-closure-d9c0b9d011c346a08297944f3ad17aed/regression.txt`。
- 浏览器实际点击导出ZIP并校验原主题/实际截图；导入不写作者，展示前后图后独立保存/重开；过期结果、未保存草稿被阻断，无pageerror。PNG/JSON报告位于上述根的`temp/test_external_handoff_buttons_0/hps-editor-browser-external/`。这些是本机忽略产物，不随Git迁移。
- 合成音频用例验证原voice/timeline/SRT字节随包提供、既有actionId与语块约束有效；不是新真实配音或听审。早一次用例把全部动作误绑第一语块，被原AUDIO_ACTION_WINDOW正确拒绝，夹具改为按真实窗口绑定，没有放宽绑定规则。
- 同身份已封存包重导出核验后复用，ZIP字节及mtime保持，避免并发下载时重写文件。原始内容/音频/资源/字体/播放器和时序源码身份均核对，旧结果不跨版本保存。
- 设计面板DOM及人工候选面板检查分别通过；frontend quality、全库ruff和Agent能力矩阵生成一致性通过。最后修正设计导出局部操作令牌，避免旧异步操作清除新页操作标记，两个面板DOM再验通过。
- 以上不代表完整CI、真实HTTP传输或真实外部Agent自主修复已验收。真实服务未换版，源代码尚未提交推送。

## 0.9.98 执行规范与真实输入验证

- 4个相关测试文件29项通过（66.18秒，1个既有anyio弃用提示）；范围：任务完整性、Windows实际源路径规范化、
  真实共享取帧、Web/Agent处理函数、原保护导入/保存、浏览器按钮与旧0.1兼容。
  隔离根：`outputs/handoff-execution-7143816fb9c24eeeb143aae571d8e6c4/`。ruff、Agent生成一致性、前端质量与diff检查通过。
- 真实Token试验基线由原archive candidate的scene/binding等值落盘，仅挑本页contract和被引用PNG；
  原绑定语块与完整讲稿逐项一致。当前共享播放器实际0/8750/17500ms截图及250ms采样报告passed。
  这是实际原材料的可读性改进任务，没有人为制造错位，也没有执行/伪造外部Agent结果。
- 交付ZIP、完整来源hash、封存任务与隔离run见[试验说明](../../agent/real-trial-token-2026-10-19.md)。
  真实项目DB/作者/批准/音频未写；本机未发现历史handoff所指结冰课程，所以本轮使用实际存在的Token材料。
- 等待用户交外部Agent执行并回传result.json/report.md。当前包无真实音轨、无系统接口凭据，
  外部运行验收标not_run，由本机隔离页原服务预览后反馈；尚不能宣称修复目标达成、用户画面或正式输出通过。

## 0.9.99 导入闭环验证

- 最终9个测试文件81项通过（49.71秒、1个既有anyio弃用提示）：ZIP路径/链接/设备名/大小/类型限制、
  真实共享取帧、原作者保护和显式保存、Web/Agent/MCP/CLI、旧交换、浏览器ZIP结果导入与反馈下载。
  隔离证据根`outputs/handoff-delivery-final-4b994187836a4e73872e5ada55874405/`。
- 浏览器人工看图后修正全局input样式覆盖hidden的冲突，隐藏的文件选择器不再重复出现；
  UI全流程再验1项通过（36.73秒），证据`outputs/handoff-delivery-ui-14008cf5fa8944439d762a1c835b70d8/`。
- 真正localhost TCP/Uvicorn/FastAPI原Web路由、独立DB/runs验证输入ZIP下载、交付ZIP预览、原实际前后截图、
  报告留存、不自动保存和无效回执409通过；报告`outputs/handoff-http-final-6710ce11ce614a298b28ac97e14d6650/http-smoke.json`。
  这不是运行中的完整应用中间件/账号部署验收，真实8010服务未启动或换版；测试临时服务已退出。
- 初轮测试76项通过、2项夹具问题：Windows写ZIP时先规范化了应当拒绝的反斜杠，
  以及新增报告summary导致旧选择器不唯一；均修正测试实际输入/明确目标后全绿，未放宽解析或产品门禁。
  初次HTTP夹具给语义场景却缺binding被422拒绝，改为原合法非语义夹具后烟测通过。
- 全库ruff、前端质量、Agent生成一致性、diff检查通过。无新增provider/TTS请求、原项目写入、commit/push或部署。
- 第二轮真实输入包和原失败反馈已封存；新task_id=025c1a7a…16dca2，API1.53/hash058164e686563076。
  旧结果不改ID、不重签，等待用户给同一外部Agent修订；当前未得到合规修复/用户视觉签收。
