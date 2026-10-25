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
