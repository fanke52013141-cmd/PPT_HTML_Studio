# 关联布局、生产接线与原图定位审核交接 · 2026-10-25

## 本批结果

用户要求的工程顺序已落实：补齐受支持的关联布局、原关系避让和第三生产检查点，再将独立原图定位与逐对象证据接入生产保真审核。真实跨课程定位/保真质量、人审和部署仍是独立未验项。

基线为本机 `0a9d27c` 加前批未提交容量优化；本批继续在同一工作树实施，不覆盖既有编辑器 manifest 修改，未提交、推送或重启正式服务。

## 具体变化

| 能力 | 实现 | 边界 |
|---|---|---|
| 关联列布局 | 原注册同列 2—3 张卡片与一个底栏，冲突后的对象按合法间距向下联动 | 最多4对象；不改文案、尺寸、横向位置或动作；空间不足明确停止 |
| 显式关系避让 | 复用原 point 附着点求解与原 vector/全帧 QA | 不更换关系对象、方向或 anchorId；不是自由重绘箭头 |
| 生产接线 | 编译后、分配变体后、还原操作后三个检查点共享确定性入口 | 第三个入口不新增模型修复轮数；失败仍保留原反馈和停止 |
| 原图定位 | 仅给原图、准确文字身份/路径及尺寸，增加卡片正文；端点当前坐标不进入定位请求 | 首版精确定位文字/容器；图片主体和关系继续整图审核 |
| 配对证据 | 原图用独立定位框，HTML用真实对象框；整图＋最多两张重点对照板 | 框保持模型建议；缩放/裁切范围明确，不能当作者坐标 |
| 不确定处理 | ambiguous/not_found/HTML几何缺失停止到 evidence_review | 不猜素材失败、不自动重试、不自动批准 |
| 定位复用 | 同图、同准确目标、同定位版本时复用，明确记录源 scene 与新候选关联 | 内容、范围、版本改变重新定位；不改写原模型观察 |

新增 `html_linked_layout.py` 为关联布局/生产修复所有者；原 `html_capacity_repair.py` 继续拥有容量搜索。`html_design_agent.py`、`html_reference_localization.py`、`html_review_evidence.py` 分别承担审核编排、独立定位和配对证据，未新增渲染器。

新增审核片段 `design-fidelity-review/1.1.0`，内部 input0.4.0/facts0.1.0；旧直接审核默认1.0.2与旧窗口实验保持。真实运行 fragment/hash、实际消费者、原保护/返回校验及生成/设计来源闭包同步；定位请求单列 reference_localization 用量，不增加原共享模型预算，不估算未知费用。

## 已执行验证

- 新旧还原、设计审核、独立证据、关联布局、容量、运行片段和计量组合：109 passed，179.31秒。
- 参考定位/正文部位/容器/跨版式/旧证据/runtime/计量组：137 passed，29.72秒。
- 快照、任务恢复、生产阶段、设计复用与计量组：74 passed，262.09秒。
- 第三生产检查点及两个调整后的保真回归专项：3 passed，38.77秒；其中真实浏览器容量恢复继续保留原 motion/binding。
- 关联布局专项：6 passed，29.62秒，包含实际人工叶字段保护阻断。
- 上述组有重复，不相加为独立用例数。定位/保真模型响应使用明确替身，只证明请求、消费者与停止合同。
- 本批没有调用真实模型/图片供应商，没有写用户作者页或批准。

完整命令输出及 JUnit 在 `outputs/linked-20261025/`；快速检查和最终小范围复测结果随 `delivery-summary.json` 汇总。

## 可重复的浏览器验收

`scripts/benchmark_linked_layout.py` 已实际执行，三个受控用例全部通过，证据在 `outputs/linked-20261025/acceptance-v1/`：

| 用例 | 结果 | 原完整动态检查 |
|---|---|---|
| 三卡片＋底栏 | 联动后 candidate，几何阶段1次复验 | 563个输出帧/动作边界，问题0 |
| point关系穿字 | 原关系身份保持，避让后 candidate | 366个输出帧/动作边界，问题0 |
| 人工锁定下游位移 | needs_revision，保留原稿 | 原缺陷保留，不越过保护 |

几何阶段观测耗时分别4.785秒、3.198秒、0.112秒；不包含前置容量检查，不是整页机器耗时或供应商延迟，不据此推导真实课件生产速度。

每例保存 input-scene/input-binding、before/after、操作、来源、逐步审核和原 temporal 报告。上述图文来自版本化受控夹具，不能作为真实课程成功率分母。

```powershell
Set-Location -LiteralPath 'C:\Users\Administrator\Desktop\html动画\PPT_HTML_Studio'
New-Item -ItemType Directory -Path outputs\linked-tmp -Force | Out-Null
$env:TEMP=(Resolve-Path outputs\linked-tmp).Path
$env:TMP=$env:TEMP
.\.venv\Scripts\python.exe scripts/benchmark_linked_layout.py --output outputs/linked-acceptance-new
.\.venv\Scripts\python.exe -m pytest checks/test_html_linked_layout.py checks/test_html_independent_review.py -q --basetemp=outputs/linked-tests-new
```

输出目录使用新名称；Windows 冻结页面路径应保持较短，系统临时目录无权限时使用上述隔离目录。没有通过降低 QA 或跳过浏览器处理这些环境问题。

## 原图审核验证的实际含义

受控测试使用在不同坐标绘制的同一文字，核验原图裁切与HTML裁切实际不同、无当前坐标泄漏、相同目标的第二轮不重复定位、换准确文字后重新定位且原图没有该文字时停止。正文 body 是必需路径，不能只用标题替代。

本批尚未度量真实模型的漏检率、误配率、跨课程泛化或用户接受率。大幅位移的输入合同通过，不等于模型真实识别能力已通过。真实样本应沿原生产接口冻结并单独配对评估，不把此处替身结果加入真实模型分母。

## 与完整方案的关系

当前明确的“关联布局和三处生产接线”已完成受支持范围的工程实现；T06/T07 也已有生产接入及受控验证。完整计划仍保留未完成项：真实跨课程留出集、更多版式/多主体定位、素材能力预检、全任务预算/供应商恢复完善、人工接受、完整音视频交付与默认发布验收。不能据本批将完整 M1/M3 的69条验收全部标通过。
