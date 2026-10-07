# 平面效果库实现定义 0.1.0

HPS-026—034；独立效果实验，不注册E1/E2/P01运行能力。实施状态先定义、后实现；视觉批准以实际作品审阅为准。HTML结构＋CSS/SVG/Canvas 2D，时间单位毫秒，尺寸为逻辑像素。

统一入口 `FlatEffects.mount(parent, type, parameters, theme)`：返回 `element`、`at(progress)`、`geometry()`、`destroy()`。进度必须在0—1；几何为当前屏幕边界，Canvas另提供粒子逻辑位置。对象稳定ID由实例指定；风格值与组件行为分开。未知类型、非法尺寸、超长文字、非法数量明确拒绝。

| 编号/组件 | 参数与范围 | 几何/控制 | 视觉与运行限制 |
| --- | --- | --- | --- |
| A01 paper | text≤12字符；width≥180 height≥70；font20—64；tilt±6° | 整体出现、轻微弹性落位；主体＋6px硬阴影 | CSS标签，标签文字单行必须适配 |
| A02 arrow | width≥180 height≥100；线宽2—8 | SVG曲线进度0—1，结束时箭头出现 | 固定规范曲线，非任意路由器 |
| A03 mark | text≤16字符；width≥280 height≥90 | SVG椭圆描画进度；文字独立 | 不能遮挡正文；不做任意形变 |
| A04 sun | width,height≥100 | SVG八光线；轻微二维旋转和比例脉冲 | 太阳是固定语义图标，其他图标需新资源/定义 |
| A05 flow | count1—24；width≥180 height≥140；seed整数 | Canvas按进度求值六条默认粒子路径，可返回positions | 纯时间、数量教学示意、固定种子、DPR≤2；无物理模拟 |
| A06 text | text≤80字符；font20—64；width≥180 height≥70 | CSS短文本/双行标题，重点可指定强调词 | 真实文字、字号与宽度适配须检查 |
| A07 panel | width≥180 height≥100；radius0—32 | CSS背景容器和边框、二维揭示 | 颜色/边框/阴影由theme控制，不加复杂材质 |

theme包含paper/ink/yellow/blue/coral及字体；数字线宽保持逻辑单位。共享语义与类型不随主题复制。time→progress由场景负责；at不依赖前序帧；Canvas每次清屏，不留累积轨迹。没有循环CSS动画，暂停/导出由同一个时钟驱动。

调用预算：此实验每场景≤30组件、Canvas≤24粒子。参数边界、两主题、短长文字、大小尺寸与乱序取帧验收；Canvas对每个粒子返回逻辑中心，HTML/SVG使用实际DOM边界。输出目前HTML/静态PNG/无声视频；PPTX未实现。

本次独立试作不改应用/数据库/Agent/生产Prompt；设计图与资产提示词属于实验任务，来源和结果保存。图板注释是制作说明，不能进入场景。旧实验保留。
