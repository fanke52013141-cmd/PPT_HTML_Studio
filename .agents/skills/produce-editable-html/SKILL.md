---
name: produce-editable-html
description: Produce and verify editable HTML slides from this repository's slide contracts, repair unsaved layout candidates or saved scene typography/layout/motion, and diagnose failed HTML production. Use for 生成可编辑HTML、初稿溢出、调整文字位置字号、验证自动生产与二次修改. Use registered components and shared APIs; exclude image-only production, standalone websites, and generic framework advice.
---

# 可编辑 HTML 生产与局部修复

Skill 版本：1.2.1（2026-10-12）。目标是交付实际可打开、可编辑、来源可追溯的作品。

本文代码与文档路径均相对仓库根目录；`references/`、`evaluation/` 相对本 Skill 目录。
先读 `docs/contracts/html-presentation/README.md`，再读其下 `runtime/visual-v1/application-production-0.3.0.md`、`scene-repair-0.1.0.md` 和 `candidate-layout-agent-0.1.0.md`。从 `agent_contract.capabilities` 获取实际可调用能力和请求 Schema。参考图谱不等于运行组件目录。保持内容、场景、资源、绑定为唯一源；DOM/截图/视频为派生物。

## 执行主体与任务路由

- 说明哪些是程序渲染、哪些是模型规划或修复、哪些是人工编辑。模型返回计划、共享组件渲染 HTML，不能说成模型直接编写了最终 HTML。
- 当前运行时 Agent 使用 `html_candidate_agent.py` 中的提示词，没有自动加载本文件。修改 Skill 不等于改变豆包运行行为；接入状态与版本必须分别记录。
- 初稿使用生产入口；未保存的容量失败使用内部候选 Agent；已保存作品使用局部修复入口。资源、网络、Schema 错误先定位失败边界，不能用排版循环掩盖。
- 文案语义重写、增删节点或换模板回到权威内容和新规划；新图片走素材服务。禁止运行时 Agent 任意修改组件源码或生产 CSS。
- 默认黑灰白基线；保留用户已选风格和人工修改。通过字号层次、间距、对齐、线条与灰阶改善美感，不以不断缩小文字作为通用解法。

## 初稿

1. 读取当前页权威visual_contract和注册模板。检查项目文字/图片模型绑定，默认neutral-baseline黑灰白。已有素材先验证 assetRef、身份、版本及文件内容并显式复用；不能因已有图片而误入新生图分支。
2. 用html_review.produce进入生产，由服务调用模型返回plan；结构错误由服务一次重试；容量失败的未保存候选由服务内部 LangGraph 排版 Agent 最多三轮，实际截图/测量驱动，严格重验才保存。资源/Schema 错误不进入循环。失败停止，不手写计划后声称自动成功。html_review.plan_generate仅用于独立规划诊断，其输出不会自动被produce复用。
3. 有新图片时停在design_review。展示设计候选并沿用已授权的批准范围；审批使用实际design candidate key。
4. 接受后复用同一任务继续独立主体与场景生成。禁止整页图片替代HTML正文；准确文字、关系由代码控制。
5. 读html_editor.read，再用html_repair.evidence检查实际渲染。展示本次任务实际保存的HTML和带时间截图，不以旧样板替代。诊断预览 passed=false 不能当作已保存成功。纯代码页沿用现有无生图分支。

## 局部修复

在需要复现一页输入或核对检查版本时，先读 `docs/contracts/html-presentation/runtime/visual-v1/input-snapshot-0.1.0.md`。使用 `scripts/html_snapshot_check.py freeze-render --run-dir <run> --slide <id> --expected-revision <revision>`，随后 `review --snapshot <path>` 检查固定输入，展示返回的实际 HTML。generation 快照已由生产任务消费；恢复规则见 `docs/contracts/html-presentation/runtime/visual-v1/production-recovery-0.1.0.md`。同输入失败/中断可显式重提交，已返回响应复用但归一化与实际检查重做。intent/unknown、坏产物或过期 revision 必须先诊断；不要修改阶段账本或换一个无意义参数绕过阻断重复生图。取消不恢复；作者已保存而任务中断时先读取现有作品核实。QA 校验必须匹配期望快照和证据目录，不能只看报告的 passed。此入口目前只检查静态终态，不批准视觉、不证明动态/音频/导出通过；不能替代下述作者编辑 API。

