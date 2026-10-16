# A06 旧项目第一页失败候选接续记录（2026-10-15）

范围是本机 `D:/software/PPT_HTML_Studio` 的项目 `d1f5885a_122521`，不是另一台机器的项目 `8ce1222f_194645`。原第一页任务 `html_5b3d0bbc80df4d4b83e4` 保持 `failed`，设计还原 JSON 阶段仍是不可查单的 `unknown`；没有重新请求、修改任务账本、保存作者 scene 或写人工决定。

## 已核对的证据

- 原整页设计候选 `e434ba0d743a2ac57c1842df1bc4df234f7b32d6854a2fb597865c43521e09a8` 的图片 SHA-256 为 `fffbf402204c571aaebbcebd128253f40cab5ec98b6202eca785fe07dac992a4`，本机文件在 `runs/d1f5885a_122521/planning/html_visual/candidates/slide_001/designs/<候选 key>/design-reference.png`。
- 原未保存页面截图 SHA-256 为 `ac3b43229a2b3b4fd367c6c67d100ecff08b501e9356ce01c957259d1fca4b8a`，位于 `runs/d1f5885a_122521/planning/html_visual/candidates/slide_001/design-reconstruction/d5cd7ad02e6c90934c828ef66ddc2ff4b7ae53dc732bea08c8bee54d49643cb6/0/current.png`。截图来自共享组件渲染，并非已保存作品。
- 原布局 Agent 在设计理解变体应用**之前**通过严格检查；变体应用后的人工候选工程检查失败。`s1-summary` 槽位高 91px，选中的 `summary-relationship-panel` 最小高 140px，差 49px；`s1-anchor-label` 也溢出。原人工候选 key 为 `b8a62d8d5932f64f5c0bbf97d132082909b29c0e78cdbc71a35ff0aa80cd6ec9`，原接受请求返回 `409 CANDIDATE_ENGINEERING_FAILED`。
- 目视对照还显示：参考图右侧“分词器”是叠在主体右下的双层卡片，旧页面只显示分散的图标/文字；标签在参考图中单行，旧页面挤成多行；关系线落在主体中部而非参考高光附近；总结条的分区和字阶也不一致。这些是视觉审阅意见，不能由几何修复自动视为通过。
- 以当前代码只读读取原 LocalJob，`task_view` 给出 `input_state=stale`、`recovery.can_resume=false`、`reason=dependencies_changed`。当前人工候选接口要求 `input_state=current`，所以原 key 不应被重新拿来接受。旧证据仍可用于诊断，但不能提升为当前候选。
- 在独立的 `outputs/a06-old-candidate-repair-2026-10-15/` 临时目录中，只复制原素材字节并试算了总结面板 `height=140、offsetY=-27` 与标签加宽上移的注册实例属性；严格检查返回 `CONTENT_SAFE_ZONE: s1-summary`。这说明只扩大旧槽位会越过安全区，不能靠放松高度门槛解决。该临时结果未写回原项目，`proposed-scene.json` 与 `proposal-report.json` 仅供定位。
- 新增独立注册变体 `summary-relationship-compact`（最小 1100×91，原大面板仍需 1100×140），在同一隔离目录用归档场景与素材字节，将总结节点显式选择新变体并把标签移到参考图附近。当前共享浏览器严格工程检查 `passed=true`、`capacityIssues=[]`；90px 变体测试拒绝，见 [能力合同](../../contracts/html-presentation/runtime/visual-v1/summary-relationship-compact-0.1.0.md)。这只是未保存的工程提案。截图中的“分词器”仍未形成参考图的双层浮卡，标注线与高光锚点的视觉关系也不佳，因此视觉状态仍为 `changes_requested`。

## 处理结论与下一版本边界

原候选工程失败，保持历史证据；未以 Agent 身份代用户记录人工驳回。现有代码已在设计理解操作之后做严格容量复检，并对容量问题调用有界布局修复，测试覆盖该路径。它只约束**新**生产，不能反向修改原 `unknown` 回执或让旧截图成为合格页面。

若继续同一课程，先建立具有明确新来源身份的第一页版本，保留原设计图和 1024×1024 素材的有效字节及来源，明确记录与旧任务的关系；不能通过修改旧任务参数或伪造恢复来补发同一未知设计还原请求。新紧凑变体已验证容量，但还需实现或选择注册的右侧浮卡造型，校正标注锚点与标签连线；不应把隔离目录截图直接写进作者文件。之后在新版本重跑当前严格检查、原图对照与用户评审。作者提交、正式视觉批准、音频与 A04 仍是独立停点。

## 本轮验证

`checks/test_html_presentation_details.cjs` 的浏览器检查 8 项通过（含紧凑变体 91px 可用、90px 拒绝）；独立旧页提案严格工程检查 `passed=true`。Agent 合同回归 432 项通过，包含 `planning` 独立固定连接与 Web/Agent 结果一致，Ruff、Agent 合同生成校验和 `git diff --check` 通过。视觉引擎 `visual/tests/verify.cjs` 首次在 `amber-science` 随机跳转像素一致性检查失败，立即复跑 14 项通过；这是已有同类偶发问题，尚未定位为本次变体改动或修复。真实模型还原、原图相似度、作者保存和整课验收均未执行。
