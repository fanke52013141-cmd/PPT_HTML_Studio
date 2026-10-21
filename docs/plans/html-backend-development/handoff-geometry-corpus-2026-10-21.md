# 几何扩样、真实模型回退与跨机材料 · 2026-10-21

基于main `015139b`继续本地开发；包0.9.113/API1.60.0保持。未提交、推送、重启或部署。用户授权推进发布handoff的前三项，并说明原四页课程保存在另一台电脑。原课程没有迁移到Git；本机不伪称复现`runs/ec60bbd4_010236`。

## 已实现与兼容边界

- `html_geometry_repair.py`内部实现0.1.1：无显式端点的注册槽位线性箭头复用原SVG解析，包括箭头头部/描边，仅移动被穿文字。同一对必须有实际穿字证据；该对其他时刻的非文字接触继续受检，独立其他碰撞停止。单对象有限候选、scope、人工保护及6次sampled/3次完整检查预算保持。不新增多对象联合搜索、CSS、字号调整或规则豁免。
- `overlap-policy.json`补登记`explanation-labeled-v1@0.1.0`的既有figure/subject、figure/anchor-label容器关系。marker、relation及真实穿越无额外豁免，旧候选的真实问题仍报告。
- `scripts/benchmark_capacity.py`隔离复制保留`revision.json`与选中页`edits-*.json`，动态检查读取原修订；此前丢弃人工保护的隔离结果不能视为已验证保护。
- `scripts/evaluate_geometry_corpus.py`接收明确来源的host-only清单，原页、历史候选、受控扰动及fixture分开统计。course/page去重；同页不同候选不增加独立页面数。缺讲稿/绑定/资源记录blocked。默认零供应商；显式`--live-case`至多一个案例、两次物理调用，共用总等待预算。unknown落盘且不重放。不保存作者/批准。
- `scripts/geometry_case_bundle.py`标准库独立工具，白名单导出作者scene/binding/revision/人工保护/visual_contract、资源与选中页已有TTS文件；不导出数据库、模型配置或批准。导入在写入前验证路径、重复项、数量/字节预算和全部hash，只允许新隔离目录。

关联HPS-007/009/010/013/015—018/023—025。字段/API兼容，无迁移；原候选/QA的源码或策略hash变化后必须重新检查，历史批准不转移。

## 本轮实际证据

`outputs/geometry-corpus-20261021-v1/`包含五项清单和原结果；另一个主线扰动在`outputs/geometry-mainline-20261021-v1/`。只涉及三个历史页面身份、三个课程主题，其中两项来自历史模型候选、一项为人工还原样页。三种扰动都来自同一蒸发页，不是新增三个课程；原正式课程/新独立真实故障页扩样仍等跨机材料。

| 输入 | 来源/检查结果 | 解释 |
|---|---|---|
| 遴选正式定义 | 10月17日真实模型诊断scene/binding；540时刻，保留needs_revision | 多种标签/图片/非文字穿越，不是纯箭头文字任务，不发模型强修 |
| 蒸发原页 | 10月12日真实模型runtime_skill结果；473时刻，unchanged | 正常对照保持原样 |
| Token历史样页 | 人工还原；原绑定引用讲稿缺失，BEAT_GONE/blocked | 不编造讲稿或音频补成“成功” |
| 蒸发主线穿字扰动 | badge-1(-200,100)；几何改offsetY为148；473时刻通过 | 5次sampled、1次完整检查；几何33.898秒，0模型调用 |
| 蒸发标签/标签扰动 | badge-1(-118,48)，与另一badge独立重叠，needs_revision | 不把多种碰撞冒充纯穿字 |
| 蒸发双标签穿字扰动 | badge-1(-118,48)、badge-2(-118,24)；无单对象几何解 | 进入原geometry_first真实回退，两标签offsetX改为-18；473时刻通过 |

两个通过候选都只改变presentation位置，原文字、样式、动作和binding保持；候选生成后作者、源文件及当时工作源码hash不变。后续本机两个旧CRLF文件转回发布manifest要求的准确LF字节，重建编辑器，再用最终代码零模型重新preview两候选，均473时刻通过。当前候选和截图在`outputs/geometry-final-review-20261021/`，不是旧key沿用。没有save或批准。

真实回退使用本机原绑定`glm-5.3-flash`，thinking enabled、65536、温度1.0及原推理设置；1次物理请求，137.045秒，输入13841/输出6890/总20731 tokens，reasoning6839，费用null。整个案例184.205秒，含原几何/完整复验。没有重试或unknown；这是受控扰动上的真实模型路径成功，不是新课程自主生产成功率、执行器排名或人审批准。

已实际查看原蒸发页、遴选问题页、几何与真实回退前后同一时刻截图。模型回退后两标签移到箭头右侧，穿字解除；审美、真实旁白/音画与用户接受仍pending_review，未做正式输出。报告及媒体在本机outputs，不进入Git。

## 另一台电脑如何接续

本机已生成可直接复制的`outputs/geometry-transfer-kit-20261021.zip`，内含独立脚本、README和脚本hash。把工具包复制到保存课程的电脑，等课程停止编辑，在那台电脑实际checkout根执行（工具包路径含空格时加引号）：

```powershell
.\.venv\Scripts\python.exe <工具包路径>\geometry_case_bundle.py export --source-run .\runs\ec60bbd4_010236 --course-id token-course --case slide_001:obj-anchor-label --case slide_003:obj-card-2 --case slide_004:obj-header --output .\outputs\geometry-source-20261021.zip
```

导出两张已知故障原页和一张正常原页；仍只是一份课程。不要把历史机器的绝对checkout路径照搬到新机器。若原run已换名，使用当前实际路径；缺原作者scene会明确停止。其他课程的新问题应另导出独立course-id/slide/scope。

把输出ZIP通过共享目录/文件传输送回本机，核对导出打印的SHA256后：

```powershell
.\.venv\Scripts\python.exe scripts/geometry_case_bundle.py import --bundle <收到的ZIP路径> --output outputs/transferred-token-course-20261021
.\.venv\Scripts\python.exe scripts/evaluate_geometry_corpus.py --spec outputs/transferred-token-course-20261021/cases.json --output outputs/transferred-token-evaluation-20261021
```

默认不调用模型。依据无解报告，在新输出目录对明确的新案例选择`--live-case page-1`才真实回退；旧unknown先核实，不通过换目录重发。脚本不连接其他电脑或自动发送文件；目前没有远程电脑的连接，因此原课程独立扩样还没有执行。

## 验证与下一步

- visual构建、动态策略、SVG线段与实际DOM向量几何检查通过。
- 新跨机边界、来源分母、物理预算、原保护及几何/组合入口与快照回归最终**48 passed**，39.19秒，`.tmp/geometry-corpus-20261021-regression.log`。
- 首次扩展到快照的回归36通过/12失败，定位两个继承的CRLF工作字节与发布manifest不符；仅转换LF即可匹配原hash。未手改manifest或放宽校验。修复后编辑器构建和**17项**测试通过，最终48项通过。
- canonical quick通过，`.tmp/geometry-corpus-20261021-quick.log`；Ruff及`git diff --check`通过。未运行本批canonical full，不替代远端CI。
- 新增单测第一轮有两项测试自身问题（异常类型、输出目录落在源下），修正后通过；没有移除隔离检查。

接下来先回传包，再用新独立课程补充真实故障/无解/正常页分母；收集多对象无解分布后再决定是否定义联合搜索。当前已验证多对象模型回退可用，但不能因此立即更改默认执行器、扩大自动保存或将当前候选视为用户批准。
