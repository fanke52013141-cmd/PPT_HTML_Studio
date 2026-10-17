# 阶段3、4执行记录：2026-10-17

## 阶段3最新生产复验：0.9.66 当前设计，视觉审核拒绝

当前定义新设计任务`html_e78a650920f543aba68a`成功design_review：规划1次20.91秒、生图1次32.39秒；参考上传2次、生成提交1次、poll3次、extract1次。无独立主体资产。候选key=`1546733307aed11833a0a6c858453ca470cf881fc0d266e2e55b00d9e45751bc`，图像SHA256=`b81aec5dabe40d82d9e7ce5f3ed7fe52897e4b3ba4f6bd0041e141ec847950a6`。用户已明确确认这张图用于系统还原测试，不代表最终视觉通过。

真实还原任务`html_b990ad561c7146f2b245`使用正式系统执行器、独立数据库/项目，无Codex手写页面替代。所有5个适配器请求完整返回，不是unknown；最终failed，上游修订要求`upstream_revision_required`，routes=[capabilities,reconstruction]，automatic_retry=false。作者scene不存在，无视觉批准、无音频/逐句语义QA或正式输出。没有执行第二轮还原以绕过能力停止。

| 实际阶段 | 适配器次数 | 累计耗时 | 结果 |
|---|---:|---:|---|
| 设计理解（含一次结构修复） | 2 | 18.35秒 | 通过分工 |
| 容量修复 | 1 | 4.18秒 | 通过，使用low/180秒及runtime0.2.0 |
| 受控HTML还原 | 1 | 276.65秒 | 6项合法操作，三张text-card-label高度136及注册icon |
| 独立视觉审核 | 1 | 423.89秒 | changes_requested，拒绝正式作者保存 |

工程/容量检查通过不等于设计还原通过。独立审核发现：三张text卡片把“标签：内容”作为内联文本，现有whole-part样式工具不能表达参考图的标签/内容上下两行；caption、stat-2、stat-3对齐与参考不同；summary关系面板构图仍不同。需核对这类能力在设计理解阶段为何没有提前停止，避免付出后续约11.7分钟请求成本。

审核本身也有事实错误：它建议summary切换summary-panel，但allocation-applied.json证明summary本已使用该变体。模型将“已注册变体名字”误当作必然具有药丸压长箭头等视觉能力，不能照建议无效重试；需将当前变体与实际可实现特性对照纳入评估。准确内容和代码语义归属继续高于参考图，不插入换行改原文来规避能力边界。

本轮只调用真实服务，无新代码修改。原九页项目未写入。证据在忽略目录`outputs/stage34-current-design-20261017/stage3-v066-*-result.json`及该项目的design-reconstruction/34060785085de4bc8480ab1b92abd8d99d4c951008b2fe5bff0e2b304e21360e/。阶段3已实际执行到独立视觉审核，但未验收通过；阶段4九页真实扩展仍应等待这些流程问题收敛。

## 摘要与排版修复后续（0.9.66）

summary-panel固定120px状态列造成长文字+内边距超格；改为保留120px下限、按内容展开，严格总体宽度不变。原末轮场景去除from/to的14px缩字号，重放严格passed=true且pageErrors=[]。这只是隔离工程重放，非正式生产或设计保真签收。

局部修复增加公开子部件诊断、节点尺寸能力、由canvas盒触发推导的内边距尺寸提示，以及前轮决策；GLM请求级low/180秒，其它阶段不变。runtime片段0.2.0保留旧0.1.0并更新hash。

完整原初态+binding+合同的最终系统Agent诊断（outputs/summary-agent-low-replay-v5-20261017）：2次决策，含浏览器检查21.05秒，严格容量通过。原真实生产3次决策674.95秒失败。组件、输入和模型参数共同变化且只有单次成功，不将全部改善归因low或推断费用。原生产失败和已耗预算保持；没有写作者场景、新生图或完整设计还原。

前四次诊断分别为：缺绑定、缺合同导致绑定错误、模型误判尺寸不可编辑后stop、设置外高36而有效高度仍0后无进展停止。所有完整响应已留存，不算unknown、不以最终成功覆盖先前调用。最后补充尺寸提示后marker外高72解决内边距问题。

视觉构建和capacity.test通过；全量verify连续两次在既有neutral-science seek非确定性断言失败，仍未解决。定向Agent/Skill/容量进展回归初次56通过1失败，为新测试错误要求仅line/scroll溢出也必须有canvas尺寸提示；修正为不臆造跨单位尺寸建议并单独复测。各阶段工程和视觉验收继续分开。

## 最新终态：上传链路恢复，容量修复未通过

任务`html_5c9044ed6d35485aa811`最终failed，stop_reason=budget_exhausted，repair_status=needs_revision，automatic_retry=false。设计理解2次、素材适配器1次均返回，容量修复3次合计674.95秒；外部适配器累计6次约748.62秒。最终`summary-def`的scroll_width=404、clientWidth=400、容差1 css_px，仍未通过。初始label高度和零高度marker问题经注册操作解决；后两轮只将摘要from/to字号从20逐步减为16、14，未彻底解决摘要内部宽度。没有保存作者scene或进入设计还原/独立视觉审核，也没有正式视觉批准。

本次已在真实提供者验证参考图上传、一次生图提交、原ID查单恢复以及独立素材返回；长期连接可靠性和旧无证据unknown仍未验证。新瓶颈为容量修复的max推理耗时及内部布局诊断/操作效果。不得清零3轮预算重新跑同候选或重复生图冒充修复。后续须从真实summary测量、注册部件能力及repair输入入手，不放宽404>401的严格限制。

