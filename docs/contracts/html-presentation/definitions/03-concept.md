# DEF-CONCEPT：概念块

版本 0.1.0；type component.concept；公共语义组件；HPS-001/002/004/005/007/018。
定义 specified；实现 not_implemented；验证 partial（文档）；P03 实现，P05 复用验证。

用途：表达一个概念的名称、解释、可选插图。不能用两个概念块的摆放自行推断因果或
数值比例；对比关系由场景 relations 记录，流程/数据等以后定义独立语义组件。

| data 字段 | 类型 / 必填 | 默认 / 约束 | 归属 / 覆盖 / 影响 |
| --- | --- | --- | --- |
| titleContentRef | Id / 是 | 非空 text 内容单位 | 实例文字；内部排版/锚点 |
| bodyContentRef | Id / 是 | 非空 text 内容单位 | 实例文字；同上 |
| figure | 对象 / 可缺省 | 缺省=无图；{assetRef,fit,alt} 遵守 Image 卡 | 实例；素材与布局 |
| variant（Node 字段） | 枚举 / 可缺省 | 由风格 concept.variant 解析；above/side/text-only | 公共登记变体，风格选择 |

figure 存在时只允许 above/side；缺省时只允许 text-only。风格默认可能选择 above，
无图实例须明确选 text-only 或使用该风格登记的无图回退；不存在无条件隐藏配图的回退。
公开目标：`self`（整个概念区域）、`title`、`body`、`figure`（有图时）；均支持整体
出现/强调/勾画，title/body 可使用 TextAnchor。无图仍保留目标名称定义，但绑定 figure
报 MISSING_TARGET，而非悄悄操作 self。

内部结构由 Group、两类 Text、可选 Image 及风格需要的 Vector 容器组合。内部 DOM ID
和装饰不进入作者数据；公开 part 映射由渲染器维护。实例数据不复制标题正文值。

外部布局仅分配概念区域。内部先扣 padding，再按变体排图文：above 为配图在上，
side 为配图在起始侧，text-only 无图。figureRatio 只分配内部可用尺寸；标题/正文用实际
字体测量，间隔消费 spacing；不得把兄弟概念挤出自身区域。图区域包含透明边界。
测量返回最小需求、各 part 矩形、文字行、溢出诊断；具体可读性阈值由 P02 风格定。

初始可见性继承 Node；parent/self 的 reveal 与子 part reveal 相乘；self highlight 可画
容器描边，body/title highlight 可画目标底色，不改变布局。文字或图片仍按公开目标求几何。
同一有效目标重复写同通道需时间检查，不能靠内部多个 DOM 实现规避冲突。

可编辑标题/正文内容引用、图片版本、允许变体及参数；人工锁定按 DEF-EDIT 分字段。
换变体保留 nodeId 与公开 part；text-only 切换前须处理 figure 绑定。复制概念由宿主
映射 content/anchor/action；删除给出受影响清单。

输出：HTML/视频目标支持组件组合；图片 PPTX 为整体截图；基础可编辑 PPTX 将来展开
为受支持文字/图片/形状，不把 DOM 当可编辑对象。背景效果超支持范围明确降级。
依赖：四原子、风格、素材、目标测量。错误：缺正文 INVALID_FIELD、未知变体
UNKNOWN_VARIANT、布局不足 TEXT_OVERFLOW/LAYOUT_CAPACITY、无图目标 MISSING_TARGET。

正常：样例的 node.concept-html 与 node.concept-image。替换内容的复用例：同样模型
可比较“同步学习/异步学习”；不需要新增学习主题组件。无效/修改验收 C04/C10/C17/C18。
定义升级遵守入口兼容策略；具体变体比例改变需报告视觉影响并重排。
