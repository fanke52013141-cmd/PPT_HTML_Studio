# 系统问题台账 · 2026-10-21

验收目标：定位、复现并改善系统问题；课程页是样本，逐页修好不作为系统优化完成标准。当前记录以事实分层，离线校验通过不等于真实模型能力通过。所有本地源码变更未提交/推送，应用未重启；运行数据不公开。

| 问题 | 证据与已做改动 | 尚未解决/下一验证 |
|---|---|---|
| 规划混用对象/槽位/需求ID | 真实端点/coverage失败；Prompt0.3.6与具体path、合法ID、键差集反馈已实现 | 新模型两轮纠错效果未验 |
| 正文裁切、箭头穿字漏拦截 | 父卡片Range边界和还原前后原30fps检查已实现；真实候选3处正文越界、3组穿字被拦截 | 拦截不代表自动修复；手工结构保存未新增浏览器门禁 |
| 还原模型错误unchanged | 首轮此前只有参考图，现补当前HTML双图；工程失败不能由unchanged清除 | 新真实模型判断可靠性未验 |
| 设计要求与组件能力不匹配 | 理解0.7.5/内部协议0.3.0完整逐对象观察，与能力分工独立；同图固定标签插图识别4/4、图标6/6，系统缺口漏检0/2、误报0/8 | 一课开发集未验泛化；0.7.4额外figure误拦已留证，最终本例未复现；原模型把缺口写asset_identity，程序派生正确类型，不能冒充模型分类已解决 |
| 审核不确定后诊断不具体 | 原43条facts中的subject/asset_identity不确定现能明确定位，保留证据和evidence_review停止入口；缺/重/未知清单用response_repair | 核验入口仅是派生审计/progress，不是自动恢复服务或新增UI；不确定不能自动认定素材错误，不补发 |
| 外部超时缺可靠回执 | 第2页素材和第4页回退结果unknown，未重发 | 提交ID/查询能力、未知恢复机制尚未改造；供应商支持情况须另查 |
| 默认浏览器截图不稳定 | 同DOM截图不同；原校验器对照也复现，场景字节一致；正式软件捕获检查通过 | 默认GPU捕获原因未解决，不放宽测试 |

## 本批系统优化证据

运行Prompt遵循项目optimize-prompts/produce-editable-html Skill。改动在html_design_policy、html_design_agent、html_review_facts原所有者，不新增渲染器、不替换素材/TTS、不手写课程作者。理解required_features兼容增加independent_illustration（默认仍省略/[]），只有image对象满足；明确要求而card/figure等不支持则原understanding单次合法结果转unsupported/capabilities，后续素材/排版/还原不执行。未声明时不扫描appearance中文猜需求，不虚构成功。

默认facts表通过严格Schema和完整键检查后，观察不确定、空证据或适用对齐缺失得到ReviewFactsIncomplete详情；既有ValueError兼容、原错误码和失败阻断不变。诊断的evidence_review/response_repair是核验分类，不是自动业务返工路由；不继承到可保存作者、不签发通过。保留完整response.json与hash、具体检查键和所有不确定项，进度提示automatic_retry=false；还原调用把该提示转交原任务进度。字段/图像/模型参数、600秒low、原调用预算保持。合法完整审核结果路径不改。

新增正反例覆盖所有节点/变体的插图能力、普通图标仍合法、单次理解提前停止、未知观察不推断素材返工、缺/重清单区分、审核hash/停止动作/零重试。归档真实回放与受控特征扰动分开记录在`outputs/system-diagnostics-20261021/summary.json`：供应商0、作者写入0；归档响应不改写。相关回归终态补录于下方。

验证终态：新增`checks/test_html_system_diagnostics.py`5 passed；`test_html_review_facts.py`、`test_html_design_agent.py`、`test_html_design_policy.py`和`test_html_runtime_skills.py`107 passed（132.15秒）。包含新增系统例、facts/能力/片段及还原失败分支的最终相关组82 passed、3 deselected（42.06秒，按变更范围未重复运行三项浏览器还原例）。两组有重复用例，不相加作独立覆盖数。全仓ruff、Agent契约同步和git diff --check通过；真实模型识别/声明召回、付费延迟/费用与自动恢复仍未验证。

后续优先：固定参考集的完整观察优化已复测，见[识别评测](feature-recognition-benchmark-2026-10-21.md)：0.7.5观察TP4/TN6，无FN/FP/未决；系统缺口TP2/TN8保持。原模型严格问题类型仍有2未决，与程序派生判定分开。两轮7次HTTP全部返回、无unknown，usage/费用null；第4页云雨原标签仍弃权，不事后改标签。接下来扩充未曝光的跨课程样本，以新版本标签覆盖容器/标注归属负例，核验分类一致性；供应商回执与unknown恢复仍单独待做。历史验证终态保留为当时状态，本段为最新结论；未改作者、重启应用、提交或推送。
