# DEF-LAYOUT / DEF-RECIPE：两列布局与对比配方

两卡版本 0.1.0；公共布局/配方库维护；HPS-002/003/005/007/018。
均定义 specified；实现 not_implemented；验证 partial（文档）。P03 排版；P05 替换内容验证。

## DEF-LAYOUT / layout.two-column

用途：顶部标题与下方两列内容，不表达先后或因果。槽位为 title、left、right；三个均
必填、每槽恰好一个根节点且不同，title 类型 atom.text，其余为 component.concept。
这里声明的是首轮支持集，后续新增槽位类型须扩定义，不绕过检查塞任意 HTML。

| 参数 / 输入 | 类型 / 必填 | 默认和限制 | 归属 / 影响 |
| --- | --- | --- | --- |
| canvas.safeInsets | 四非负值 / 是 | 从文档取得，不允许布局覆盖 | 实例规格，永久安全区 |
| slots | 对象 / 是 | title/left/right 完整映射 | 实例组装，目标/覆盖 |
| layout.columnRatio | 数值 / 可缺省 | 基础 0.5；左列占可用宽的 [0.35,0.65] | 风格偏好；实例允许覆盖 |
| layout.columnGap | 数值 / 可缺省 | 风格 spacing.columnGap；≥0，小于可用宽 | 风格；实例可在声明范围覆盖 |
| layout.titleGap | 数值 / 可缺省 | 风格 spacing.titleGap；≥0 | 风格；实例可在声明范围覆盖 |
| layout.align | 枚举 / 可缺省 | start；首轮仅 start | 公共行为，不能随机垂直居中 |

令安全区域为 (L,T,W,H)，标题实测需求高为 hTitle；列顶部 y=T+hTitle+titleGap，
列高度 h=H-hTitle-titleGap，列净宽 w=W-columnGap，左宽=ratio*w，右宽=(1-ratio)*w。
标题宽 W；左列 x=L；右列 x=L+左宽+columnGap。最终由实际测量结果决定，不写死正文坐标。
先测标题，再将两列分别交概念内部布局；所有隐藏元素保留占位。槽位几何是派生结果。

优先级：画布安全区/类型/人工锁定/可读性为硬约束；比例与间距为允许范围内偏好。
冲突不牺牲硬约束。标题太高、列无法容纳或 figureRatio 与文字需求冲突报告
LAYOUT_CAPACITY/TEXT_OVERFLOW/CONSTRAINT_CONFLICT；建议换已登记变体、改作者约束或拆页，
首轮不自动改讲稿拆页。不以固定字数代替测量容量。

布局本身无动作目标；动作绑定槽内节点。更换布局保留节点身份，必须提供槽位映射。
换风格先检查支持集与锁定，再排版。输出：ResolvedLayout.slotRects 与 nodeGeometry；
各格式使用同一几何，但原生 PPTX 需单独换算。正常见完整例；无效 left/right 同 ID
→ INVALID_SLOT。验收 C04/C05/C14/C17/C18/C26。

## DEF-RECIPE / recipe.two-concept-contrast

用途：将两个概念按并列对比组织为一页，不保存某课程正文。不替代公共布局算法。

| 字段 | 类型 / 必填 | 默认 / 限制 | 归属 / 修改影响 |
| --- | --- | --- | --- |
| recipeId, version | Id, semver / 是 | recipe.two-concept-contrast@0.1.0 | 公共定义 |
| layoutRef | VersionRef / 是 | layout.two-column@0.1.0 | 公共组合 |
| slotTypes | 对象 / 是 | title=atom.text；left/right=component.concept | 公共支持集 |
| relationType | 枚举 / 是 | contrast | 公共表达意图 |
| stages | 数组 / 是 | intro-left、intro-right、compare，按此顺序 | 公共讲解阶段名，不是时间 |
| parameterDefaults | 覆盖项[] / 可缺省 | []；只填允许参数 | 公共配方偏好，视觉仍受风格约束 |
| assetRequirements | 对象 / 是 | 两概念各一个独立插图；contain；图中文字由 HTML 表达 | 公共配方要求 |

配方展开要求 left/right 内容存在对应 contrast 关系；三个语块按页面 beatIds 分别承担
阶段，第三语块关联该关系。时间由 DEF-TIMELINE 解析，配方不内置实际音频时长。
配方可推荐动作，但样例实际动作存在 Slide.actions，不能隐式再生成第二套动作。
风格引用支持的配方和参考页；装饰与插图画风来自风格，不复制概念组件。

公开目标沿用节点 part；没有新的“第几列”身份。正常示例三个语块；无效用 contrast
配方却 relations 声明 cause → CONTENT_RELATION_MISMATCH。验收 C01/C03/C17/C22。
当实际内容不适合两个概念，应选择其他配方，不能靠删掉必讲项通过校验。
