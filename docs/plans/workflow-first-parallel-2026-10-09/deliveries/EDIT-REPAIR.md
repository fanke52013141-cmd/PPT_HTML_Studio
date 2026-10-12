# 可编辑初稿与局部修复交付 — 2026-10-10

后续完整产品验收见[冷杯Workflow验收](WORKFLOW-ACCEPTANCE.md)：两轮完整生产未通过。本文1—5为局部能力与指定模板初稿验证，不能据此声称完整冷杯workflow已成功；坏初稿自动进入修复仍需补齐。

用户授权的1—5已在现有HTML服务中实施。默认黑灰白，未更换音频、图片后端或引入LangChain/LangGraph。现行规范：[scene-repair 0.1.0](../../../contracts/html-presentation/runtime/visual-v1/scene-repair-0.1.0.md)，契约包0.9.18，Agent API1.18.0。原E验证和设计提案中“不支持最终字号/位置、无真实文字模型”的叙述保留为历史证据，以本账本更新后的范围为准。

| 步骤 | 已实现 | 验证范围 |
|---|---|---|
| 1 实例编辑 | scene0.5受限位置、尺寸、公开文字部位字号/字重/行高/对齐；compiler→共享renderer→Web面板/Agent同源 | 实际浏览器修改、保存、重开；旧scene不能混入新字段；文字改宽/字号后重新测量换行 |
| 2 局部修复 | preview/generate/save/evidence四能力；scope、revision、候选key、人工字段保护；不改文案语义或对象结构 | no-op、409、过期key、越界/溢出不保存；AI可继续调整自己的字段但不能覆盖人工字段 |
| 3 时间验证 | 实际播放器采样动作边界/中心/均匀时间；指定对象对碰撞、可见越界、截图和测量 | 中途碰撞被发现，修正入场偏移后通过；首RAF负时间边界修复。最多240帧，属于有限采样 |
| 4 Prompt/Skill | 初稿html-plan-0.4.0、修复html-repair-0.2.0；初稿包含完整字段契约，失败带原JSON与诊断；模型只输出允许操作 | 修复最多两轮；实际加载produce-editable-html Skill并由Codex执行API序列，没有宣称无人干预Agent已完成 |
| 5 真实模型 | doubao-seed-2-1-pro-260915，通过配置的Ark兼容ChatCompletions；修复附实际PNG图像 | 初稿API200→编译/实际HTML证据200；多模态修复200→保存200→Web/Agent重开一致。供应商为真实调用，不是替身 |

初稿由模型返回受注册能力限制的plan，程序展开为HTML场景。模型没有直接输出任意HTML/CSS。修复由模型返回有界操作，程序验证后保存源scene和binding。DOM、截图、视频均为派生产物，避免临时改浏览器样式后丢失。

## 实际证据

隔离目录：`outputs/scene-repair-validation-2026-10-10/`（Git忽略）。`live-report.json`记录模型、HTTP结果、操作和时间检查；`real-plan.json`为实际模型初稿；`real-repair-candidate.json`及项目`planning/html_visual/records/repair-*.json`保留请求、原响应和诊断。`draft.html`是模型初稿页面，`reconstructed.html`是原单页经真实模型修改后的页面。使用共享player/data和验证后的素材，不以整页位图冒充可编辑页面。

实际修复：headline正文字号28逻辑px、相对槽位右移20px；card-2的enter offsetY从-100改0。对card-1/card-2在0—38500ms检查176帧，指定碰撞检查通过，pageErrors为空。时钟为author，没有确认音频的同步结论。

同一个真实模型初稿页也经真实多模态API完成二次修改：obj-caption正文24逻辑px、相对槽位上移20px；保存200、Web/Agent重开一致，证据real-draft-repair-candidate.json。没有人工补正模型输出。

真实实验先暴露了两个Prompt问题：初稿首轮缺少完整字段Schema、图标目录混入SVG路径；修复输出错误kind/action或遗漏part。未手改模型JSON冒充成功，修正Prompt后重跑真实请求；失败记录仍保留，失败时原场景未写入。

模型连接写入用户授权的现有本地设置；密钥不写Skill、Prompt、Git或报告。业务验收使用隔离DB/runs与真实Web/Agent路由TestClient，只冻结授权模型配置快照；未验证真实网络服务器的认证中间件、多人并发或完整课程任务。

工程回归：44项Python检查通过（repair、multimodal、review、E production）；播放器修复后再跑repair/multimodal，15项通过。另有既有Agent/MCP/CLI及元数据回归结果。共享播放器14项浏览器检查、5场景、pageErrors=0；元数据生成--check、前端质量及git diff --check通过。实际编辑器浏览器修改/保存/重开通过；最终两份HTML重新截图，pageErrors=0。源文件凭据扫描无匹配。测试不写用户真实项目。

播放器修复兼容范围：数据、布局、字阶与时间契约不变，首帧时间下界保护；固定对象translate3d合成消除随机时间跳转的像素差异，可能改变部分抗锯齿像素。构建后的共享player与实际预览均更新；本轮未重新验收完整视频编码/导出。

## 下一步

1. 审阅实际可编辑HTML的美感，记录具体对象反馈；技术检查不会自动批准视觉。
2. 选一篇真实文章跑多页，检查每页真实规划、设计停点、独立主体及人工修改保留。
3. 复用已确认音频，检查真实音频绑定后的时间区间和正式导出；不要从作者时钟预览推导音画同步。
4. 若现有确定性编排不能满足后续多轮工具选择/持久恢复，再评估Agent框架。当前Skill+现有服务已能约束初稿和局部修复。

本轮没有新生图、最终美感批准、全课程MP4/PPTX验收、线上提交或部署。HTML源可编辑不等于快照PPTX/视频内部对象可编辑。
