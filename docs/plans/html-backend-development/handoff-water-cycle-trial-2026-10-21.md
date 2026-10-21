# 水循环四页真实流程验证 · 2026-10-21

用户授权在本机重新制作四页课程，替代当前无法取得的另一台电脑原课程材料。基于本机main `015139b`及几何扩样本地改动执行；无提交/推送。当前已完成第2—4页真实还原尝试，均未通过，作者保存0/3；不是HTML/声音/输出闭环完成。

## 最新终态：还原、自然故障和代码修正

用户随后明确接受第2—4页当前设计用于HTML还原测试。执行前核对图片sha256；过期key仅走原零供应商参考复用，沿相同图片字节继续，没有把此授权当作正式HTML/语义/声音批准。以下终态覆盖下文早期“未还原/无unknown”的历史记录。

| 页 | 实际任务 | 终态 |
|---|---|---|
| 1 | `html_46dba801af4c44168aa6` | 补温度/气压条件的规划修订两轮均PLAN_VISUAL_COVERAGE。权威需求清单为空，模型却用visual_group ID编造coverage键；离线删除这项额外字段可通过规范化/语义构建，未把修改计划提升为生产候选 |
| 2 | `html_e5231a1cb23b4f4c8936` | 独立素材提交158.590秒后EXTERNAL_OUTCOME_UNKNOWN；无可查询供应商任务ID，禁止重发。设计理解已返回，作者未保存 |
| 3 | `html_98727f0494b8403da209` | 素材和容量修复返回，受控还原答unchanged；独立审核因asset_identity事实不确定而失败关闭。实际截图存在卡片正文/底栏问题，不能以结构通过升级为合格 |
| 4 | `html_c967640305e9419ba71e` | 三轮容量修复后受控还原答unchanged；独立审核要求回capabilities/reconstruction，保留三条箭头穿字、大插图退化为图标等缺陷，未保存 |

自然故障扩样使用原失败候选的准确scene/binding/contract，在隔离副本复验，不是人为扰动或已接受作者。第4页540个时刻检出3组stroke_crosses_text（318/213/207次），几何单对象搜索无合法提案；原单页内容/关系与作者均保持。第3页432个时刻检出卡片/摘要重叠107次；其失败回滚的资源按原阶段JSON及PNG hash在隔离副本重建，未改生产资源。

第4页自然故障的有界模型回退仅提交1个物理请求，593.185秒超时；返回0正文字符、130843推理字符，finish_reason为空，结果unknown（REPAIR_MODEL_UNVERIFIED），费用与用量null，作者/源代码未变。整例627.322秒含几何与其他检查。本次因此有两个不同输入的未知结果：第2页素材提交和第4页隔离回退；都未重发，不能归为自主修复成功。

本机证据目录为`outputs/water-cycle-validation-20261021/`：`reconstruction-summary.json`、`reconstruction-authorization.json`、`page1-coverage-offline-diagnosis.json`、`real-candidate-geometry/`、`card-candidate-temporal-v2/`、`natural-fallback/summary.json`，以及第3/4页真实还原截图。运行数据不提交Git。

工程定位发现：原受控还原每轮虽保存current.png，首轮却只附设计图；这是早期超时排查留下的单图策略。当前改为每轮原设计＋当前实际HTML截图，固定图序、角色/hash留证，程序Prompt0.6.1、受控片段0.7.3与注册hash及合同同步。两轮预算、600秒/low effort、原工具/保护、独立审核不变；旧unknown不因修复重发。此变更只验证出站证据完整性，不证明能自动修复以上故障；未重启服务或再发供应商请求。

离线回归：`pytest checks/test_html_design_reconstruction.py checks/test_html_runtime_skills.py checks/test_html_design_agent.py checks/test_html_build_snapshot.py -q`为94 passed（156.27秒），覆盖原共享渲染、两轮图序/首轮图片hash、还原超时一次提交、非法动作拒绝、运行片段身份及快照来源。`scripts/run_checks.py --level quick`完整通过（含lint、Agent契约同步、前端所有权及原应用回归；7项既有可选基准跳过），`git diff --check`通过。真实模型双图效果和正式课程批准尚未验证。

后续开发顺序：

1. 验证双图出站、首轮/修复轮图序与hash、unknown只提交一次、原保护和快照来源；记录离线回归，不冒充模型质量。
2. 已实现原规划所有者精确反馈：对象ID/槽位区分、空需求覆盖规则、字段路径/合法ID与需求键差集；保留严格校验，不自动删除模型字段。Prompt0.3.6及验证边界见[规划优化handoff](handoff-planning-diagnostics-2026-10-21.md)，真实模型纠错效果待验。
3. 已接入还原生产链的父卡片正文边界与30fps/registered工程前置，见[工程前置handoff](handoff-production-preflight-2026-10-21.md)。关系端点错误仍回原规划坐标修复，组件能力差异回capabilities，不扩大局部几何搜索或改语义；这不代表原页缺陷已修复。
4. 补全供应商提交回执/可查询性后再决定未知恢复。已有未知仍保持，不以切换模型或新任务ID重发。
5. 有可保存的合格HTML后才验证保存恢复、TTS/绑定、逐句QA和输出；当前这些仍未执行。

