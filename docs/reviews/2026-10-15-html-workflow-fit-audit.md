# HTML 功能与可见流程适配复核

2026-10-15，Asia/Shanghai。审核对象：main `7238aa3515e809bd4f7cf2789bd08ce78e9e1f24` 加尚未发布的HTML工作区整理；契约0.9.45。按 code-review-and-quality 核查正确性、服务归属、恢复/批准保护、界面及能力边界。此报告是审查证据，不是功能验收批准。

## 结论

**主生产顺序一致，但功能与可见流程尚未完整适配。** 分镜 → 整页设计图 → 用户确认 → 独立主体素材/代码还原 → 真实音频绑定 → A04 → 人工签收 → 正式输出的后端链已接入，未知结果保护和目标门禁保留。上一轮做的是界面整理，不能因此称为全流程功能完成。

本机A06仍在第一页设计待确认；没有实际HTML、其余四页、TTS或完整视频证据。读取任务/页面/状态未点击生成或批准，未修改用户作者数据、旧unknown或运行任务。

## 需修复的问题（按影响顺序）

### 1. P1：可见步骤未使用同一套真实当前性状态

定位：static/flow.js:104、static/flow.js:123、static/flow.js:202、static/flow.js:230；static/workspace_navigation.js:325；html_creation_workflow.py:412。

设计图和还原页面仍共用旧completionSteps=[4]；HTML就绪为false时，getVisibleStepState(5, {'4':'completed'}, {htmlScenesReady:false})仍返回completed。前端读html-visual/status只保留ready布尔，未消费设计候选/批准失效/音频状态的分项事实。后端七阶段也把“设计、素材、实际HTML”合成一项，与新的两个面板不同。

实际查询A06返回设计needs_review、场景缺失，旧step3/4仍pending；水结冰项目真实HTML状态needs_review、音频stale，而旧step3/4/6/7均completed。不能拿旧完成字段证明当前审核通过。输出后端仍blocked，没有发现由此绕过导出门禁。

修复方向：以已有设计候选、实际场景、当前批准、音频和A04事实投影各步骤；明确“已生成/待确认/已过期/完成”，保留每页及全课聚合。别再用单一ready布尔或旧图片阶段完成位代替。

### 2. P1：配音页缺少与新流程一致的同步审阅闭环

定位：static/narration_audio.js:247、static/narration_audio.js:503；static/event_bindings.js:252；static/html_review_panel.js:265；static/html_scene_editor.js:654、static/html_scene_editor.js:698。

配音页是讲稿编辑与audio控件，HTML编辑器是画面时间滑块/播放；没有把两者接成同一播放时钟。现有A04提供每句三帧截图与模型判断，不能替代完整画面与音频联播试听。逐句QA入口在前一步还原面板的折叠区域；配音确认按钮却导航到数字人或输出。用户顺着侧栏往后走会漏掉必需签收，再被导出门禁拦截。

修复方向：将逐句核验与实际同步试听作为配音阶段的显式操作，复用已有音频绑定/共享播放器/A04服务；确认后明确导航到尚缺的签收，不能仅改按钮文字或自动签收。

### 3. P2：已确认设计重新打开后不能查看原图

定位：static/html_review_panel.js:446。

恢复只在needs_review时showDesign；accepted_for_reconstruction分支仅showAssetRetry。点击“查看/修改设计图”回到设计面板时，已确认的原图会隐藏。隔离DOM probe复现accepted_design_hidden=true；不依赖付费供应商。

修复方向：展示当前已确认设计与接受状态，原图可查看；将查看、修改、新版本和继续还原分开，不把已确认图再当未确认图自动接受或盲重发。

### 4. P2：按钮门禁缺少前置条件且被父面板覆盖

定位：static/html_semantic_qa.js:24、static/html_review_panel.js:380。

QA start只看required，当前真实A06显示SEMANTIC_SCENE_MISSING仍可点击。更具体的复现：无语义报告时人工签收按钮本来disabled，父面板页面review结束后querySelectorAll('button').disabled=false将其启用。父面板不应重置独立QA、素材板、编辑器的按钮权限。后端仍校验报告/版本，不能推断无效签收能够成功；问题是界面误导和无意义失败。

修复方向：父面板只管理其自身请求按钮；QA由自己维护报告/场景/音频/运行状态前置条件，显示缺什么、下一步去哪。

## 能力边界需在产品中明确

