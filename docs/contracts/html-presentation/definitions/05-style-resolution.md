# DEF-STYLE / DEF-PARAMETERS：风格包与参数解析

两卡版本 0.1.0；公共风格协议/解析器维护；HPS-001/003/004/005/009/013/018。
定义 specified；实现 not_implemented；验证 partial（文档）。实际风格 P02 选择、P03 解析。

## DEF-STYLE：style.pack

风格包是公共接口的视觉实现。可覆盖结构变体、素材要求和搭配约束，公共语义与公开目标不变。

| 字段 | 类型 / 必填 | 范围 / 缺省 | 归属与修改影响 |
| --- | --- | --- | --- |
| styleId, version, label | Id, semver, 非空文字 / 是 | 确切版本 | 风格定义；发版不覆盖旧作品 |
| definitionState | 枚举 / 是 | draft/specified/deprecated | 风格状态；draft 不可正式输出 |
| use | 枚举 / 是 | product 或 structural-fixture | 风格用途；夹具不宣称审美通过 |
| tokens | 对象 / 是 | 本表下述完整参数，不接受任意 CSS | 风格视觉值 |
| fonts | 字体引用[] / 是 | [{assetRef,weight}]；weight=100..900 的整数 | 风格固定资源版本 |
| support | 对象 / 是 | components/variants/layouts/recipes/actions 的明确版本列表 | 风格支持集 |
| assetPolicy | 对象 / 是 | illustrationDescription、iconDescription、paletteRoles、background、controlGranularity | 风格素材规范 |
| assetRefs | VersionRef[] / 可缺省 | []；声明可用资产，不代表待生成已经存在 | 风格资产 |
| defaults | 参数覆盖[] / 是 | 至少 concept.variant；不得替代 tokens 来源 | 风格选择，解析记录 |
| overrideRules | 对象 / 是 | 参数路径→范围或 allowed 枚举；无声明不许覆盖 | 风格可进一步收紧公共范围 |
| references | 对象[] / 是 | product 正式指定时非空；夹具可 [] | 风格参考集，每项有状态/位置 |
| compositionRules | 对象 / 是 | forbiddenCombinations[]、fallbacks[]，缺省不得隐式回退 | 风格组合边界 |

references 项为 `{referenceId,sceneRef,stage,reviewState}`；sceneRef 是包内相对路径，
stage 是 initial/intermediate/final/boundary；reviewState=pending/accepted/rejected。
没有实际画面和 accepted 记录时，风格只能 draft，不能 specified 或视觉 verified。

### 首轮 token 清单（完整参数必须填齐）

| 路径 | 类型 / 范围 | 消费者 |
| --- | --- | --- |
| colors.background/surface/ink/muted/accent/highlight | #RRGGBB 或 #RRGGBBAA | 背景、容器、文字、标注 |
| typography.{slide-title,concept-title,body,caption} | 每角色 {fontRef,weight,size,lineHeight,letterSpacing,colorRole} | Text；size>0，lineHeight 为倍率 ≥1，letterSpacing 有限，colorRole 属 colors |
| spacing.padding/titleGap/columnGap/innerGap | 设计单位 ≥0 | 布局/概念内部 |
| stroke.width / stroke.radius | width>0；radius≥0 | 图形/容器/标注 |
| concept.figureRatio | (0,1) | above 高度或 side 宽度所占内部比例 |
| readability.minTextSize / maxBodyLines / maxTitleLines | >0 / 整数≥1 / 整数≥1 | 风格验收阈值；不作公共固定值 |
| motion.revealDurationMs/highlightDurationMs/drawDurationMs | 整数 ≥0 | 未显式指定时的动作默认 |
| motion.easing | linear 或 ease-out-cubic | 公共缓动函数 |

fontRef 是字体 VersionRef；不得仅写操作系统字体名。语义 token 不支持任意表达式；
P01 只允许直接值和 fontRef，token别名/计算器后续登记，因此不存在默认允许的别名循环。
maxLines 是验收约束，不允许直接截断超出部分。P02 根据实际字体和样板填写阈值。
所有角色 size 必须 ≥ minTextSize；slide-title/concept-title 使用 maxTitleLines，body/caption
使用 maxBodyLines。这些夹具阈值只是字段示例，不证明实际字体可以满足。

