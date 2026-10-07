# E1-ASSET / READINESS / GEOMETRY

版本 0.1.0；公共资源/测量维护；HPS-006/007/009/013/014/018/023/029/030；定义 specified。
资产字段：id/version/kind=image、file{path,mimeType,sha256}、intrinsic、实际 alphaBounds、点 anchors、provenance、quality 全必填。只支持 PNG 与精确版本。
路径为 assets/ 下包内相对路径，不准 ..、反斜线、URL、盘符或不规范段。资源来自构建时检查的包；浏览器不自行联网找图。
锚点{x,y}为归一化点，ID 唯一、范围 [0,1]。这是 E1 新点锚定义，不改变 P01 矩形锚卡。
构建检查文件存在、SHA-256、PNG 尺寸/alphaBounds；浏览器校验包内字节 SHA-256、解码和实际尺寸，不把元数据当成功。
图像库 quality=conditional-experiment 仅允许 design-exploration。本轮不升级 motion-02 未通过的源边缘/留边为资产库 approved。
预览离线资源包由脚本从固定文件生成，不含密钥。JSON 是可编辑来源，生成包不是第二份手工配置。没有远程 URL 回退。

字体采用显式系统字体实验策略：等待 fonts.ready，并探测指定字体与两种通用回退的测量差异；未探测到则 FONT_UNAVAILABLE，不自动替换。该探测不证明全部字形覆盖；测试用 CDP 保存真实平台字体。系统字体无可分发文件，跨环境/字体哈希级可移植导出未完成。
资源解码或哈希失败、缺字体、容量错误均阻断新场景 renderReady；返回带 code/path/nodeId 的诊断。替换失败保持此前已就绪场景，异步旧请求不能覆盖新请求。
同一载入修订只能在资源、字体、全部静态/动态文字容量与几何检查后成为 ready。就绪 Promise 不得把失败吞成成功。

时刻 self 几何包含：target、coordinateSpace=canvas、localRect、localToCanvas=[a,b,c,d,e,f]、polygons、rects、opacity。
image 使用 contain 得到资源→局部映射，再围绕资源锚点应用 t 的旋转/位移一次；另外返回 visibleContent 的 alphaBounds 四角。整图 self 不是素材内部语义对象。
text 使用实际 DOM 测量，返回各行矩形，正文是纯文本；当前仅 self，不接收文本范围 selector。预览缩放/窗口偏移在边缘转换，结果保持设计单位。
path 保留完整四点曲线的控制凸包矩形与 sampledPolyline；这是保守包围，不冒充精确曲线外轮廓。ring 返回矩形及 center/radius。
透明目标保留几何；不计算跨对象像素遮挡，opacity 不等于最终无遮挡可见度。画布本身不是所有 Canvas 对象的目标。
正常：旋转图片四角跟随求值、文字跨行可测。错误：缺资源→ASSET_UNAVAILABLE，字节不符→ASSET_HASH_MISMATCH，尺寸不符→ASSET_DIMENSION_MISMATCH，无锚点→MISSING_REFERENCE；不返回假零坐标。
编辑换图需提供新资源版本与哈希、重测锚点/尺寸/动作；输入不被渲染器改写。HTML/视频可用本地实验资源，PPTX/完整离线字体包/目标交互编辑不在本轮。
