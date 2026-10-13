# A02 语义对象分解与生图状态交付

2026-10-13，Asia/Shanghai。开发目录 `D:\Program Files (x86)\PPT_HTML_Studio`，父提交 `b1e3db8`。按最新交接的A02/N02实施；实际提交以本记录所在Git提交为准。本轮未部署或推送，未调用付费文字/图片服务，不改真实项目、音频确认或人工批准。

**A02对象分工、设计状态输入及资源/预算工程校验完成；实际生成质量与课程语义未签收。下一步A03：新动作编译与真实配音绑定。**

## 实现

- 新[合同卡](../../contracts/html-presentation/runtime/visual-v1/object-decomposition-0.3.0.md)：scene_plan0.3.0，design_brief0.2.0；契约包0.9.33，Agent API1.23.0、规划能力1.2。保留A01规划0.2.0和旧默认0.1.0，不重写存量作品。
- `html_object_decomposition.py`归属纯规划层：所有实际对象声明职责、角色、代码/独立主体归属和初始/结束状态；逐句动作推导before/after可见状态，绑定来源摘要。instructional初始隐藏，隐藏不能强调、可见不能再进入，标注不能先于主体/标签。
- 独立主体数量按最终对象计算，包括已有资源；默认1、最大2，不扩展模板槽位。图片不能承担代码文字、数据或关系；仅整张主体控制，不虚构图内分层、精确容量条、变形或隐式退出。
- existing仅引用输入提供的项目资源，原PNG加载器核对真实字节、版本、alphaBBox及锚点；新增选中资源参数，无参数时旧加载行为保持。具体锚点及尺寸进入摘要；focus不能冒充具体部位。generate锚点保持pending_asset，不自动接受素材板候选。
- brief和实际分类PNG参考包携带同一原句/意图/对象/状态序列。已有主体PNG实际复制为附件，并在manifest/cacheKey记录身份与字节；锚点或字节变更阻断旧规划。独立素材请求仅携带自身用途/相关语块与状态，low/1K/透明底，prepared_not_called或reuse_only。
- 规划Prompt0.6.0、设计Prompt0.4.0及独立主体Prompt0.2.0接入真实输入组装；沿用项目optimize-prompts方法，派生字段/散列不要求模型计算。Web/Agent/MCP/CLI同源传递版本及严格asset_budget，不创建新API或任务池。

## 验证

最终综合回归 **594 passed**，退出0（Starlette/anyio既有弃用警告1项）：新A02、A01及公共接口、旧规划/brief/审阅/生产/创建/恢复/模型绑定/素材生产/标注/编辑、全部Agent。不是594个实际课程验收项目。

定向案例包括：文本→分词器→Token单元分别显现；输入占用、输出预留与共享窗口分别由代码承担；预算/字段/初始状态/隐式退出/图内控制拒绝；真实隔离PNG锚点和附件、选中资源检查、图像/锚点元数据/参考包内容篡改拒绝；新旧HTTP返回一致及无场景/批准写入。两个Token案例是合同fixture，不是生成课程或视频签收，semantic仍not_run。

Ruff、Python编译、Node语法、Agent生成文档一致性、source registration、startup hooks和限定diff空白检查通过。V01仍为上轮已复现的server.py1162>1100，本轮未改该文件，未重复宣称全仓全绿。没有实际付费生成、听审、数字人或正式导出验证。命令与源散列见[证据](evidence/a02-narration-validation-2026-10-13.json)。

审查按code-review-and-quality的五个维度进行，修复新Prompt分派遗漏、类型化HTTP返回默认空值引起摘要不一致、参考包缺真实主体附件以及仅图像hash不能检测锚点变化等问题。没有新增依赖或复制外部源码；无新增OSS借鉴项。没有降低旧测试的业务断言；能力版本/支持枚举断言按增量更新。

## A03接入要求

1. 扩展既有场景/绑定兼容合同，让稳定actionId而非object:type成为新动作身份，消费0.3.0对象角色和推导状态。
2. 初始背景/装饰显式处理；instructional的enter/emphasize绑定真实beat窗口，重复强调保留身份。新路线缺映射拒绝，不比例缩放，不默认0ms。
3. 验证主体/标签/标注实际生命周期和每个beat开始/中点/结束帧、真实配音尾部。保持当前SEMANTIC_COMPILER_PENDING直到完整接入，旧格式保持。
4. 后续生产接入准备好的设计/素材请求时，继续原设计确认停点、任务、provider与影响登记；不得把本轮prepared状态当作已发起生成。A04语义QA、A05整课调度、A06真实课程仍未完成。
