# 统一流程评估清单交接 · 2026-10-15

承接 [执行证据优化](handoff-workflow-agent-evidence-2026-10-15.md)。本批将已有流程事故回归接成统一、可反复运行和比较的入口；不继续打磨页面，也不调用真实模型/生图服务。

## 使用

```powershell
# 只查看 18 项清单
.venv/Scripts/python.exe scripts/evaluate_html_workflow.py --list --out outputs/unused

# 建立基线：目标必须是 outputs 下的新目录
.venv/Scripts/python.exe scripts/evaluate_html_workflow.py --out outputs/workflow-eval-baseline

# 后续开发后，同一清单与历史结果比较
.venv/Scripts/python.exe scripts/evaluate_html_workflow.py --out outputs/workflow-eval-after --baseline outputs/workflow-eval-baseline/report.json
```

如本机未安装 Playwright 默认 Chromium，共享解析器可选择已安装的 Edge/Chrome；也可按现有机制设置 HPS_CHROME 为真实可执行文件。显式失效路径不会被绕过。

[固定评估定义卡](../../contracts/html-presentation/runtime/visual-v1/workflow-evaluation-0.1.0.md) 提供 18 项表格；可执行来源为 `checks/fixtures/html_workflow_evaluation.json`。调用、复用、路由、停点、作者和批准六项预期独立记录；证据类型区分纯函数、模型替身、故障注入和真实浏览器。

## 实现边界

报告不会把预期调用数当生产实测，不推断 token/费用，测试耗时不能证明模型变快。每项映射明确测试选择器与参数数量；未收集、跳过、失败或执行器异常都不能通过。只读展示案例使用真实浏览器和替身 API；容量预算案例显式注入诊断/编辑，不能据此声称真实模型会改善排版。

子进程数据库/runs 强制隔离，输出不可覆盖；未导入 server 或触碰真实任务。新增执行器自身的失败关闭测试，覆盖参数漏跑、失败/跳过、基线不匹配及历史输出保护。当前生产接口/模型策略保持，无需重载应用服务。

## 运行记录

首次接线运行：26 个 Python 参数项通过，浏览器测试因旧硬编码 Chromium 路径启动失败，报告正确显示 17/18，原始失败证据保留于 ignored `outputs/workflow-evaluation-20261015-baseline/`；该次清单尚未固定参数项数，不作为最终基线。随后将该浏览器测试接到既有共享解析器，并固定每个检查的参数数量，最终结果补记如下。

- 正式基线：ignored `outputs/workflow-evaluation-20261015-v1/report.json` / `report.md`，**18/18 通过**；Python 参数项 **26 通过**（56.00 秒，执行器含启动开销为 58.098 秒），浏览器进程通过（2.975 秒）。具体 pytest 内部耗时以原始日志为准。
- 同清单复跑：ignored `outputs/workflow-evaluation-20261015-repeat/`，**18/18 通过**，Python **26 通过**（52.25 秒），比较结果为 regressed=[]、recovered=[]、unchanged=18 项。此结果证明本轮同清单重复执行保持通过，不是模型速度提升。
- 评估器自身 **4 项通过**：参数缺失/失败/跳过不能通过、同清单比较门禁、非法基线执行前拒绝、历史输出目录保护。Ruff、JS 语法、清单与契约 JSON、Agent 生成矩阵和 diff 空白检查通过。
- 真实数据库只读复核仍为项目 1、active_jobs=0；应用没有重载、写入或续跑。没有新增真实供应商调用。现有 Starlette/anyio 弃用警告保持。

## 后续

最小真实供应商案例已执行至独立审核并停止：见 [遴选考试真实案例](handoff-live-linxuan-2026-10-15.md)。离线18项通过未覆盖审核色彩/语义文字职责冲突、真实长时思考与父子协作停止状态；真实还原没有通过，不追加为离线通过项。

未来改动先跑同一清单，检查 regressed/recovered 和对应原始断言；变更场景数量或预期行为时建立新清单基线，不改旧报告。若需要评估真实模型时延、冗余输入或理解准确率，另建最小供应商实验；离线全绿不是整课、语义或视觉验收。

2026-10-15 后续：清单0.2.0扩展20项/43个Python检查与浏览器验证，通过20/20；新增依据/语义归属/实际能力/等待规则。另用原遴选案例真实系统Agent复验，详见[修复交接](handoff-design-review-fix-2026-10-15.md)。旧18项报告保持，不跨清单计算改进率。
