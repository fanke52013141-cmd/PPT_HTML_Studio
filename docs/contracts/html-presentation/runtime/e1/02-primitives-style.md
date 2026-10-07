# E1-TEXT / IMAGE / PATH / RING / STYLE

版本 0.1.0；公共原子/呈现维护；HPS-002/003/004/005/007/013/018/023/024/025；定义 specified。
本轮支持 text、image、path、ring，不支持 Group/Concept 或其他 P01 动作目标；未实现能力必须拒绝，不静默画成图片。

共同输入：id、type/typeVersion、zIndex、initialOpacity 全必填；初始透明度 [0,1]。公开目标仅 {nodeId,part:self}，无 selector。
文字/图片/圆的 box 为画布单位矩形。path 引用四点三次贝塞尔，不接受任意 SVG/脚本路径。

| 类型 | 输入与职责 | 风格/布局/目标 |
| --- | --- | --- |
| text | role=title/subtitle/caption；content 静态纯文本或 beat-summary | HTML textContent；字体/色彩/行高/字重/maxLines 来自 style.textRoles；动态摘要测所有语块容量 |
| image | assetRef、anchorId、fit=contain、rotationDeg | 独立栅格资产；保比例，空白槽位不裁掉；锚点参与位移旋转；self 为整框，visibleContent 为 alphaBounds 派生几何 |
| path | pathId、initialProgress、colorRole、strokeWidth、dash | Canvas 精确绘制；进度按参数 u 的曲线前缀，不等于弧长匀速、物理轨迹或 P01 annotate |
| ring | box、colorRole、strokeWidth、innerRatio | Canvas 圆环与内点；不承载科学数值；geometry 使用盒与圆说明 |

style 只有登记字段：背景 base/leftGlow/rightGlow、accent/path 色角色、三种文字 role 和明确系统字体。实例不得插任意 CSS。
所有矩形布局占位在 opacity=0 时仍保留。不会自动缩字号、截字、省略号或重生资产。超过 maxLines/box 的内容返回 CONTENT_CAPACITY_EXCEEDED，正式就绪阻断。
有意遮挡由 zIndex 表达；整个目标几何不等于真实无遮挡区域，当前不计算跨节点像素遮挡。人工审阅保留。
简单背景为 renderer 风格呈现，非可选对象目标；字与 Canvas 绘制按全节点层次组织，不强制 HTML 永远位于图片之上。
字体首例明确采用测试机 Microsoft YaHei；不默默改用新字体，不分发商业字体文件。字体探测与实际浏览器证据见资源卡；跨环境未验证。
用户可改公开字段与资源引用，编译后重测；没有应用级锁定/撤销管理。空文本仅动态语块间隙允许，静态文字非空。
输出：实际 DOM 文字、图像/矢量与时刻几何；未知节点→UNSUPPORTED_CAPABILITY，无效内容→INVALID_FIELD。原生 PPTX、富文本、句内锚点本轮不支持。
验收：两实例不改组件代码；替换文字/图/路径；超长字和未知节点阻断；文字不被当 HTML 执行；旋转几何与渲染一致。
