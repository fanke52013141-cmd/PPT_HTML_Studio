# 局部修复输入与流式观测 0.1.0

HPS-007/009/010/013/015—018，包0.9.111，2026-10-20。内部Prompt0.3.4/0.4.3，API1.59.0保持。

## 定义与责任

- html_repair_feedback只投影模型输入。当前scope、实际问题对象及显式关系端点保留几何/文字测量；所有截图时点的全邻居boxes及全部箭头/标注几何仍提供，原始报告留盘。全页检查对象对数量保留，送模列表只含涉及scope的对；全页原检查不缩范围。binding只传scope动作，呈现目录只传适用节点类型；文字内容、动作身份、保护路径、截图/时间对应和绝对补丁规则保持。
- html_scene_repair只对显式supports_stream_progress的生成器开启已有stream_output，支持functools.partial。不改变模型、thinking、温度、输出额度、等待时间或两轮预算。局部记录在原records下；无能力标记的第三方生成器保留原签名。
- json_llm_transport保留原流聚合权威，增加收到HTTP响应头的时点及经过窄字符/长度检查的x-request-id；不复制其他头或凭据。只在完整stop后交付JSON，usage只传原安全计数，截断/中断不作为JSON修复输入。读取静默与总流预算仍分开，不声称SDK读等待等于严格总墙钟截止。
- agent_runner/progress.mjs是纯SDK事件计数；只发送首个SDK可见事件、首正文/工具参数、最后事件时间和文字/推理/参数长度，至多约5秒一次及必要边界。SDK可见事件不是TCP首字节，不能假称网络阶段定位。字符计数不能换算token、费用，也不据此跨适配器评价能力。
- PiJSON持久本次调用的stream-N.json，在静默等待中每5秒更新本地elapsed/silence；按白名单接收事件数值和状态，日志不保存思考、正文、工具参数或异常正文。阶段/任务超时保持原守卫，失败仍unverified，不自动重发。进度回调失败也必须回收子进程/管道。usage和候选权威保持，流进度不授予批准。

## 兼容与验证

无作者Schema、Agent请求/响应字段或数据库迁移。PiJSON公开supports_stream_progress使原ProductionStages接入既有model_stream回调；新模块加入runner_identity和生成源码闭包。旧快照/阶段身份按原规则过期，不反签旧unknown请求。

本地真实SDK+模拟HTTP/SSE正反例覆盖图片、submit_json、原生thinking/65536/温度保持、工具参数进度、阶段timeout和无重试；纯事件测试检查节流与正文/思考不外泄。原真实页面只重放输入与原浏览器检查，不调用模型。输入字节下降只作为负载数据，不宣称token/费用/真实延迟已下降。
