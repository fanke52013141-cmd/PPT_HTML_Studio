# Legacy / Pi 真实评测：尚未形成配对 · 2026-10-20

基于main `00fb81d43c77968a9e0bc734a75a2fd44689457c`及累计本机未提交优化。应用源码为`D:\Program Files (x86)\PPT_HTML_Studio`，附件工作区为`C:\Users\Administrator\Desktop\html动画\PPT_HTML_Studio`。本批新增评测工具与文档，合同包0.9.110/API1.59.0保持。

## 数据与判断

本轮真实发起模型请求，没有预设修复补丁。**没有完整配对，不能判定Legacy或Pi谁更好，保持Legacy默认。**

| 批次 | 页面/适配器 | 等待配置 | 任务总耗时 | 发起次数 | 终态 |
| --- | --- | --- | --- | --- | --- |
| 首批 | slide_001 / Legacy | 180秒 | 186.251秒 | 1次HTTP | APITimeoutError，无输出/用量 |
| 独立新页面 | slide_003 / PiJSON | 600秒 | 604.243秒 | 1次SDK model_call | 阶段timeout，0工具交付，无token回执 |

首批Legacy实际HTTP等待180.769秒，其余时间含原检查/宿主工作。Pi总耗时也含检查开销。SDK model_call是发起事件，不证明供应商已接收；本地timeout不表示供应商取消或未计费。两次供应商最终结果均unknown，费用null。

首批计划8项，实际运行1项，7项not_run，0完整配对。首批停止后，未重发第一页，在尚未请求的第三页单独使用GLM现有生产默认600秒等待；独立批次计划2项，运行Pi 1项，Legacy 1项not_run，0完整配对。两批页面/预算不同，不能拼为公平配对，也不计算两侧质量优劣或总体自主成功率。

当前连接在这两次任务的给定预算内未提供可验收候选，首先需要请求进度与供应商终态观测。不能推断重叠检查误报、模型能力不足、thinking参数错误，或Pi比Legacy慢。此前受控补丁2页通过不充作真实模型成功。

## 原始证据

综合报告为`outputs/repair-runner-evaluation-20261020.md`。

- `outputs/repair-runner-paired-20261020-v1/`：protocol、judgement-rules、baseline/source-manifest、report；Legacy子目录http-calls.json、business-inputs.json、result.json及原repair记录。
- `outputs/repair-runner-paired-600s-20261020-v1/`：独立protocol、baseline/source-manifest、report；Pi子目录business-inputs.json、result.json及原repair异常记录。
- 两批source_unchanged/code_unchanged均true；工作树指纹分别为`02f9f3236151fd307aee7a97719247021c9d8dfda0714d1f952dd7da6c1b4fd9`、`66c199e363f75901090cfbf0d8ed2f82dfd11cd097c0ce7c4945d433feb65f75`。实验结束后的统计边界修正和文档不反写历史指纹。

数据库、课程/资产副本、模型材料仅在outputs下，禁止提交。原配置只读，未输出密钥；未导入server、启动正式服务或写原课程/音频/批准/生产数据库。

## 工具与判定口径

`scripts/compare_repair_runners.py`默认dry-run，真实请求须`--live`；output必须新建。两页重复按AB/BA交替；`--slides`选择独立页面，`--request-timeout`显式180或600，不降低连接输出额度。每侧最多2次模型发起，Legacy格式回退/JSON修复占同一物理调用预算；Pi完整SDK由原PiJSON执行。unknown终止当前整批，不自动重放。

冻结原课程模型glm-5.3-flash、max_tokens65536、温度1.0、thinking enabled；公开配置hash见protocol.model.config_hash。原generate_repair/preview宿主、scope、只改布局/保持语义、30fps全部输出时点及动作边界检查相同，不保存候选。

本批比较原宿主上的Legacy JSON生成与PiJSON适配器，**不代表完整Pi自主工具任务或新页生产**。业务Prompt/schema/图片字节首轮hash会核对；HTTP封装存在差异：Legacy response_format/reasoning_effort=max，Pi submit_json/native thinking，不声称HTTP字节一致。当前无完整配对，不能报告首轮输入已配对一致。

失败、unsupported、无进展、格式错误和timeout留在attempted；未运行单列，不剔除unknown后只算成功。不同预算不合并，usage/cost未知不估价。旧outputs/editor-benchmark的Doubao明确参数小编辑案例与当前任务不同，不并入本轮。

## 验证与后续

新增2项回归通过：AB/BA、独立页面、计划/运行/失败分母、未运行和缺失/不同hash不算可比较。Ruff、git diff --check通过；canonical quick通过，日志`.tmp/repair-runner-paired-quick.log`。未修改生产Prompt、renderer、模型配置或默认执行器，无数据库迁移。

五维复核：运行导入前设置独立DB；复制沿原受限基准工具；原候选/检查保持权威；格式回退计预算；已发起异常均保留；缺失hash不误判一致；未提交的预算拒绝不计HTTP发起。原始回执无凭据。

下一步先补脱敏首包/首正文/推理计数、最后活动时间，以及供应商request ID和终态核对，区分排队、推理、输出和传输停滞。随后用新任务身份补足同模型同预算配对；先核对unknown，不为完成统计重发。本批不再追加模型请求，未提交/推送；源文件同步两处本地目录，运行数据仅留实际应用目录。