| 当前说明 | 实际能力 | 适配结论 |
|---|---|---|
| 多张配图可用素材板 | 素材板可生成、提取、接受为资源，编辑器可人工改assetRef；自动语义生产的asset_budget固定1 | 部分支持。多张素材尚未自动分配到多个页面对象，不等于多素材自动还原闭环 |
| 动画/圈画/高亮 | plan0.2 PlannedAction.type仅enter/emphasize；注册annotation可描引线 | 出现/强调及注册标注支持，自由手写圈画、任意状态变化/退出并未实现；不能以取消旧勾画入口冒充替代功能完备 |
| 数据图表属于页面对象 | 规划节点种类中没有原生chart/table；已有图形和组件可表达有限关系 | 不能承诺通用图表数据绑定/编辑。先定义具体图表类型及公共能力，再扩展 |
| 每页不一定展示标题 | 三个当前生产模板header槽均required，规划会拒绝缺失header | 页面名称与大标题概念已澄清，无标题生产页仍未实现；用户说可暂时保留标题，不作为立即阻断项 |

来源：html_semantic_design.py:19、html_production_service.py:318、html_semantic_plan.py:28、html_storyboard_planning.py:31/205、html_engine/visual/templates/*、effects/registry.json、static/html_asset_sheets.js:99、static/html_scene_editor.js:266。

## 核验与保留证据

- 后端相关联合回归：62 passed / 1 failed（27.33秒），集合为test_html_creation_workflow、test_html_course_jobs、test_html_audio_binder、test_html_semantic_qa、test_html_model_binding_integration。不能报告全绿。
- 失败test_workflow_job_cache_hit_and_changed_input_conflict_preserves_manual_scene单独重演仍失败；捕获mark_failed分类证明DESIGN_PROVIDER_MISSING，即测试没配置设计图provider却仍期望直接生成scene。这些后端/测试文件本轮未改，fixture与当前“所有页设计先行”规则未对齐。应修正夹具并重新验证缓存/人工保护，不删除断言或放宽设计门禁。
- flow回归、面板DOM16项、正常应用向导/导航/恢复、A04浏览器6类检查通过。使用HTTP doubles，不能登记为真实整课生成。
- 额外隔离DOM与纯flow probe复现上述状态、已接受原图隐藏、过早QA、父面板错误启用语义签收；没有调用实际produce/批准服务。
- ignored本机证据：outputs/a06-local-normal-20261014/workflow-fit-audit-live.json、workflow-fit-probes.cjs、workflow-fit-probes.json。原始运行仍留在runs，本报告不包含密钥或生成媒体。
- 原发布记录中的两项Agent planning字段缺口保持未解决；本轮没有完整Agent suite重跑，不将其登记已通过。

## 建议处理顺序

先统一真实步骤状态和配音后核验闭环，再修复已确认设计查看/继续及独立模块按钮权限；随后根据具体课程需要扩展多素材/图表/无标题模板/更多动作。每轮分别记工程、实际模型、试听与人工签收，未完成前A06仍partial。

## 后续修复记录（2026-10-15，尚未发布）

- 已确认设计恢复时重新展示原图与已确认说明，隐藏重复确认按钮；仍保留原候选标识及素材修改入口。
- 父面板忙碌/恢复只控制自身 `button[data-action]`，不覆盖独立 QA、素材板及编辑器的按钮权限。
- QA 启动遇到缺少场景、缺少音频或无效输入的服务原因时禁用；缺少报告仍可启动，不改变后端审核与人工签收门禁。
- 面板 DOM 回归扩展至19项，覆盖已确认原图回看、重复确认隐藏及独立按钮保持禁用；语义 QA 回归增加缺场景/缺音频/无效绑定及缺报告可启动的检查。两组、正常向导导航回归、frontend quality及 `git diff --check` 通过。均为隔离测试，不是实际课程批准。
- 步骤状态投影基础代码已加入，仍须完成来源与输出事实验证；统一音频播放时钟和配音后签收导航仍未完成。
- Stitch 编辑请求传输失败；随后成功读取原项目屏幕清单，未发现新增设计，不能登记布局优化已完成。
- 配音页新增 HtmlAudioReview：复用现有编辑预览绑定服务，audio.currentTime 驱动画面、绑定字幕定位、切页/项目/步骤停止；过期音频拒绝联播。逐句 QA 迁移至此，音频确认后全课同步未完成则留在配音页。新增隔离浏览器测试通过，覆盖音频时钟、句子定位、切页暂停、过期拒绝、无生成/批准请求及图片后端隔离。共享真实播放器及真实课程试听仍待验证。

## 最新工程核验（接续上方分阶段记录）

上述四项实现缺口已有修复和针对性回归。共享真实播放器与真实绑定服务的隔离音频联播通过；正式输出当前性、迟到状态读取、输出前置导航及七面板×三宽度已新增验证。HTML配音不再读图片列表，首次旁白同步入口恢复。67项后端联合回归通过，旧失败夹具修正为设计先行和显式接受，原人工冲突断言保留。

Stitch既有三稿已取回并据其结构落实代码布局，新的编辑请求没有确认结果，不重发、不冒称新生成。当前交接及仍待真实课程/视觉核验的项目见[2026-10-15闭环交接](../plans/html-backend-development/handoff-html-workflow-closure-2026-10-15.md)。上方的“尚未完成”是修复前/中间阶段记录；实际课程签收仍未完成。
