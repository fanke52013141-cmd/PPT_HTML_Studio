# 图片转HTML七项离线优化交接 · 2026-10-25

## 范围与状态

按用户授权推进搜索、预算、离线验收、布局覆盖、设计前检查、原图复核恢复、素材与缓存七项。实现范围以[定义卡](../../contracts/html-presentation/runtime/visual-v1/reconstruction-offline-optimization-0.1.0.md)为准。仍在原工作树，保留前批修改和两份继承的编辑器manifest；没有提交、推送、重启服务或部署，没有真实供应商调用。

## 主要实现

1. `html_capacity_repair.net_operations`合并绝对属性赋值；去掉验证前的前4项截断，只有新合法状态消耗测量名额，避免重复/no-op占位。
2. `html_page_budget`通过任务上下文共享整页截止时间及模型入口/检查子进程次数。最终严格检查有保留区；迟到结果、嵌套阶段、异常后上下文恢复均有测试。默认900秒/80次检查子进程/12次模型入口调用；原底层HTTP尝试计量仍由传输所有者负责。
3. `scripts/verify_reconstruction_v2_acceptance.py`执行O7-01—07及两组浏览器基准，检查必需案例集合、来源/证据hash、JUnit完整性和成功案例完整30fps报告；原69AC可导入但未被本次入口认证的项保持not_run。
4. `html_layout_groups`补充注册横排/图文对/多行的受限位置提案；继续原编辑保护和完整动态检查。现有三阶段横排经真实共享渲染；图文/网格策略有受控单测，当前没有新增2×2生产模板。
5. `html_design_feasibility`在新设计出图前按真实字体和准确文字测量注册槽位投影，容量不足在付费出图前阻断。插画及完整关系不在该投影结论内，后续三检查点保持。
6. 定位未决时导出本地`workbench/index.html`：并排原图/当前图、文字框预览、JSON编辑/下载。`resume_review`校验准确文字、身份、原图、作者/人工覆盖和运行版本，重新生成修正框对应的文字边缘诊断，再只恢复保真审核；不替代原审批。`scripts/replay_reference_review.py`是明确离线响应回放入口，产品面板未新增按钮/HTTP接口。
7. 素材缓存命中时复核实际尺寸/alpha边界，损坏停止；`html_asset_geometry`输出主体可见占比与锚点诊断。`html_review_cache`仅在整页内对相同完整输入复用测量/截图/动态报告，校验文件hash并保留不可变截图；改字体、输入或模式后重新检查。ROI按问题/位移排序，完整审核清单保持。

所有新增生产模块进入设计身份和生成快照。无新HTTP/Agent字段，无数据库迁移、作者保存入口或批准权限。

## 本地执行

```powershell
python scripts/verify_reconstruction_v2_acceptance.py --output outputs/optimization7-new
python scripts/verify_reconstruction_v2_acceptance.py --verify outputs/optimization7-new
python scripts/run_checks.py --level quick
```

输出目录必须不存在。首次验收器在Windows子进程文本编码上失败，已固定子进程UTF-8并重新执行；旧日志保留。横排浏览器一轮发生Target page closed，独立重跑通过；不将失败原记录修改成通过。

最终证据索引：`outputs/opt7/delivery-summary.json`。专项、回归、生命周期组可能重叠，不相加为唯一案例数。原模型定位准确率、跨课程保真、人工视觉签收、部署仍不由这些工程证据推导。

## 后续边界

- 图文和多行策略需要匹配注册槽位才会提案，不是任意页面自动重排。
- 本地定位复核已有可执行产物与内部恢复函数；若需产品面板恢复按钮，需另行同步公开API/Agent合同和前端浏览器回归。
- 设计前检查仅覆盖可测量代码文字，不能预测生成图片内部的结构正确性。
- 预算对图片远端只做调用前后合作检查，不承诺中断远端请求；不对unknown自动补发。
- 缓存是整页内的精确输入复用；没有跨页模糊匹配、自动合板或自动裁剪。

## 已运行验证

- 工程/设计回归62项通过；生命周期、恢复、共享渲染与Agent合同548项通过。组间有重叠，不合计为唯一测试数。
- 受控生产回归保存50份共享预算报告，审阅缓存实际命中12次；只证明受控链路发生复用，不推导通用耗时或费用降幅。来源及hash见`outputs/opt7/cache-proof.json`。
- 真实本地浏览器通过复核页红框更新、下载JSON一致性、坏JSON提示、390px移动端无横向溢出；桌面截图已人工查看，证据见`outputs/opt7/ui-check.json`和`workbench-desktop.png`。此图为明确受控夹具。
- 最后审查修复人工定位修正后文字边缘证据过期的问题，对应12项定位/恢复回归通过；原观察保留在session，新诊断按修正hash另存。
- canonical quick、Ruff、compile、Agent合同同步及diff空白检查通过。最终七项验收包以delivery-summary指定版本为准，早期输出保留历史。

最终统一验收：`outputs/opt7/acceptance-final-r2`，七专项72项通过，7个真实浏览器基准预期结果全部满足；二次verify必须仍通过。原69AC保持独立not_run记录，不因该专项结论整体升级。全部源与证据hash见该包manifest和交付索引。
