# 标注工作台与定位配对执行器交接（2026-10-25）

实现用户本轮指定的两个功能：项目内可视化评测标注、通过既有模型接口执行定位前后配对实验。契约包0.9.118、Agent API1.64.0。定义见[标注与实验规范](../../contracts/html-presentation/runtime/visual-v1/annotation-experiments-0.1.0.md)。

## 界面使用

在HTML项目“设计图生成”页面展开“评测标注与配对实验”，点击“读取评测数据集”。该功能为项目工具，不改变原八步流程。

### 创建和标注

1. 展开“从本项目已保存页面创建数据集”，输入英文小写/数字/连字符的数据集名称，选择页面，填写各自课程及开发/留出划分。相同课程不得跨开发/留出，同一原图不能重复混入分母。创建只复制已验证当前设计PNG与已保存scene，不调用模型。设计过期须先沿原设计/原图复用流程刷新，不自动重签旧设计。
2. 选择数据集和样本，打开原图标注。工作台仅显示原图，不以当前HTML截图或坐标生成gold。选择对象/部件，拖框并填写实际转录与身份依据；多行可新增区域。背景/边框另选“框选容器”；未找到、不确定有明确状态。
3. 点击“使用标注，返回工作台”，填写标注者，点击“保存标注草稿”。允许未完成草稿，但不能进入实验。每次保存核对revision、源hash及固定对象/part身份；冲突须重新打开，不覆盖别人的版本。
4. 另一位复核者核对原图后填写姓名及至少8字依据，选择“复核通过并封存”或“要求修改标注”。封存要求文字、容器及未找到状态完整、像素框合法。旧版本保留；再编辑会产生新草稿，不改旧gold。

姓名为人工声明，实际登录账号另外留存于版本审计；不同姓名不等于认证了不同账号/真人。标签reviewed不是生产画面视觉批准。

原CLI导入工具仍可使用，输出目录放在本项目`planning/html_visual/evaluation/datasets/<dataset_id>`。应用工作台要求每集最多40页；导入后仍要完成工作台草稿和独立复核。历史标签不因文件自称approved而绕过该流程。

### 运行实验

1. 全部样本都已复核后，展开“运行固定样本配对实验”。选择before/after协议0.5.0或0.5.1、项目text或planning模型角色，以及重复次数1—5。所选项目模型须明确supports_images=true。只运行原图定位协议，不执行整页生图、TTS或视频流水线。
2. 点击“开始配对实验（调用项目模型）”明确提交。两组模型摘要、Prompt字节、样本/gold及算法源hash随实验冻结；不接受任意endpoint、密钥、Prompt或可执行代码。相邻样本/重复轮采用AB/BA交替顺序，不能漏掉失败/unknown/not_run后只算成功页。
3. 当前样本、组别、总数、已完成数、模型/HTTP计数及安全流式进度可查看。请求经过原JSON适配器和网关治理；原格式回退及JSON修复每次真实HTTP均计量。单模型调用不等于单HTTP请求。界面默认按完整分母预留模型次数与两倍HTTP次数，API可明确调整有界额度与时间。
4. “停止配对实验”沿原LocalJob取消。停止协作发生在安全检查点；远端已提交请求可能完成，不声称已取消供应商计费。停止后不进入下一调用、不自动重发。取消的原始部分证据保存在实验目录，任务保持cancelled。
5. 完整返回时显示分开发/留出的对比报告。失败/unknown时任务停止或失败并保留完整分母；费用未知为null，不估算。工程观察、参考像素误差与真实视觉/语义批准分开。A/A同配置控制允许，不宣称是优化提升。

同配置重复提交返回原任务。已知完整结果在数据库终态丢失时，可由精确回执恢复，零模型重发；恢复会核验冻结原图/scene/gold、Prompt、源hash、实际请求、响应、逐次回执及最终报告。任一损坏阻断。unknown依据“原图hash＋原始对象/part投影”阻断，不能靠换模型、协议、标签版本、数据集名称或目录绕过。

## 自动化接口

Web：GET `/api/projects/{project_id}/html-evaluation`，POST `/api/projects/{project_id}/html-evaluation/action`；工作台HTML为按项目授权的只读沙箱入口。Agent使用相同模型，路径前缀为`/api/agent/v1`。MCP为`ppt_html_evaluation_read`与`ppt_html_evaluation_command`。SDK对应`html_evaluation_read`、`html_evaluation_command`。

