# 未保存候选累计容量求解 0.1.0

2026-10-25；HPS-007/009/010/013/015—018/023—025。现有契约包/API 版本保持；本增量没有新增公开请求字段或数据库结构。

## 所有者与输入

`html_capacity_repair.solve_capacity_candidate` 接收 scene、binding、manual、beats、run_dir、共享检查依赖、取消/来源 checkpoint 和进度回调。它不要求已有作者页，不写作者/批准。候选资源沿原生产事务暂存/回滚，资源仍由原资源加载器验证。

`repair_candidate(..., deterministic_first=True)` 先尝试该求解器；原新页编译后容量失败与组件分配后容量失败均启用。成功继续原保真审核；确定性搜索耗尽或未找到候选时，记录该路径证据后保留旧模型回退。blocked/stale 不进入模型回退。直接调用 repair_candidate 的旧默认行为保持。

## 候选与预算

- 使用原尺寸提示、画布/动作边界、已注册静态操作和手工保护校验。最多 4 个容量目标，不扩大到任意关联对象移动。
- 保留中间候选，允许依次修好两个或多个对象。每层最多保留 4 个状态、每状态最多试 4 个候选；目标及尺寸/字号/行距类型按固定顺序轮转。
- 默认最多 32 次渲染测量（包括基线和严格复验）、4 层搜索、4 次最终检查，共享 120 秒预算。剩余时间传入每次子进程调用；原有进程终止回收可能需要额外时间。
- 候选操作最多 20 项；中间状态不可保存。字号候选保持 24px 下限。实例未显式设置字号时，仅在诊断明确给出公开 part 与实际字号，或对象只有一个公开文字部位时，使用该实测值；不猜多部位的字号归属。
- renderer 给容量诊断补充 `part` 证据；未找到部位时为 null。旧报告仍可读取，纯测量附加字段不改变 scene Schema。

## 检查与状态

诊断渲染的 `passed=false` 不能证明仍有容量缺陷；当 capacityIssues 消除且已有真实几何时，必须运行原严格检查，并通过 preflight_dir 显式接入作者时钟、30fps、registered、完整输出时段及动作边界检查。只有真实完整动态报告通过才返回 candidate/unchanged。

状态区分：candidate、unchanged、needs_revision、budget_exhausted、blocked、stale。`NO_FIT_WITHIN_POLICY` 仅表示本次允许/实际搜索候选未找到通过者，不证明任意布局均无解。当前搜索有分支裁剪，深度/次数/时间/最终检查限额到达时显式 budget_exhausted。

保留每次 scene、report、render、operations 和最终动态报告。通过前比较原 scene/binding/manual/resources 及 resolved_scene_inputs，来源变化不签发通过。生产 checkpoint 继续校验原冻结快照、定义、修订及取消。容量求解源码加入 design definition identity 和 generation snapshot；旧候选按原规则失效，旧作者不自动重写。

## 已保存页兼容

原 capacity_first 单候选策略、指令和公开请求保持；其已有可选 scene/binding 分支现可显式传 manual/beats，不再丢弃保护或强制读取作者页。已保存页仍检查原 revision/audio/source。未把旧编辑器接口静默切成累计搜索。

## 验证与边界

2026-10-25 后续实施：[关联布局与独立原图保真审核](linked-layout-reference-review-0.1.0.md)已接关联列、显式 point 路由与第三检查点。下方“仍按后续任务实施”为首批容量增量的历史边界，当前新增范围及其未验项以后续协议为准。

- `checks/test_html_candidate_capacity_solver.py`：累计两对象、真实保护器、原图/资源来源变化、预算与默认字体、严格动态复验及原模型入口零调用。
- `scripts/benchmark_candidate_capacity.py --output <新目录>`：正常页、两卡片、预算、人工保护四种受控夹具，真实原浏览器检查；现存输出目录拒绝覆盖。
- 相关原候选、容量、生产、设计、快照和提示词回归分别记录于交接。
- 本批不是跨课程真实模型保真验收；关系 point 路由的自动串接、三卡片空间联动、全局预算、独立原图定位及发布默认切换仍按后续任务实施。
