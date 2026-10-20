# 本机固定案例与容量输入优化 · 2026-10-20

## 目标与范围

按发布handoff的优先顺序，建立本机可重复基准并定位容量修复的输入问题。
源目录为`D:\Program Files (x86)\PPT_HTML_Studio`，基于main的00fb81d4和此前未提交的编辑器换行修复。
本批不接续另一台机器的Token unknown请求，不修改课程作者、配音、批准或数据库。

## 可重复运行入口

```powershell
$env:PYTHONUTF8 = '1'
# 选择全新输出目录；存在则拒绝，不覆盖之前的失败证据。
.\.venv\Scripts\python.exe scripts/benchmark_capacity.py --output outputs/capacity-fixtures-NEW
# 本机真实课程内容，独立冻结输入/资源，原页面只读。
.\.venv\Scripts\python.exe scripts/benchmark_capacity.py --source-run runs/ec60bbd4_010236 --slides slide_001 slide_003 slide_004 --output outputs/capacity-course-NEW
```

版本化夹具在`checks/fixtures/capacity-baseline/`：普通页、超大字号文字页、长关系摘要页。
共享凝结教学场景，保留完整原文；关系页保留11个显式动作及准确来源的测试语块绑定。
这些是合成压力变体，不冒充真实模型生成课程。固定scene的hash随清单保存；修改案例须显式更新清单，旧输出不改写。

真实内容基准从本机冻结结冰课程三页：19对象/18动作、8对象/6动作、11对象/11动作，覆盖多关系、图表及三阶段结构。
资源、当前scene/binding和讲稿复制到新输出目录；不复制人工批准、历史作业或凭据。输入文件hash在复制时与完成后核对。
模型为null、provider_calls=0、usage/cost=null；本批没有授权或发起付费模型实验。
真实课程模式完成表示取证完成，不代表所有页面通过；逐页strict_passed是独立结论。

两种模式都记录HEAD和已跟踪工作树字节hash（含本工具/夹具的首次未提交版本），不只记录Git提交号。
严格检查、诊断、实际截图、容量triggers及测量落盘；离线压力修复另存实际出站请求、图片hash、原180秒预算、实际补丁和重验。
离线补丁来自明确的夹具答案，不是模型自主决策；不能用这些成功率或耗时评价Legacy/Pi或推算token费用。

## 定位到的输入问题及修复

关联HPS-010/013/015/017，按仓库optimize-prompts技能追踪`repair_candidate`实际system/user/图片、注册操作解析、原candidate预览和浏览器消费者。

1. 同一对象有多个canvas_px盒宽/高触发项时，旧循环保留最后一项，较小的后项可能覆盖较大的要求。现在按所需外尺寸取最大值，和诊断顺序无关。
2. 旧geometryConstraints只按当前尺寸/变体下限计算，与capacitySizeHint推荐的扩高尺寸脱节。现在用同一份尺寸提示计算动作全过程的安全偏移。
3. 旧feasible只检查画布，不检查公开偏移±400及宽高工具范围。现在取交集，避免把需要offsetY=-460之类的建议写成可行。false仅表示当前建议不可行，不证明没有其他排版解。

没有把css_px滚动/文字边缘或行数直接当canvas_px；没有静默扩时限、缩减推理/输出预算、自动应用补丁或放宽校验。runtime片段、操作Schema、API1.59.0/合同包0.9.108保持。
更新原归属合同、索引和CHANGELOG记录兼容修复；原源码快照已包含html_candidate_agent.py，工作树变化沿原hash当前性守卫处理。

## 实际结果与局限

- `outputs/capacity-baseline-20261020-v1`保留首次关系案例因夹具缺显式binding而失败的记录，不覆盖。此为评测装配错误，不算模型失败。
- 补齐来源绑定后的v2：普通页初检通过、0次离线决策；文字页初检因2行>1行、scrollHeight224>48及文字底边超限失败，一次指定字号补丁后重验通过；关系页因scrollWidth431>400失败，一次指定term样式补丁后重验通过。
- v2三例分别约2.94/4.728/4.624秒，包含本机浏览器开销且与回归并行，只作执行记录，不作为性能排名。原文、节点身份、动作、来源绑定保持。
- `outputs/capacity-real-course-20261020-v1`：三页静态严格检查均通过，无当前容量问题；源输入和执行期间代码hash保持。原课程未保存或批准。
- 已查看关系页最终截图：工程容量通过仍不代表字号层级、美感或逐句动态通过；本轮没有用户视觉签收、30fps逐帧验收或音频听审。
- 相关原回归首轮66项通过；最终测试和完整证据路径追加在下节。

## 后续决策

现有三页均无容量失败，不能据此解释另一台机器的180秒超时。已证实的是输入推导的三个边界问题，尚未证明真实模型成功率或耗时改善。
下一轮应在新任务/新身份下使用同一冻结材料和明确模型预算进行Legacy/Pi对照，分别统计理解、容量、截图审核和未知结果；不能把本批离线答案送入模型输入或重发原未知请求。
本批源码仍未提交/推送，也未启动正式应用服务。

## 最终复跑与证据

`outputs/capacity-baseline-20261020-v3/summary.json`三类全部达到预设离线工程目标，执行期间工作树hash不变。每例单独保留initial.png和offline-final.png，既有layout-agent逐轮请求/诊断/response留档；本次约3.000/4.733/4.886秒，仅是本机并行测试执行记录。

额外以真实普通结冰页`runs/c16bc2b3_203534`冻结验证，`outputs/capacity-ordinary-course-20261020-v1/summary.json`严格容量通过，source_unchanged=true；与前述三页复杂课程合计4页真实内容，均未调用模型。

最终相关回归见`.tmp/capacity-final-tests-v2.log`；Ruff和git diff --check通过。原83项之后增加实际出站请求断言，最终84项全部通过，耗时54.14秒。完整全库2775项是前一批编辑器修复的结果，本批不重复宣称全库已验证当前变更。

代码质量复核：容量计算仍归原candidate owner；没有新renderer、业务存储或依赖；真实课程只读复制，路径限制与1GB总量/128MB单文件预算，评测新目录拒绝覆盖。差异保持原生成/保护/严格编译器入口。
