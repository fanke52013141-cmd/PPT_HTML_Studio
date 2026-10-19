# 外部 Agent 交接闭环与二次编辑：换机 handoff

日期：2026-10-19，Asia/Shanghai。仓库：`fanke52013141-cmd/PPT_HTML_Studio`，目标分支`origin/main`；本批基于`1eac2aca74e4a11c5b2f71d32bba6bd1e516ab05`提交源码更新，不是应用部署或课程数据迁移。
当前契约0.9.102、Agent API1.55.1、能力hash `1955ba5626df4f5b`；任务/结果JSON0.2.0，执行规范2.1.1，verification1.0.0。实际发布提交从Git日志及本批[发布备注](../../releases/2026-10-19-external-agent-handoff-and-editing.md)读取。
本文件顶部状态覆盖旧handoff中的“待外部回传/本地未发布”历史描述；旧记录不删，按各自日期和验证对象理解。

## 先读这些文件

1. 根README及`docs/contracts/html-presentation/README.md`：正式规则和当前入口。
2. `docs/agent/external-page-handoff.md`、`external-agent-entry.md`、`external-agent-execution.md`：页面操作、实际随包入口、执行/验收/交付。
3. `docs/contracts/html-presentation/runtime/visual-v1/external-agent-workbench-0.1.0.md`：输入2.1及2.1.1勘误、人工草稿和混合来源保存。
4. `editor_ui/README.md`和本文件“下一批开发”：已接入的开源交互和未实现项。

## 已实现的功能

### 外部任务与结果交换

- “调整页面与动画”内的“外部 Agent · 导出输入 / 导入输出”支持导出输入包、导入Agent输出、原检查/前后图、反馈JSON/完整反馈ZIP及独立保存。
- 输入ZIP含准确内容、实际原播放器截图、独立PNG素材、解析主题/布局、scope/人工保护、原动作/时间资料、约束/Schema、执行说明和官方Python/Node预检。设计图页另有只读设计材料导出，不等于已生成的可编辑作者页。
- 严格输出为`delivery.zip`，根目录`result.json/report.md/verification.json`；静态proposed另附绑定最终result原字节的`preflight.json`。旧JSON单文件模式仅兼容，不能绕过严格任务要求。
- 导入按当前任务/材料/源码/API/作者revision/音频身份、操作Schema和旧人工保护复核，再调用原repair/播放器；导入不写作者，通过后也须用户显式保存。外部不获得人工来源、审批或任意代码执行权。
- 必需能力不足必须needs_input/unsupported、operations=[]；看图能力要求为true的候选须有实际原图审阅记录。文件模式原DOM/指定遮挡/after可not_run，由主机接续。能力声明及审阅记录是外部证据，完整性通过不能证明模型内部确实调用视觉工具。
- `manifest.json`及存在的`trial-manifest.json`属于本轮材料校验，不是旧答案；冷启动必须核验。原旧输入包不回填新规则/ID。

### 人工二次修改

- 正式编辑器已经集成Moveable0.53.0、Selecto1.26.3，以及React Timeline Editor1.0.0：画布拖动/单对象缩放、框选/多选移动、吸附、撤销/重做、保存与重开。时间轴使用原音频/播放器的单一时钟，有有效音频和绑定才允许相应动作编辑。
- 外部合法静态候选可创建持久B/A/W工作草稿：B原页、A外部候选、W人工修改。当前接手面板提供对象/参数、撤销重做、恢复A、恢复工作草稿、原检查、显式保存；容量/几何失败可留诊断草稿，但正式保存必须全部复验。
- AI候选先按原AI保护重放，人工只在原scope/静态Schema内修改；最终只为人工实际触及且相对B确实改变的叶字段增加保护，不把全部AI改动误记成人工修改。
- 当前人工接手仍是参数面板，主画布保留B，A/W以实际图或诊断图另显；候选/W直接画布编辑、已保存版本恢复、关联组局部采用、辅助布局试算未实现。

## 真实外部 Agent 复测：到哪一步算通过

本机实际Token课程第3页的历史未保存候选，等值隔离为revision1；目标是底栏from/to的17px字号提高到至少22px，保留准确内容、关系、主题、PNG、全部motion/binding及非scope对象。不是重新设计整页或完整音画成片测试。

