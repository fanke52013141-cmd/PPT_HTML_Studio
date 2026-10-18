# 课程结构与设计前覆盖 0.1.0

2026-10-18，契约0.9.88；HPS-007/010/011/013/015—017/023—030/035—037。实施前定义。

- 保留既有scene0.7和旧静态arrow。新增arrow的from/to显式端点（objectId及0—1局部point，或图片anchorId，二者互斥）、head（默认true），lineStyle（solid/dashed）；成对提供，禁止连接自身/其他关系/未知对象。拥有端点的arrow占全内容坐标槽，不允许独立空间覆盖或偏移动作；共享时钟逐帧由端点对象运动派生，透明度不得超过任一端点。无头连接用于标签引线，有头连接用于有向关系；不在图片内绘制语义。
- 新chart节点：数据points（2—16个有限归一化点，x严格递增）、xLabel/yLabel、min/max（max>min）、单位unit、可选plateau区间索引。plateau明确要求区间y相等；坐标轴/曲线/标签全部代码渲染，禁止自由SVG/CSS。标签容量必须检测，不接受裁切；只允许整体位置/尺寸，不能局部修复数据或标签。图示不宣称真实实验测量值。
- card-outline保持原title/body/icon/动作，白底描边及圆形图标底。figure-frame-dashed复用frame-top标题规则，仅容器虚线。annotation-dashed-no-arrow全虚线无箭头。旧变体保持。
- 新注册模板science-relations-v1提供八个可选有端点关系槽；chart-explanation-v1提供独立图表和放热关系；process-three-stages-v1提供三个代码阶段卡、标签和连接关系，仍最多一个可选非语义主体图片。共用关系表达，不按课程页造组件。
- 模板relationPolicy=explicit时，箭头必须有端点。权威合同可带visual_requirements（id/kind/minCount），计划visual_coverage将需求id映射到对象id列表：relation/chart/stage的对象存在、类型和端点/图表合法，在build_semantic_design前验证。缺声明时不声称自动读懂任意自然语言需求；离线覆盖清单不代替真实生产合同或模型计划。
- 规划目录、原normalize→A02→compile→render/seek→binding路径、源快照、Agent元信息/Skill/影响同步。工程夹具不保存到真实项目，不产生批准，不调用模型/图片/TTS。组件和数据变化后原设计/视觉/A04/输出需要重验，原声音字节保持。

验收：四页固定夹具包含缺关系/端点/平台/阶段负例；原文、已有动作身份、人工保护和旧arrow兼容；1592/1600宽度及DPR1/2确定性seek；实际共享渲染、容量、端点跟随/未显示端点隐藏连线。能力通过不等于真实模型或课程验收。
