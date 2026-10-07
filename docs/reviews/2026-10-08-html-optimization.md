# HTML 后端优化与验收记录（2026-10-08）

本轮结论：已修复本地应用的关键流程缺陷，完成可重复的工程验收。**不能据此宣布整个产品验收通过**：真实模型、数字人合成、真实课程全流程、PowerPoint 打开和用户视觉评审仍未完成。

审查输入：[外部审核报告](../plans/html-backend-development/review-report-2026-10-08.txt)、[独立代码审核](2026-10-08-html-backend-review.md)、现有开发计划及 AC01–AC20。外部报告关于文档与状态过期的判断成立；“没有代码问题”的结论没有覆盖下列实际缺陷。

本轮代码提交：`21ffb51`、`ac823f3efd5853f45f973aaa40a5ecf58fc288d9`。修改直接在唯一运行目录完成，未发布远端，未覆盖继承的其他改动，未使用原项目数据库进行测试。

## 已修复的缺陷及验收方式

| 编号 | 原问题 | 最终处理 | 验收证据 |
|---|---|---|---|
| R01 | 分镜、设计、资产服务没有串成应用生产链，运行依赖固定资产 | `html_production_service.py` 连接规划、效果图、设计参考、生图资产、受约束编译、实际渲染和保存；运行器读取项目资源包 | 五页、三种模板，真实 Chromium 渲染与透明 PNG 装载；模型使用可检查请求的替身 |
| R02 | Web 保存调用不存在的方法或错误参数 | 修正共享 store 调用、无修改保存和版本冲突行为 | Web 保存、no-op、409 回归 |
| R03 | 审阅面板挂错位置、无法可靠选择当前页、监听自身变化形成循环 | 挂载到第三步内容面板，显式刷新、页选择器、上下文令牌；取消任务和进度轮询 | 真实浏览器 6 项检查，100 次刷新稳定，无页面错误 |
| R04 | HTML 输出沿用图片确认和来源门禁 | 按后端分派，HTML 检查当前场景审阅与批准，图片路线保留原门禁 | 后端与输出测试，前端流程检查 |
| R05 | HTML 场景或资产变化不使输出失效 | 输入清单涵盖场景、主题、布局、模板、实际资源字节、字体、绑定及相关运行文件；视频/PPTX 摘要包含该清单 | 场景修改同时改变两类输出指纹，绑定修改使批准失效，无关资产不影响当前页 |
| R06 | 空场景或旧场景也可能显示已批准 | 必须对比当前已保存文档与当前输入指纹；共享锁下批准；缺失和失效返回具体原因 | 空场景未批准、过期候选 409、真实 readiness 检查 |
| R07 | Web HTML 路由未统一账户过滤 | 采用项目查询公共服务，任务状态和取消也限制项目/类型 | 另一账户返回 404；Agent 同步检查 |
| R08 | 动作按总时长比例拉伸，无法跟句子绑定 | beat ID 对应真实音频窗口，enter/emphasize/exit 显式绑定；新 HTML 视频缺少绑定时拒绝启动 | 同样 10 秒音频、不同句子起点产生 1000ms / 8000ms 动作起点；旧比例逻辑只允许显式兼容 |
| R09 | HTML PPTX 同步返回，绕开正常任务/产物/下载链 | 使用持久任务、统一登记和指纹、列表/下载/删除链 | 实际 PPTX 创建、LocalJob、登记、下载、删除；16:9 快照，不承诺原生可编辑对象 |
| R10 | 持久任务未接入，取消后晚到结果可覆盖状态 | 应用接入 worker、重启恢复与显式重试；状态 SQL CAS + attempt 校验，旧尝试不能完成新尝试 | 实际后台生产、幂等提交、取消后成功拒绝、旧 attempt 无法污染重试 |
| R11 | 效果参考是整页样图；缓存只按 ID；图片请求未带真实参考 | 独立效果样本标注 ID / CSS或SVG / 作用，内容摘要缓存；设计请求带效果图，资产请求带效果图和设计图 | MISS→HIT；请求实际 reference_paths 检查；当前库 7 项 CSS/SVG，未冒充已有 Canvas 效果 |
| R12 | 账本把 pending/blocked 混成 passed，文档和提交占位符过期 | 每条 AC 独立状态，任务汇总遵循最弱未完成项，真实历史提交替代 this-round；更新契约/交接 | task-ledger 与 acceptance-manifest 本轮更新 |

额外修复：FFmpeg 8.1 仅传颜色参数不足以写入完整视频色彩元数据，现通过滤镜和 H.264 元数据设置并以 ffprobe 验证；DOM Range 支持跨文本片段及 emoji 的 UTF-16 边界；设计简报生成后不再修改资产需求而破坏其 SHA；普通写入异常回滚场景及资源文件。

## 工程验收结果

测试隔离由 `checks/conftest.py` 管理数据库与运行目录。没有将测试项目写入用户正式数据库。