| 阶段 | 结果 | 归属与边界 |
| --- | --- | --- |
| 最早首轮 | 原compiler拒绝保留入场端点越过800px内容边界 | 操作Schema合法不代表全过程布局合法 |
| 执行2.0试验 | 只改字号，真实DOM约48px超过44px预算 | 输入实际值/预算表达和便携检查不足，执行也未完成联动修复 |
| 输入2.1试验 | 参数工程检查通过；外部声明不能看图，严格交付拒绝 | 规范中“纯参数候选”泛化表述有歧义，已由2.1.1修正；不把主机诊断通过算成外部正式成功 |
| 执行2.1.1新试验 | 完整交付/看图记录、独立官方预检、严格导入和原播放器预览均通过 | 80个有限采样时刻、指定4组对象对及三项字号目标通过；尚未保存/人工批准/正式输出 |

最新真实任务ID：`054a3371b97282ea48dd5def1d807f775df26245614ee547f0e9c93eec54ad03`。
输入ZIP SHA256：`19d80b37a9622b0527125a7947b50f8dfc5f4f7f2212dbd48d07d8d70e76a6b9`。
外部delivery SHA256：`543076070004c601643d0ee55f299fb13b737323b8e94df33605b4304f3d2633`。
结果原字节SHA256：`3112c316ed51eb3c04c400ab2d3b2e1348e6295401b2eac38ee29922e7ba363b`。

这次外部只改四个叶字段：from/to字号17→22、底栏高度140→144、offsetY -32→-33。原DOM标签高约48.00001px，限值48px，在已有1px容差内；保留入场端点底边800px，正好到内容边界。第三卡与底栏终态间距14px。实际图未见新增截字/重叠；与上一修复版视觉接近，交付合规与间距改善更明确。
该方案用满容量和边界预算，后续改文案/字体/位置须重验，不沿用旧回执。只验证列出的对象对与有限时刻，不声称全对象/连续全时段安全。

可迁移的证据摘要：[external-agent-token-2026-10-19.json](../../validation/external-agent-token-2026-10-19.json)。本机原始ZIP、截图、原系统回执保留在忽略的`outputs/external-agent-input211-20261019`及`outputs/external-result-review-input211-20261019`，桌面对应“外部Agent复测_规范2.1.1_20261019”。原指定“agent辅助html转动画”目录仍是旧交付，不能混为新结果。

明确未通过/未做：真实作者保存、用户当前视觉批准、真实音轨试听/音画同步、逐句语义批准、正式视频输出、跨课程批量稳定性。单页首轮成功不证明自主失败恢复；更换模型/工具后不把变化归因于规范单因素。

## 服务和模块所有权

| 所有者 | 职责 |
| --- | --- |
| `html_external_handoff.py` | 输入包、当前任务/身份、原repair组合和采用资格 |
| `html_handoff_models.py` / `html_handoff_contract.py` | 交换模型、按已登记能力派生操作Schema |
| `html_handoff_execution.py` / `html_repair_static.py` | 能力/逐项验收、同源事实、原静态操作 |
| `scripts/check_external_task.py` / `html_engine/tools/handoff-preflight.cjs` | 随包官方静态预检；不是第二渲染器，不替代原DOM/视觉 |
| `html_engine/visual/relationship-capacity.cjs` | relationship内部容量纯逻辑，renderer/导出/工具共用 |
| `html_handoff_diagnostics.py` / `html_handoff_workbench.py` | 原系统诊断、持久人工工作草稿/检查/混合保存 |
| `html_handoff_routes.py` / `agent_api/html_handoff_routes.py` | 原account/project权限、工件锁、原失效；外部Agent仅work_read，人工写仅Web |
| `static/html_external_handoff.js` / `static/html_handoff_workbench.js` | 输入输出、反馈、接手参数UI；复用公共transport/escaping，不画第二套页面 |
| `static/html_scene_editor.js` / `html_editor_canvas.js` / `html_editor_timeline_bridge.js` | 正式编辑器草稿、事务/撤销/保存、开源画布和原音频时间轴适配 |

没有数据库迁移，原图片工作流、TTS/音轨、资源、数字人、原硬边界及审批流程保持。保存复用原最小重建/失效，不新增业务失效原因。

## 下一批开发：优先改善二次修改

以下为待实施方案，不能描述为本批已交付。沿HPS-007/009/010/013—018及对应编辑/工作区卡补定义和验证，不整体更换renderer或音频系统。

### 第一批：候选画布、易懂属性和操作恢复

