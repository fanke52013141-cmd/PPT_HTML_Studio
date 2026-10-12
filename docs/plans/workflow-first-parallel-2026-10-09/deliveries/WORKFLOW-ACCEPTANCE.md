# 完整冷杯 Workflow 验收 — 2026-10-10

历史验收：以下为加入候选 Agent 之前的两轮固定生产流程失败记录。最新实施和冻结验证见 [候选排版 Agent 交付](CANDIDATE-AGENT.md)。

当时结论：固定生产流程未通过。本次没有交付新的合格HTML，不能用此前人工计划冷杯页替代结果。未据此选择Agent框架。

## 冻结方法与实际调用

从既有冷杯页只提取准确文字与单个现有透明素材。分镜visual_groups和五条真实内容语块为输入，不复制旧scene、旧plan、坐标、模板选择或字号。模型为真实doubao-seed-2-1-pro-260915。POST现有html-review/{slide}/produce，由现有HtmlWorkflowJobs运行generate_scene_plan→produce_scene→review_scene→保存。规划最多两轮格式纠错，实际HTML采用共享浏览器渲染；修改阶段预定使用现有多模态repair API，由模型自行选字号与位置，不提供数值答案。

测试使用隔离DB/runs和FastAPI TestClient，生产服务与模型请求均真实；模型绑定由验证程序读取授权的本地设置快照。provider=None表示本轮只有已有素材，不发送新生图请求。未验证真实网络认证入口，应用生图设置为空，新素材生成不计通过。两轮输入字节完全相同；每轮开始记录生产源码、Prompt、运行目录哈希，结束均确认未变化；人工修改模型计划或场景次数均0。

## 两轮结果

| 项目 | 第一轮 | 第二轮 |
|---|---|---|
| 模型选择模板 | explanation-cards-v1，11对象 | explanation-cards-v1，11对象 |
| 规划结构校验 | 第一响应已有image_asset缺need；正常第二轮纠错后接受 | 同样经过正常两轮后接受 |
| 素材 | 模型指定使用已有冷杯，生产却把所有image_asset送入新素材分支；IMAGE_PROVIDER_MISSING | 第一轮结束后补齐显式素材复用；本轮复用成功，没有图片请求 |
| 实际渲染 | 生产被素材问题挡住；另行诊断未改动的模型plan，副标题role=title导致60px高文字进入48px槽位，被拒绝 | 实际生产review拒绝intro：文字2行总高76px，槽位52px；没有改写模型输出或放宽检查 |
| 自动修复 | 未进入 | 未进入；现有repair要求已保存scene，初稿在保存前已被拒绝 |
| 完整结果 | 未通过 | 未通过 |

第二轮源码与提示词在任务期间保持冻结。两轮之间的素材复用修复是明确记录的工程修改，第一轮失败没有被覆盖，也没有把第二轮包装成同一冻结版本。

第一轮验证脚本错误地调用LocalJob.get_result；修正为既有get_payload accessor后读取原任务，没有重新调用初稿模型、改变生产代码或改模型响应。这属于测试观察器缺陷，记录在第一轮report.harness_issue；不掩盖实际生产失败。

## 可查看证据

- `outputs/frozen-workflow-validation-2026-10-10/`：input.json、frozen-definitions.json、report.json、production-job.json、diagnostic-scene.json、diagnostic-review.json及真实模型原响应。
- `outputs/frozen-workflow-validation-2026-10-10-round-2/`：完全相同的input.json、新冻结版本、report.json、production-job.json、原始规划响应和技术review结果。
- 第二轮index.html是验收结果页，不是生成成功的幻灯片。没有拿此前人工制作的页面冒充本轮输出。

## 本次修复与验证

HPS-001/011/013/023—028，契约0.9.19。仅将明确提供的visual_groups.available_assets身份/版本与真实项目资源、计划image引用一致时复用。原raster归属保持image_asset；不更改图片像素，不通过owner=code绕过素材管理。没有明确提供时仍生成新素材，错配/坏资源拒绝，显式素材返工仍沿用原设计确认。新provenance记录supplied_asset_ids，旧记录不迁移，API和DB不变。

23项E production回归通过，包含提供素材无需生图服务、版本错配不发送请求、不保存，以及原新设计停点、恢复、引用指纹、素材返工等保护。真实第二轮证明素材复用已越过原阻断点，但不能从单模块通过推导整页通过。

## 下一步开发目标

只补齐初稿失败后的自动修复闭环：将未保存候选scene、binding、真实失败测量/截图交给有界修复；不先把坏初稿保存为产品，不只对已合格页面测试。明确candidate与已保存scene边界，保留原作品、候选key、人工保护和有限次数；失败保留证据，通过后才保存并展示最终HTML。

同时把槽位角色/容量约束进入初稿规划和验证，避免title字号占用headline、长解释语占用小intro框。修复若只解决代码逻辑而未通过真实模型生产，不记功能验收完成。完成后再次用同一输入跑固定流程；目标仍是原冷杯成品质量与可编辑性。

当前证据支持完善确定性workflow，不能证明豆包一定不能完成，也不能证明需要LangChain/LangGraph或动态Agent。下一次验收必须实际产出合格HTML，才进入用户美感审阅。
