# 讲稿语义规划与代码/图片分工

在用户指出“讲的和画面不对应”、需要多对象分步解释，或要求审查规划输入时读取。

1. 先读取权威 narration_beats 和当前计划版本。默认旧生产仍使用0.1.0；独立 `html_review.plan_generate` 或生产 `html_review.produce` 可请求 `{"plan_version":"0.2.0"}`。Web/Agent/MCP/CLI同源。模型返回结构化计划，共享组件渲染HTML。
2. 核对原句/id/hash未变；每个视觉语块有visualIntent、targets、独立actionId和expectedState；纯旁白有理由。检查返回evidence.semantic_design中的对象分工、初始可见和逐句可见集合。此为声明推导，不是播放验证。
3. 代码负责准确文字、数据、关系和分步对象；当前新版只支持一个独立图片主体。整张图片只能整体出现/强调；不要把图片内多个概念当成可独立控制的对象。多个内部状态需要重新规划，不可靠写一个更强Prompt声称已分割。真实资产与锚点仍须既有资源验证。
4. 遇到SEMANTIC_ASSET_*、SEMANTIC_IMAGE_STATE_CHANGE、SEMANTIC_ACTION_BEFORE_ENTER、预算不足，回到规划。已有合法actionId在结构修复时保持；不要路由到容量排版Skill，也不改人工字段伪造通过。
5. 检查实际request.json：本页原句、不同的屏幕文案、视觉约束和素材身份必须在；不带音频路径、审计散列、完整效果目录或其它页。必要上下文包含真实模板槽位/行数预算，不以缩短字符数为目标。原句重复只做精确判等删除，不总结或猜测等价。
6. A02的design_brief/reference_package传入分工和讲解状态；生成一张完整终态设计参考。A03使用scene0.6和binding0.2明确编译初态与多个稳定动作；作者时钟为预览，真实音频按稳定语块窗口绑定。先读semantic-runtime-0.1.0契约，核对原句哈希及所有分段文字，不能用错页音频或全页按比例猜测。
7. 听审预览展示真实音频及逐句导航，记录timing_source；供应商句级时间戳不保证词级或每个内部语块的精确对齐。正式输出仍检查音频确认。重复强调的set_motion/set_binding明确附actionId；位置字号修改保留scene0.6，不能降到0.5丢失初态。新增或删除语义动作回到规划。

真实Agent范围：只有候选容量修复通过LangGraph加载config中的受控排版片段。语义规划是有界JSON模型服务，不加载该排版片段或整篇SKILL.md；本文件指导Codex操作，也不会自动进入豆包上下文。不要把职责文档数量说成可运行Agent数量。

结构通过不能给语义、听审、审美或导出批准。泛化figure即使填齐purpose/expectedState，也可能没有实际解释内容；必须保持semantic_review=pending_review，交A04真实帧QA。验证报告记录模型是否实际调用、未返回是否unknown和人工改写次数；超时不盲目补发。新实验更改输入/策略时单独记录，不冒充旧请求恢复。
