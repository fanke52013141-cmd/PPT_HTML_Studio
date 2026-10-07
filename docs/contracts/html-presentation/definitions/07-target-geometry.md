# DEF-TARGET：稳定目标、文字锚点与几何

版本 0.1.0；公共目标/测量协议；HPS-004/006/007/009/018。
定义 specified；实现 not_implemented；验证 partial（样例范围/引用）；P03 测量、P04 动作跟随。

## 作者目标

| 字段 | 类型 / 必填 | 约束 | 所有权 / 修改影响 |
| --- | --- | --- | --- |
| nodeId, part | Id, 字符串 / 是 | part 必须属于类型公开目标；原子 self，概念 self/title/body/figure | 实例绑定，定义控制含义 |
| selector | 对象 / 可缺省 | 缺省=整个 part；可 text-anchor 或 asset-anchor | 实例细粒度目标 |

selector 为 `{kind:"text-anchor",anchorId}` 或 `{kind:"asset-anchor",assetRef,anchorId}`。
不接收 CSS、DOM 路径、数组序号。一个 TargetRef 只指一个语义 part，几何可以是多个矩形。

TextAnchor 必填 `{anchorId,target,contentRef,textRevision,quote,range,prefix,suffix}`。
target 为不含 selector 的 `{nodeId,part}`；contentRef 对应该 part 当前文字内容；
textRevision 是内容修订整数；quote 非空；range `{start,end}` 为码点半开区间，
0≤start<end≤码点长度。prefix/suffix 必填字符串，可为空；示例保存紧邻各最多 16 码点上下文。
range 切片必须等于 quote；重复短语由范围和上下文定位，不仅匹配 quote。

DOM Range 接口用 UTF-16，必须显式从码点索引转换。锚点不得切断 grapheme cluster：
emoji 联结序列、组合字符都需要固定环境的边界检查；实际分段器版本在 P03 记录。
源文字变化使旧 anchor 待检查；即使 quote 还存在也不擅自改 revision/range。
无唯一位置 STALE_ANCHOR；范围非法 INVALID_TEXT_RANGE；不存在 part MISSING_TARGET。

AssetAnchor 使用 assetRef 与 Image 版本一致、anchorId 存在，坐标经 contain/cover 后
映射；替换资产后旧 selector 无效。不能对 asset-anchor 施加 reveal，诊断 TARGET_CAPABILITY。

## 几何输出（派生，不写回作者源数据）

ResolvedLayout 必填 `{inputFingerprint,environmentRef,canvas,slotRects,nodeGeometry,targetGeometry,diagnostics}`。
nodeGeometry 项 `{nodeId,parentNodeId?,localRect,localToCanvas,zIndex,clipRects}`；
localRect 和 clipRects 均明确坐标空间，矩形宽高≥0；localToCanvas 为六项二维仿射矩阵
`[a,b,c,d,e,f]`，定义 x'=a*x+c*y+e，y'=b*x+d*y+f；zIndex 有限整数。

targetGeometry 项 `{target,coordinateSpace:"canvas",rects,polygons,textLines?,resourceRef?}`；
rects 是轴对齐包围矩形，polygons 是对应实际四角，不用包围框替代旋转后的对象。
文字跨行保留多个 rect/polygon，textLines 记录 `{range,rect}`，range 使用同一码点单位。
clipRects 为 `{coordinateSpace:"local"或"canvas",rect}`，先统一空间再求可见边界。
坐标链：资源归一化→原图→适配/裁切→节点局部→父组→画布→预览显示；透明边界另存。

基础几何在无动画变换下测量。P01 三动作不改变空间矩阵，勾画直接使用此几何；
未来新增变换动作时只应用一次时刻矩阵。预览窗口偏移与缩放只在交互/显示边缘转换，
勾画数据保持画布单位，设备像素比不会改内容身份。

测量依赖字体/图片就绪、布局和风格解析，修改任一度量输入使几何过期。组件提供 part
映射，目标解析器校验动作支持；公开接口不要求编辑器知道组件内部 DOM。
输出/错误：成功返回几何映射；失败返回对象/字段/来源，不返回假坐标 (0,0)。
编辑锚点是独立源操作、需 expectedRevision；导出使用相同固定几何并记录转换。
正常例 anchor.html-control；无效重复短语只带 quote → INVALID_FIELD。
验收 C06/C07/C08/C12/C14/C15/C16；未知新版拒绝，禁止隐式换索引单位。