support 的 components/layouts/recipes/actions 为 VersionRef[]；variants 是组件 typeId→
变体名[]，不得声明未登记变体。assetPolicy.background=opaque/transparent，
controlGranularity 首轮 one-object-per-asset；其 description 为非空文字，paletteRoles 为
colors 中角色数组。overrideRules 值为 {min,max}（数值）或 {allowed:[...]}（枚举），
不能为空，数值有限且 min≤max，最终范围不得放宽公共约束。
compositionRules.forbiddenCombinations 每项 {componentType,variant,layoutId}；
fallbacks 每项 {componentType,fromVariant,toVariant,reason}，目标变体必须受支持，
并保持公共目标/语义。P01 夹具均为空数组，未来登记组合前补正常与失败例。

正常例 [结构夹具风格](examples/style.fixture.json) 包含具体示例数值但字体 pending，
无视觉参考，不可作产品验收。无效：缺 body 字体/缺 accent → STYLE_INCOMPLETE；
styleRef 不支持 layout → STYLE_UNSUPPORTED。风格切换案例 C09/C17/C18。
风格无独立动作目标；时间默认改变后重新编译；字体/间距变化重新测量。

## DEF-PARAMETERS：统一解析

覆盖项为 `{path:string,value:字段类型}`；同一层不允许重复 path（PARAMETER_CONFLICT）。
层顺序：公共基础 → 风格 tokens/defaults → 登记变体 → 配方 → 文档 → 页面 → 节点。
文档的覆盖字段首轮在 output 以外可选 `parameterOverrides:[]`，同 Slide/Node 格式。
例子暂不使用文档覆盖，但字段是正式首轮设计的一部分。

| 可覆盖路径 | 可写层 | 公共范围 | 硬约束 / 归属 |
| --- | --- | --- | --- |
| layout.columnRatio/columnGap/titleGap | 配方、文档、页面 | ratio [0.35,0.65]，gap ≥0 | 风格可收紧；节点不许改页面布局 |
| concept.variant | 风格、节点 | above/side/text-only | 必须与 figure 存在及风格支持一致 |
| concept.figureRatio | 风格、节点 | (0,1) | 风格收紧；容量实际测量 |
| text.align | 节点 | start/center/end | Text.data.align 与覆盖不可同时提供冲突值 |
| text.colorRole | 节点 | colors 中声明角色 | 不允许覆盖实际字号/字体规避可读性 |
| stroke.width | 节点 | >0 | 风格范围与边界测量 |

Typography 数值在首轮只允许风格填写，字号等局部能力以后按需求登记。canvas、
nodeId、contentRef、target、版本、时间和诊断门槛均不是样式覆盖字段。锁定不豁免范围。
缺省公共参数必须有已定义来源；例如 concept.variant 默认来自风格，不猜测为 above。
Node.variant 是 concept.variant 的语义便捷字段；规范化为节点层参数，同层双写报错。
同样，显式 Text.data.align 对应 text.align，Vector.data.strokeWidth 对应 stroke.width；
缺省时使用各卡公共/风格默认，显式便捷字段与同路径覆盖项双写一律报 PARAMETER_CONFLICT。
公共变体仅改变结构算法，不另偷偷设置字体；配方缺省不含硬约束。

输出 ResolvedParameters：`{inputFingerprint,entries:[{scopeId,path,value,sourceLayer,sourceRef}],diagnostics}`。
指纹定义在输出卡；各节点继承的字段生成自己的 scopeId 记录。硬约束校验发生在最终值
确定后，并保留来源方便定位。非法覆盖 PARAMETER_NOT_ALLOWED；冲突 CONSTRAINT_CONFLICT。
例：公共 ratio .5 → 风格 .5 → 页面 .6，最终 .6 来源 page；节点写 .6 必须拒绝。
正常/非法/锁定/无变化验收 C04/C17/C18/C20/C21；解析不是 CSS cascade。
