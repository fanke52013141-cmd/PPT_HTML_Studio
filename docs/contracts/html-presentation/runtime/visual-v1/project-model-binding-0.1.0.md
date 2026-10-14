# 项目模型绑定 0.1.0

2026-10-14 图片参数增量：固定/继承连接public_config中的resolution/quality（兼容toapis_*别名）冻结为image_resolution/image_quality，进入summary.parameters。分辨率限1K/2K/4K，质量按已有提供方枚举校验；实际HTML图片请求使用冻结值。省略保留原1K/low，含参数的身份随配置hash变化，旧请求与批准不自动迁移。

范围：N03，HTML guided 生产文字/图片提供者。关联 HPS-014–017、HPS-026、HPS-030。不改变 image、TTS、创作包和全局连接的既有实时引用行为。

## 输入、持久化与优先级

`planning/project_model_binding.json` 保存 `schema_version=0.1.0`、整数 `revision` 和 `bindings`。text/image 各有 mode：`inherit`（显式全局）或 `fixed`（连接快照）。API 另接受 `legacy`，移除该用途覆盖并恢复创作包/全局继承。API 固定绑定输入仅 connection_id，不接受客户端提供的 endpoint、凭据或快照。expected_revision 必填；过期写入返回 409。

无文件的旧项目：复用创作包 `model_bindings.storyboard`（文字）和 `image_generation`，缺项才用全局；不静默改变旧项目。固定绑定在服务端复制 provider/model/endpoint/public_config/credential_ref 和 connection_id，凭据仅保存引用。全局连接变更不改固定项目；密钥轮换在下一任务解析引用时生效。已提交任务的密钥与配置留在内存，不持久化密钥。

相同 mode/connection_id 保存是 no-op，明确 rebind=true 才重新抓取同一连接。更换只影响未来生成，保留已批准作品、音频和运行任务。固定连接后停用/归档仍保留项目快照；凭据被删除则明确失败，不回落全局。损坏/未知版本文件失败，不猜测继承。

## 运行与公开边界

`freeze_project_models(project, required=("text",))` 在提交时返回 text/image 不可变运行值；缺少可选图片配置保留错误，实际需要生图时失败。返回 `summary()` 仅来源、连接 ID、提供者、模型、配置 hash、就绪状态和绑定修订；不返回 endpoint、公有配置或凭据引用。图片缓存应包含配置 hash，任务 submission_key 与持久 payload 包含 summary。

`configured_image(..., model_binding=...)` 消费冻结图片值，不能再查询全局。文字通过已有 JSON service 的 model_binding 参数消费。主对话负责生产任务接入和 Agent 同步；模块实现不等于完整产品接入。

## 失败、兼容与验证

固定绑定类型错/连接不存在/不可新选：400；修订冲突：409；账户鉴权复用 project_or_404。新文件不需数据库迁移，不写旧创作包。保存不修改现有场景、批准、音频、输出；新生成成功后的失效仍由现有生产服务负责。

正常/边界样例：两个项目不同模型、旧包继承、显式全局继承、同连接 no-op/重新固定、并发 revision 冲突、连接编辑后固定值不变、冻结后密钥/全局变化不影响任务、缺凭据无回退、错误不泄密、图片附件实际传递。实际测试与未验证范围见 model-binding-handoff.md。


## 0.2.0 增量：规划与多模态分开（2026-10-14）

关联 HPS-014–017、HPS-026、HPS-030。planning 是可选的独立文字规划用途，仍选择 text 类型连接；text 保持设计理解、受控还原、截图审核与局部修复用途，image 保持图片生成。Web/Agent/MCP/CLI 共用 ProjectModelBindingUpdate，新增 planning 选择并保留修订冲突与显式 rebind。旧客户端省略 planning 时保留既有配置；legacy 清除项目覆盖。含 planning 的保存采用 schema_version0.2.0，继续读取0.1.0，旧格式不自动改写。

项目 fixed 优先；HTML 阶段默认 html_planning_connection_id / html_visual_connection_id 仅用于未固定用途。未配置独立 planning 时沿用有效 text；阶段默认连接失效则报错，不回落其他供应商。旧项目的固定模型保持原值；任务启动前冻结 planning/text/image，并把独立规划身份加入任务/候选/快照来源。连接变化阻止原任务冒充原请求恢复，不修改已批准音频或作品。

连接 public_config 可提供 max_tokens、reasoning_effort(low/high/max)、temperature(0–2)、supports_images 布尔值。有效参数进入冻结指纹和公开摘要，密钥仅在凭据库保存引用。GLM-5.3 系列请求显式开启 thinking，默认 reasoning_effort=max，格式回退和 JSON 修复同样保留思考；glm-5.3 收到图片在本地拒绝。2026-10-14用户要求拉满输出额度：冻结绑定及JSON适配器上限同步到65536，已有低额度及显式任务max_tokens_limit保持；已冻结/已提交请求不追改，固定项目须明确rebind后才消费新连接参数。65536是请求额度，不保证供应商一定接受或返回同等长度，真实调用另记。

规划使用专用 generator；设计/视觉阶段继续使用原 json_generator；两者均经原任务阶段回执，未知上游结果不盲目重试。正式规划 Web/Agent 共用入口也解析冻结 planning。工程连接验证不代表规划语义、设计还原或视觉签收通过。

2026-10-14 本机验收修复：共享generate_scene_plan显式传request_timeout=600，包括最多一次结构修复；请求前证据登记实际600秒参数。原先未传参数时落入JSON适配器120秒默认。保持正常思考参数和严格结构检查，超时异常直接退出，不当作结构失败重试。旧unknown仍按原任务核验，不能通过源码超时修复或新快照补发同一语义请求。
