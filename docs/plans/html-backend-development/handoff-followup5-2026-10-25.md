# 五项后续开发交接（2026-10-25）

接续P0/P2，完成逐项验收工具、诊断覆盖、主面板内直接框选、固定配对评测工具和注册布局扩展。契约包0.9.117，HTTP请求合同与Agent API1.63.0保持。定义见[验收与工作台规范](../../contracts/html-presentation/runtime/visual-v1/acceptance-workbench-evaluation-0.1.0.md)。

## 1. 原69项的独立规则与证据判定

`config/html_acceptance_criteria.json`固定69个原AC、原条目hash、required_level、检查选择器、命令、完整/支持性覆盖与剩余要求。`html_acceptance_criteria.py`只读校验规则/证据/源码hash、测试类名和用例名、参数分母、重复/跳过/失败、未知条目及越界路径，不执行证据中的命令。缺证据pending，过期/损坏failed；支持性测试通过仍pending。涉及真实模型、人审和发布的层级不由上传的passed声明签发。

捕获并验证已实际执行、且其同目录manifest.json封存了执行时源码与证据的JUnit（可重复添加多个输入）：

```powershell
python scripts/verify_reconstruction_criteria.py --capture-junit outputs/followup5/acceptance-verified/O7-01.xml --capture-junit outputs/followup5/acceptance-verified/O7-06.xml --evidence outputs/followup5/ac-evidence.json --output outputs/followup5/ac-verification.json
```

日后复验去掉`--capture-junit`，保持原evidence，不重新签名。`--require-all`要求69项所有层级通过，任一pending/failed都返回非零；默认模式允许报告pending，但不允许failed。机器结果同时含counts及all_required_passed，退出0不等于整体验收通过。

`reconcile_reconstruction_acceptance.py --criterion-evidence <evidence.json>`重新执行严格校验再合并原账本；不读取外部自称passed的汇总报告。未提供逐项证据时保持原task级partial策略。

## 2. 诊断覆盖

共享诊断0.2列明capacity、geometry、reference、resource、protection、stale、no_fit、budget、unknown、incomplete和infrastructure，给出处理路由和中文入口说明。保留原code、目标/part、首次时刻、未四舍五入的测量及canvas_px/css_px/lines等量纲，不跨单位加总。未知码/单位停止自动修复；预算不足和无解分别记录。静态及逐帧、已保存修复共用同一投影，本地预览显示对应行动说明。原QA通过判据不变。

## 3. 主面板直接框选

原定位复核入口中选择对象/部件，直接在原图拖框，填写实际转录和身份依据，应用文字框；有背景框时切换容器模式并应用容器。点击“使用修正，返回主面板”，然后在主面板显式“提交修正，继续审核”。旧JSON导入/导出作为可选高级方式保留。

iframe仍为allow-scripts/allow-downloads沙箱。消息必须来自本frame，匹配会话hash和本次随机nonce，页面切换/clear使旧nonce失效。该消息只装载候选，不自动调用审核、保存或批准；提交仍走原ReferenceCorrection模型、原LocalJob和完整性校验。框选按原图像素计算，不按当前HTML坐标定位。

## 4. 固定配对评测及真实样本标注入口

仓库`checks/fixtures/reconstruction-pairs`含4个人工构造光栅夹具、2个互不重叠的课程分组、开发/留出划分、固定gold版本及源hash。它们用于验证评分工具，不代表真实课程或真实模型表现。trials-template明确before/after、每样本重复号和not_run，不填入伪模型结果。

```powershell
python scripts/evaluate_reconstruction_pairs.py --root checks/fixtures/reconstruction-pairs --dataset checks/fixtures/reconstruction-pairs/dataset.json --trials checks/fixtures/reconstruction-pairs/trials-template.json --output outputs/followup5/pairs-not-run.json
```

评分强制每个case/repetition/arm覆盖且唯一；失败/unknown/not_run进入分母。分开发/留出统计定位文字与区域、独立工程观察、参考像素MAE、时延、usage/cost；未知费用null。像素相同不等于语义/保真/审美批准，fidelity与human approval保持待独立审核。相同课程或相同参考图禁止跨开发/留出泄漏，不能用留出结果选择Prompt/模板。

真实样本用本地清单导入，无供应商调用：

