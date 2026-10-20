# GLM 原生参数修复与真实复测

用户明确指定官方聊天接口、thinking enabled、max_tokens=65536、temperature=1.0。契约0.9.107，API1.59.0字段保持，无数据库迁移。

## 已修改

- html_agent_jobs.execution_profile统一真实参数；GLM-5.3系列取消8192硬截断，使用冻结连接额度，上限65536。其他模型维持原8192/off兼容配置。
- html_pi_json与局部工具worker使用同一profile。agent_runner在SDK实际payload中写入thinking.type=enabled、max_tokens、temperature，删除冲突的max_completion_tokens/reasoning_effort字段。SDK通用thinkingLevel仍是内部会话选项，不能用它推断供应商实参。
- 项目文章/分镜候选优先使用项目planning连接；看图/局部修复使用text视觉连接。Web与认证Agent共用dispatch，幂等恢复先于重新解析模型。
- 本机两个GLM连接已设置65536与温度1.0，密钥只通过原credential_store更新。data/credentials.json及data/model_connections.json保持Git忽略，无凭据进入源码或本文件。

## 验证

checks/test_html_pi_agent.py与checks/test_html_pi_workflows.py：32 passed。新增真实Pi SDK对本地HTTP服务的出站断言，覆盖JSON和完整工具循环：thinking enabled、65536、温度1.0。checks/agent/test_html_pi_routes.py：2 passed，验证文章采用glm-5.3规划连接、原Web/Agent状态与候选保留。合计34项，已有Starlette弃用警告。相关Ruff、Node语法及定向diff空白检查通过。

## 真实课程新参数对照

本机证据目录：outputs/pi-glm-native-20261020，使用独立trial.db与runs。原课程为A06 Token五页课的slide_003。沿原显式设计复用入口生成新当前key `fee79faf399bf563060834d0d0864d2411677be7fcb543720c68464fa217a626`，没有生图/规划调用，原PNG字节保留。新参数与新模型身份独立于之前8192试验，不重放原未知任务。

- Legacy：官方接口200，设计理解561.567秒后正常stop，返回完整unsupported对象；31,437总token，21,527输出token，其中21,250推理token。判断设计图新增“输入/输出”标签和总结栏左侧文字，但冻结计划缺少相应对象/字段，路由planning。该判断仍是模型结论，需人工核查是否把重复参考文字误判为必需语义。
- Pi：1次模型调用、0次submit_json，600.650秒后阶段终止；任务外部状态unknown，usage/cost为空，lookup_supported=false。请求身份 `c34efacbe9492d5e91520356837917c6df344bfc6fc8b190cc4c22101a2e8769` 为应用生成的请求身份，不承诺可在服务商后台检索。
- 两边作者revision=0，无新场景、无批准、无独立素材调用。不能将参数修复、HTTP200或完整unsupported返回称为新页验收成功。保留Legacy默认。

## 后续

先核查设计图新增标签与冻结计划的关系：必要语义应回规划补齐；仅重复信息应按权威内容策略处理，不以单例放宽通用门禁。Pi此次请求结果未知，禁止原样自动重发。新实验先形成有实质差异且当前有效的计划/设计输入，并分别记录Legacy/Pi预算与结果。仍需实际HTML截图、播放和用户审美验收。

本批未commit/push、未重启正式服务；运行服务是否加载新源码须另外核实。
