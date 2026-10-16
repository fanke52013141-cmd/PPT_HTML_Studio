# 多标签规划与呈现能力接续

用户授权“进行下一步计划”，承接[审核规则修复](handoff-design-review-fix-2026-10-15.md)，补通用语义对象和组件能力，再用原遴选案例验证。Codex 修改框架和测试，实际业务计划仍交系统配置模型生成。

## 定义与实现

规范：[多标签讲解与注册呈现0.1.0](../../contracts/html-presentation/runtime/visual-v1/labeled-explanation-0.1.0.md)。契约包0.9.53，Agent API1.34.0/plan_generate1.2，语义规划Prompt0.3.0；原请求/作者/数据库格式不变。

- explanation-labeled-v1@0.1.0 提供六个可选代码text标记与三个代码arrow关系槽，原十一槽及其公共对象继续复用。每个活动槽通过原对象、角色、初态、动作、原句及绑定验证，不让图像补语义标签。
- 固定 science-explanation-v1@0.3.0，新文件与原@0.2.0并存；旧文件/模板不改。intro、顶部图注、独立标记和总结区有明确容量；原主题按布局ID兼容，不复制色板。
- 四个新注册变体：text-emphasis-bold（既有runs强调字重）、arrow-up、figure-caption-top、summary-relationship-columns（term与takeaway在第三列）。新ID经原set_variant选择；不开放任意CSS或内容修改。
- compiler/schema/renderer与派生validator、catalog、data/player由build重建；新图注和总结实际子区容量检查，旧变体保留。
- 原语义规划入口发送真实新模板/槽位预算，明确图内标签及关系归代码。没有将考试名称或本例标签写进组件业务分支。
- 参考目录以前只按runtime布局ID登记，无法同时表示两个版本；保留原未加版本ID，新并存版本登记为runtime-layout:science-explanation-v1@0.3.0。实际布局仍按id+version解析。catalog构建和41个派生文件一致性校验通过。

## 工程验证

固定清单0.3.0、ignored `outputs/workflow-evaluation-20261015-v3/`：**21/21**；Python **49项**、原工作区浏览器与新部件浏览器各一次。新用例覆盖六个真实代码对象与来源/动作、七标签拒绝、旧模板不能偷用新槽、未绑定对象拒绝、受保护编辑不改文字/动作、整part工具与新变体选择。

另有规划/语义/新能力 **50项**通过；引擎基础14项/5场景通过，原呈现细节8项通过；新浏览器验证六个代码标签、三个向上箭头、400/700分段、图注避让、第三列term/chip、容量拒绝、seek像素一致、旧引用保留。

生产/设计/快照/运行Skill/恢复/API联合首次 **559通过、1失败**。失败仅在旧测试按layout.id取首项，错误拿到并存新版本；生产路径已按id+version查找。测试改为精确引用，失败用例与新规划/评估器定向 **12项**通过。没有修改旧布局、用排序掩盖问题或放宽容量。Ruff、JS语法、Agent生成矩阵、契约索引与diff空白检查通过。未重跑视频导出，因本批未改变导出器；不据此宣称导出或音频已验证。

能力截图为 ignored `outputs/labeled-explanation-20261015/capabilities.png`，是通用夹具，不是遴选作品。夹具标签/箭头仅用于能力/容量/时间验证，示范组合未作科学语义或审美批准，不能充当系统Agent自动生成证据。

## 同案例真实复验：未完成

新增 `scripts/evaluate_html_labeled_planning.py --live`：只读原项目模型与配置，隔离DB/runs，复用原设计作后续诊断；先用原权威视觉合同走正常generate_scene_plan，再编译并交原理解Agent。生产代码/注册定义固定，未知结果不得换参数自动重发。此实验不重规划整课，不生图、不写作者或批准。

初次启动 `outputs/live-linxuan-labeled-plan-20261015-v1/` 在本地参数组装时TypeError：调用者和包装器重复传stream_output，**HTTP=0**。已修正为合并kwargs，原记录保留；这不是供应商超时后的重试。

真正模型实验在 ignored `outputs/live-linxuan-labeled-plan-20261015-v2/`：GLM-5.3规划连接，max_tokens64000、reasoning_effort=max、temperature1.0、阶段预算1800秒。**1次适配器、1次HTTP**；首块0.803秒，累计10236块但content_chars=0，仅思考计数；最后进度155.910秒后无后续数据，**流280.559秒ReadTimeout，适配器281.635秒停止**。属于SDK读等待失败，不是1800总预算耗尽。无完整JSON、finish_reason或usage，费用/用量未知。

脚本state=stopped，规划外部结果unknown；没有格式修复、模型切换、第二次供应商请求或手填计划。**尚未得到新计划，未调用理解Agent，更未生成实际本例HTML**。原失败设计和作者scene=0保持，不能宣称系统模型已会用新模板或本例质量改善。

## 状态与后续

组件定义/实现及离线工程验证完成；真实“内容→多标签计划→设计理解”尚未完成。先核对原供应商请求状态和连接稳定性；无查单证据的同步未知请求不自动补发。后续新实验须明确保留本次失败、实际请求与费用未知事实，不能用新输出目录掩盖历史请求。

本地正常服务确认active_jobs=0后重载当前checkout，父进程33956/服务34548，仍为127.0.0.1:8010和原data/projects.db、runs。startup complete，meta确认API1.34.0/hash a74f99de4aa057b1；真实项目保持2个，active_jobs=0，原遴选作者scene=0。未续跑旧过期任务、提交代码或推送。

成功生成新计划后，需核对全部必要标签/关系是否代码化、对象语义与原句不变、资产need不含语义文字，再做正常设计/素材/还原与独立审核。原图历史批准不自动变成新计划或新版作品批准。性能、父子任务暂停、文章限定词及音频/逐句QA/正式导出仍未在本批解决。
