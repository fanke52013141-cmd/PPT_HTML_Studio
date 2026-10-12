# 本地 HTML 输入快照与静态 QA 0.1.0

2026-10-12。HPS-009/011/013/014/016/017；S01 与 S04 首版定义卡。

| 项目 | 定义 |
| --- | --- |
| 身份 | hps.html.input_snapshot 0.1.0、hps.html.quality_report 0.1.0 |
| 输入快照 | generation：分镜页、严格生产选项、最小模型身份、实际规划代码、注册定义、分类参考 PNG、明确提供的已有素材；不虚构未来生成素材 |
| 渲染快照 | render：已保存 scene、当前 revision、选中主题/布局/模板、编译 bundle、Schema/效果、图片实际字节、字体实际字节及已有来源/编辑/binding 记录 |
| 目标 | html_preview 使用作者时钟；video 另执行原视觉、实际分镜完整页面集合的音频确认与合法绑定门禁，保留音频/文本/元数据/字幕/时间戳并用原 binder 解析派生 scene |
| 所有权 | 作者 scene 仍由编辑器拥有；快照只读、派生，不成为第二份正文或新的任务状态源 |
| 身份 | canonical JSON 与逐文件 SHA-256 生成 snapshot_id；source_revision 参与身份；快照不含明文凭据 |
| 并发 | 同项目锁内建立快照；拷贝前后校验实际源文件散列与 revision。同尺寸且恢复 mtime 的变化仍被发现 |
| 文件 | 项目 planning/html_visual/builds 下分配临时目录，校验完整后 rename 为内容身份目录；不使用硬链接；已存在且完整的同身份快照复用 |
| 预算 | 单文件不超过 64 MiB，总计不超过 256 MiB，清单不超过 512 项；坏路径、目录逃逸、缺文件、哈希不符明确拒绝 |
| 字体 | 首版只接受当前已支持的 Microsoft YaHei，复制本机三份字体到本地快照，通过 @font-face 先加载，再启动原共享播放器；font_scope=local_only，不声明可再分发 |
| HTML | 原 bundle 渲染器与当前选中定义，使用冻结图片 pack，不依赖项目实时素材；网页内编辑只产生临时预览，作者持久编辑仍走原 API |
| QA | snapshot_id、revision、scene_digest、checker 代码/浏览器版本、问题 ID、对象/时间定位和 evidence 散列；工程、视觉、音频、导出分别记状态 |
| 首版检查范围 | 静态终态测量和截图；连续时间未验证，音频/导出未测试，视觉 pending_review。没有自动视觉批准 |
| 兼容 | 独立 Python/CLI 原型入口，不改 Web/Agent 响应、scene 格式或旧审批指纹，不接管 LocalJob；正式视频执行接线在 S05 |

manifest 自身的身份可检查，文件逐项检查；它不是数字签名，不作为外部来源可信性的证明。模型只能提供结构化作者输入，不能生成或加载任意渲染脚本。运行目录来自受控本地工程。

QA 验证必须给出要匹配的快照与证据目录；报告内容改动、换成另一快照或截图内容改变均无效。验证 valid 表示对应关系未损坏，不表示工程状态通过，更不表示用户批准。原编辑器保护、409 及有界修复逻辑不因报告归一化而改变。

CLI：scripts/html_snapshot_check.py 的 freeze-generation、freeze-render、verify、review。创建需要 --run-dir 与 --expected-revision；生成快照加 --contract，渲染加 --slide；检查加 --snapshot。错误只返回受控代码，不回显原始秘密。

实现：html_build_snapshot.py、html_snapshot_review.py、html_quality_report.py 与 review-snapshot.cjs。首版没有让自动生产任务消费生成快照，也没有实现图恢复或完整的无进展修复策略；这些属于 S02、后续 S04 与 S05 接线。
