# PPT Studio流程Skill共用边界

项目内操作Skill在执行制作任务时按需读本文件，不作为整篇模型Prompt。实际能力与参数从 `agent_contract/capabilities.py`、模型Schema及当前服务入口取得。

## 先确认路线与身份

读取实际project.visual_backend、canvas_ratio、project_id、slide_id和run_dir，路径由项目服务解析，不凭文件存在猜backend、不另建运行副本。`inputs/article.md`为完整文章源，`planning/visual_contract.json`为当前分镜，旁白/声音读取当前项目状态。

| 任务 | 图片路线 | HTML路线 |
| --- | --- | --- |
| 视觉 | 完整位图→AI Mask/RLE→PNG层 | 计划→设计图确认→代码/独立素材→受控操作→共享渲染 |
| 动作 | 原reveal builder与bind_reveal_timeline | html_semantic_runtime、html_audio_binder，稳定对象/actionId |
| 验收 | 现有图片/Mask/声音确认与渲染门禁 | 设计接受、工程、视觉、音频、逐句语义签收分开 |
| 输出 | 原Remotion/PPTX任务 | 原HTML正式快照输出任务；PPTX为图片式 |

HTML入口先读 `docs/contracts/html-presentation/README.md` 再读所需runtime卡；图片路线遵守AGENTS的纯白外底、原图/归一化配对、精确Mask和产物失效规则。不要把图片专有门禁套给HTML，也不要借HTML能力重绘图片路线正文。

## 调用与状态

优先使用原Web/Agent/CLI服务，让服务负责持久化、锁、失效和确认；诊断脚本只在明确诊断任务中运行，不代替正常生产入口。原语义计划、图片/声音/视频有独立身份和hash，文件存在或旧任务成功不足以证明当前可用。

请求只消费本阶段必要输入；保留准确文字、限定条件及关系来源。模型建议不等于批准。读取当前返回Schema，不让模型编造内部ID、hash、未注册操作或任意CSS。人工修改通过原受保护编辑接口保留。

外部unknown/intent、断流和取消依原任务恢复合同核实，不能换参数、目录、模型或任务ID盲目补发。本会话用户已明确暂不重发原遴选未知请求；其他任务按各自授权，不把本例限制变成所有任务永久禁用。

## 验证与交付

区分定义/实现、结构/工程、真实模型、人工审阅、声音/语义/输出，各自报告passed/failed/not_tested/pending_review。付费实验不由离线测试推定通过，不估算未知费用，不记录密钥/原始Authorization。

报告本次实际产物、当前性、证据、失败路径和下一步。回归测试使用隔离数据库/runs；不导入server来做静态扫描，不把运行数据提交Git。项目需要变更合同/代码/运行片段时，先更改唯一所有者，再同步版本/hash与消费者。
