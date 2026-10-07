# HTML 后端开发成果审查与优化方案

审查日期：2026-10-08。代码基线：`1616bae`，同时读取当前工作区；本地存在继承的未提交修改，未重置或改动业务实现。审查范围：`3d52135..1616bae` 的 HTML 新增链路及当前应用集成，约 102 个文件；按核心调用链定向审查，并非对整个原项目逐行审计。

结论：**request changes。共享视觉和服务基础已经形成，但尚不能验收为可用的完整应用生产流程。** 核心问题集中在真实入口、状态与导出集成，不能仅依赖已有单元测试数量放行。以下问题是已确认缺陷或明确未接通的任务，并非因缺少模型密钥导致的推测。

## 本次验证

- 重新执行全部 `checks/test_html_*.py` 和 `checks/test_project_visual_backend.py`：68 passed。
- `npm run test:visual`：13 checks，4 scenes，0 page errors。
- Agent 契约生成物校验、visible flow 与 frontend quality 检查通过。
- 在临时 DB/runs 与合成浏览器页面中复现保存、批准、指纹、音频和 UI 问题；未使用真实用户项目进行失败注入。
- 原始复现结果：[后端复现](2026-10-08-html-backend-review/backend-reproduction.json)、[UI 复现](2026-10-08-html-backend-review/ui-reproduction.json)。UI 为隔离页面复现，设置观察回调上限以避免持续占用；未操作用户当前浏览器页面。
- 查看现有 `water-facts-final.png` 视觉证据。模型真实生产、真实课程全流程、数字人服务、PowerPoint 打开未在本次审查执行，不能宣称通过。

现有测试多数覆盖模块函数与路由存在，未覆盖新网页保存入口、实际 DOM 接线和完整输出合同，因而存在测试通过但产品失败的情况。

## 必须优先解决的问题

### R01 / P1：缺少“计划→设计→资产→可执行场景”的实际生产编排

位置：`html_visual_review_routes.py:99–122`；`html_visual_review_service.py:226–227`；`html_design_brief.py`、`html_asset_service.py` 的生产调用缺口。

生成计划接口返回语义 plan 并保存生成证据，但没有将其编译为 renderer 使用的 scene、写入场景存储、调用设计候选/冻结或资产生产。新资产也没有进入播放器的项目资源包。播放器 `visual/player.cjs:4` 与 apply 使用固定 `window.VisualData` catalog/pack，来源是仓库构建的样例资源。代码检索中 build_design_brief、freeze_design、produce_asset 尚无应用生产调用方。

影响：用户即使配置真实模型，点击生成计划也不会自动得到可审阅的新课程画面；不能将这个缺口归因于 API 密钥。现有样例和工具可运行不证明应用闭环。

优化：新增应用级生产编排服务，明确 plan、design candidate、freeze、asset manifest、executable scene 的阶段产物和保存入口；提供 plan→scene 编译器及项目 scoped catalog/pack。设计/资产服务继续保持窄依赖，禁止通过修改全局样例 data.js 注入用户资产。

补充验收：在隔离项目中输入新课程，使用 stub 的计划与独立资产先验证编排；产出此前仓库没有的 node/asset ID，由同一播放器审阅和导出。然后实际模型跑一次。每个阶段有产物和失败状态，不能以返回 plan JSON 代替 C02/C03/C04 完成。

### R02 / P1：Web 保存场景入口必然异常

位置：`html_visual_routes.py:103–109`。

路由读取 `_dependencies.write_json_atomic`，但 HtmlVisualDependencies 没有该属性；save_scene 也没有对应参数。复现得到 `AttributeError: 'HtmlVisualDependencies' object has no attribute 'write_json_atomic'`，写入尚未发生。

优化：删除失配参数，通过已有 store 原子写入实现；Web 与 Agent 使用同一个应用服务处理锁、版本、校验和失效，避免两个写入口分别拼装参数。

补充验收：真实 FastAPI TestClient PUT，分别覆盖成功、no-op、revision 冲突、非法场景；不是仅调用 save_scene 或检查路由已注册。

### R03 / P1：审阅面板 DOM 与刷新机制错误

位置：`static/html_review_panel.js:19–22,105–119`；实际内容面板在 `static/index.html:316`。

选择器 `[data-step="3"], #step-3` 命中导航栏 li，而非 `#step-panel-3`。读取 currentSlideId 的路径也不对应当前 state 的 slides/activeSlideIndex。全 body MutationObserver 触发 refresh，refresh 每次设置 textContent 再产生 DOM mutation，形成自触发循环。

隔离复现：审阅区父节点为 LI，实际内容面板无审阅区；观察回调达到人为设置的 30 次上限；点击计划发出 `/html-review//plan/generate`（slide ID 为空）。

