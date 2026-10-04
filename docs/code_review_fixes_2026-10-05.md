# 2026-10-04 代码审查整改结果

日期：2026-10-05。依据 `docs/code_review_2026-10-04.md`，在已有未提交改动上核实并修复；未提交代码或启动第二个应用服务。

## 功能与可靠性

| 项目 | 结果 |
| --- | --- |
| B1 数字人超时 | 两处整段音频请求使用 `timeoutMs: 900000`；共享 transport 回归检查验证实际定时器为 900 秒。 |
| B2 背景跨项目写入 | 使用 `PPTStudio.runtime.state.currentProject`，移除 sessionStorage 兜底；弹窗绑定打开时项目，迟到读取和切项目后保存不会应用到其他项目。真实 Chrome 回归验证 A→B 切换不写入，重新打开 B 后只写 B。 |
| B3 子进程泄漏 | 调速、旁白初始化、Manifest 初始化复用 `run_subprocess_killable`；超时返回码转译保留接口行为。POSIX 子进程创建独立 session，避免误杀父进程组；真实短超时测试检查进程退出。 |
| B4 合成路径 | 输出固定为项目内可下载的默认 MP4；底层视频必须是当前项目内存在的 MP4，拒绝越界和输入输出同路径。解析后校验也拦截符号链接逃逸。 |
| B5 AI Mask 假完成 | 仅实际写入自动 Mask 的组计入 updated；全部被人工保护的组计入 skipped，不能制造 AI 完成态。 |
| B6 TTS 暂存泄漏 | 系统 temp 创建暂存目录，整个准备和执行生命周期由 finally 清理，包括命令准备失败；跨盘发布先复制到目标同目录临时文件，再原子替换，失败保留恢复逻辑。补充 ignore。 |
| B7 Prompt 门禁 | 使用 v8 ContractVersion 识别当前协议，保留独立的映射行为验证；同时清除另一旧脚本中已过期的 v7 文案断言。 |
| S1 工作流候选 | `repository_paths.resolve_comfyui_tts_workflow_path` 被预检、缓存签名和实际合成共用，统一相对路径和 URL 处理。保留 legacy data 优先项及 config fallback，避免覆盖用户自定义工作流。 |
| S2 渲染状态 | 提交响应为 queued，与提交阶段持久化状态一致；worker 开始后轮询显示 rendering。 |
| S3 DocLayout 默认 | fallback 使用 DEFAULT_SETTINGS，去除相反的硬编码默认值。 |
| S4 标注输入证据 | AI 条目和快照携带真实 image/narration hash；移除 annotation ID 分配时的输入 no-op。 |
| S5 重启恢复 | annotation runtime 初始化时显式调用 interrupt_orphaned，再创建任务管理器。 |
| S6 强调密度 | EMPHASIS_LIMITS/EMPHASIS_LEVELS 成为唯一来源，规划、Prompt、服务和任务复用。 |
| S7 媒体工具 | 数字人和色彩验证复用 scripts/media_tools；共享候选包含 Remotion、数字人环境变量和既有 runtime 路径。 |
| S8 架构门禁 | 保留现有限额；添加限额变更说明要求，架构门禁通过。已有未提交的 Storyboard store 拆分被保留，本次未扩大 server 或 engine。 |
| S9 规划文档冲突 | 两份历史规划明确以 ui-spec 为准，冲突条款不再作为恢复旧样式的依据。 |
| S10 资产环境变量 | 数字人 launcher 接受 PPT_STUDIO_ASSETS_DIR，专用变量和显式参数优先；environment.md 补充优先级。 |
| S11 未收集的检查 | 22 个旧脚本改为 pytest 可收集的函数，同时保留直接运行入口；原来发现阶段执行的断言现在在测试执行阶段运行。更新收集门禁。 |

## 前端与清理

- AI Mask、项目配置、风格参考、背景、一键生成和旁白保存统一使用 API；FormData 直接复用已有 API.post 支持，避免引入无调用者的 transport 接口。
- 4 份字符转义实现复用 escHtml，保留参数转字符串语义。
- AI Mask 预览事件已有幂等保护，保留该改动；删除 500ms 反复 boot，改为 DOM ready 初始化。
- One-click boot 添加幂等保护，避免 visibilitychange 重复注册。
- 增加 transport ownership guard，并补充 12 个扩展模块和 flow 的职责；event_bindings 的范围明确为共享核心启动和绑定。
- 删除已核实的未消费常量、参数、依赖字段、latest_active、前端 generation requirement/roles、旧逐页数字人入口、旧制作方式入口和 course 无用计数。
- 检测阶段不再落盘无人消费的 elements/*.png，保留 element ID 和按需视觉裁剪。

## 保留项与复核差异

- 大范围 CSS 删除未执行。style/stitch/annotations 正在承载已有未提交 UI 调整，报告没有给出可逐项应用的完整 231 条规则清单；动态 class 和层叠覆盖不能仅凭零静态引用删除。
- 当前 step2-slide-card/fields 包裹真实表单，不删除其节点及配套布局；需要独立视觉比对后再清理。
- `UI优化方案.md` 和 `hand off.md` 实际被 `scripts/build_portable_package.ps1` 引用，报告的零引用结论不成立，保留文件。
- `checks/rebuild_project_reveal.py`、`checks/run_project_ai_mask.py` 是可直接调用的项目维护 CLI；没有内部调用者不足以证明不可用，保留。
- Toast 仅错误显示策略保留；账号默认配置入口、Prompt 刷新入口和 JOB_STATUS_UNAVAILABLE 等报告明确要求产品决策的项未盲删。
- 历史空目录 `tts-stage-7zmwa62_` 的删除被自动审批以 `blocked by policy` 拒绝，未提供具体原因，目录保留；运行时 finally 清理及 ignore 已修复。
- 不删除历史 ffmpeg 路径探测；已安装在该位置的用户仍可复用。共享解析消除差异比删除兼容路径更稳妥。
- 测试全程使用 conftest 的临时数据库/项目目录；浏览器测试运行静态 fixture，未操作真实项目。

## 验证

- `python -m pytest checks -q --disable-warnings --tb=short`：1486 passed，8 skipped，2 warnings。
- `python -m ruff check .`：通过。
- 全部前端 JS `node --check`：通过。
- 12 个 `checks/test_*.js`：通过，其中浏览器检查使用本机 Chrome 和 Codex bundled Playwright，未安装新依赖。
- 新增/更新行为回归覆盖路径越界、默认合成输出、工作流 fallback、实际子进程超时、人工 Mask 保护计数、TTS 准备异常清理、输入 hash、跨项目旁白保存和背景弹窗保存。
- 静态扩展引用检查、source registration contract、架构大小门禁和 diff whitespace 检查：通过。
- 未调用真实云模型、TTS 服务或长时视频渲染；这些集成依赖没有在本次整改中消费。
