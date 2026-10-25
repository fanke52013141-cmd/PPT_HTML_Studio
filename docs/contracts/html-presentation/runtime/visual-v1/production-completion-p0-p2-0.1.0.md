# P0 / P2 生产接线与能力补齐 0.1.0

2026-10-25；HPS-007/009—030/037。本轮授权范围：主面板定位复核与恢复、统一诊断/受保护修复入口、69项验收对账，以及高频注册布局与明确身份的跨页素材复用。

## 定义卡及完成条件

1. **定位恢复**：Web/Agent按项目、页和原生产任务读取该任务明确登记的workbench。不得扫描其他任务猜来源。返回修正数据、未决对象、同源预览及最近恢复任务；主面板允许导入修正并显式提交。恢复使用原LocalJob生命周期、冻结的文本模型、取消检查及精确回执，不规划、不生图、不保存作者或批准。恢复任务只交付审核证据，原失败任务不伪装成功。身份/来源变化、重复未知请求阻断。Web和Agent请求/响应及能力版本同步。
2. **统一修复**：共享类型化诊断包含code、目标、来源阶段、测量及处理路由。新增layout_first固定目标策略复用未保存累计容量/关联布局求解器，已保存适配另核对revision、audio、scope和原候选preview/key；只显式save能改作者。旧策略兼容。
3. **验收账本**：原69项逐项列required_level、已有源码/测试/证据和缺口；partial/not_run不得显示passed，真实模型/人审保持独立。提供可重复生成/校验的仓库内账本和总表，不依赖桌面绝对路径。旧总计划状态按实际工程进展更新，不整体升级。
4. **P2布局**：首批补齐左右图文对照和图表+说明注册结构；复用已有代码组件、原素材、原主题与完整QA。模板有明确容量、可用部位及保护负例；无自由CSS/自动分页。
5. **P2素材**：同项目内按显式asset id+version+sha256复用原已登记PNG。模型只从当前可用素材清单引用，输入必须已有该资源；不按名称、图像相似性或模型描述猜测。复用核对字节、alpha尺寸及anchor，保持来源、单页资源依赖闭包和人工保护；无新增生图。跨项目资源或未知/损坏身份拒绝。跨页派生资源改动经原场景保存和失效流程。

## 验证

审核通过后，生成与精确session/scene/原图/截图/源码绑定的reference_review_key。只有同项目同页成功复核任务登记的key可提交生产；主面板复用原snapshot里的design_candidate_key显式续接。只恢复已注册静态操作，文本、对象、动作、绑定和人工保护由原候选守卫检查，随后重跑原静态/全帧检查和原保存流程。取消或未知任务不能用孤立证据绕过生命周期，数据库丢失终态时仅允许复用完整已知回执，无再次模型请求。

下游影响：复核任务和证据发布不修改作者状态；显式续接和跨页绑定最终经原save/invalidation流程，仅对实际保存页面生成依赖失效记录。复用原页的资源字节与批准状态均不改写，目标页不继承视觉批准。

可执行验证：`python scripts/verify_reconstruction_v2_acceptance.py --output outputs/p0p2/acceptance-finalized`；完成后 `--verify outputs/p0p2/acceptance-finalized` 验证原证据与当前源码哈希。`python scripts/reconcile_reconstruction_acceptance.py --output docs/plans/html-backend-development/reconstruction-acceptance-ledger.json --junit outputs/p0p2/acceptance-finalized/O7-06.xml` 可生成69项账本；所有task层证据只标partial，不冒充逐项真实质量passed。

主面板真实浏览器流程、Web/Agent跨账号/跨页负例、持久任务与并发/取消/unknown、原严格候选保存门禁、69项完整性、两类新模板原渲染和跨页复用零供应商调用。真实定位准确率、跨课程视觉效果和部署独立记载。
