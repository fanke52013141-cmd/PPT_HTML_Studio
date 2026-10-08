# 实际 HTML 静态效果

用户在2026-10-09要求查看实际HTML，随后明确不生成语音。

- [打开仓库HTML](review.html)：相对路径引用同目录两张独立透明插画和上一目录生成参考；数据、主题和渲染器随页保存。文字/卡片/编号/刻度/关系箭头/图表/标签是实际DOM或SVG。默认显示HTML，参考整图仅在对照模式显示。本地原单文件html-effect.html是派生副本，不重复入库。
- 本机应用预览：`http://127.0.0.1:8010/reviews/capability-reconstruction/`，可切换生成参考、滑动对照、隐藏插画。依赖本机Microsoft YaHei字体，系统字体不重新分发。
- [实际画面](html-effect.png)、[滑动对照](comparison.png)、[代码部分](code-only.png)。这些图片来自Chromium浏览器截图，不是生成的整页PNG。

## 可追溯输入

源 `scene.json` 保留原拆解13个对象身份；主题 `theme.json` 提供外观；`renderer.js` 实现当前实验组件，`template.html` 提供浏览与对照。原生成图仍是 `../generated.png`，精确布局由[静态定义卡](../reconstruction-definition.md)冻结；坐标从生成构图转录，原LLM初拟位置未假装成为精确布局。

`scripts/extract_capability_demo_assets.py` 调用现有项目配置并使用ToAPIs skill入口，模型为用户指定 `gpt-image-2.5-sunburst-vip`，low/2K/透明，参考原生成图分别提取水杯与冰块，共2次成功任务。保留原PNG字节；只分析alpha可见边界，通过HTML缩放与平移显示主体。图片编辑会重绘细节，当前冰纹和玻璃高光与原参考不同，未宣称无损拆图。

`scripts/build_static_reconstruction_demo.py` 派生单文件HTML及当前应用static预览；`html_engine/tools/capture-static-reconstruction.cjs` 取得真实浏览器截图。当前静态实验没有写课程作者数据，也没有改变音频、批准或生产服务模型。

## 当前结果与边界

实际浏览器：13个对象、2张已解码2048²图片、字体就绪、纯色背景rgb(251,250,248)、0个audio/video节点、0个页面脚本错误。资源哈希、可见边界、缩放、实际字体文件与浏览器版本在 `build-evidence.json`、`browser-evidence.json`。

浏览后修正右侧正文容量与温度标签重叠。温度曲线是定性示意，下降起点对齐20℃刻度；未沿用原生成图不一致的刻度位置。标题淡渐变显式采用允许的F01，见主题记录。标题字形、正文宽度、刻度玻璃层次和插画纹理仍有可见差异；技术渲染完成不等于视觉批准。

状态：静态HTML演示已完成，视觉 pending_review；生产模板回收/自动组装/动画/声画/导出本轮未做。无新语音调用。此次不是完整自动化还原工具，也不宣称所有61项浏览器示例均已集成应用生产注册表。

## 2026-10-09 后续用户反馈与资产备注

用户认为当前方案比较OK，同时指出美感不足，要求先打好视觉地基。进一步明确：先做出漂亮的真实代码样板，把代码能达到的美感传给生图模型，不能只提供普通技术效果。此反馈未升级为生产视觉通过。

材料已归档到[代码美术资产清单与形成备注](../../../assets/code-art-references/README.md)。历史“F01表示渐变”的文字与主题引用存在错用，目录F01为纯色、F02为线性渐变；标题80px与旧目录18–48px也不一致，均登记待修，历史字节保留。详见[形成记录](../../../assets/code-art-references/formation-notes-2026-10-09.md)。
