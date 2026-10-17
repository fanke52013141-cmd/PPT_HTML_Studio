# 首轮审核：局部证据实验与协议稳定性修复

## 当前结论

首轮全量覆盖继续强制执行；局部对照证据已实现，但真实实验没有达到默认启用条件，保留显式实验入口。默认生产仍用原参考图与HTML整图，运行片段0.10.0修复已知重复字段的一致性消费。视觉稳定性未通过，未进入逐页打磨、作者保存或正式验收。

本轮合同0.9.71，定义见[局部对照证据](../../contracts/html-presentation/runtime/visual-v1/local-review-evidence-0.1.0.md)。上轮0.8.0真实实验是独立样本，不能把两轮数字混成同一次改进。

## 实现

- html_review_evidence.py按实际终态geometry生成左右对照窗口与targetId/label/image_index/row映射，最多两张派生PNG；保留完整两图，原单次请求不变，满足适配器4图/每图400万像素预算。
- 所有对象都记录窗口或缺失原因，完整review_checklist保持。源图、实际截图、scene及派生图hash可追踪；返回后再核对源，模块进入generation snapshot闭包。
- 同坐标参考窗口明确unverified_same_coordinate_window，非已识别参考对象框。直接查看生成表已见参考卡片标题被截断、来源混入卡片窗口；因此不能拿局部证据生成成功替代区域定位成功。未开发OCR/参考区域识别/DOM实测，不作这些能力声明。
- 实验0.9.0与默认生产0.10.0分别受控注册；local_comparisons默认False，正常还原流程保持双整图。模型只做原系统审核，无Codex代写本例HTML或问题清单。
- 0.10.0解析器显式兼容issues中的已知reference_alignment元数据。非空值仅可属于typography，必须与唯一同对象typography coverage完全相同；不确定、矛盾、无对应检查、其它需求上的非空字段和任意其它未知字段仍拒绝。Schema仍不要求此重复字段。没有补issues、改状态、删未知字段或增加模型重试。

## 真实配对实验

两张固定截图来自原reference-workflow-agent-20261017归档；scene/原图/截图与原记录hash核对。fixed-0含三张卡片与caption四个已核实对齐差异，fixed-1含caption一个差异；每图每策略三次，交替顺序。before采用first-review-stability-20261017-v5封存的0.8.0真实Prompt/Schema/输入，after是本轮0.9.0实际review_fidelity加局部窗口，不传前轮问题。

仍使用项目冻结glm-5.3-flash、temperature1.0、thinking enabled、low、64000和600秒。实验记录outputs/first-review-local-evidence-20261017/{manifest,model,trials,http-attempts,summary}.json及每次request/response。12次适配器调用对应12次HTTP入口，全部返回完整JSON，无未知结果、无补发。用量/费用无可靠证据，保留null。

| 同轮指标 | 0.8.0双整图 | 0.9.0局部对照 |
| --- | ---: | ---: |
| 独立首轮次数 | 6 | 6 |
| 合法可消费响应/完整coverage | 5/6 | 3/6 |
| 已知问题有效召回 | 7/15，46.7% | 6/15，40.0% |
| 单轮找全已知问题 | 3/6 | 3/6 |
| 中位请求耗时 | 20.709秒 | 27.276秒 |

0.9.0两次响应把reference_alignment重复写进issues，严格原Schema拒绝；另一次把caption参考对齐声明为left、当前合同center，却没有对应typography问题，被覆盖一致性门禁拒绝。原失败状态保留。

已知召回沿用(targetId,typography)匹配，只覆盖已核实对齐目标，不代表每条附加问题都被独立验证。15是五个缺陷在三次实验中的暴露次数；无效响应计零有效召回，未标注额外问题不自动算误报。样本只有两图三次，不主张统计显著或总体准确率。

实验脚本旧after日志前缀为design_fidelity_review-review，六次流进度日志会覆盖，逐请求request/response、耗时和HTTP入口列表各自独立保留。此次全部完整返回，不依赖覆盖日志判定unknown；脚本已改为每次独立前缀，后续实验不再覆盖。该修正未重新请求供应商。

## 0.10.0本地回放

scripts/replay_html_review_responses.py只读取这六份原始after响应与原请求，逐份记录request/response及解析源码hash，使用独立输出及数据库路径，无提供者调用，不修改原任务。证据outputs/first-review-local-evidence-replay-20261017/replay.json。

| 同一份已返回JSON | 原0.9.0解析 | 0.10.0严格类型兼容回放 |
| --- | ---: | ---: |
| 合法响应 | 3/6 | 5/6 |
| 有效已知问题 | 6/15 | 11/15 |
| 单轮找全记录 | 3/6 | 5/6 |
| 新增模型调用 | — | 0 |

两份相同且可核实的重复字段得到消费，一份漏报问题仍拒绝。这个结果证明解析损失减少，不能称为0.10.0新模型请求的73.3%真实召回率，更不能替代完整生产或视觉验收。实验局部对照仍默认关闭，原0.9.0失败不回写成功。

## 验证与下一步

最终隔离回归134项全部通过，97.33秒：覆盖、局部窗口及预算、默认关闭实验、已知重复字段正反例、共享规则、设计Agent、还原和源闭包/受控片段。早期一条固定双图断言随实验暂时改为四图，最终恢复对正常入口的双图断言，并增加独立四图实验测试。编译及diff检查另记；原neutral-science seek失败未修改或宣称解决。

下一批应优先统一单一审核事实输出，减少issues/coverage重复表达；参考区域定位须返回可核实身份与完整内容区域，不能继续按HTML同坐标裁剪后宣称定位。固定同图独立复验通过前，不开启局部对照默认策略，不增加逐页修复轮次。0.10.0默认Prompt的新模型输出、真实定位、不同页面泛化与整课验收均待验证。
