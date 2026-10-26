# 2026-10-26 还原优化与23项工程验收

本批将目录换行一致性、候选公平性、定位评分及真实样本准备工具，与23项工程验收矩阵一并交付。源码基线8aa5695；当前验证和发布终态见[工程交接](../plans/html-backend-development/handoff-engineering23-2026-10-26.md)。

## 行为变化

- 目录哈希涉及的文本检出固定LF，已封存CRLF/混合字节来源保留原字节；逐字节哈希检查保持。
- 16项容量候选按对象/部件/操作类别公平分配，避免长标题字号梯度挤掉正文；原24px下限、scope/manual和完整30fps检查保持。
- 定位评分检查部件状态，多行一对一匹配不再穷举；配对报告保留改善、退步、不可比较及完整分母，不推测费用。
- 数据准备增加曝光声明和只读readiness审计；本机3课程5页均为历史开发样本，真实留出集与人工标签仍缺。没有真实供应商调用或人工批准写入。
- 动态报告接收器复用原timeCoverage，拒绝frames/times共同截断；不复制时间算法，不放宽任何原门禁。
- 23项工程规则登记精确完整检查，覆盖真实浏览器、生产接线和显式故障注入；原69项criterion和required_level不变。真实模型、人审和正式音视频验收独立。

## 复验

```powershell
.venv/Scripts/python.exe scripts/verify_reconstruction_v2_acceptance.py --output outputs/new-acceptance --original-plan docs/plans/html-backend-development/reconstruction-acceptance-plan-v2.json
.venv/Scripts/python.exe scripts/verify_reconstruction_v2_acceptance.py --verify outputs/new-acceptance
.venv/Scripts/python.exe scripts/run_checks.py --level quick
.venv/Scripts/python.exe -m pytest checks/agent -q
node html_engine/tools/catalog-build.cjs --check
```

输出目录须不存在。Git只携带源码、测试、契约、证据摘要和复验命令；本地数据库、outputs/runs、课程图片、凭据及生成媒体不发布。仓库更新不等于服务部署，不重启本地应用。


## 本机验证回执

最终封存273项工程检查、10个受控浏览器基准全部通过，二次校验无错误；逐项AC为36 passed、0 failed、33 pending，本轮23项工程补证全部通过。quick全套通过，Agent519项通过（73.45秒），原69项要求与层级保持。

首轮测试已通过，但证据导入发现旧命名测试来源漏封存；修复GATES来源收集后重新完整执行，最终包不复用首轮签章。中间夹具被原Schema/边界阻断的失败日志保留，不宣称初跑全绿。

代码更新仅面向origin的PPT_HTML_Studio main，不向原图片工程推送，不部署或重启应用。剩余33项真实数据/模型/人审/正式输出门槛保持；本轮无真实供应商调用。