优化：使用明确内容面板 ID 和唯一当前页 helper；由项目/页切换事件刷新，移除全 body 观察循环。状态更新幂等，切换 image 项目清理/隐藏面板，异步请求绑定项目/页的版本，展示实际截图与问题对象，不只是路径字符串。

补充验收：实际静态应用壳的浏览器测试，检查面板位置、当前页 URL、操作后状态不被覆盖、空闲时无持续回调、切换项目无残留。

### R04 / P1：输出前置条件仍按图片后端判断

位置：`video_render_service.py:187–200`；`pptx_service.py:206–216,831–845`。

视频 start_render 在后端分派前无条件执行 validate_visual_provenance_set，要求原 visual_draft.png/provenance。HTML 正常项目无这些图片产物，会在进入 HTML runner 前被阻断。PPTX readiness 同样仍调用图片/reveal 检查；前端依据 ready 禁用按钮。

优化：按 backend 注册 readiness policy：image 继续原规则；HTML 核验当前场景、项目资产、有效视觉批准及已确认音频（视频）。PPTX 按自身需求判断，不伪造图片 provenance/Mask 文件。

补充验收：没有 visual_draft.png/Mask 的有效 HTML 项目可提交视频与 PPTX；缺场景/资产/批准时准确拒绝；原 image 项目仍遵守原门槛。

### R05 / P1：HTML 输入没有加入输出指纹

位置：`artifact_fingerprint.py:90–125,150–173`；共享 worker 使用该指纹做复用和输入变化检测。

旧指纹覆盖 slides 内的图片/音频等文件，没有 planning/html_visual/scene-*.json 及实际主题、布局、字体、项目资产包。复现：场景更名后视频与 PPTX digest 均不变。

影响：改画面后可能复用旧成品；长任务期间换场景无法可靠识别输入已变。仅调用失效函数不足以替代完整输入指纹。

优化：建立 HTML resolved-input manifest，将有序场景、资源内容 hash、主题/布局定义、字体、runtime、绑定时间和输出选项纳入指纹；预览、批准和导出共享该 manifest。导出读取提交时冻结输入，完成时核验当前版本。

补充验收：逐项修改内容/主题/布局/字体/资产/动作/字幕参数，所有实际影响输出的变化必须改变 digest；no-op 不变；运行中改输入不得登记为当前成品。

### R06 / P1：批准状态接口绕过有效性判断

位置：`html_visual_review_service.py:359–360`；`html_visual_review_routes.py:178–187`；`agent_api/routes.py:358–364`。

Web/Agent 查询均传 scene=None，服务直接返回 valid=True，不校验当前 scene/runtime。复现：旧批准后改场景，接口行为仍为 true；传入当前场景的服务检查才为 false。批准记录仅保存引用和固定字体名称，不能充分表示实际依赖内容。

优化：加载当前场景，缺失时无效；比较 R05 的 resolved-input digest。批准请求携带被审阅版本或 expected_revision，核对 scene ID 与 URL slide ID，避免批准请求中的临时候选被误当成已存页面批准。

补充验收：批准后改场景/资源/主题，Web 和 Agent 查询均 valid=False；页面删除无效；批准的内容必须等于实际存储和截图内容。

### R07 / P1：新 Web 路由缺少创作账号隔离

位置：`html_visual_routes.py:49–54`；`html_visual_review_routes.py:65–69`。

两处只按 Project.id 查询，未按当前账号筛选。原应用 `project_path_service.project_or_404` 已提供账号隔离，Agent HTML 查询也有 account_id 条件；全局 token/origin 中间件不替代项目归属校验。

优化：直接复用 project_or_404，并校验 slide 属于当前契约；不要再手写仅按 ID 查询的 helper。

补充验收：账号 B 使用账号 A 的项目 ID 查询、写入、生成、审阅、批准，均 404且不产生任何文件或模型调用。

### R08 / P1：动作没有按实际讲稿语块绑定

位置：`html_audio_binder.py:92,108–122`。

当前把所有动作 start/duration 按总时长比例缩放；没有使用 C01 的 beat→object/action 映射。两份总长同为 10 秒、第二句分别从 1 秒和 8 秒开始的时间轴，动作均保持 5 秒。

影响：不能保证“讲到什么，显示什么”，同一总时长下停顿/语速变化会造成明显错位。当前测试反而断言比例缩放结果，因此不能证明 AC12。

优化：保留稳定 beat/action ID，按已确认 segment 的开始/结束时间与一次性手工偏移绑定；只有明确声明 normalized_time 的纯背景动作才采用比例缩放。缺失、重复、越界关联必须拒绝。区分音频内容结束与音频文件尾部时长，不依赖当前 ffmpeg 注释所称的自动末帧保持。