1. 读html_editor.read，冻结revision；选定公开对象ID和scope。暂停帧仅用于定位，基础属性会影响对象整个生命周期。
2. 根据问题选set_presentation、set_text_style、set_motion或set_binding；字段以生产Schema为准。字体/布局需scene0.5，服务显式升级；annotation不能覆盖其坐标空间。
3. 已有明确参数可调用html_repair.preview；需模型推断调用html_repair.generate。请求使用实际revision、scope、instruction、time_range_ms、step_ms、overlap_pairs。不让模型生成source、candidate_key或批准。
4. 对已绑定动作调整set_binding；不要把动画变换后的屏幕位置写作基础坐标。关系引线和图片锚点由同一渲染器重算。
5. 检查candidate.review、diff、clock、截图；仅在授权范围内用html_repair.save提交原request和candidate_key。保存再验证，409重新读取不覆盖；失败保持原作品。
6. 再读editor并重看实际页面。服务最多两轮模型修复；超限或needs_input/unsupported清晰报告原因。AI保护人工字段；不能将source改human规避保护。用户明确人工操作才使用human。

## 必须区分

- generate通过配置的兼容chat接口发送最多4张实际PNG截图和测量报告；模型必须具备图像输入能力，不能静默去掉图片后声称完成视觉判断。正常 evidence 已提供末帧参考几何、文字测量和全部问题摘要；完整有限采样轨迹留在本地。仅当输入确实含原始 frames 时才涉及防御性过滤。保留真实 frame_count，不能把未传 frames 误报为零采样。实际调用与图像接受仍需真实验证。截图由程序提供时间索引，对象身份以结构化输入为准。
- 默认有限采样，未提供overlap_pairs不代表全部遮挡检查通过；高风险区间用16ms步长，超过240帧预算要缩短区间。容器/主体的合理覆盖不能误标碰撞。排除项必须来自注册关系并记录理由，保留原诊断，不能任意删掉失败对象对。
- 文案语义重写/增删节点/换模板需回到权威内容与新规划候选；独立主体重生成走素材服务，不能通过局部操作隐藏。
- 作者时钟不是确认音频。排版修复不重新TTS；输出仍需现有音频和视觉批准。
- HTML源可编辑不代表快照PPTX或MP4内部可编辑。服务不提供持久undo；会话撤销按现有编辑器执行。

## 诊断、验收与持续打磨

1. 遇到失败先读 [失败经验](references/failure-lessons.md)。区分已证实、待证实、已排除原因；检查实际请求摘要与调用日志，不能根据本地报告大小推断网络负载或 HTTP 500 原因。停止本地等待不等于取消供应商请求。
2. 修改工具调用时验证真实签名及必填参数（包括 schema_hint），不能只靠接受任意 kwargs 的 mock。模型结果仍经过代码 Schema、权限、容量与保存门槛。
3. 交付实际 HTML 链接、当前 revision 和证据路径。工程、真实模型、二次编辑、视觉审阅、正式导出分别标注 passed / failed / not_tested / pending_review。截图必须检查文字层次、可读性、留白和图文融合；几何通过不能代替审美批准。
4. 每次实验固定输入、代码与 Prompt 版本，记录调用次数、修复轮数、耗时及人工改动。中途改代码后另记实验版本；单页成功不推广为多模板可靠。缺失指标用 null，不估造数据。
5. 按 [迭代机制](references/evolution.md) 把新失败加入 [评估案例](evaluation/cases.json)，定位属于规则、Prompt、工具、资源、网络还是审美问题，再修改对应层。结构检查、人工案例走查和真实模型评估分别记录，不能互相冒充。

调用方式：MCP ppt_html_editor_read / ppt_html_repair_preview / ppt_html_repair_generate / ppt_html_repair_evidence / ppt_html_repair_save；或 `python -m cli.pptctl html repair-<mode> --project <id> --slide <id> --file <request.json>`。工具权限沿用宿主，不引入第二服务。保存密钥到既有设置，不写入Skill、Prompt、产物或Git。
