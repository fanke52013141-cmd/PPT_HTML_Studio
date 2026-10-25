# 定位恢复、图文避让与知识网格交接 · 2026-10-25

## 本轮范围

接续七项离线优化，补齐定位恢复防重复请求、本地复核表单，以及生产注册的2×2知识卡片模板。原作者保存、音频、视觉批准、工作流入口和HTTP/Agent接口保持；未提交、推送、重启服务或部署，没有真实供应商调用。

规范与定义卡：[定位复核恢复与知识网格](../../contracts/html-presentation/runtime/visual-v1/reference-recovery-grid-0.1.0.md)。前批结果仍见原交接，不能拿旧验收包验证本轮变化后的源码。

## 实现

- `html_reference_workbench_ui.py`：对象/部件选择、文字分区、像素框与转录表单、容器表单、导入修正文件、适应/150%/200%缩放和下载；原高级JSON模式保留。来源文字只展示，实际转录需人填写；越界框不修改当前数据，其他会话导入被拒绝，移动端表单无横向溢出。
- `html_reference_replay.py`：按修正内容、执行模式和可选执行身份独占创建intent；同份修正并发只派发一次，完成回执核对结果hash后复用。unknown/中断、部分回执、损坏结果拒绝自动重发。复用返回`replay_receipt`，明确零本次派发；它是原记录，不是当前模型的新判断。
- `html_reference_workbench.resume_review`：调用前后核对修正文件和会话文件，继续核对原图、作者和定义；修正后重新生成文字边缘诊断。离线回放CLI按响应hash绑定`offline_supplied_response`，与configured_transport回执隔离。
- `html_layout_groups`：在原注册区域分离的image/figure与text/card间，按原水平或垂直分离轴提出两侧的单对象位置调整。支持不同基线的图文；尺寸、文字、关系和动作不改，实际图框/邻居/动画冲突仍交原整页QA。
- `knowledge-grid-v1`：注册2×2卡片布局与模板，复用header/card/summary；intro可选。黑灰白neutral-baseline主题精确增加兼容项。兼容清单原8项满额，扩为32且保留唯一性、ID及精确解析，视觉预算/边界不变；原构建重建validator/catalog/data/player。
- 所有新增生产模块进入原设计身份和生成快照；统一验收增加UI、并发/回执负例、图文和网格基准。

## 验证与证据

证据索引：`outputs/opt7-followup/delivery-summary.json`；最终统一包以该索引为准。每组结果可能重叠，不合计为唯一测试数。

- 聚焦布局、复核、回执、UI、验收负例和快照组46项通过。
- 本地浏览器已验证表单修改、越界阻断、导入会话身份、缩放和下载JSON一致性；390px移动端无溢出。桌面截图已查看，`workbench-desktop.png`/`workbench-mobile.png`与`workbench-ui-check.json`为受控夹具。
- 新网格经normalize→compile→原共享渲染及完整30fps检查；上排卡片加高后，下排两卡向下联动22px；保护下排位置时阻断。原scene、文字、motion和binding保持。`grid-after.png`已查看，仅为受控工程案例，不是人审批准。
- 原视觉引擎测试通过，新增测试核对网格必需槽、32项主题注册容量、重复注册拒绝及未知布局拒绝。
- 图文故意扩宽至1000px的首例空间不足，原QA拒绝；可修复的900px案例通过，没有放宽检查。旧失败输出保留。

## 执行

```powershell
python scripts/verify_reconstruction_v2_acceptance.py --output outputs/optimization7-new
python scripts/verify_reconstruction_v2_acceptance.py --verify outputs/optimization7-new
npm --prefix html_engine run test:visual
python scripts/run_checks.py --level quick
```

最新布局基准含三卡列、point路由、保护列、错位图文、网格联动和保护网格六例；容量基准四例，合计10个预期结果，成功及合法停止分开记载。原69项AC仍不整体升级。

## 未覆盖边界

复核仍为本地产物工作台＋内部恢复函数，没有产品主面板按钮/公开HTTP恢复入口；未改变原场景生产最终保存与批准。真实模型、跨课程保真、视觉签收和部署仍独立。新网格是明确注册的固定结构，不是任意CSS或自动分页；其他主题没有自动开放兼容。

参考分类目录已通过原catalog-build重新生成，当前统计11个布局、9个模板，`catalog-build --check`检查41个文件为current。目录源闭包变化后，旧验收包不再代表新源码，最终统一包另存。新增定义/主题兼容清单遵循原来源新鲜度：旧候选/批准不会自动重新签收，必要时走原显式复用/复核。

初轮UI回归发现390px表单输入框按固有宽度溢出，已调整移动端字段宽度并由真实浏览器复验；旧失败日志保留，不计入最终通过组。网格定义最初遗漏主题兼容注册，原编译器明确拒绝，随后补齐原主题兼容项与有界清单容量，新增负例确认未知布局和重复项仍拒绝。

## 最终结果

最终统一包`outputs/opt7-followup/acceptance-current`：83项专项通过，10个浏览器基准预期结果全部满足；执行前后来源一致，二次verify通过。原生产/规划/设计/快照/复用/恢复/任务存储回归141项通过（386.94秒）；组间有重叠，不相加。quick、原视觉引擎及新增知识网格注册约束检查、catalog --check、Ruff、Agent合同同步与diff检查均通过。最新受控工作台桌面/移动端图与网格/错位图文证据已归档，完成/停止/故意损坏负例回执另有receipt-index。所有文件hash见delivery-summary及验收包manifest。
