# DEF-SCENE：文档、场景与身份

版本 0.1.0；类别：公共数据契约；维护：场景定义库；HPS-001/006/010/011/014/018。
定义 specified；实现 not_implemented；验证 partial（仅 P01 文档/样例一致性）。P03 建立正式 Schema。

用途：保存一份可编辑演示的作者输入，分别关联画面、讲稿和来源。
首轮支持一个画布、多页结构、单页样例；章节、转场、多轨媒体暂不进入最小字段。

## 文档输入字段

| 路径 | 类型 / 必填 | 缺省 / 约束 | 归属与覆盖 / 修改影响 |
| --- | --- | --- | --- |
| schemaVersion | semver / 是 | 首轮 0.1.0，未知版本拒绝 | 公共；迁移才改；影响全体解释 |
| contractVersion | semver / 是 | 本样例 0.4.0 | 公共规则引用；不以它代替 Schema 版本 |
| documentId, revision | Id, 整数 / 是 | 文档稳定 ID，修订 ≥1 | 实例，宿主分配；影响任务快照 |
| title, language, purpose | 非空字符串 / 是 | language 首轮 zh-CN；purpose 为课程表达目的 | 实例可编辑；内容一致性 |
| authoringState | 枚举 / 是 | draft 或 confirmed；不是渲染就绪状态 | 实例工作流；确认不豁免资源门槛 |
| canvas | 对象 / 是 | width/height >0；单位 design-unit；safeInsets 的四值 ≥0，横/纵总和小于宽/高 | 实例规格；全部排版 |
| styleRef | VersionRef / 是 | 风格必须按版本解析；draft 也可引用定义夹具 | 实例可换；重排/视觉 |
| definitionRefs | VersionRef[] / 是 | 所使用公共类型的确切版本，不得重复 id | 实例依赖；能力及版本检查 |
| contentUnits | ContentUnit[] / 是 | 至少 1；值是文字而非 HTML | 实例；几何/锚点/一致性 |
| relations | Relation[] / 可缺省 | []；首轮 type=contrast，两个不同 contentId；不可伪造因果 | 实例语义 |
| assets | AssetVersion[] / 是 | 见 DEF-ASSET；允许字体 pending，正式输出阻断 | 资源拥有文件，实例固定引用 |
| slideOrder | Id[] / 是 | 非空，与 slides ID 集合完全相等，无重复 | 实例；全片顺序/合成 |
| slides | Slide[] / 是 | ≥1；节点只属于一个页面 | 实例；本页变化局部传播 |
| narrationBeats | Beat[] / 是 | ≥1；每项主属一页 | 实例；音频/时间 |
| textAnchors | TextAnchor[] / 可缺省 | []；见 DEF-TARGET | 实例；改字后待检查 |
| timingInput | 对象 / 是 | 见 DEF-TIMELINE；明确 manual 或 existing_audio | 实例时间输入 |
| outputIntent | 对象 / 是 | 见 DEF-OUTPUT，不等于已导出 | 实例要求；能力检查 |
| extensions | 对象 / 可缺省 | {}，首轮不得填未登记键 | 公共扩展边界 |
| parameterOverrides | 覆盖项[] / 可缺省 | []；只允许定义的文档层参数 | 实例；按字段重排/重画 |

## 内容、页面与节点

ContentUnit 为 `{contentId, revision, kind, value, required, source}`；kind 首轮 `text`，
value 非空字符串，required 布尔必填。source 必填 `{kind:"authored", locator:"..."}`
或 `{kind:"imported", locator:"..."}`；locator 非空，不表示自动联网取回来源。
relation 为 `{relationId,type:"contrast",contentIds:[Id,Id],required:boolean}`。

Slide 必填 `{slideId,revision,title,purpose,layoutRef,recipeRef,nodes,slots,beatIds,actions}`，
可缺省 `parameterOverrides:[]`、`locks:[]`。slots 为 slotName→nodeId；引用根节点。
beatIds 为该页全部语块的有序 ID，和 Beat.slideId 一致；语块不可双重主属。
layoutRef/recipeRef 均为 VersionRef。页面默认继承文档风格；首轮不允许逐页改风格。

Node 必填 `{nodeId,typeRef,data}`；可缺省 `parentNodeId`（缺省=页面根）、`variant`
（定义默认）、`initialVisibility:"visible"`、`parameterOverrides:[]`、`locks:[]`、
`extensions:{}`。initialVisibility 为 visible/hidden；隐藏保留布局。
只有 Group 源节点有显式 children。语义组件内部实现节点是派生结果，不重复保存为作者节点。
两列布局的根 title 是 Text，left/right 是 Concept；概念内图像由资产引用展开为 Image。

Beat 必填 `{beatId,revision,slideId,text,contentRefs,targetRefs}`，可缺省 `relationRefs:[]`。
text 非空纯文本；contentRefs 非空且无重复；targetRefs 是公开目标列表，允许 ≥1。
内容与讲稿各保存自己的表述，并通过 contentRefs 关联，不能假装措辞相同即复用同一文本修订。
required 内容至少被一个非装饰目标及语块引用；required 关系至少被一个语块引用。
覆盖检查还需语义审阅，存在引用不等于讲述准确。

## 输出、身份与编辑

输出为已规范化源场景（仍无几何），及结构/引用/覆盖诊断。字段默认由宿主填入，
原始作者输入与规范化记录可并存；排序不重新生成 ID。
编辑文字仅提高对应 content/beat、页面和文档修订；复制页为页/节点/动作/锚点/语块分配
新 ID，重映射内部引用；内容和资源可显式共享，复制默认对内容也分配新 ID以免联动修改。
复制语块引用的 relation 也分配新 relationId，所指内容采用同一份 contentId 映射；
页外内容引用保持其显式外部关系并列入检查，不按数组位置猜测为页内对象。
删除列出悬空引用，不自动改绑；AI 临时 ID 只在提案内，接受时宿主映射。

依赖：引用的能力定义、风格、资源、目标；公开目标由各节点类型提供。
排版/外观/时间分别交给布局/风格/时间卡；文档自身不渲染一个可绑定 DOM。
导出需形成 RenderBundle，不把原始 JSON 当 MP4/PPTX。

正常例：[scene.example.json](examples/scene.example.json)。非法例：slideOrder 包含不存在 ID
→ MISSING_REFERENCE；复制页沿用节点 ID → DUPLICATE_ID。相关验收 C01/C02/C03/C19/C20/C21。
旧图片 visual_contract 的映射在 DEV-01 后续实现；P01 不改写旧文件，也不推断其 ID 稳定。
