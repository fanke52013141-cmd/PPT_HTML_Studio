# E 线交付：中性参考生产、设计审阅与局部返工

后续实例编辑、Prompt/Skill、动态修复与真实豆包模型验收见[编辑与修复交付](EDIT-REPAIR.md)。下文较早验证记录保留历史状态；“字号/位置尚不支持、文字模型尚未调用”已由后续交付更新，不能作为当前接口说明。

2026-10-10。目录 D:/software/PPT_HTML_Studio，起始提交 25610ce。本轮在当前项目实施；根 Agent 同时承担共享入口集成，未另开运行项目或真实服务。

## 已实现

1. D 分类包接生产：按当前节点选择文字、连接、容器与标注图，默认黑灰白。实际内容、指导、附件、尺寸和哈希校验；真实附件进入 provider，并用 SDK fixture 核对打开/读取的字节。
2. 完整页面设计停点：有图片需求时先返回 design_review，不生成独立素材、不替换场景。明确确认候选 key 后恢复，不重复规划或整页设计请求；最终 HTML 审批仍独立。
3. 设计修改与单主体局部返工：修改方向产生新候选，旧图保留；当前未修改页面可以复用已确认设计，仅返工透明主体。内容、模型、修订、定义失效与人工资源保护明确报错。
4. neutral-baseline@0.2.0：严格灰阶主题复用现有组件/布局/字体；两个硬编码蓝灰阴影改用既有 shadowRGB。旧主题引用不改；播放器/目录更新会按照原规则使旧批准过期。
5. Web/Agent/MCP/CLI 同源请求和当前候选读取；Agent API1.17.0 / produce1.1。页面提供设计预览、修改、确认、恢复、单主体返工；项目/页面切换清空状态，隔离迟到响应。
6. 来源与缓存：响应 hash、D cacheKey、真实参考字节、模型与项目修订绑定请求/恢复；production provenance 进入批准和输出指纹。cache 遥测不成为作者资源；正式资源或来源改变仍增加修订并触发下游失效。同输入重复恢复为 no-op。

定义、提示词I/O与API：[application-production-0.3.0](../../../contracts/html-presentation/runtime/visual-v1/application-production-0.3.0.md)。新增模块 html_reference_package.py / html_design_candidates.py / html_production_models.py；原生产、资产、任务、编辑及批准层保留各自归属。

## 验证与过程

供应商为 fixture；D装配/文件验证、SDK附件打开、实际HTML/截图、持久任务、Web/Agent HTTP和浏览器交互实际执行。没有使用用户凭据发起外部生图，没有写入用户真实数据。

E专属覆盖：停点与多附件；确认恢复且不重复LLM；四类过期输入；候选/附件损坏；缓存与设计修改；单主体返工；失败保留旧页/回执；相同输入no-op；来源指纹；low/2K提示与透明参数；严格请求；Web/Agent一致与任务状态。

首次联合48 passed；随后较大范围256 passed（一个第三方Starlette/anyio deprecation warning）。修正正式资源变化也需增加修订的边界后，再运行同一范围，最终结果追加在本文末尾。

原面板11项、新设计面板恢复/确认/设计修改/素材返工/项目隔离以及frontend ownership通过。视觉引擎build=5 themes/5 scenes；稳定重跑14项passed、pageErrors=0。D装配器8项、目录41文件--check通过；Agent生成合同一致。

失败记录：首轮E测试的附件role名称及注册目录读取不匹配；候选缺请求身份导致两个修改方向在同字节时混淆，已修复。五页fixture主体调用从2改为3，因为新的相关分类参考字节不同，正确地使资产缓存失效。一次visual浏览器等待超时及一次目录README读取UNKNOWN错误，稳定构建后重跑通过。D旧测试固定4主题，新增中性主题后更新为5，保留其他计数/hash断言。

复现：HPS_CHROME指向本机Edge；pytest全部checks/test_html*.py + test_project_model_binding.py + Agent编辑/CLI/client套件；visual/tests/verify.cjs、test_html_review_panel.cjs、test_html_design_panel.cjs、test_frontend_quality.js、node --test catalog-assembler.test.cjs；catalog-build --check、generate_agent_contracts --check、git diff --check。

## 后续与边界

low与2K已进入匹配供应商的参数/提示，是否被真实服务接受及实际尺寸未验。新设计、主体与实际HTML美感、内容和边缘待当前用户审阅；技术成功不构成批准。

本轮生产仅接D standard/neutral。彩色配色、实验风格、B双主体模板、新字体和自由路径仍未接生产，不扩大现有预算或scene词汇。音频与数字人服务保持复用。

下一步：当前配置真实一页多参考设计→用户确认→透明主体→实际HTML对照，记录真实供应商参数/尺寸；验证一次主体返工及人工编辑冲突；再交F做五页课程、真实旁白字幕、MP4逐帧与完整解码、PPTX实际打开、恢复和最终签收。其他风格在默认路径验证后按显式配色接入。

本轮成果在本地，未commit/push或上线。

最终复验：正式资源/来源变更修订逻辑及cache遥测清理后，同范围256 passed，112.03s，exit0；一个第三方deprecation warning。视觉engine稳定14项、D装配器8项通过。未运行真实外部供应商/用户视觉/课程签收。

## 真实单页验证 — 2026-10-10

使用内置 imagegen 技能生成三张真实完整设计图，经手动图像字节桥接导回 produce_scene；不是应用配置供应商 SDK/HTTP/UI 端到端验证。采用人工准备的注册 condensation 计划，未调用真实规划 LLM。隔离目录 outputs/e-validation-2026-10-10；Prompt、实际 D 附件及哈希、候选记录、尺寸和审阅报告均保存其中，运行文件不提交。

