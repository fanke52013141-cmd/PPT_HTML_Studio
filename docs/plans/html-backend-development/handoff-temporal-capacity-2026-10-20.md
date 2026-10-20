# 动态检查与容量请求留证 · 2026-10-20

在本机容量基准之后，继续优化原检查链；基于00fb81d4和前两批未提交修复。
未调用模型、重发unknown请求、修改源课程、签发人工批准或启动正式服务。

## 定位和修复

1. 原registered重叠策略缺少science-relations-v1、chart-explanation-v1、process-three-stages-v1模板登记，真实课程调用会以OVERLAP_POLICY_UNREGISTERED停止。按各模板0.1.0补齐策略；仅science-relations继承既有figure/subject和figure/anchor-label容器关系，其他两模板无排除对。未知版本继续拒绝。
2. 显式关系箭头的DOM承载层为1600×800，旧动态检查把整个透明层当成遮挡区域。改用实际SVG图元DOM边界，沿用annotation的坐标归一化方法。箭头仍进入全部registered对象对，真实交叉和越界不豁免。该检测仍是保守矩形近似，不等于像素级路径碰撞判定。
3. 容量适配请求新增同request_id的request-outcome.json：原180秒预算、实际耗时、返回/异常状态及异常类型。异常正文不写入该补充记录；usage/cost未知为null。本地异常不证明请求提交或供应商终态，submission_state保持unverified；原ProductionStages持久回执、unknown及禁止自动重发策略仍权威。返回仍需原操作和浏览器检查。

归属仍在html_candidate_agent.py、原temporal-review.cjs及版本化overlap-policy.json，没有新renderer或作业存储。
HPS-009/010/011/013/014/016/017；更新原动态QA/容量合同、索引和CHANGELOG，合同包0.9.108/API1.59.0保持。上述检查器/策略已在原构建快照源码闭包中，旧报告按原当前性守卫处理，不篡改已有快照。

## 真实隔离课程结果

```powershell
$env:PYTHONUTF8 = '1'
.\.venv\Scripts\python.exe scripts/benchmark_capacity.py --source-run runs/ec60bbd4_010236 --slides slide_001 slide_003 slide_004 --temporal sampled --output outputs/temporal-course-NEW
.\.venv\Scripts\python.exe scripts/benchmark_capacity.py --source-run runs/ec60bbd4_010236 --slides slide_004 --temporal output_frames --output outputs/temporal-30fps-NEW
```

使用原evidence/音频绑定/共享播放器，原confirmed音轨不变。模式、时钟、实际时点、对象对、排除来源、逐帧DOM与截图保存到隔离输出。
CLI completed表示执行/来源核对完成，不表示每页通过；真实结论看cases[].temporal.status。
静态失败不进入动态检查；预算不足、未知策略或基础设施失败标blocked，不自动降采样或改为explicit免检。

| 页面 | 采样点 | 承载层修复前重叠记录 | 修复后记录 | 结论 |
| --- | --- | --- | --- | --- |
| slide_001 | 157 | 7699 | 1170 | 仍有矩形重叠待审，未通过 |
| slide_003 | 87 | 308 | 43 | 图表与指向图表的关系箭头被标出，未通过 |
| slide_004 | 73 | 1566 | 0 | 有限采样通过 |

表中是跨采样时点的重复报告数量，不是独立缺陷数，更不是AI成功率。
已实际查看slide_003最终截图：箭头从卡片指向图表内部，矩形检测会标出该关系；不能为使结果通过而直接豁免整个chart/relation对象对。
对slide_001还需逐组核查，不将全部剩余标记判为真实视觉问题。

slide_004进一步按30fps检查501个输出帧/动作边界时点，0问题，frame_complete=true、continuous_time_verified=false、clock=audio_timeline。
此为原确认音频时钟下几何检查，不是音频听审、美感批准或导出成片验收。

完整证据：outputs/capacity-temporal-20261020-v1（修复前）、v2（修复后）、capacity-temporal-30fps-20261020-v1。
三轮source_unchanged与code_unchanged均为true；原课程作者/音频未保存或改写。运行文件不进入Git。

## 验证与下一步

新增真实浏览器DOM回归：0.5倍舞台下透明承载层不误报、路径真正穿过卡片仍报重叠、路径越出内容安全区仍报错。该用例进入pytest，原节点不新增白名单。
新增请求返回/TimeoutError回归：仅调用一次、关联原request_id、保留异常传播、脱敏正文、未知usage/cost不伪造；原失败result.json仍存在。
模板版本和箭头对象对保留断言通过，原28项容量相关首轮通过；最终联合结果见本机.tmp/capacity-temporal-final-tests.log。

下一步应研究“连接到图表的合法端点接触”和“穿过文字/非目标内容”的区分，再定义更精确检查；先保留当前失败及截图，不能扩大无证据豁免。真实模型对照及默认Pi切换仍未开展。
本批代码质量复核与Ruff/git diff --check通过；未提交、未推送。

最终联合测试54项通过（68.11秒），另9项架构/运行保护检查通过；日志为.tmp/capacity-temporal-final-tests.log及.tmp/capacity-temporal-boundaries.log。
