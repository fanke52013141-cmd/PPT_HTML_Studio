# 正文边界与动态工程前置 · 2026-10-21

本地未提交/推送，未重启应用或提交新供应商请求；包0.9.113/API1.60.0保持。承接水循环试验的卡片截字、卡片/摘要重叠及自然关系箭头穿字。当前交付是检测与生产门禁，不是原页已经修复或通过视觉/声音验收。

## 实现

`html_engine/visual/renderer.cjs`复用原DOM Range和capacityEvidence，对card与text-card的正文额外测量实际父容器内部边界（扣边框、内边距），保持1 CSS像素容差；不改文字、CSS造型、尺寸、颜色或动画来通过。解决子段落高度/行数都合格，但被父卡片裁切的漏检。capacity补充父容器左/上边界证据，浏览器bundle由原build重新生成。

新增左/上边界检查仅用于父卡片，不把普通inline span的字形上沿超出自身行内框误当作裁切。容量已失败时保留静态诊断，动态检查明确标记blocked_by_capacity；先按原容量/剩余还原预算处理，修复后再做完整动态复验，最终不得跳过。避免严格prepare拒绝容量失败候选时，误把它归为检查器故障并丢掉修复机会。

`html_visual_review_service.review_scene`的内部preflight_dir组合原静态审阅与原review-temporal/checkTemporalPage；还原每轮请求前给出当前问题，每个候选（含unchanged）静态检查后复验。作者时钟、30fps output_frames和动作边界、registered策略及既有SVG线段/文字规则保持；没有新增模板豁免、替代渲染器或自动几何改写。报告缺失/失败、完整覆盖声明缺失、范围/fps/帧序不符均失败关闭，不降采样。

原始scene/spec/report/实际截图留在还原候选审计中，纳入原production provenance；模型只消费有限问题分组、首末时刻/次数及首个实际测量（至多64组，截断显式标记，完整报告保留），附scene和raw report hash。报告声明连续时间未证明、声音时钟/审美/语义未验收。

`html_design_reconstruction.py`程序Prompt0.6.2、运行片段design-reconstruction/0.7.4及注册hash同步。最终工程失败先反馈剩余还原轮次，不调用独立保真审核、不返回可保存生产结果；原两轮/600秒/low effort、注册静态工具和人工保护不变。原模型/素材unknown不因源码变更重发。

范围是设计还原生产链；原手工编辑器的结构保存接口没有增加浏览器检查，原repair显式预览/保存继续使用其动态检查。无新公开参数、API/Schema或数据库迁移，旧候选/批准按源码和bundle指纹重新核验，不升级历史证据。

## 验证与真实材料

- 专项受控测试覆盖：父卡片溢出（旧子元素高度、行数都合法，仅新增父边界触发）、原SVG实际穿字与30fps完整证据、报告缺失/错误/覆盖不完整或旧通过结果拒绝、unchanged仍失败且不能进入保真审核/作者保存。
- 原共享视觉引擎build完成，容量/关系摘要/局部强调单测与5场景14组浏览器检查通过，pageErrors=0。
- 最终真实失败候选只在隔离副本只读复验：第3页三张卡片分别检出约16.65 CSS像素底部越界；第4页540个时点检出3组stroke_crosses_text（318/213/207次），GEOMETRY_PREFLIGHT_REJECTED。原图/讲稿/关系与原项目作者均未写入、供应商请求0。最终机器记录在`outputs/production-preflight-20261021-final/summary.json`；较早`outputs/production-preflight-20261021/`保留收窄普通inline上边界误判前的诊断，不作为最终结果。
- 扩展回归64 passed（1009.17秒），涵盖生产恢复/集成、容量Agent、原SVG检查、快照/来源等。随后完成inline边界范围与blocked_by_capacity收尾修正，最终专项`test_html_production_preflight.py`＋`test_html_design_reconstruction.py`为13 passed（65.73秒）；原视觉引擎测试再次通过5场景14组，pageErrors=0。64项扩展组未在收尾后全量重跑，不将专项与扩展重复计数。
- 全仓ruff、Agent契约同步与git diff --check通过。无真实新模型修复/视觉批准试验。默认浏览器截图像素一致性是上一批已留证的独立问题，本批不放宽该检查、不声明问题已关闭。

## 后续

沿原有限容量/还原/关系坐标修复路径解决已拦截的问题，缺能力回capabilities、端点/关系语义错误回planning。先检查当前源码与任务状态；既有unknown仍不补发。合格HTML作者保存、声音/绑定/逐句QA和正式输出尚未在这套新课程闭环验证。
