---
name: produce-editable-html
description: Produce and verify editable HTML in PPT Studio using registered scene plans, design checkpoints and protected editing. Use for HTML生成、设计还原、未保存候选修复、讲稿画面诊断; exclude image-only Mask/reveal production and generic websites.
---

# 可编辑HTML生产与修复

版本1.23.0，2026-10-18。先读 [共用边界](../workflow-contracts.md) 和仓库docs/contracts/html-presentation/README.md；从agent_contract.capabilities读取当前能力，不把此操作说明整篇传模型。

## 选择任务

| 当前状态/意图 | 路径 |
| --- | --- |
| 新页/新设计/明确设计修订 | html_review.produce，先设计后接受，沿原候选身份 |
| 未保存容量失败 | 原candidate Agent/严格证据；其他资源/Schema错不进排版循环 |
| 已保存页的布局/动作修改 | html_editor.read→原repair preview/generate→验证→授权内save |
| 文案/节点增删/换模板 | 回权威规划，不用局部样式补丁替代 |
| 声音/逐句QA/正式输出 | 原服务和独立签收门禁 |

新生产/失败恢复读 [references/production-and-recovery.md](references/production-and-recovery.md)；局部编辑、音频/A04或输出读 [references/edit-and-deliver.md](references/edit-and-deliver.md)。讲稿到对象的语义问题再读 [references/semantic-planning.md](references/semantic-planning.md)，重复失败定位用 [references/failure-lessons.md](references/failure-lessons.md)。

## 不变的判断

准确内容/主题/人工保护高于参考图。模型决定合法计划和操作，程序共享组件渲染；代码拥有所有语义文字、标签和关系。缺对象回planning，缺工具回capabilities，独立非语义图片问题才assets。工程、静态保真、逐句语义、声音和人工签收分开。

不手写本例plan/HTML后声称系统Agent成功；不自由CSS、不整页位图替代正文、不以改source绕人工保护。尊重当前revision、候选key、源闭包和实际hash；文件存在不代表当前可用。原unknown不补发，暂停不等于供应商已取消。

## 检查与交付

读取实际任务进度、runtime_skill身份、调用/HTTP与复用事实、read/total等待预算；unknown用量/费用为null。查看当前scene、实际截图和声音/动作证据，给实际产物路径、revision、状态和未验证项。几何通过不等于审美批准。

例：灰阶HTML不抄原图彩色；图内缺字应补规划对象，不让主体图补字；cancelled子任务不复活；仅改布局的同值保存不重TTS。

按局部编辑Skill执行：核对受保护叶字段，绝对赋值；已有动作只改原句偏移；缺能力或冲突明确停止，不改source、不生图、不合成声音。

保护祖先适用于整个子树，manual_protection=true不等于整页禁止编辑。固定效果对照使用 `scripts/benchmark_html_editor.py`，Skill组只传上面的操作摘要；只有显式--live才请求模型，四例和失败/unknown均计入分母，费用未知保留null，单次耗时差不宣称稳定提升。

本Skill演进读 [references/evolution.md](references/evolution.md)，案例在 [evaluation/cases.json](evaluation/cases.json)。历史案例声明需与当前合同核对，不能当作新能力或签收。

注册结构选择：figure-frame-top为带框顶部标题；annotation-dashed只改虚线外观，target/anchor/label及空间禁止变动；summary-strip-divided只适用无heading的三栏关系，不增加正文前缀。原set_variant、保护、容量与独立签收门禁继续执行。

定义更新后保留原设计：显式reuse_design_candidate_key重新核验同页原计划/图片，返回新待审key，零规划/生图/TTS。不自动接受，不重签旧候选；新key仍需用户接受，旧设计接受不代替HTML/A04。图标先看对象自带tag/note及currentRender，icons只列可选装饰；标注圈/线虚实按注册混合变体分别选。

课程结构离线补齐见course-structures-0.1.0：显式端点关系、chart与三阶段模板，card-outline/figure-frame-dashed/annotation-dashed-no-arrow。权威visual_requirements必须完整映射visual_coverage；没有清单不宣称自动理解全文。新模板必须通过normalize/A02/compile和真实共享渲染，不以手写离线夹具声称模型生产成功。像素、结构、语义和人审分别记录；未通过项不能因工程检查通过被隐去。

正式无头审核/取帧/视频使用共享软件合成捕获策略；交互GPU像素另验。相同已接受设计的素材按设计hash/准确need/模型/参数复用，appearance措辞变化不重生；匹配缓存损坏停止，历史缺身份不可猜测迁移。权威visual_requirements必须进入实际规划请求，缺coverage在生图前阻断。先通过捕获/恢复/真实请求预检验证，再恢复课程生产，不拿离线夹具代替真实批准。

原图正确但显式关系point坐标有误时，可将reuse_design_candidate_key与repair_relation_points说明配对，仅0.2.0语义计划；一次受控模型请求只改既有端点坐标，不改对象/文字/动作/模板，不生图/TTS、不写作者，不代签收。人工覆盖阻断；原unknown不补发。新key仍待接受，普通原图复用仍零模型调用。

坐标修复必须先检查项目视觉text模型supports_images=true；planning可使用独立文本模型，image保持。显式原图复用允许在图片模型摘要完全相同时刷新text/planning绑定，保留源模型身份并生成新待审key，不自动转移批准。unknown必须保留，改模型不能当作重发授权。

端点修复Prompt0.1.1必须把严格输出Schema放入首次system消息；共享schema_hint仅供JSON语法恢复。关系键顶层映射仍拒绝，不自动转换旧响应或补发请求。

描边文本卡片需要局部强调时使用已注册text-card-outline-emphasis，保留原runs、卡片和图标；不要改为无框text-emphasis-bold或将全段加粗来冒充局部强调。set_variant/typography仍受原保护和容量约束。