```powershell
python -m cli.pptctl html evaluation-read --project <project_id>
python -m cli.pptctl html evaluation-command --project <project_id> --file <command.json>
```

命令文件是`{"command": {...}}`，action枚举create_dataset、read_case、save_labels、review_labels、start_experiment，详细必需字段从共享EvaluationCommand Schema获取。例如：

```json
{
  "command": {
    "action": "start_experiment",
    "dataset_id": "science-reference",
    "before": {"protocol": "0.5.0", "model_role": "text"},
    "after": {"protocol": "0.5.1", "model_role": "text"},
    "repetitions": 1,
    "max_model_calls": 8,
    "max_http_calls": 12,
    "total_seconds": 1800,
    "request_seconds": 600
  }
}
```

默认8次模型调用只覆盖最多4页×2组×1次；额度不足在调用前拒绝。任务状态和取消沿原`html-review/tasks/{job_id}`接口。未知请求无通用“重试”按钮，不换目录清预算。实验记录位于`planning/html_visual/evaluation/experiments/<key>`，标注版本位于dataset的annotations子目录，不进入作者scene/音频/批准文件。

## 验证与源码复核

最终结果：7组工程验收180项全部通过，执行前后源码一致且二次verify通过；原10个浏览器基准符合成功/预算/保护等预期。Agent全套464项通过；项目模型绑定、快照和生产恢复41个唯一回归用例完成验证（初跑40通过、1个夹具准备错误；同用例固定源码重跑通过，原错误保留于regression.xml，逐项对应见regression-resolution.json，不宣称初跑全绿）。各组有重叠，不相加。

原69项仍为12 passed、57 pending；新工具及受控返回不替代真实模型、人审和发布证据。最新AC报告和账本已按本轮封存包更新。

界面实际浏览器截图在`outputs/evaluation/final-browser-evidence`；受控实验的冻结输入、实际出站字段、逐次HTTP/usage与精确回执示例在`outputs/evaluation/final-experiment-evidence`。这些是注入返回的工程证据，mode为injected_response，不计作真实模型实验。用量汇总覆盖全部HTTP；任何一次缺失usage时该次模型调用总量null，分次已知记录继续保留，费用始终不推测。

最终统一验收包为`outputs/evaluation/acceptance-complete`；其manifest封存执行时源码、JUnit和原浏览器基准。专项包括真实浏览器保存两页/独立复核/排队取消、Web/Agent同构与跨账号隔离、真实HTTP回退/修复计数、unknown及改gold版本阻断、冻结/预算/迟到取消、完整回执恢复和损坏证据拒绝。单独回归项目模型绑定、原快照与生产恢复，Agent全套及规范quick另有记录；结果和hash索引见`outputs/evaluation/delivery-summary.json`。

```powershell
python scripts/verify_reconstruction_v2_acceptance.py --verify outputs/evaluation/acceptance-complete
python -m pytest checks/test_html_annotation_store.py checks/test_html_evaluation_execution.py checks/test_html_evaluation_api.py checks/test_html_json_observer.py checks/test_html_evaluation_browser.py -q
python -m pytest checks/agent -q
python scripts/run_checks.py --level quick
```

复核按正确性、可读性、架构、安全和性能五轴执行：标注写入独立owner，保存与封存采用原项目锁和版本/源守卫；实验复用原worker/store/模型/JSON服务，HTTP观察器为任务ContextVar，默认空，不猴补全局客户端；前端仅原API、安全DOM和带nonce的沙箱消息，切页移除监听与定时器。有限数据集、矩阵、调用与时间额度；provider错误不把密钥或原始异常文本写进公开状态。请求只发送原图和必要对象身份/准确文字，不发送gold或HTML几何。没有新增生产作者保存或批准路径，下游失效仍由原生产保存服务处理。

本轮验证使用隔离数据库、runs及受控返回，没有真实付费供应商调用。测试中的Alice/Bob与模型返回是夹具，不代表实际人工标签或真实准确率。没有提交、推送、服务重启或部署；已运行服务须加载此源码版本后才有新API。真实原图标注、人审签收及实际模型比较保持独立。
