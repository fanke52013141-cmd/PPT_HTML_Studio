# 审核依据、能力路由与等待修复

用户目标：先修通用流程，再用“什么是遴选考试”原失败案例复验；不逐页美化，不由 Codex 手写业务 HTML 来替代系统 Agent。

## 已实现

对应规范：[审核依据、能力路由与等待 0.2.0](../../contracts/html-presentation/runtime/visual-v1/design-review-authority-0.2.0.md)，契约包 0.9.52、Agent API 1.33.0。

- `html_design_policy.py` 统一准确内容/主题高于图片、图内语义标签归代码的规则，并从真实受控编辑工具推导能力。
- 设计理解/还原/独立审核实际加载三份 runtime fragment 0.2.0；输出新增必需 requirement。程序依需求和工具决定路径，保留模型原分类和证据。新增 design_review；缺语义对象交 planning，缺呈现工具交 capabilities，图片身份/渲染问题才交 assets。
- 独立审核移除前一 Agent 完整结论，还原移除重复理解和全量变体目录；保留图像证据、准确对象、实际几何及适用工具。
- 流式包装保留调用方显式 request_timeout，缺失才默认 1800 秒；三设计阶段实际 600 秒。模型、思考和输出上限不降。metrics 记录实际预算；每次 completion 预算不是整任务绝对墙钟上限。
- 新源码及 runtime fragment 纳入快照/候选身份；不迁移旧响应、不重签旧候选、不改原失败。无需数据库、作者场景或导出格式迁移。

## 离线验证

固定事故清单升级 0.2.0，ignored `outputs/workflow-evaluation-20261015-v2/report.md`：**20/20**，Python **43 项**通过和一次实际浏览器检查通过。旧 18 项基线不跨清单比较。

设计/还原/生产/等待/重放/评估器联合运行首次 93 通过、1 失败：旧替身未补必需 requirement；已补为 unsupported_presentation，失败用例及重放验证定向 **6/6** 通过。没有放宽必需字段校验。

快照/runtime skill/执行指标 **59** 通过；恢复/任务/API **453** 通过；流式聚合、截断不修复、实际预算退出与参数保持 **6** 通过。Ruff、JS 语法、前端质量、Agent 矩阵生成校验、契约索引路径检查通过。现有 Starlette/anyio 弃用警告保持。

## 同案例真实诊断

脚本 `scripts/evaluate_html_design_review.py --live`，输出 ignored `outputs/live-linxuan-review-20261015-v2/`。模型是原系统连接 GLM-5.3-Flash，max_tokens=64000、reasoning_effort=max、temperature=1.0。通过共享 JSON 多模态适配器执行，Codex 不代写 scene，不将人工观察作为模型答案。

原设计 SHA256 `41126b1f2b648602ce20d1d6993431cc1bc12242a5edf42899d8ca38e3ee964a`；原理解场景 `3ab864b9e3779a94a3cee38dc338543229ce015ccae42c764daef32fa8b46c79`；原失败还原场景 `b6c8ea6d5be73e63bf7fd3a1de1a5abb36b9257e49cbc29c45731b6814c37c98`。均按归档核验，未改内容、图片或布局。

启动前曾被 ARCHIVED_REPORT_MISMATCH 拦住，尚未发出模型请求或创建输出；检查确认工程报告用默认 JSON 空格、模型记录用紧凑 JSON，两个模块原哈希算法不同。重放改为按各自原算法校验，并新增损坏场景/图片/工程报告拒绝测试；未改旧报告或取消校验。

两臂为独立诊断，不是续跑旧过期任务：第一臂重放原始理解输入，第二臂单独审核原失败截图，即使第一臂停止也不意味着生产继续。没有新规划、生图、素材、还原操作、作者保存、音频、视频或批准。

理解臂已返回：**unsupported → planning**，一次适配器/HTTP，154.659 秒。指出主体插图内“市地级以上机关”“内设机构”“下级机关”等是语义文字，但计划没有对应代码对象，不能让图片模型补字。旧理解 ready，此次在主体生图/容量修复/长时还原前即发现同一缺口。模型输出仅一项，不据此断言所有能力缺口均已提前发现。单次耗时比旧 96.488 秒更长，不宣称提速。

独立审核臂最终 **changes_requested**，一次适配器/HTTP，**588.448 秒**；完整流在 588.231 秒正常 stop，未延长 600 秒预算，没有截断修复或重试。返回 **10 项**：semantic_text 1、unsupported_presentation 6、typography 3。最终 routes=`capabilities,planning,reconstruction`，原来 `assets,reconstruction` 的错误职责不再重现。

实际模型行为：缺失机关标签明确要求新增代码对象，禁止图片补字；图注遮挡伴随内部位置/层级工具缺失交能力；分段强调、总结面板内部位置、tag/chip 装饰交能力；整 part 字号/字重才交还原。新审核没有要求恢复原图蓝绿；描述参考图绿色标牌只是定位证据，不是恢复色彩指令。模型建议仍需人审，例如图注问题同时建议调整主体避让，只能视为缓解方案，不能推定新增能力已实现。

共 **2 次适配器、2 次 HTTP**，各自显式 600 秒，耗时合计 743.107 秒不是整实验墙钟。保留 max 思考、64000 输出、温度 1.0。流终态提供实际 usage：理解 total_tokens=17129，审核=34201，合计 **51330**；费用无账单为 null。HTTP 开流记录的 usage=null 不表示没有用量，完整用量见 stream JSON 和 `comparison.json`。

理解输入 system+user UTF-8 为 12289 字节，旧次 8435；新增真实能力/依据使其增大。审核 15456 字节，旧次 15695，仅小幅减少。未包含图片、schema_hint 或 token 换算。两臂都比旧次慢，**没有时延改善证据**；提前停止避免继续进入原素材/修复/还原链，但不按旧耗时或 token 估算节省费用，不从单案例外推成功率。

`comparison.json` 与 `evidence-sha256.json` 保存归档对比及证据散列；原设计/截图/原失败记录保留。真实数据库仍为 2 个项目、active_jobs=0。正常服务确认无运行任务后从本 checkout 重载，父进程17716/服务24312，127.0.0.1:8010、原 DB/runs；startup complete，meta 确认 Agent API1.33.0/hash8e6142d20236326a。未续跑旧过期任务。

## 范围和后续

本轮验证的是提前发现缺口、审核依据、路径和预算实现，不代表本例 HTML、完整课程、视觉或逐句 QA 已通过。原失败保留，仍无作者场景和最终批准。课程协作暂停落入普通失败、第三页讲稿限定词弱化、容量诊断说明属于前轮已记录问题，本轮未修复或宣称验证。

后续按用户授权补了[多标签规划与注册呈现能力](handoff-labeled-capabilities-2026-10-15.md)：六个代码标签/三个关系槽和四个新变体，离线21/21。真实同案例规划一次请求因ReadTimeout停止，没有新计划或理解结果，不能记为模型使用新能力已验证。