1. 将合法A/W挂到已有共享播放器和Moveable/Selecto适配器：导入→继续编辑→在候选上直接选/拖/缩。界面清晰切换B/A/W；主编辑器事务桥接到工作服务，原scope/Schema/人工保护/当前性始终有效。失败草稿用既有诊断模式显示，不伪装成已通过。
2. 属性面板显示“左侧标签字号/底栏高度/向上移动/上方间距”等中文含义；内部仍映射登记part和绝对赋值操作。高级字段按需展开，不要求用户读JSON或obj-summary/from/offsetY。不因UI方便扩充外部修改权限。
3. 单次手势一个原子事务；允许有界工作草稿临时容量失败，便于字号/父框/位置联动修改。原作者不变，保存前仍完整检查。
4. 工作草稿及操作历史可跨刷新恢复；与正式页普通Map会话草稿区别明确。先实现可靠恢复和原子撤销，再提供保存前检查点和恢复为新revision；不把会话undo冒充历史版本回滚。

第一批验收：用最新Token原始页和外部候选，用户不改JSON即可增大字号、拖动底栏、撤销重做、刷新恢复、查看问题、检查保存并重开；原文/资源/motion/binding、人工叶保护及音频保持。另测容量失败草稿、越界、旧revision、切页迟到响应及旧人工保护反例，保存失败不得污染作者。

### 第二批：联动提示、版本和局部协作

1. 从同源actual/limit/保留动作推导缺口及余量：例如“需扩高/入场端点越界”，提供可预览、需确认的联动方案；不静默缩字、改安全线、自由CSS或放开scope。
2. 保存前检查点、已保存版本恢复为新revision，并按原失效规则重新验证；不迁移旧视觉/语义批准。
3. 按可验证的关联组比较/采用：字号与父框/位置等依赖联合复验，不任意剔掉单条操作却沿用旧通过回执。
4. 人工保存后从当前版本重新签发局部Agent任务，明确保留人工字段；不要求重做全页。草稿直接导出如后续需要，须另定义其身份/保存语义，当前不冒称已支持。

Agent独立完成与自修复另测：固定布局、动作、带人工保护及缺能力应停四类案例；包含首轮成功、真实反馈后二轮修复和合法停止。记录有效修复/误改/人工介入/轮数/耗时与未知费用，不加无限重试，不调用未授权付费服务。

## 换机、运行和数据边界

- 只从本项目origin/main获取源码；禁止推送原图片项目upstream。Git不含数据库、runs、outputs、桌面测试包、课程图片/音轨、模型凭据、字体或虚拟环境。
- 目标机先按requirements-dev及html_engine/editor_ui/Remotion锁文件准备依赖、Chromium、FFmpeg和生产Windows Microsoft YaHei字体；构建生成物从源重建，不能仅修改bundle/validator。CI使用提交原字节，勿全仓换行归一化。
- 从实际仓库根目录启动，使用`start_server.py`，显式设置独立DB/runs/host/port；不能启动第二实例共用数据。模型和可选数字人连接在目标机检查，不替换现有音频方案。

```powershell
$studioCheckout = (Get-Location).Path
$env:PPT_STUDIO_HOST = '127.0.0.1'
$env:PPT_STUDIO_PORT = '8010'
$env:PPT_STUDIO_DB_PATH = Join-Path $studioCheckout 'data/projects.db'
$env:PPT_STUDIO_RUNS_DIR = Join-Path $studioCheckout 'runs'
.\.venv\Scripts\python.exe start_server.py
```

本轮不部署/启动/重启生产服务。其他机器仅有代码时，应新建测试项目或私下安全迁移必要课程数据后重新导出任务；历史task_id/ZIP记录不能自动成为目标机当前任务，不能改旧result的ID重新采用。

## 验证与发布备注

已有针对本地执行2.1.1的531项相关回归通过，另有单项封装重跑、Ruff、能力矩阵、空白检查通过；更早输入2.1的608项与此有重叠，不能相加。真实外部结果独立于这些夹具测试，见上述证据摘要。
本批推送前的canonical full记录2717 passed、8 skipped、1项TEMP隔离位置前置断言失败；修正测试环境后该项原断言重跑1 passed。完整runner退出码仍为1，不声称单次全绿。编辑器16项、共享视觉14项（pageErrors=0）、Remotion TypeScript及Ruff/矩阵通过；详见发布备注。GitHub CI以本次实际commit的运行结果为准，不沿用旧提交成功状态。

本机全量检查的环境注意：必须按锁文件安装`jsonschema`及其依赖；测试TEMP保持系统短目录。首次检查使用过深的仓库内TEMP，使冻结快照预览入口路径达到255字符并失败；同一快照原字节复制至短路径后通过。默认GPU像素复验避免与其他浏览器套件并行，软件生产捕获仍严格检查。首次未完成的全量运行不作为通过证据，最终以环境修正后的完整运行记录为准；未降低现有断言或安全边界。
