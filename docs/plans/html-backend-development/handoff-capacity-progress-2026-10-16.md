# 容量诊断消费与无进展判断 · 2026-10-16

## 问题与修复

继续验证容量错误说明时，发现共用RepairProgress只比较available/measured等字段，未比较新诊断的triggers/effectiveLimits。行数或文字边缘已发生变化但盒尺寸相同，会被提前归为unchanged_measurements。已保存页把原始证据包装在issues[].details，原实现也未读取该层。

html_repair_progress.py现在比较两层中的精确触发谓词与有效限值，触发项排序后比较，说明文字、顺序及报告路径不算进展。保留旧报告兼容、重复场景/补丁停止、原轮数预算、严格检查、人工字段保护和automatic_retry=false。事实变化只允许预算内继续，不保证改善或收敛。

实际候选Agent原本已把capacityIssues完整送入模型，本轮补测试确认triggers/effectiveLimits、相等scroll/client证据、protectedPaths和剩余决策次数确实出站。没有新增Prompt、Skill正文、模型或生成请求；这是消费端判断修复，容量runtime片段仍0.1.0，不能表述为真实模型选策效果已提升。

## 验证范围

新增固定WF-029，覆盖行数变化、有效限值变化、已保存报告details及文案噪声；实际LangGraph使用检查器/模型替身，分别验证改善后两次通过、不变一次后停止、预算两次后停止，原scene保持且不写作者文件。报告位于ignored `outputs/workflow-evaluation-20261016-v8/`，profile0.8.0，不与不同清单直接比较改善率。

最终固定清单29/29通过，包含79项Python参数实例及5个Node执行器。容量进展与已保存修复回归20项通过；前一批进展/时序QA16项通过；进展/Agent接口/受控Skill回归482项通过。批次存在重叠，不相加宣称独立覆盖数量。合同同步及diff检查通过。

## 交付与运行状态

源码合同0.9.59，Agent API1.39.0/hash2f9000d34a3b464d；html_review.produce1.8、html_repair.generate1.2，无数据库/作者格式迁移。

只读HTTP核对8010仍为1.37.0；此前服务换版被自动审批拒绝，仅返回“blocked by policy”，本轮没有换方式尝试停止进程。源码与当前运行服务不同，不能声称新闭环或本修复已生效。真实库仍2个项目、active_jobs=0、10张表记录与备份一致。

未付费调用、未重发原遴选unknown、未生成新业务HTML，未commit/push。真实模型能否正确选择扩容、合理行高、调整字号或回规划仍未验证；待换版阻塞解决且新实验明确获准后再测。现有离线替身只能证明输入证据、工具执行和停止规则，不能替代真实模型质量、审美或全流程签收。
