# 规划诊断与重试输入优化 · 2026-10-21

本地未提交/推送，未重启运行中的应用，也未新增供应商调用。包0.9.113/API1.60.0保持。承接水循环真实试验中的PLAN_RELATION_ENDPOINT和PLAN_VISUAL_COVERAGE失败；不改写原失败或unknown。

## 变更与边界

- `html_course_structure.py`仍是纯校验所有者：非法关系对象引用返回准确path、actual、合法对象ID，以及输入若是槽位名时对应的对象ID。提示不自动采用，箭头/标注仍不能作为关系端点。
- 覆盖键错误返回权威required_ids、missing_ids、unexpected_ids和重复需求ID；数量/重复/不存在对象、对象类型错误分别提供事实。缺省/空需求清单只接受省略visual_coverage或{}，不为visual_groups推断需求，不自动删字段。
- `html_visual_review_service.py`唯一语义规划Prompt升级0.3.6，首次system和实际schema_hint明确对象ID/槽位/需求ID边界。原第二轮完整invalid_plan和diagnostic.message消费详细事实，原审计保存同一错误字符串。
- 原错误码与字符串接口不变，所增强的message内容为JSON事实；对象/动作身份、两轮、1800秒/low effort/流观测、unknown不重发保持。规划模块已有原快照源闭包，无新增注册器、API/Schema或数据库迁移。新源码使旧候选须重新核验，历史批准不升级。
- 合同/HPS-010/013/015—017/023—025已在课程结构卡、索引、README、CHANGELOG同步；没有将操作Skill全文塞入模型。

## 验证

- 新增11项无供应商测试全部通过：槽位与对象身份不同的端点、未知/不允许端点、缺省/空需求、缺失/额外键、覆盖类型、第二轮准确事实及审计、连续错误仍拒绝、超时一次提交。合法计划和动作身份保留。
- 最终相关测试组（planning diagnostics、semantic plan/design、labeled planning、course structures）105 passed / 1 failed。失败项为原默认浏览器1600宽度截图像素一致性；正式软件捕获及其它规划/编译/结构检查通过。第一次运行另有两项新测试把规范化补入的exit=false误当成身份改变，修正测试为与合法规范化计划比较后，两项通过；未改生产规范化行为。
- 原规划/审核接口兼容测试`checks/test_html_visual_review.py`另8 passed。
- 对默认截图失败做一次隔离原版本校验器对照：从Git HEAD读取原html_course_structure模块，在独立进程内使用相同输入/当前渲染器编译；新旧四页scene JSON逐字节相同。原校验器对照同样在slide_002、1600宽、DPR2失去像素一致性，DOM/结构检查通过。证据`outputs/planning-diagnostics-20261021-baseline/summary.json`及原截图。此对照仅排除本次规划校验变更对场景字节的影响，不是完整历史应用回归，也没有解决默认浏览器的捕获问题；检查标准未放宽。
- 全仓ruff、Agent契约同步与git diff --check通过。未用离线替身声称真实模型纠错率、费用或延迟改善，未保存作者/批准。

## 下一步

优先把正文实际溢出、关系穿字的检查证据接入还原和保存前反馈；关系端点需回原规划坐标修复，组件差异回能力阶段。默认浏览器截图一致性单列调查，软件正式捕获不得代签交互GPU结果。真实新请求需加载当前源码并检查原任务状态；既有第2页素材/第4页回退unknown继续禁止重发。合格HTML尚未保存，声音/绑定/输出仍未验收。