- [主回归记录](2026-10-08-html-optimization/final-regression-tests.txt)：524 passed。包含全部 HTML 测试、项目后端、PPTX 路由、迁移、生命周期、账户隔离与 Agent 集。
- [补充原路线回归](2026-10-08-html-optimization/legacy-regression-tests.txt)：31 passed。PPTX 构建/导出/前端、视频新鲜度/组件、生成控制、图片去重。
- 浏览器 HTML 面板：6 项通过；视觉引擎：13 项 / 4 场景 / 0 页面错误；visible-flow、frontend-quality、Agent 契约生成检查通过。
- Ruff 检查本轮新增服务和验收测试通过；定向 `git diff --check` 通过。
- [五页生产基准](2026-10-08-html-optimization/production-benchmark.json)：三种模板，真实资产、编译与浏览器渲染，约 0.9–2.4 秒/页。**模型提供者为替身，这不是真实模型延迟或审美结果。**过程页实际保存开始、中间、结束三帧。
- [三页视频证据](2026-10-08-html-optimization/video-benchmark.json)、[MP4](2026-10-08-html-optimization/three-page-smoke.mp4)：1600×900、30fps、H.264/AAC、yuv420p，色彩空间/传递/原色均 bt709。期望 6 秒，容器约 6.064 秒，视频流 6 秒。音频为合成静音，用于验证编码链，不代表已试听真实讲稿。本项显式测试旧绑定兼容模式，句子绑定另有独立回归。

可重复命令：

```powershell
$tests = @(Get-ChildItem checks/test_html_*.py | ForEach-Object FullName)
$tests += @('checks/test_project_visual_backend.py','checks/test_pptx_routes.py','checks/test_database_migrations.py','checks/test_pipeline_lifecycle.py','checks/test_project_lookup_account_isolation.py','checks/agent')
python -m pytest @tests -q
python -m pytest checks/test_pptx_job_construction.py checks/test_pptx_export.py checks/test_pptx_frontend.py checks/test_video_freshness.py checks/test_video_render_components.py checks/test_generation_control.py checks/test_image_generation_dedup.py -q
node checks/test_html_review_panel.cjs
node checks/test_visible_flow.js
node checks/test_frontend_quality.js
node html_engine/visual/tests/verify.cjs
python scripts/generate_agent_contracts.py --check
```

测试存在一条已知第三方 Starlette/httpx 弃用警告，不是失败；未来依赖升级另行处理。

## 公用层与风格层的归属

公用：账户与项目查询、JSON 契约、对象/动作/beat、布局槽位校验、资源质量检查、输入指纹、任务、审阅批准、视频/PPTX 和字幕时间。不能在这些服务中硬编码某一风格颜色、插画或排版。

风格：主题字体/颜色/间距/圆角/阴影等属性、效果允许范围、图标和插画规则。模板引用主题和注册布局，约束槽位种类、数量和容量。实例填内容、资产、动作及句子绑定。效果参考图、设计图、资产、关键帧、审阅与输出是可失效的派生产物。

新契约：[应用生产流程与所有权](../contracts/html-presentation/runtime/visual-v1/application-workflow-0.1.0.md)。Scene 等既有结构版本没有因为应用接入被随意改写；Agent API 更新到 1.12.0。

## 本地使用与剩余验收

关闭后从原桌面快捷方式重新打开即可加载此运行目录的当前代码。HTML 项目进入第三步，选择页面，生产→查看真实截图与问题→审阅→批准。内容/资源/绑定改变后须重新审阅批准，再进行音频绑定及输出。产物走原有任务、登记和下载流程。

本轮只读检查显示：LLM 与图片模型名已有配置，**两类 API 密钥均未配置**。因此不能补齐真实服务生成质量。后续依次执行：

1. 配置真实提供者，在应用里生产至少五页真实课程，覆盖不同结构；记录实际发送的效果/设计参考与产物对应关系，核验成本、失败重试和耗时。
2. 用户按原科普参考评审构图、文字拥挤、插图对应、可实现性及底部字幕区；批准只是工程门禁，不能替代人的审美判断。
3. 使用已有 TTS 方案生成真实讲稿音频，核对每句对象出现/运动/消失、字幕和完整多页视频；使用已有数字人接口合成并核对。
4. 使用 PowerPoint 打开实际导出的 PPTX，验证字体/画幅/图像及阅读效果；该输出是静态快照型 PPTX。

当前限制：面板提供页选择、生产、审阅、批准、取消，完整可视化对象/动作/语义锚点编辑器仍需补齐；模型读取全局配置，项目独立模型绑定尚需产品化；取消在阶段边界生效，不保证中断远端模型请求；资产默认中心锚点仅为几何信息；普通异常可以回滚，多文件写入期间进程崩溃尚无事务日志自动恢复，需要重新审阅/生产。Agent 任务路由暂借用 Web 入口，后续可下沉为统一薄服务以降低耦合。

这些限制和未通过项在验收账本中保留，不应被后续 Agent 当作已完成。
