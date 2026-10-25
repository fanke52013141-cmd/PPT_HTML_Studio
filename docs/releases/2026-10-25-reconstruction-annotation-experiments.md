# 2026-10-25 图片还原优化、标注工作台与定位配对实验

本批发布累计的图片转HTML工程优化、P0/P2接线及后续工具开发。契约包0.9.118，Agent API1.64.0；详细使用方式见[最新交接](../plans/html-backend-development/handoff-annotation-experiments-2026-10-25.md)。

## 变化

- 未保存候选累计容量修复、关联布局、共享整页预算、候选去重/调度与严格静态及30fps检查。
- 独立原图定位与配对保真证据、主面板框选修正、持久复核和原设计显式续接；未知结果不自动重发。
- 已保存页layout_first修复、统一诊断与scope/revision/audio/人工保护守卫；仅显式原保存入口改作者。
- 注册知识网格、左右图文、图表说明、宽正文双卡片及三列对比；同项目素材按id/version/sha256显式复用。
- 原69项独立验收规则、封存证据校验、固定开发/留出集及配对评分工具。
- 项目内可视化标注、草稿/版本/声明的独立复核；定位实验冻结样本/Prompt/项目模型，AB/BA调度、实时进度、取消和精确回执恢复。
- 任务本地HTTP观察器覆盖原格式回退和JSON修复；逐次用量完整时才累计，缺失保持null，不推测费用。
- Web/Agent/MCP/SDK/CLI同步；编辑器清单及视觉目录由原生成工具重建。

## 已有验证

合并远程更新前，封存包`outputs/evaluation/acceptance-complete`的180项工程检查及10个浏览器基准通过，Agent464项通过。补充回归41个唯一用例完成复验；初跑的1个夹具准备错误和重跑记录均保留，不宣称初跑全绿。原69项为12 passed、57 pending，未签发整体验收通过。

本地outputs/runs/数据库、凭据、测试临时目录及生成媒体不提交。仓库保留代码、合成夹具、规则、交接与可复现命令；本机原始证据由delivery-summary.json列出hash。新机器需重新运行验证，不能把本机文件路径或工程夹具当作真实模型/人审证据。

## 远程整合与发布备注

本批功能提交为`2457ce3`。发布前fetch发现远程main新增4个提交，整合到`63f1318`：保留外部Agent候选契约、项目模式字段转发、错误信封、限流及编辑器清单预检修复，未覆盖或改写远程历史。冲突按共同语义处理：Agent API保留1.64.0，保留内部0.1.0占位默认/路由缺省0.2.0的区别；能力文档与编辑器清单由原生成命令重建。

合并后将标注、原图续接、素材复用的模型owner登记到新加的来源检查；参数流检查中的通用分发清单与实现同步，专门的严格校验/路径编码/负载转发用例继续运行。合并启动模块的重复导入以满足原1100非空行限制，未放宽检查。仅清理SSE测试末尾的多余空行；按Windows CRLF语义做定向空白检查，未执行全仓库换行重整。

提交前复验发现并修复的失败保留在本地日志：quick初跑1项体积边界失败，Agent初跑3项登记/分发分类失败，登记补充过程中复跑1项失败。最终结果单独记录，不能把修复前的运行宣称为通过。最新本机复验目录为`outputs/publish-20261025/`，不随源码发布。

已完成的整合后复验：快速检查全套通过；Agent最终519项通过（通用分发的5个参数化实例由原有专门接口用例覆盖，因此相较初跑总数减少5）；视觉引擎检查、目录41个生成文件一致性、编辑器清单新鲜度、Agent契约一致性、ruff及定向Git空白检查通过。模型来源白名单保持封闭，未知输入、鉴权、并发修订与未知远端结果守卫均保留。

追加生产回归初跑为87 passed、2 failed（89个唯一用例）。两项失败均为`test_pi_selected_design_runs_original_production_and_records_restorable_ai_version`的模拟服务未识别新增`reference_targets`输入，错误进入旧设计理解分支；补充分支后，两项通过原生产流程复验。未修改生产成功条件、重试规则、人工签收或断言。初跑/诊断/修复后JUnit均留在本机目录，按89个唯一用例统计，避免重复计数。由于此夹具源文件在封存范围内，最终证据重新生成到`acceptance-final`，不复用旧包冒充当前源码证据。

最终封存结果：`outputs/publish-20261025/acceptance-final`的180项工程检查、10个受控浏览器基准全部通过，封存校验返回`passed=true, errors=[]`；这是夹具修复后的当前源码结果。原69项独立验收仍为12 passed、57 pending，不因本次工程测试或仓库推送自动通过。Git提交记录及本发布备注构成本批代码交接入口。

## 复验

```powershell
python scripts/run_checks.py --level quick
python -m pytest checks/agent -q
python scripts/verify_reconstruction_v2_acceptance.py --output outputs/release-20261025/acceptance --original-plan docs/plans/html-backend-development/reconstruction-acceptance-plan-v2.json
python scripts/verify_reconstruction_v2_acceptance.py --verify outputs/release-20261025/acceptance
npm --prefix html_engine run test:visual
node html_engine/tools/catalog-build.cjs --check
```

仍待独立完成真实课程标注、实际模型配对实验、人工视觉签收与正式音视频发布。工具代码更新不自动重启服务、运行付费实验或部署。