## 早期设计阶段记录（保留原停点）

## 实际项目与服务

- 项目：`b3174200_112545`，名称“水循环｜四页真实流程验证 2026-10-21”，HTML/guided/16:9，review_policy=all_stages。
- 应用从当前checkout通过`start_server.py`单实例启动，127.0.0.1:8010，显式本机data/projects.db与runs；原服务启动前端口无监听。未运行第二实例、未重放历史unknown。
- 项目图片固定绑定本机已有“A06 Sunburst Official 2K low”连接；文字glm-5.3-flash、规划glm-5.3就绪。未更改全局连接/模型参数。配置就绪与浏览器/字体预检通过，实际图片请求成功。
- 项目是一个四页课程验证项目，未创建额外课程库/章节容器；不能把它统计成四个独立课程。

## 已完成

1. 原`source.set(topic)`实际生成文章，使用原导入路径保存。发现“凝结成小冰晶”表述后，通过原source接口修正为凝华，原生成稿另存证据。
2. 原Step2 script/visual/compose生成四页：概念/三态、蒸发蒸腾成云、条件对比、降水回流。16个语块按序拼接与四页旁白逐字一致；后续视觉意图修订均保留原讲稿及其他页合同。
3. 原`html_review.produce(plan_version=0.2.0, runner=legacy)`生成设计。没有手写scene/HTML或把Codex设计冒充系统生成。
4. 当前四张设计已生成并实际查看，全部停在design_review，候选key未接受，未生成作者HTML。

当前候选任务：

| 页 | 当前任务 | 状态与观察 |
|---|---|---|
| 1 | `html_967ea96b0682487aac85` | 设计待审；需补齐温度/气压条件，清理重复标签；不建议直接最终视觉接受 |
| 2 | `html_13e107fab8a846ce9851` | 设计待审；太阳引线已修正为“太阳供能”，可建议先用于还原测试 |
| 3 | `html_a30db8dfe7d24a989cc9` | 设计待审；静态水面与独立代码对比，建议先用于还原测试 |
| 4 | `html_4f93d22f07ff4d8cb81d` | 设计待审；降水/分流/回流，建议先用于还原测试 |

完整key/hash、当前原接口回读及图片位于本机`outputs/water-cycle-validation-20261021/`；入口`design-review.md`。原文件保存在`runs/b3174200_112545/planning/html_visual/candidates/`，不提交Git。

## 必须保留的自然失败

共8个持久设计任务，17次已测量适配器调用（规划/图片合计，不等于仅17次LLM；也不包含文章和Step2调用）。有3个任务失败、5个任务完成设计停点；其中第2页原成功图有语义错误，后来修订，不能把5次任务成功当成5张合格页或自主成功率。费用未知，未估算。

- 第1页原任务`html_b8041b4b4bfe48ed8073`：524.321秒，输出258237字符后finish_reason=length，明确MODEL_OUTPUT_LIMIT。不是unknown；原记录保留，不盲重发。
- 第1页第二任务`html_01d35a4a8058433e8caf`：两轮模型使用slot名`stage-1`等作为关系objectId，而实际对象ID为`obj-stage-1`，PLAN_RELATION_ENDPOINT阻断。第三次实质改为静态分类对照，才规划通过；没有程序替模型修ID或放宽校验。
- 第3页原任务`html_e79430189fea406b8213`：两轮SEMANTIC_IMAGE_STATE_CHANGE。第二轮已口头声明图片不变，但expectedState expression随语块改变仍不符合严格相等规则。修改视觉意图为图片仅出现一次、不重复强调/声明新状态，由代码独立表达条件，新任务通过。规则未放宽。
- 第2页原任务`html_13db2a5078384f96a38b`完成设计，但实际“水蒸气进入大气”引线指向太阳；核对原计划annotation.anchorId确为sun。原错误图保留，修订权威视觉意图后重新规划/设计，当前图已将太阳标签改为“太阳供能”。

所有任务最终已返回，无本轮unknown；既有另一课程unknown未触碰。输入修订和每次提交、终态、阶段、实际测量均留本机记录。

## 下一步与批准边界

目前未运行HTML还原、真实几何故障检测/修复、保存恢复、TTS/音频绑定或视频导出；这些不能用设计任务成功代替。第1页仍有内容条件与重复标签问题，保留changes_requested建议；第2—4页可建议用户先接受为还原测试参考，不等于正式视觉/语义/声音批准。

按项目produce-editable-html/review-visual-drafts流程，必须有用户对当前具体候选的接受决定，才能携带原design_candidate_key继续还原。得到决定后核对key/current输入，沿原produce继续；不同页保存可能改变项目修订，旧key须按原复用/重新核验路径处理，不能转写批准。第1页先通过规划/设计修订补齐原条件，再请求具体候选接受。

独立真实故障扩样、几何能力与模型回退的最终验收仍需实际HTML；本轮当前只证明文章→讲稿→视觉分镜→四页设计停点以及上述真实失败和恢复路径。