补充验收：总时长相同而句子边界不同，关联动作必须跟随边界；插入停顿、修改 offset、随机 seek和跨页拼接实测；时间误差按 AC12 一帧计算。

### R09 / P1：HTML PPTX 返回合同与应用下载链不匹配

位置：`pptx_service.py:473–543`；`static/output_render.js:564–568`。

HTML 分支同步返回 immediate/file/manifest，前端仍必须 res.job.id；产物没有 ArtifactRecord（artifact_id=None）。即使绕过旧 readiness 成功生成文件，界面仍报“服务器没有返回 PPTX 任务编号”，列表/下载路由也无法找到该产物。

优化：接入既有 persistent PPTX job 和 artifact lifecycle，按 backend 选择 runner；保留统一 job/result/download 合同。明确快照不可逐对象编辑，步骤与字幕选项走同一任务参数。

补充验收：应用中点击生成→轮询→作品列表→下载→重启后仍可下载；失败保留旧成品；不能只检查临时目录里 zip/PPTX 存在。

## 第二批优化与验收记录修正

### R10 / P2：任务存储尚未成为实际生成任务机制

位置：`html_task_store.py`；生成/审阅入口仍同步直接调用函数。

当前 submit/recover/cancel store 无应用调用方，未见启动恢复挂载、worker、提交/轮询/取消链；不能据 store 的单元测试认定 F02/AC18 已集成。mark_succeeded 也缺少“取消后晚到结果不得改成功”的状态保护。

优化：R01 编排接入持久化执行器、启动恢复和 cooperative cancel，业务输入 hash 与 revision 固定；提交/完成在事务中保护。增加并发幂等、取消后迟到完成、服务重启测试。

### R11 / P2：效果参考图不是用户要求的标注效果库

位置：`html_engine/visual/tools/effect-cache.cjs:20–47,79–91`。

工具只是选 scenes[0] 截一张课程终态，不会把 N 个效果分别展示并标 ID/backend/作用；过渡效果无法从终态理解。缓存 key 对 effects 只取 ID 列表，不包含效果完整参数/版本；并删除旧缓存引用。现有模型入口为文本 JSON 调用，未见把效果图作为图像附件送入实际设计生图请求。

优化：真实组件分格渲染标注 atlas，动效提供关键状态小图；缓存按完整定义及字体/布局/主题 hash，保留被冻结设计引用的旧版本。模型请求同时附图片与文本映射，记录脱敏请求和附件 hash。只为变更能力增量更新。

补充验收：可以从图中识别每个效果、实现 backend和用途；更改同 ID 参数使 key 变化；冻结旧设计仍能访问原参考图；实际生图服务请求含对应附件。

### R12 / P2：验收状态过度汇总，视觉证据不足以放行

位置：`docs/plans/html-backend-development/task-ledger.json` F03；acceptance-manifest.json AC09/12/14/18/20。

F03 标 passed，但用户视觉审阅、真实课程、服务和软件验收尚未完成，且本次发现以上工程缺陷。单页工具导出不能证明应用多页输出；模块 CAS测试不能证明 Web 写入；“需用户完成真实导览”不应掩盖开发链本身未接通。

查看 water-facts 证据仍存在数据呈现不足：三个温度仅作为分散文字，没有相应图表/刻度关系；中部留白较大，与底部状态条的教学主线不够统一。这是模板层需再审的具体项，不宜仅靠“用了不同结构”认定完整视觉通过，也不需要增加生图解决。

优化：任务状态拆分 implementation/test/visual/e2e；F03 当前应 changes_requested 或 partial。每个 AC 登记 exact command、输入、hash 和证据；真实课程自动/工程路径由 Agent 补齐，用户负责最终视觉审阅。数据页增加注册的 SVG刻度/关系可视化，保留当前色系，先做可复用表现组件再替换实例。

## 建议实施顺序

1. 修 R02、R03、R07：恢复基本网页写入/操作和账号边界，加入真实路由与浏览器回归。
2. 实施 R01 并接 R10：贯通项目级生产编排、资产包和任务执行，先使用受控输入验证，再实测模型服务。
3. 修 R05、R06、R08：统一冻结输入、批准和音频动作关联，保证修改后状态可靠。
4. 修 R04、R09：接通输出门槛、视频/PPTX 任务和下载登记；跨页实测。
5. 完善 R11、R12：效果图二次约束与实际可视化，再提交真实课程截图/短片给用户。

每批以明确行为测试放行，不以再增加几百个模块测试作为目标。完成前保留原工作区改动和已成功作品；不要继续扩主题或布局数量来掩盖集成缺口。

本次交付为审查与修复方案，未修改业务代码；上述问题修复后须复审，不能直接把本报告当成完成证明。
