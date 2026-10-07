# 手绘平面效果库 0.1.0

首批七类组件已实现，见[效果库](atlas.html)、[参考图](atlas.png)、[实现定义](DEFINITION.md)。通过当前限定实例的运行检查，生产视觉批准待审阅。不是E1/E2新增注册能力。

使用effects.js的FlatEffects.mount(parent,type,parameters,theme)，返回at(0—1)、geometry()和destroy()。例子：

```javascript
const label=FlatEffects.mount(host,'paper',{
  id:'term',text:'蒸发',width:230,height:95,fontSize:44
},{yellow:'#ffdf87',ink:'#343c49'});
label.at(1);
```

type为paper/arrow/mark/sun/flow/text/panel，对应图板A01—A07。此编号是本库内部索引，与候选FX-*规划编号不是可互换的运行ID。颜色值和字号由参数提供，语义/动作共享实现，不复制主题组件。太阳只是第一种已实现图标；不宣称已有完整图标库。

图板由同一个effects.js实际渲染，不由生图模拟。修正前用于生成场景的图板保存在[输入快照](../../experiments/evaporation-01/input-effects.png)，最终图板增加粒子终态高度错落等微调。提示词中的实现归属和图板版本一起保存；不能把新导出的图板伪称为当时输入。

[20秒完整场景](../../experiments/evaporation-01/index.html)、[复用验证](../../experiments/evaporation-01/reuse.html)和[实验记录](../../experiments/evaporation-01/README.md)使用本库。当前二维效果不包含3D、真实物理流体或任意SVG形变。减少装饰运动在场景层提供，库自身只接收显式进度。

图谱静态代表帧没有替代动画说明。后续增效先补定义、参数/目标/时间，再实现与验收并重新导出图板。动态样例观看场景播放器，各组件的进度控制见实现定义。

本库作为首个优先建设的[手绘科普风](../../../docs/styles/handdrawn-science/README.md)效果基准。参考图按版本复用，不按页重新生图；字幕安全区由场景承担，不在组件内部硬编码。