第一版字阶、灰阶材质可用，但三卡横排，和当前注册纵向模板不一致，并缺 figure note。定位为提示输入只给槽位身份、没有实际几何；补入注册布局匹配版本的 canvas、活动槽位框，PromptVersion 升为 html-design-reference/0.3.0。第二版恢复纵向与标签，但把 blue/green 运行时 tone 键当成配色；灰阶参考内容现在递归移除 tone，保留准确文字、原计划和 scene 语义。第三版视觉恢复中性灰阶与纵向，仍遗漏“观察冷杯表面”“水滴来自空气中的水蒸气”两条 figure 标签，几何和字幕留白并非像素精确，不能登记完整视觉通过。准确文字与字幕边界必须由实际 HTML 保证并再次对照。

三张返回尺寸均为1672×941 RGB，内置工具未开放 low/2K/具体模型控制，不能标记这些供应商参数通过。最终候选 key=1eebba9663f9531bc588cd6abcddda6d68e5fc05270c25aa16b57310d2073ba3；stage=design_review，saved.changed=false，无实际场景、透明主体或用户批准。历史候选均保留，定义修改后旧候选不可直接恢复。

修复后联合34 passed（21项 E、13项工作流/集成），36.93s；git diff --check 与合同索引 JSON 解析通过。第一次工作流测试未指定 HPS_CHROME，5项浏览器依赖检查失败；指定本机 Edge 后13项通过，再运行最终联合34项通过。不覆盖或伪造实际用户审美、SDK供应商、音频视频与课程验收。

下一步仅确认第三版的视觉方向；实际 HTML 要补齐标签、严格保留字幕区，生成透明冷杯主体，再比较复刻保真度和执行一次局部返工。本轮仍未提交或推送。

## 实际 HTML 展示 — 2026-10-10

用户要求查看实际 HTML，继续第三版候选的重建。内置生图生成透明冷杯 subject-v1.png，经同一生产服务恢复候选、透明资产检查、注册组件展开和真实浏览器技术 review 后保存场景。没有调用新的规划或整页设计模型，没有将整页参考作为背景；没有批准最终 HTML 或资产边缘。

实际页面 outputs/e-validation-2026-10-10/reconstructed.html 复用共享 player.js、data.js 和产出的项目资源，默认展示终态，保留实例 JSON 编辑与播放。实际截图 actual-html.png；浏览器 pageErrors=0，11个对象，两条遗漏的 figure 标签在 HTML 中完整出现。生成过程及结果见 subject-request.json、reconstruction-result.json、actual-html-check.json。当前仅内置生图手动桥接的单页技术展示，自动模型规划、应用供应商传输、旁白音频/课程导出及一次局部返工尚未验证。

对照观察：布局方向、准确内容、灰阶、独立图片与字幕安全区已由代码控制；当前注册组件的标题编号、图标底板、figure 容器及结论条与生图设计并非一比一。不得将技术通过记为美感通过。下一步以实际 HTML 为用户审阅对象，按审美反馈精修共享呈现；避免只展示生图而推迟可编辑页面验证。

## Agent/Web 编辑 API 实测 — 2026-10-10

后续设计细化见[初稿、可编辑场景与动态修复](../generation-editing-repair-design.md)：生产与修复的输入输出、实例覆盖、动态区间检查、人工/AI同源编辑、实施顺序。属于设计提案，新增字段和流程尚未实现，不能据此扩大当前能力。

用户提出自动 Agent 是否能达到当前效果，以及位置、字号的二次编辑。当前展示仍为人工注册计划→程序组件展开，并非真实规划 LLM 自动生成。只读核对本地应用设置：文字模型 gpt-4o-mini，应用 llm_api_key 为空，模型连接注册和凭据文件不存在。因此没有发出真实模型请求或把替身结果当真实规划。用户选择先完成 API 编辑验证，再配置文字模型。

在 outputs/e-validation-2026-10-10/api-validation 的独立数据库及实际场景副本中，以 FastAPI TestClient 调用既有 Web 与 Agent HTTP 路由，不启动真实服务或写真实项目。11项调用断言：读取、修改标题预览、保存、重开、Web/Agent读取一致、重复保存no-op、旧修订409、Web及Agent逐对象fontSize/position请求均422。拒绝后保存内容不变。实际浏览器技术审阅通过；修改后的 api-edited.html / api-edited.png 浏览器pageErrors=0，11对象。证据 report.json、actual HTML check 与 API修改结果均在隔离目录；未验证生产认证中间件、网络服务、模型自主工具调用。

当前对象内容、资源锚点和动画可编辑；最终槽位框与字号由注册layout/theme控制。动画enter的offset不是最终布局位置。Scene/编辑API未定义逐对象fontSize与position，不能在Skill中声称可用，也不能绕过Schema写自由CSS。

建议顺序（尚未实施的新能力）：先定义并实现受限的实例位置/文字样式覆盖，覆盖Schema→compiler→renderer→编辑接口/UI→几何/容量检查→人工编辑保护→预览/输出与Agent同步；再编写HTML生产/审阅/局部修订Skill并验证真实规划LLM。已有API是可调用工具，不等于自主Agent。Skill规定模型使用工具的步骤与验收，API负责可执行能力。若多轮模型判断、工具调用、人工停点和中断恢复复杂到现有编排不足，再评估LangGraph；尚未选择或安装框架。参考官方 https://docs.langchain.com/oss/python/langgraph/overview ，其持久执行、人工介入与状态恢复属于编排能力，不能替代美感库或未实现的编辑字段。
