# 项目模型绑定 0.1.0

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
