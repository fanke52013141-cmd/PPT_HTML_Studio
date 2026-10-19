# 真实外部 Agent 试验：Token 第 3 页

任务来源为本机真实项目 `d1f5885a_122521`（A06 Token 多页课程），页面 `slide_003`，
标题“输入和输出，要分开看用量”。本机没有历史 handoff 所述已保存结冰课程，不能拿历史记录冒充当前输入。

## 来源和实际状态

使用原项目 `planning/html_visual/candidates/slide_003/design-reconstruction/` 下的
`0dfd45e89a6ffef0ac46d583406b08acd6a990c42c08fe156cc416284168ef51/allocation-capacity-repair.json`
中的原 scene 与 binding；这是实际生产流程留下的未保存候选，不是测试 fixture。
讲稿来自原 visual_contract；绑定 sourceBeats 已逐项与讲稿核对。模型主体 PNG 复用原字节，
SHA256 `111825b1aa0e17d9a975fba7d1f71b928c4f8e70b61fd4cf4ac860bd3cfa5609`。

原候选在隔离目录 `outputs/external-agent-real-token-20261019/isolated-run/` 等值落盘，
试验 project_id=`external-token-static-20261019`，revision=1。原项目作者、数据库、批准、音频不写。
旧工作流曾为通过容量检查将底部 from/to 字号缩至17px；本次以此真实候选为基线测试改善可读性，
没有人为添加碰撞或损坏数据。当前共享播放器实际重新检查通过，截图不是旧报告或重绘示意图。

本机该页没有真实音轨，任务仅为 static_repair、作者时钟；不能评判音画同步。
原 reconstruction/reference.png 作为历史辅助设计图保留，不是当前接受的设计。
候选中已有代码与图片分工/视觉表达的局限另记，不能通过本次局部修复冒称整页语义验收通过。

## 具体任务和验收

请改善底部“费用怎么算”总结模块的可读性与层级，同时保持其所有文字和关系、标题、主体插画、
主题及动作/绑定不变。范围为 obj-summary、obj-card-1、obj-card-2、obj-card-3；允许必要时在同一布局内
调整三卡的公开布局参数为底栏腾空间，优先仅修改底栏。不得改其他对象。

1. 底栏 from/to 的有效字号从17px提高到至少22px；takeaway至少22px，其余正文不得靠缩小解决。
2. 保留 heading/from/to/term/takeaway 的全部现有文字与方向关系；不得隐藏标题、删除内容或用整页图片替代。
3. 仅使用原主题 neutral-baseline@0.2.0、解析布局及该对象支持的注册变体/公开参数，保持全页风格一致。
4. 原播放器容量/渲染与250ms有限采样检查无新增错误；业务验收额外核对底栏与三卡、字幕区边界，
   无截字/越界/非法遮挡。指定字幕安全区以 task 的 layout 定义为准。
5. 图片字节、讲稿、全部 motion/binding、非scope对象保持等值。不能满足时明确返回缺口，不改一般约束。

字号阈值是本任务的业务条件，不是全产品通用字号规则；几何检查通过仍须看实际前后图。

## 给外部 Agent 的文件与交付

完整输入 ZIP：`outputs/external-agent-real-token-20261019/Token-slide003-agent-input.zip`。
其中原协议 core 清单为 manifest.json；本次辅助来源/历史图按 trial-manifest.json 校验。
先读 START-HERE.md、TRIAL.md、EXECUTION.md，再核对 task.json、content.json、实际 evidence/ 和 assets/。
原目标、scope、风格、逐对象严格Schema、模板均在包内，不需要项目数据库、API密钥或整库源码。

Agent首轮交付 result.json 与 report.md；无原系统接口时，Schema/内容/范围可以自检，实际渲染项必须标为 not_run。
不能新增JSON字段或输出任意HTML。交接方收到后在上述隔离副本用原 html_external_handoff.preview_result 复核，
查看前后图/diff/检查，再决定是否回传一轮具体反馈。当前真实项目中没有这个试验ID，不能直接当生产项目导入。
本轮任务不要求、不授权修改原项目或保存隔离候选；如要采用再明确处理。

交付结果衡量：目标达到情况、误改、人工介入、轮数、实际耗时与费用；未知为null，无法执行和失败也留档。
本文件说明试验输入已准备，尚无外部 Agent 结果或用户视觉签收。

## 已收到第一轮结果及第二轮交接

用户交回delivery.zip与result.json/report.md，6个操作格式/scope合规。原0.9.98封存任务有效时已运行
原preview，返回SCENE_INVALID / CONTENT_SAFE_ZONE:obj-summary：终态793，保留enter.offsetY=12后为805>800。
未保存、未批准，基线保持revision1。完整原交付和真实错误在
`outputs/external-agent-real-token-20261019/returned-first-round/`。

规范与API更新到0.9.99/1.53后重新导出第二轮包
`outputs/external-agent-real-token-20261019/Token-slide003-agent-input-round2.zip`，
新task_id=`025c1a7a0d6fc115c6c3568f076ee907e41d415f199cd547a6cd060d5216dca2`。
包内有第一轮原结果/报告/系统反馈，仍仅第二轮单候选，无额外付费工具授权。
基于新输入重新修订，不能只换旧结果ID；本机原项目与声音保持不动。