## 上传连接定位与当前续进

只读GET检查`https://api.toapis.com/v1/uploads/images`在trust_env=False/True下均建立HTTPS并返回404，证明检查时主机可达，不证明上传POST可用或认证成功。DNS返回198.18.0.46；未修改代理/DNS/TLS验证设置，也没有证据确定是哪一方的暂时网络故障。

对旧任务完整边界证据核实后，上传-only connection_failed可标为not_submitted；原unknown复制留档。源码变化后用新快照任务`html_2e7c008e58084bfeada9`执行，而非冒充旧快照恢复。4次参考上传、1次生成提交取得`tsk_img_01M53SW4XC1FW8Z4T0VJ7912CD`；本地提取结果时失败后，系统对原ID查单1次成功，复用密封规划与图片，任务在design_review成功，累计规划适配器2次、图片1次、复用1次。lookup入口只有poll/extract各1次，无上传或新提交。

当前新设计key=`cd8e83337f2bacea907c7a8d20eb6fc42c3e617232585c3c1511264cdd5cca12`，图片SHA256=`79063ddc274eddd4926b50473e04ca3f863ca11800e22d93056ba025cf15b1ae`。用户明确确认用于还原测试，含02/24页码与额外图内标签的问题留待系统识别；不代表最终视觉批准。

还原任务`html_5c9044ed6d35485aa811`由正式系统执行器运行。设计理解经一次完整JSON修复通过；独立素材5次参考上传、1次提交，任务ID=`tsk_img_01M53T1T96YCFNA3XTXRE7435G`，图片正常返回（poll4次、extract1次）。后续编译检查触发candidate_capacity_repair，正在使用原3轮预算和绑定的max推理，不擅自更改模型/等待规则。最终结论以下续记为准。

恢复相关完整回归40项通过。新传输证据仅定位本次入口，不倒推旧无证据unknown或费用。

## 当前结论

阶段3真实单页未走通：当前定义的新设计实验在参考图上传时连接失败，未进入设计生成POST。阶段4修改影响的隔离回归通过；九页真实HTML生产仍未通过，不作为正式验收。

## 九页状态

读取固定案例`linxuan_nine_plan_20261016`当前合同和`current_design`服务：

| 页面 | 当前设计状态 | HTML真实验证 |
|---|---|---|
| slide_001 | 无候选 | 未测试 |
| slide_002 | 历史候选ef5f82fe…ba2290a，needs_review且stale | 新实验仅规划通过，上传失败 |
| slide_003 | 无候选 | 未测试 |
| slide_004 | 历史候选13d26b2e…90e7f8，stale；曾获测试用途确认 | 历史独立素材unknown，未通过 |
| slide_005—009 | 无候选 | 未测试 |

历史候选因当前源码定义变化失效，不重签或改写其身份。新图仍应展示并明确用于重建测试，测试用途不等于最终视觉批准。

## 阶段3：独立真实实验

任务`html_b330951113da482799ff`，plan_version=0.2.0。使用正式`HtmlWorkflowJobs`、配置化规划及图片适配器；数据库为SQLite只读备份后的隔离副本，产物在忽略目录`outputs/stage34-current-design-20261017/`。只复制当前讲稿合同和模型绑定，使用全新隔离项目；原九页项目未写入。没有手写plan/HTML或复用过期候选冒充系统成功。

系统规划适配器2次（含一次有界修复），合计约54.2秒，合法plan/brief已封存。图片适配器进入1次，约5.25秒后失败；`provider_error={code:connection_failed,phase:submit}`为底层粗分类；更精确的本地传输证据为`boundary_entries={upload:1}`、`last_phase=upload`，没有submit/poll/extract入口和上游任务ID。因该ToAPIs适配器按上传→提交顺序执行，本次执行没有进入生成任务POST；不能据此推断其它旧unknown探针的阶段或供应商账单。

原任务保持failed/EXTERNAL_OUTCOME_UNKNOWN，没有自动重发、主体素材、HTML或作者保存。聚合usage/cost为null，不能宣称零费用。探针脚本末尾输出摘要时访问空result产生本地AttributeError，发生在任务结果已落盘之后；不改变原任务上面记录的传输失败原因。

下一步：只读检查供应商上传端点可达性、DNS/TLS和网络条件；确认连接问题后再决定恢复方式。原unknown仍先核实，不以新目录反复提交同请求。

## 阶段4：修改影响回归

首次四组测试61通过、1失败；`test_new_rebuild_snapshot_cannot_bypass_unknown_model_request`缺图片服务夹具，触发DESIGN_PROVIDER_MISSING而没有进入预期unknown。补充禁止被调用的图片替身，并断言文字适配器只调用一次及确实登记unknown；保持原生产门禁。

新增九页固定结构的三类修改影响实验：只改第2页标题、讲稿或主体素材引用；其余八页没有重建项；讲稿变化要求TTS，标题/素材变化复用TTS。该测试验证重建计划，不代表实际执行九页重建或真实配音。

最终`test_html_rebuild_plan.py`、`test_html_scene_editing.py`、`test_html_action_editing.py`、`test_html_semantic_qa.py`共65项通过。覆盖人工编辑、动作身份、冲突、逐句QA与最小影响边界；不能替代实际九页视觉与语义验收。

阶段1指纹是当时快照；本轮新增测试和文档后工作树已变化，原指纹不再声称匹配。后续提交前生成新基线，保留原清单作为历史证据。
