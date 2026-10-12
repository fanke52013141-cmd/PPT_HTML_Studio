# S03 最小重建定义卡 0.1.0

2026-10-12；HPS-010/011/014/015/017/030。输入/输出为新增内部格式，不改变 scene、音频确认或人工批准格式。

| 项目 | 定义与当前实现 |
|---|---|
| 身份 | hps.html.rebuild_plan 0.1.0；canonical JSON 生成 plan_id，包含 before/after 输入散列、逐页差异、阶段/原因、项目阶段和 no_op |
| 纯函数输入 | before/after：pages（slide_id→scene、binding、narration、audio、font_family）、order、引用 assets 实际字节/元数据、themes/layouts/templates/fonts/runtime 指纹、可选公开文字/图片 models 身份。order 必须与 pages 一致且不重复；TTS参数变化应纳入朗读输入，并保留原服务的运行参数确认门禁 |
| 只读采集 | html_rebuild_inputs.capture_inputs 读取当前契约顺序、已保存作者场景/绑定、实际旁白及 TTS 输入、现有音频产物、引用图片、注册定义和本机字体；同项目锁和读前后散列校验。模型身份由调用方明确提供，不读取或输出凭据 |
| 复用含义 | reuse 是依赖分析中的复用候选，必须再由现有实际文件、身份、资源、音频与审批门禁验证；reuse_requires_artifact_validation=true。它不是跳过工程检查的通行证 |
| 局部文字/样式 | 屏幕字、字号、位置：本页 compile/static QA/temporal QA/visual approval/page video；保留图片生成、旁白/音频及无关页。仅动作或 binding：时间绑定/动态/批准/画面，不要求重新 TTS 或静态字形测量 |
| 图片/锚点 | 引用/版本或实际字节变化：引用页的素材身份/锚点、编译、静态/动态、批准、画面；替换已提供的实际图不意味着自动重新生图。未引用素材变化不增加页面工作 |
| 字体/定义 | 引用字体变化必须重测布局/文字/字幕；引用主题变化重验外观，布局/模板变化还需规划。共享播放器、catalog、Schema/效果等全局运行输入变化按真实共享依赖重验所有页面，不伪称其他页批准仍有效 |
| 旁白/音频 | 最小稳定 TTS 单元仍为现有页面：朗读输入变化要求该页 TTS、对齐、音频确认、字幕、绑定、动态和视频，全片字幕偏移/组合跟随；只有音频产物变化不要求重做 TTS。现有确认散列防止错误沿用旧音频批准 |
| 顺序/删除 | 仅重组总片顺序、字幕偏移、引用/课程检查，不自动再生成剩余页图像或音频；删除页的旧产物只作为历史，不当作新课程有效页面 |
| 模型设置 | 改变未来生成任务身份，不自动重生现有冻结素材、已保存页面或音频 |
| 接入 | editor/repair preview 返回 dry-run；save_editor 写文件前计算同一计划，与作者文件同组回滚保存 rebuild-<slide>.json。当前 editor read 只暴露散列与作者内容仍匹配的计划。生产任务记录 rebuild 阶段、result 和作者回执；S02 恢复使用同一影响记录 |
| 未确定调用 | 相同语义输入/选项/模型已有 intent/unknown 时，重建产生的新源码/定义快照身份不能绕过原请求阻断；先对账，不能通过新 submission_key 重复付费调用 |
| 影响账本 | html_scene_changed 接收内部计划并放入现有 pending_impacts.details.html_rebuild_plan；原影响 generation/source_version 保护保留，同值保存不写影响。下游失效仍归 invalidation_service，API 调用方提交数据库 |
| Agent 兼容 | API1.19.0，editor preview/read 与保存结果增加可空 rebuild_plan，旧数据为 null。Web/Agent 共用实现；MCP/CLI 沿用已有能力和请求。无新数据库表、任务类型或第二可写工作流状态 |

执行范围：局部编辑按现有编辑/修复 API 实际执行，QA 与正式输出继续走原对应服务。纯计划不发模型请求、不会擅自触发 TTS 或删除历史视频。原始低层 scene PUT、非 HTML 图片后端不改造成新的自动调度器。跨页/字体/顺序的计划用于明确原服务重建范围；本轮不宣称新增视频分段缓存或所有阶段的无人值守执行，正式快照导出接线另属 S05。

CLI（UTF-8 输出）：`python -X utf8 scripts/html_rebuild_check.py capture --run-dir <run>` 保存 stdout 为 before/after 输入；`python -X utf8 scripts/html_rebuild_check.py plan --before before.json --after after.json` 只分析，不写项目、起服务或调用模型。

质量边界：工程检查、真实供应商调用、审美批准与课程导出分别记证据。历史批准保留文件，由依赖散列判断是否有效；不能因为计划允许复用而恢复过期视觉/音频批准。html_input_manifest 不再根据 mtime/size 缓存摘要，同大小且恢复 mtime 的替换仍可检测。
