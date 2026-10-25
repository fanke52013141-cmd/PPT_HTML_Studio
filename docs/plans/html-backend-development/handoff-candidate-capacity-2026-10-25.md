# 候选容量累计修复交接 · 2026-10-25

基于 `0a9d27c` 实施，本批为本地源码修改，未提交/推送/部署。原工作树的两个 editor manifest 修改及既有测试临时目录保持。

## 结果

新页编译后与设计组件分配后的容量失败，进入原 `repair_candidate` 前先尝试确定性求解。修复可以累计多个对象，不必让每个单对象补丁独自通过整页检查。新增路径保留准确内容、manual、binding 和 beats；不要求已保存作者页，不写作者/批准。

受控两卡片夹具同时将卡片高度从注册 102px 压为 80px；最终共同恢复到合法尺寸，原严格检查及作者时钟 0—18000ms、30fps 输出帧/动作边界共 563 个时刻通过，问题组 0。修复模型/供应商调用均为 0。

同一受控输入的本轮原型在加入“先恢复注册容量”之前需要 32 次测量、39.685 秒；改进后 7 次测量、10.628 秒。时间受本机并行测试负载影响，仅为本次本机观测；32→7 是相同夹具的搜索次数变化，不能宣称真实课程成本或跨课程成功率提升。

## 实现所有者

- `html_capacity_repair.py`：未保存候选累计求解、预算、严格复验、来源检查；原可选候选适配保留 manual/beats，避免 load_editor 强制依赖。
- `html_candidate_agent.py`：内部 deterministic_first 入口，成功继续原流程；确定性未成功保留原模型回退并记录证据，blocked/stale 停止。
- `html_production_service.py`、`html_design_reconstruction.py`：两个生产检查点启用确定性优先。
- `html_engine/visual/renderer.cjs`：容量诊断附实际公开文字 part，供继承字号使用；原 bundle 已重新构建。
- `html_design_candidates.py`、`html_build_snapshot.py`：容量源码纳入设计/生成身份，旧候选按原规则重验。

公开请求 Schema、Agent API、生产 Prompt 和批准权限未变。字号底线、原候选操作守卫与完整动态检查保持。

## 验证

本机运行先设置 TEMP/TMP 为工作区内的隔离目录，避免系统临时目录 EPERM。冻结快照测试使用较短的 basetemp：长路径下 Chromium 会对实际存在、超过 260 字符的 file URL 返回 ERR_FILE_NOT_FOUND；短路径复验另留报告，未放宽检查。

- `scripts/benchmark_candidate_capacity.py --output <新目录>`：四个真实浏览器受控用例全部通过（normal、two-cards、budget、protected）。
- 生产/还原/候选/修复/参考复用相关组：69 passed。
- 新增纯逻辑、保护负向与来源闭包专项组：12 passed、1 browser 用例未在该子集中重复运行；与其他组存在重叠，不相加作为独立用例数。
- `npm --prefix html_engine run test:visual`：容量、关系容量、强调与 5 场景/14 检查通过，pageErrors=0。
- `scripts/run_checks.py --level quick`：通过。
- 全仓 Ruff、Agent 契约同步、git diff --check：通过。
- 快照/恢复/生命周期/动态 QA 短路径复验：125 passed，270.03秒；早期长路径失败报告保留为环境诊断证据，不作为通过。

运行证据保存在 `outputs/optimization-implementation-20261025/`，不提交课程/运行媒体。

## 与 v2 计划的对应与未完成范围

本批落地 T02/T03/T05 的容量子集及 T04 的最终全动态复验；T00 仅完成本地工程基线，真实 24 页跨课程留出集未齐。内部状态已区分预算、无候选、blocked 与 stale，但 T01 的完整类型化跨缺陷路由尚未交付。

仍待实施：三卡片空间联动、关系 point 路由自动串接、第三个还原后检查点的统一求解、独立原图定位接入、素材能力预检、全任务共享模型预算、真实跨课程配对、人审、音频/正式输出与发布回退验收。原模型回退仍存在，不能宣称所有几何/容量请求已经零模型。

因此本批是可复验的容量工程增量，完整 M1/M3 保持未完成。没有把受控夹具或 mock 保真审核记为真实用户接受。

## 复现

```powershell
Set-Location -LiteralPath 'C:\Users\Administrator\Desktop\html动画\PPT_HTML_Studio'
New-Item -ItemType Directory -Path 'outputs\capacity-tmp' -Force | Out-Null
$env:TEMP = (Resolve-Path 'outputs\capacity-tmp').Path
$env:TMP = $env:TEMP
.\.venv\Scripts\python.exe scripts/benchmark_candidate_capacity.py --output outputs/capacity-acceptance-new
.\.venv\Scripts\python.exe -m pytest checks/test_html_candidate_capacity_solver.py -q --basetemp=outputs/capacity-tests-new
```

证据输出目录必须是新目录；不要覆盖旧运行。候选报告归档包含每步 scene、report、render、operations 与最终 temporal 原报告。
