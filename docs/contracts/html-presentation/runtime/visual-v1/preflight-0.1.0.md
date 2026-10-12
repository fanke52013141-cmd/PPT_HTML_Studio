# HTML 按目标预检 0.1.0

2026-10-12。HPS-009/011/013/014/017；S00 定义卡。

| 定义项 | 约定 |
| --- | --- |
| 身份与作用域 | hps.html.preflight 0.1.0，本地 HTML 前提条件检查 |
| 输入 | target、可选实际 scene、run_dir、现有输出目录、空间预算、宿主已解析的 text/image 布尔配置就绪声明 |
| 目标 | static_html、generate_existing、generate_new_images、snapshot_pptx、video |
| 依赖差异 | 生成才要求文字配置；新图才要求图片配置；静态/PPTX 不要求音频；video 核验确认、绑定和媒体工具 |
| 本机验证 | 实际浏览器启动，主题字体通过 FontFace local 加载；提供 scene 时共享播放器检查场景与实际资源 |
| 输出 | target、ready、逐项 code/passed/message、实际 browser_executable；provider_connection_tested=false、approval_granted=false |
| 前提边界 | 配置声明不等于连接可用；预检 ready 不替代视觉/音频批准或导出门禁；未提供 scene 的静态检查仅确认环境 |
| 文件行为 | 输出目录必须存在；临时文件检验权限，检查指定磁盘预算；不修改作者文件或恢复任务 |
| 禁止行为 | 不导入 server 或数据库 composition root，不发生成/TTS/收费请求，不输出凭据和原始异常文本 |
| 浏览器解析 | 显式 HPS_CHROME 优先，非法配置阻断；否则使用已安装 Playwright Chromium，再找系统安装根下 Edge/Chrome；无用户绝对路径 |
| 兼容 | 旧 doctor 默认路径保持；新增 --html-target 分支，不改变图片后端 Schema/API，不新增运行时 Skill 加载器 |

入口：`python scripts/ppt_studio_doctor.py --html-target static_html --json`。
生成配置声明文件只能为 `{"text":true,"image":false}` 一类布尔映射，使用 `--model-readiness <file>`。
现有场景检查加 `--html-scene <file>`，资源或视频检查加 `--run-dir <dir>`，可指定 `--output-dir <existing_dir>`、`--min-free-bytes <integer>`。

此版本提供独立 CLI 与无数据库 Python 函数，不新增 Web/Agent 公共能力，不自动将全部业务请求前置到该函数；生产审阅/导出使用共享浏览器定位。正式输出继续调用原权威门禁。

实现：html_preflight.py、scripts/ppt_studio_doctor.py、html_engine/tools/preflight-browser.cjs 与 browser-runtime.cjs。验证覆盖目标依赖、缺字体、空间、缺目录、坏主题、秘密输入拒绝、真实浏览器与字体；实际结果见 S00 交付账本。
