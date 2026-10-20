# Pi 生成、自动保存与批量任务 0.1.0

M4–M5定义卡；适用HPS-007/009/010/013/015–018/023–030/037。定义、实现、真实模型和发布验收分别记录。

2026-10-20 GLM参数修订（契约0.9.107，API字段不变）：GLM-5.3系列沿用户指定原生请求，`thinking.type=enabled`、`max_tokens=65536`、`temperature=1.0`；输出额度取冻结连接值，上限65536，不再静默截为8192。文字规划使用glm-5.3；需要真实图片的阶段使用明确支持图像的glm-5.3-flash。Pi最终出站payload显式写入thinking和max_tokens，不把SDK会话的通用thinking标签当供应商实参；其他模型保持原8192/off兼容配置。旧8192/off试验保持历史，不据此推断新参数成功率；参数变化重新签发独立任务，原未知任务不重放。调用/工具/时间/素材预算与批准规则保持。

局部修复增加delivery_policy=save_revision：提交即授权原检查通过后以AI来源另存，不赋予人工批准。保存前重新核验项目/账户/目录、原修订、音频与人工保护；提交前取消有效，进入原子保存后取消不能伪称撤销。写前意图与完成回执持久化，中断不重放未知作者写入。通过原handoff.save_result及html_scene_changed更新，下游语义/视觉/声音签收独立。

项目级固定任务为article.generate、storyboard.plan（script/visual）、scene.batch_repair。沿agent-job/1.0外壳及现有local_jobs；子页状态、失败与共享预算必须保留。文章/分镜仅候选，原权威内容、保留限定条件及应用入口不变；不能把候选自动签作已确认讲稿。批量修复仅候选，不能按子页重置总调用/时间预算。独立失败可继续剩余页，父任务outcome须明确partial_failure，partial_results保留已完成页；父任务succeeded只表示编排结束，不表示所有子页成功。

新页生成复用原html_review.produce1.14能力（POST /html-review/{slide_id}/produce），不再造scene.generate端点或第二个生产存储。runner=pi须在输入中提供明确选定的当前design_candidate_key；此输入表达设计参考选择及原生产入口的保存授权，不是HTML审美批准。沿原快照固定页/修订/设计/模型，复用produce_scene/规划/资产/重建/检查；Pi提供文字模型执行，原图像供应商、已返回缓存和未知不重发政策保持。不得新造通用CSS/renderer。该入口通过原检查后直接保存；当前不提供新页的candidate-only模式。若只需待审设计，继续原生成设计入口。独立图像调用max_image_calls默认0，显式授权0–2次；缓存命中不产生新的调用。

新页保存重验基线，原人工保护与资产身份不放宽，以AI来源留存可恢复版本，不转移旧批准。新结构只能走原生产入口；不得借repair强行新增节点。文章/分镜应用继续原导入、归一化、风险和失效逻辑。

执行器选择按任务类型显式配置Pi/既有入口。真实重复案例未达既定门槛时不得删除仍在使用的旧执行器或声称已完成默认切换；研究与产品代码状态分开。图像/TTS服务不替换，确认和正式输出门禁不改。所有新接口同步Web/Agent/MCP/CLI并保留账户与后端检查。

验收：自动保存/冲突/人工保护/取消竞态/回执/恢复；真实SDK固定JSON提交与图片字节；原生产链新页可编辑且严格设计身份；文章/分镜沿原validator与限定词检查；批量共享预算、部分失败和各页状态；原编辑器/快照/接口回归。脚本供应商不代替真实模型质量及发布阈值。

## 固定接口与交付

- 局部修复原接口增加delivery_policy=candidate|save_revision，默认candidate。can_cancel=false表示已进入保存或终态，不能承诺撤销。保存回执在planning/html_visual/pi-commits，重启未完成写入返回save_outcome_unknown并核对版本。
- POST /api/projects/{project_id}/agent/jobs；Agent前缀/api/agent/v1。GET /{job_id}、GET /{job_id}/result、POST /{job_id}/cancel（{}）。同project/idempotency_key只执行一次；不同内容409，跨账户/后端拒绝，未知请求不重发。
- task由task_type判别，禁止额外字段。article.generate输入topic（1–500字）；storyboard.plan输入phase=script|visual及requirement（最多2000字）。服务器冻结项目原文/Prompt/正式讲稿，visual须已有非待审讲稿。最大原文256KB，整体输入1MB。模型/工具/时间沿AgentLimits，Pi固定OpenAI兼容协议；GLM系列按上述原生thinking与冻结输出额度，其他模型保留thinking off/8192tokens兼容配置，实际模型配置与SDK调用另行留证；原阶段request.json记录的是业务请求，不代表适配器已启用thinking。
- scene.batch_repair输入items=[{slide_id,task:ExportRequest}]，1–5页且不能重复。父预算限制全部子任务，取消贯穿子任务安全边界；无额度页为not_started。成功页返回原严格交付及preview，仍需原保存入口重新检查当前基线。
- 新页沿原html_task_store/任务查询取消与回执，不混用agent-job外壳。runner=legacy为兼容默认，runner=pi的pi_limits使用同一强类型预算；所有文字阶段使用完整Pi SDK的submit_json工具，宿主原归一化/审阅/重建决定是否接受，SDK不能自报系统通过。
- 新页各业务阶段沿原最多两轮校验，PiProductionLimits.max_candidate_rounds固定为2，不接受声明一轮却运行两轮；全部阶段共享模型/工具/时间预算。项目文章/分镜则按max_candidate_rounds最多两轮，对已返回且未过原校验的对象附真实反馈修正；网络失败、未知请求和源变化均不进入该重试。
- 文章交付result.candidate.content；讲稿交付result.candidate={title,slides}；可视化交付result.phase=visual及candidate={slides}，均附source_identity、saved=false、原应用入口说明。网页可下载Markdown/JSON候选；二次采用进入原文章导入/讲稿/可视化保存入口，不把下载当自动审批或已应用。

## 兼容与状态

HPS-007/009/010/013/015–018/023–030/037：增加请求字段和能力，契约0.9.106/API1.59.0；旧默认调用和外部交接0.1/0.2保留，无数据库迁移。能力及源码闭包变化导致旧设计/外部包过期时须原入口重验或重新导出，保留历史，不反签。Pi生成记录AI来源及前后可恢复版本，编辑器版本恢复仍进当前草稿，不恢复旧批准。图像/TTS/导出验收无放宽。

实现包含可选Pi接线、预授权修复另存、文章/分镜/批量候选与Web/Agent/MCP/CLI。工程证据见本轮handoff；真实复杂新页、各任务重复成功率和默认切换/旧编排移除仍属单独验收，未满足时保持旧入口。