```powershell
python scripts/prepare_reconstruction_dataset.py --spec <spec.json> --source-root <local-source-directory> --output <new-dataset-directory>
python scripts/prepare_reconstruction_dataset.py --seal-labels <dataset-directory>/dataset.json
```

spec包含label_version及cases，每个case为id、course_id、split（development或holdout）、reference和scene（source-root下相对路径）。导入逐字节复制PNG与scene，并生成待人工标注的labels.json；不从HTML坐标生成gold。标注者核对原图后填写实际逐行文字、[left,top,right,bottom]像素框、container/status、annotated_by，并显式设置independent_human_labels；seal只更新gold hash，仍核验原图/scene hash、课程划分及标注结构。草稿或无标注者的标签不能评分。修改gold后原trials的dataset hash过期，必须显式开始新评测，不能续签旧实验。

返回的配对结果可记录真实请求回执和图像/返回hash，工具本身零供应商调用、无作者或人审写入。仅存在回执也不意味着真实效果通过。

## 5. 布局扩展

注册wide-body-pair-v1（宽正文双卡片）和comparison-three-columns-v1（三列对比），仅neutral-baseline主题显式兼容。复用原header/card/summary组件，固定槽位与容量，不改通用Schema上限、字号下限或渲染器。宽正文结构针对现有双卡片容量案例；三列结构针对已验证横排扩宽遮挡案例。

注册行/网格提案增加下游summary跟随，保持原槽位顺序和安全区，最多4个目标；原scope/manual保护及完整30fps检查判断候选。新增测试覆盖normalize/compile/语义绑定、真实静态与全帧、长文拒绝、未知槽位拒绝、源不变和人工保护负例。

## 验证与边界

最终结果：7组工程门禁146项通过，执行前后来源一致且二次verify通过；原10例浏览器基准符合预期，新增布局另有8例原始基准（两模板各baseline/修复/人工保护/长文拒绝）全部通过。Agent全套462项、补充回归26项通过（组间有重叠，不相加）。quick、Ruff、前端质量、视觉引擎、catalog及Agent契约一致性、diff检查均通过。

逐项AC严格判定为12 passed、0 failed、57 pending；合并原实现账本后为12 passed、53 partial、4 not_run。`--require-all`已实测返回非零，正确阻断整体验收。逐项[执行清单](reconstruction-ac-checks.md)与[验收账本](reconstruction-acceptance-ledger.md)同步，不能把146项工程测试等同69项全部通过。

主面板实际浏览器截图和通道验证在`outputs/followup5/inline-evidence`，新布局原始全帧/保护/溢出证据在`outputs/followup5/layout-evidence`。后者可执行`python scripts/benchmark_followup_layouts.py --output <新的证据目录>`复现；来源夹具及runner hash在summary中。

代码复核覆盖正确性、可读性、架构、安全及性能：AC验证复用原封存包校验并缓存同一包的检查；未知码/单位保守停止；iframe消息校验窗口、随机nonce、会话和切页生命周期；模型响应结构无效计入失败分母；真实样本草稿禁止评分；注册布局仍由原保护与完整QA裁决。未添加第二渲染器、模型重试、自动保存/批准或外部网络数据入口。测试期间修改源码的旧包保持失败/中断，不用于最终通过。

最终统一证据包`outputs/followup5/acceptance-verified`，执行前后源码hash一致才可签发工程通过；`--verify`可再次核验。其余Agent、quick、视觉引擎、catalog、源码复核和逐项证据见`outputs/followup5/delivery-summary.json`。旧P0/P2包按旧源码封存，不冒充当前源码验证。

```powershell
python scripts/verify_reconstruction_v2_acceptance.py --verify outputs/followup5/acceptance-verified
python scripts/run_checks.py --level quick
python -m pytest checks/agent -q
npm --prefix html_engine run test:visual
node html_engine/tools/catalog-build.cjs --check
```

没有真实付费调用、提交、推送、服务重启或发布。本轮“开发完成”仅指上述功能及工程验证；真实课程样本的人工作业、实际模型配对实验、人工视觉签收和正式音视频发布仍需对应独立证据。新增工具/标注/复核不改作者，不产生下游失效；实际修复保存沿原作者/音频/失效/批准门禁。
