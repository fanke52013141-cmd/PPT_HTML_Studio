# 豆包与GLM规划停顿排查

2026-10-14，Asia/Shanghai，本机新项目8ce1222f_194645。只诊断，未修改生产Prompt、原任务账本或重发原课程请求。诊断调用使用独立简单连通输入与新的水主题输入，不计为课程成功；中途主动停止流不等于供应商取消。

## 事实与证据

1. DNS/TLS即时探测：open.bigmodel.cn 0.071秒、ark.cn-beijing.volces.com 0.069秒，TLS1.3。仅证明当前连接建立正常，不能排除历史网络异常。
2. 两次简单流式JSON诊断：GLM-5.3 2.513秒完整返回，首次chunk1.176秒、正文2.465秒，174 total tokens；豆包2.1 turbo 4.158秒完整返回，首次chunk2.754秒、正文4.157秒，105 total tokens。GLM原thinking enabled / reasoning_effort=max / max_tokens65536 / response_format=json_object被接受。两次均200，无隐藏SDK重试。当前密钥、端点与基础参数可用；不证明复杂任务成功。
3. 用同一生产system组装函数与新水主题三语块，分别只做一次有界流式诊断：GLM首chunk1.421秒，60.058秒主动停读时2575 chunks、9555思考字符、0正文；豆包首chunk3.398秒，63.575秒停读时657 chunks、1161思考字符、0正文。没有保存思考文本，仅记录时间/字符数；无finish_reason，usage未知，费用未知。HTTP200且持续数据证明该实验不是始终无响应；不证明原Token请求600秒时仍处于思考，原请求无流证据。
4. 原正常分镜豆包曾在320.4秒完成，20682输出tokens中18204为reasoning；简单演讲稿78.2秒完成。单页语义规划旧默认120秒，原豆包120.1秒结束，GLM600.6秒结束。当前共享JSON调用没有stream参数，SDK默认非流式，等完整响应再解析，日志无首包或阶段分类。
5. GLM原始异常被二次checkpoint覆盖：ProductionStages.wrap异常分支先checkpoint，该checkpoint验证了运行期间被修改的源码，抛出“快照依赖已变化”，未能持久unknown；原阶段留intent。没有底层exception分类证据，不能精确宣称原GLM一定是ReadTimeout。按600.6秒及调用路径高度怀疑传输等待超时，仍需新诊断或原供应商记录核验。保留未知保护，但异常审计不能依赖当前源码仍新鲜。
6. 正常生产contract字段main_title / visible_text / display_text / visual_anchor没有映射到planning_context所消费的title / content / description。实际模型输入三视觉组仅各一个id，标题和已生成画面内容丢失。system8256字符、user438字符。这是确定的生产输入合同缺口，可导致重新推导与还原偏差；与timeout因果未单独实测，不当作已证明的超时根因。

原始去敏指标在ignored outputs/a06-local-normal-20261014/diagnostics，含四个诊断JSON及合成输入，不含凭据。保留原课程与未知请求，不登记人工批准。

## 判断与修复顺序

共同主要方向是深度思考与约束规划耗时，加上非流式等待完整JSON、缺少进度和过短/单一超时策略；不是有证据支持的“两家服务都坏了”。提高输出上限只是允许更长结果，不加速返回，原失败发生在提高到65536之前。

建议先补安全错误分类与独立于源码新鲜度的未知结果登记，再实现共享JSON流式聚合（保留thinking，区分首包/最近包/总预算，只有完整正文且正常结束才解析，未知不重发）；随后按optimize-prompts流程修复正常contract字段投影并验证真实输入合同。审阅thinking强度保持用户选择，不自动降低max；模型接受额度不等于必须生成满额度。

官方依据：火山方舟深度思考文档建议长超时（示例1800秒）且说明可用流式聚合减少非流式失败无内容的问题；GLM-5.3文档说明思考强制启用、low/high/max默认max，支持流式与JSON。来源 https://docs.volcengine.com/docs/ark/deep-thinking?lang=zh ，https://docs.bigmodel.cn/cn/guide/models/text/glm-5.3 ，https://docs.bigmodel.cn/cn/guide/capabilities/streaming 。这些是能力说明，不是本机原失败的供应商证据。

## 已实施（用户随后授权处理）

上面的建议已实施为契约0.9.44：必要输入字段投影、流式正文聚合、1800秒总预算与120秒无数据等待、安全异常分类/回执、正常界面进度。思考强度与65536额度保持用户设置。单元与界面回归通过，详见本机 handoff。20:41:00的新模型/输入版本正常请求首次chunk1.249秒，随后持续思考；20:45:06为245.989秒/62821思考字符/正文0。这为修复版请求提供了持续计算证据，但仍不能回溯确定旧600秒请求的底层错误；真实完成结果尚待核验。

20:49:55该真实请求完成：首次正文513.147秒，全部535.124秒，finish_reason=stop；completion40555 tokens，其中reasoning37777（约93%），prompt3598，total44153，7787正文字符。第一轮结构/语义设计通过，自动进入设计图片请求。新版本有效，但输入和传输同时改变，不能把成功单独归因于某一项，也不能将旧GLM600秒错误确认为同一根因。额外保存去敏指标 outputs/a06-local-normal-20261014/glm-real-plan-stream-completed.json；不保存思考正文。
