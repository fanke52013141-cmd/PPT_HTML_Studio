# 四类公共原子定义卡

以下四卡版本 0.1.0；公共原子库维护；HPS-001/002/004/007/009/012/018。
各卡定义 specified；实现 not_implemented；验证 partial（文档）；P03 实现与测量。
共同输入继承 DEF-SCENE Node；共同输出为节点渲染树、局部尺寸需求和稳定目标映射。
样例中的概念内部原子由组合组件派生；后续也能作为其他组件的基础。

## DEF-TEXT / type atom.text

用途：可编辑纯文字及其可定位范围。首轮不接收任意 HTML/富文本，角色扩展不改变文本含义。

| data 字段 | 类型 / 必填 | 默认与范围 | 归属 / 覆盖 / 影响 |
| --- | --- | --- | --- |
| contentRef | Id / 是 | 指向 kind=text 的内容单位 | 实例；改内容影响排版与锚点 |
| role | 枚举 / 是 | slide-title、concept-title、body、caption | 实例语义；风格映射参数 |
| align | 枚举 / 可缺省 | start；start/center/end | 实例允许；文字分行/位置 |
| wrap | 枚举 / 可缺省 | normal；首轮仅 normal | 公共；禁用任意 CSS white-space |

公开目标 `self` 是全文，支持三类动作；文字子范围通过 TextAnchor 绑定，不造临时 DOM ID。
字体、字号、字重、行高、字间距、颜色由 DEF-STYLE 提供。角色不能由 CSS 选择器推断。
测量使用已加载字体、宽度约束及真实文本，输出多行矩形。显式换行保留；中英、数字、
标点采用固定浏览器的正常断行规则并实测；首轮不提供上下标和公式。
fontSize 不得为了塞满无限缩小；超行/越界报告 TEXT_OVERFLOW，不裁字。
编辑保留 nodeId/contentId，content revision 递增；旧锚点重新检查。
HTML/视频目标为真实文字；图片 PPTX 为像素；基础原生 PPTX 以后映射文字，富效果另报。
正常 `{contentRef:"content.page-title",role:"slide-title"}`；无效 contentRef 指向资源 → MISSING_REFERENCE。
验收 C04/C05/C06/C07/C08/C09；新风格不得复制 Text 实现。

## DEF-IMAGE / type atom.image

用途：独立图片/图标整体及登记锚点；不把位图内部对象声称为独立图层。

| data 字段 | 类型 / 必填 | 默认与范围 | 归属 / 覆盖 / 影响 |
| --- | --- | --- | --- |
| assetRef | VersionRef / 是 | 对应 kind=image 的固定版本 | 实例；换图使旧资源锚点失效 |
| fit | 枚举 / 可缺省 | contain；contain/cover | 实例允许，槽位可限制 |
| focalPoint | {x,y} / 可缺省 | {0.5,0.5}；均 [0,1]，cover 时使用 | 实例；裁切与定位 |
| alt | 字符串 / 是 | 非空，说明图的表达对象 | 实例；语义/可访问性 |

公开 `self` 支持整体三动作；`asset-anchor` 用于强调/勾画，单独出现不支持。
contain 保持原比例完整显示；cover 裁切，先检查 safeRegion 是否被裁掉；不得拉伸截图文字。
测量区分槽位矩形、实际内容矩形、透明边界。资源 decode 成功后才 ready；缺图草稿占位
并带诊断，正式输出阻断。外观来自素材及允许的公共边框参数；不改变原文件像素。
正常 `{assetRef:{id:"asset.html-structure",version:"0.1.0"},fit:"contain",alt:"结构化页面图示"}`；
非法 cover 使安全区内容不可见 → ASSET_CROP_UNSAFE。验收 C10/C11/C12/C13。
图片型 PPTX/视频可截图；原生图片映射以后实测裁切。字体不作为 Image 使用。

## DEF-VECTOR / type atom.vector

用途：矩形、椭圆、线、受限路径；箭头/图标是用途，首轮不增加新原子。

| data 字段 | 类型 / 必填 | 默认与范围 | 归属 / 覆盖 / 影响 |
| --- | --- | --- | --- |
| shape | 枚举 / 是 | rect/ellipse/line/path | 实例或公共组合结构 |
| viewBox | {x,y,width,height} / 是 | 有限值，width/height >0 | 实例局部坐标 |
| geometry | 对象 / 是 | 与 shape 对应，见下 | 公共类型；实例填图形 |
| fillRole | 字符串 / 可缺省 | none；none/surface/accent | 风格语义引用 |
| strokeRole | 字符串 / 可缺省 | ink；ink/accent/none | 风格语义引用 |
| strokeWidth | 数值 / 可缺省 | 风格 stroke.width；>0，线不得无描边 | 允许范围内实例覆盖；边界测量 |

rect: `{x,y,width,height}` 尺寸>0；ellipse: `{cx,cy,rx,ry}` 半径>0；
line: `{x1,y1,x2,y2}` 两端不同；path: `{d}` 非空，仅 M/L/H/V/C/Q/Z 指令，
不接受 SVG 标记、脚本、外部引用、滤镜及 CSS。几何坐标允许在 viewBox 外，但实际边界
必须参加溢出/裁切检查。圆可用等半径 ellipse。
公开 `self` 支持三动作；内部路径段首轮无公开身份，不能指“第三段”。
颜色/描边由风格解析；路径边界含描边。SVG 实现仅为渲染方法，源模型仍受字段限制。
正常 line geometry `{x1:0,y1:0,x2:100,y2:0}`；零长线 → INVALID_FIELD。
基础 PPTX 原生形状是后续候选，path 明确转图/不支持。验收 C04/C14/C26。

## DEF-GROUP / type atom.group

用途：稳定包含、局部变换和裁切，不自行对兄弟节点重新排版。

| data 字段 | 类型 / 必填 | 默认与范围 | 归属 / 覆盖 / 影响 |
| --- | --- | --- | --- |
| children | Id[] / 是 | 非空，无重复，节点 parentNodeId 必须一致 | 实例；结构/目标 |
| transform | 对象 / 可缺省 | translateX/Y=0、rotateDeg=0、scaleX/Y=1 | 实例；缩放>0，首轮不反射 |
| clip | 枚举 / 可缺省 | none；none/allocated-box | 实例；边界与标注 |
| arrangementRef | VersionRef / 是 | 首轮 group.overlay@0.1.0 | 公共子项放置策略 |
| childConstraints | 对象 / 是 | 各 childId 的 x/y/width/height，w/h>0，局部单位 | 实例放置意图；布局求结果 |

`group.overlay` 定义：按 childConstraints 分配子区域、按 children 顺序叠放；要求映射
完整、约束相对分配区域合法。它是本卡内登记的最小策略，不提供通用自动排列。
变换顺序为局部缩放 → 绕分配区域中心旋转 → 平移 → 父变换，矩阵不得重复应用。
公开 `self`（整个区域）与显式子节点各自目标；组可整体 reveal/highlight/annotate。
组 reveal 的透明度乘到子节点，强调不使隐藏子项出现；初期不提供变换动画。
禁止循环/多父/缺子约束；装饰可用矢量子节点，默认不加入 required 内容。
输出可截图；原生组/旋转映射后续验证。验收 C14/C15/C16；无外观时不消费字体。

四卡共同依赖/兼容/错误记录采用入口约定；正常复用例：Text 可作页标题或概念正文，
Image 可作独立配图或概念插图，Vector 可作容器或图示，Group 可组合图示或步骤项。
这些只是复用设计，运行复用要在 P05 验证。
