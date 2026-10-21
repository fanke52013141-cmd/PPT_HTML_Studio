# 问题发现与固定样本优化交接 · 2026-10-21

## 当前任务与发布范围

用户目标是发现、复现和减少系统性漏检，不是逐页手工修好课程。下一位接手者先读根README、本文件、[系统问题台账](system-issues-2026-10-21.md)、[固定样本评测](feature-recognition-benchmark-2026-10-21.md)，再进入对应契约。

本批从main基线`015139b42e677468ca380228dfbffe23b5592554`续进，统一提交此前本机几何扩样、真实课程试验、生产前置检查、规划与理解诊断、逐对象观察以及相关测试/契约。唯一仓库为[fanke52013141-cmd/PPT_HTML_Studio](https://github.com/fanke52013141-cmd/PPT_HTML_Studio)，只向origin/main正常推送，不向原图片项目发布，不force push。提交与远端回执见本文件末尾；各专项文档中“未提交/未发布”是当时状态，以末尾回执为准。

契约包0.9.113、Agent API1.60.0保持，无数据库迁移或公开API变更。理解运行片段最终design-understanding/0.7.5、内部输入输出0.3.0；还原程序Prompt0.6.2、运行片段design-reconstruction/0.7.4；规划Prompt0.3.6。默认Legacy保持，未替换图像/TTS/数字人服务，未自动签发任何人工批准。

## 已实现内容与所有者

| 范围 | 实现与证据 | 接手文件 |
|---|---|---|
| 几何预筛及扩样 | 槽位线性箭头支持与数值筛选；隔离评测保留revision/人工保护；区分原页、扰动、正常/不支持案例 | html_geometry_repair.py、scripts/evaluate_geometry_corpus.py、scripts/geometry_case_bundle.py、scripts/benchmark_capacity.py |
| 正文溢出与箭头穿字前置 | 原Range测量父卡片四边，原30fps/registered检查在每轮还原前后执行；unchanged不能清除工程失败；容量失败先保留诊断 | html_engine/visual/renderer.cjs、capacity.cjs、html_visual_review_service.py、html_design_reconstruction.py |
| 规划反馈 | 非法对象/槽位/端点及coverage反馈包含字段路径、合法ID和差集，不改变严格拒绝及原预算 | html_course_structure.py |
| 还原输入 | 每轮原设计＋当前HTML双图，不再首轮只发送参考图 | html_design_reconstruction.py、config/html_runtime_skills.json |
| 插图与图标边界 | card仅注册图标、figure是代码容器；实际独立图片能力不能凭名称或appearance推断 | html_design_policy.py、html_design_agent.py |
| 完整逐对象观察 | ready/unsupported均保留每对象present/absent/uncertain＋短证据；程序派生组件缺口；已有image不能重复归给外框/标题/标注 | html_design_agent.py、html_runtime_skills.py、design-understanding-0.7.5.md |
| 审核/观察不确定 | 缺/重/未知键走response_repair；真实不确定走evidence_review，绑定hash、保留原响应，零自动重试；结构错误仍至多一次合法修复 | html_review_facts.py、html_design_agent.py |
| 固定标签与漏检评测 | 原图、对象、标签hash封存；原模型与程序派生分别计分；旧Schema缺新字段不算FN，unknown/模糊/来源分母明确 | scripts/evaluate_feature_recognition.py、checks/fixtures/feature-recognition-labels.json |

影响HPS-010/011/013/015—017/023—025/035—037，工程动态检查另含HPS-009。定义见[能力事实](../../contracts/html-presentation/runtime/visual-v1/design-agent-facts-0.1.0.md)、[设计还原](../../contracts/html-presentation/runtime/visual-v1/design-first-reconstruction-0.1.0.md)、[首轮审核](../../contracts/html-presentation/runtime/visual-v1/first-review-coverage-0.1.0.md)、[几何修复](../../contracts/html-presentation/runtime/visual-v1/geometry-repair-0.1.0.md)。未新增任意CSS、第二渲染器或宽松保存路径。

## 真实效果与限制

### 固定三图识别

同一水循环课程三张图，11个固定目标：4插图正例、6图标负例、1云雨模糊项不计确定分母。标签是assistant_visual_review，不是用户人工签收或独立留出集。样本未送入模型的标签字段，图像/原对象/标签hash保持。

| 指标 | 历史0.7.2 | 前一版0.7.3 | 最终0.7.5 |
|---|---|---|---|
| 显式插图识别 | 旧Schema不适用 | TP0、FN2、正例未决2 | TP4、FN0、未决0 |
| 图标负例 | 新字段不适用 | TN6、FP0 | TN6、FP0 |
| 系统能力缺口拦截 | TP0、FN2、TN8、FP0 | TP2、FN0、TN8、FP0 | TP2、FN0、TN8、FP0 |

0.7.5完整返回38条逐对象观察，但固定标签只覆盖11项；其余27项没有固定gold，不能声称全正确。中间0.7.4虽在已标注目标得满分，却把第3页图片容器也算独立插图，造成误拦，已保留失败证据；0.7.5在同例不再误拦，不事后改标签美化成绩。

0.7.5原模型把第4页问题requirement写成asset_identity：严格原模型typed缺口指标仍有2正例未决。程序依据present观察与组件事实追加unsupported_presentation后正确拦截，两个分母明确分开，不能冒充模型分类准确。最后优化两轮共7次HTTP均完整返回，无unknown；最终轮3次、47.213秒，usage/费用未采集为null。前一版0.7.3独立3次另记，不能把计分器provider_calls=0当成整个实验零调用。

样本和报告只在本机outputs下：

- feature-recognition-fixed-20261021/dataset.json，hash `aafd793d6c648ea6b083935a233e2ab96a3e0eeb7103231cdc7657742ffeeb6e`。
- feature-recognition-baseline-v2-20261021/：有效历史基线；较早baseline未区分旧Schema，不能用于结论。
- feature-recognition-new-20261021/：0.7.3实际请求/响应及调用记录；feature-recognition-v073-rechecked-20261021/：新版计分器重放，原分数不变。
- feature-recognition-observed-20261021/：0.7.4失败及一次结构修复；不得覆盖或混入最终分母。
- feature-recognition-observed-final-20261021/：0.7.5请求/响应、capture-summary.json、comparison.json；dataset hash `9eea529ccfd73f73cffebbb1c2642286579a47f4ffcdf03f08a284469f25a224`。
- feature-recognition-observed-final-score-20261021/：原响应评分。comparison.json另含程序派生评分，并验证当前代码重演与运行结果一致。

### 其它真实证据

详见[工程前置](handoff-production-preflight-2026-10-21.md)、[几何扩样](handoff-geometry-corpus-2026-10-21.md)、[课程试验](handoff-water-cycle-trial-2026-10-21.md)、[规划诊断](handoff-planning-diagnostics-2026-10-21.md)。新课程第2—4页仍没有通过完整还原，作者保存0/3。第3页三卡片约16.65 CSS像素底部溢出被拦；第4页540时点发现3组穿字。拦截正确不等于模型能自动修复，更不等于视觉/声音/导出通过。

受控双标签几何无解案例真实模型回退通过473时点；仍不是另一台电脑四页正式课程的自然无解独立样本。`runs/ec60bbd4_010236`不在本机，不能宣称已复现该正式课。

## 必须保留的未解决项

1. 模型问题类型一致性与跨课程泛化未解决；不能把一门开发课的0漏检推广为总体性能。
2. 固定标签尚未完整覆盖容器/标注/所有对象，需要发布新标签版本补覆盖；旧已测集不可变，不能看完结果再修改同一标签。
3. 正文溢出与穿字已加强检测，但无真实新模型修复通过证据；原手工结构保存接口没有新增浏览器门禁。
4. 本机课程第2页素材提交和第4页自然故障回退unknown保留，禁止换目录/模型/任务ID盲目重发。新识别实验正常返回不能反签旧unknown。
5. 默认GPU截图像素一致性问题仍存在，原检查器同输入也复现；不放宽该测试。正式软件合成捕获和交互GPU像素是不同验证状态。
6. 新课声音、音频绑定、逐句语义、作者保存恢复、完整输出未验；人工设计接受不等于HTML或正式输出批准。

## 后续开发优先级

1. 扩充未曝光的不同课程/布局，分别标注独立插图、图标、容器、标签及模糊项。另建标签/数据版本，不用同页扰动充当多门课程。
2. 将正文溢出、箭头穿字纳入冻结样本评测，包含真实正例、贴边但合法、端点接触、密集关系等负例，测漏检/误报/未决和检查耗时；依据盲区改检测，不以手修本例作完成标准。
3. 在完整观察基础上核验模型问题类型，保留确定性组件事实与类型派生；不要通过扫描自由文字猜测或削弱能力约束刷分。
4. 独立推进供应商提交回执/原ID查询与unknown恢复；先确定供应商支持的查询能力，再设计恢复路径。没有证据不自动重发。
5. 达到上述验证门槛后，才继续真实课程作者保存、声音/绑定、语义签收和正式输出；默认执行器变更另验。

## 换机与本机接续

Git仅包含源码、契约、测试、标签定义、handoff和发布备注，不含data、runs、outputs、模型凭据、数据库、课程图像/音频/视频或node_modules。因此另机拉代码后不能直接重跑本机三张图的真实评分；可先跑版本化受控tests。若要复现实图，须安全另行移交完整封存样本并核验上述hash，不能生成近似图冒充原图。几何材料可使用版本化geometry_case_bundle工具白名单导出/导入；识别运行材料没有自动云同步服务。

在实际checkout内保存已有工作后：

```powershell
git fetch origin
git merge --ff-only origin/main
.venv/Scripts/python.exe scripts/run_checks.py --level quick
npm --prefix html_engine run build:visual
```

已有依赖先核验，不自动重装；Python3.13/Node22.19或兼容高版本及Playwright Chromium安装步骤沿[前次发布](handoff-release-2026-10-20.md)。依赖缺失按锁文件安装，不启动另一份桌面/便携构建。

本机程序尚未重启，CLI测试直接加载新版源码；Git同步不等于应用部署。重启前确认原进程及任务状态，只运行一个实例，勿指向原图片项目数据。以下路径必须从当前checkout派生：

```powershell
$env:PPT_STUDIO_HOST = '127.0.0.1'
$env:PPT_STUDIO_PORT = '8010'
$env:PPT_STUDIO_DB_PATH = Join-Path (Get-Location) 'data/projects.db'
$env:PPT_STUDIO_RUNS_DIR = Join-Path (Get-Location) 'runs'
.venv/Scripts/python.exe start_server.py
```

旧候选、源码/运行片段和bundle身份改变后按原流程重新核验，不能重签历史批准；用户手改、音频及当前作者保留。

## 发布验证与回执

此前最终观察/计分/系统诊断28 passed，相关108项运行107通过、1项在运行时片段升级正确触发来源变更保护，冻结后单独重跑通过。各批测试有重叠不相加；历史专项数字见对应记录，不冒充当前全量。

本次发布前从冻结源码重新验证：

- 相关Python回归**217 passed，232.20秒**，含观察/计分/系统与规划诊断、语义/标签规划、生产前置与还原、能力/facts/运行片段、几何修复及两个新工具。日志`.tmp/publication-detection-20261021-regression.log`。
- canonical quick通过，日志`.tmp/publication-detection-20261021-quick.log`。包括全仓ruff、Agent契约同步、JS语法/职责/启动/设置与其内置相关测试，不能当canonical full。
- `npm --prefix html_engine run build:visual`成功，源码与生成player一起发布；5 scenes、5 themes、10 layouts、0新图。
- Node动态策略与容量诊断检查通过；`npm --prefix html_engine run test:visual`通过容量/关系/局部强调及5场景14组浏览器检查，pageErrors=0，日志`.tmp/publication-detection-20261021-visual.log`。
- 仅暂存可复用源码/测试/文档，发布清单和凭据模式扫描无发现；日志和真实样本不进Git。未运行本批canonical full，不以专项或quick代签远端CI。
- 提交前按Git暂存字节核验发现0.7.5片段本机CRLF与入库LF不符，已按既有.gitattributes固定0.7.4/0.7.5实际文件为LF并刷新活动registry body hash；规则语义不变。后续用暂存区body/reference实际字节重新核验全部运行片段，不能仅用工作区hash推断跨机可用。真实调用的旧身份/请求保持历史，不重签为新字节或追加模型请求。
- LF收尾后观察/计分/诊断/运行片段组**69 passed、3 deselected，11.68秒**，仅未重复三项先前已通过的浏览器用例；日志`.tmp/publication-detection-20261021-lf.log`。217项发布回归是在LF收尾前，不能宣称再次全量重跑。

发布回执：

- 源码与首版handoff共同提交：[59da921ff36f851af61e3e759b24335975e9bc3f](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/commit/59da921ff36f851af61e3e759b24335975e9bc3f)，北京时间2026-10-21 17:22:20；56个文件，2552行新增、80行删除。
- 已正常推送origin/main；`git ls-remote origin refs/heads/main`返回上述完整SHA，与本机提交一致。活动片段及引用共8个实际Git入库文件hash核验通过，暂存清单与56文件清单一致，凭据模式扫描无发现。
- 本回执、README及发布备注另作后续纯文档提交；另一台机器以origin/main最新提交为准，不只停在59da921。源码提交已包含全部本批代码/测试/契约/标签定义/专项交接。
- GitHub已实际触发源码提交的[CI #69](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/actions/runs/39576467622)，写作时in_progress、conclusion=null。通过GitHub连接器只读核验；不能把本地专项和quick或推送成功写成远端canonical full通过。后续以运行终态为准。
- 应用未重启/部署，未上传数据库、样本图片、运行数据或凭据；课程人工接受与正式输出仍未验。
