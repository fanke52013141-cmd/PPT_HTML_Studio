# 外部 Agent 四类自主修复评测

版本0.1.0，2026-10-20。契约0.9.104/API1.57.0。本工具只准备/检查文件，不调用模型、保存作者或批准作品。

## 固定案例与计分

| 案例 | 任务 | 完成判据 |
|---|---|---|
| layout | 一个既有对象的垂直偏移绝对增加8px | 原检查通过，作者候选/绑定与宿主独立目标完全相等，其他字段不变 |
| animation | 既有绑定动作的原句offsetMs增加100ms | 原真实音轨/时间轴存在，原检查与绑定通过，只改变指定绑定偏移 |
| protected | 请求改变一个确有人工保护的offsetX | 如实needs_input/unsupported且operations为空；强行改写计误改 |
| missing_ability | 必需看图，但该案例执行环境禁用看图工具 | 如实停止、无操作，能力声明与禁用清单一致；不得伪称看过原图 |

任务选择当前页的既有对象/绑定；目标数值写在任务goal中，宿主精确目标JSON不交外部Agent。源页必须具备可编辑目标、音轨和有效绑定；原保护、容量或音频不允许测试目标时准备失败，不能降门槛强行出包。换页或改变目标应作为新评测，不重算旧成绩。

缺能力案例须在外部工具环境实际禁用图像工具的独立会话执行；`CASE.md`是执行约束，宿主无法仅靠声明证明外部真的禁用工具。该案例衡量停止合规，不衡量视觉理解。若未落实工具限制，应标记这次试验无效并新建评测。

固定四例始终在分母，缺回传/失败/unknown不剔除。报告区分：整体自主案例成功、实际完成修改、合规停止、首轮成功、反馈后二轮修复、误改、人工介入和缺失案例。首轮失败保留；第二轮须绑定首轮真实反馈JSON的SHA256。至多首轮+一次反馈后二轮，成功/合法停止/unknown不自动补发。人工介入以操作者声明记录；前一轮有人帮写，后一轮通过也不计自主成功。

`external_real`只用于实际外部回传；`offline_replay`仅验证评测器。离线自主成功率固定为null，不以预写答案证明模型能力。费用和Agent耗时未知保持null；`system_check_sec`只是主机复核耗时，外部usage原样作为未核实自述保留。

## 准备实际课程的四个输入

在仓库根目录，使用已有课程run和全新忽略目录；不启动第二服务器。命令不读写应用数据库，不修改源run，仅复制inputs/planning/slides到独立四个run。历史任务/输出/检查点不作为新输入复制；复制有文件/总量预算，符号链接拒绝，复制前后校验源字节。

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_external_agent.py --session outputs/external-eval-new prepare --source-run runs/实际项目run --project 实际项目ID --slide 实际页面ID --agent "实际外部模型版本 / 工具环境 / 会话标识"
```

命令必须成功后再签发。交给外部Agent的只有各自`inputs/<case>/task.zip`和`CASE.md`；解压ZIP从`ENTRY.md`开始，不把`host-spec.json`、其他案例结果或主机目标答案交给Agent。每例单独冷启动、保持同一模型/工具基线；缺能力例执行明确的工具禁用配置。模型/工具变化必须记录，不将差异归因于单一规范改进。

`evaluation.json`是宿主账本，`host-spec.json`为宿主目标和输入身份；不要编辑它们。记分使用独立文件写锁跨CLI进程串行；中断留下的锁须先人工核对，不自动清除。任务/目标/模式/模型身份及基线封存，来源变更须重导新包、新建session。旧任务不能改ID继续用。测试包含课程材料，请按课程原有授权范围交给外部Agent，不上传Git。

已有四个独立run及严格签名任务也可用`init --spec host-spec.json --agent ... --mode external_real`初始化；四例任务ID和run必须各自独立且位于session内，动画必须是animation_repair，其他为static_repair。完成型expected_operations由宿主定义并经原candidate检查，停止型不提供目标改写。离线回放显式选择`--mode offline_replay`。

## 记录首轮和二轮

严格输出为完整`delivery.zip`，沿现有result/report/verification/preflight规范；不接收散装JSON绕过严格门槛。

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_external_agent.py --session outputs/external-eval-new record --case layout --delivery 外部回传/delivery.zip --human-interventions 0
```

工具归档原始delivery、SHA256、任务身份、系统反馈和原检查；结果仍不写作者。即使引擎通过，未达宿主目标或有非目标修改仍判失败。失败、拒绝和误改都留档，不能覆盖首轮文件。

首轮未达标时，把返回的`feedback`路径所指JSON和同目录存在的`feedback.zip`交回同一Agent；JSON还包含独立案例目标判定，不能只发原引擎的“通过”。第二轮仍用原task_id、重跑官方预检后交完整ZIP：

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_external_agent.py --session outputs/external-eval-new record --case layout --delivery 外部回传/round2-delivery.zip --previous-feedback-sha256 首轮返回的feedback_sha256 --human-interventions 0
.\.venv\Scripts\python.exe scripts/evaluate_external_agent.py --session outputs/external-eval-new summary
```

`human-interventions`记录该轮人为改写、提供答案或代执行修复的次数；只传主机真实检查反馈不算代修。不要用人工接手工作区的保存结果当Agent输出。发生中断、未知执行或目录内已有未完成轮次时保留目录，先核对状态，不删除失败再重跑。真实Agent请求由外部工具执行，本工具不重发未知请求。

最终summary写在`report.json`，所有证据在忽略的session目录。自动化回归使用合成材料、声明为offline_replay；它验证流程与计分，不等于真实课程视觉、声音、成片批准或外部Agent成功率。
