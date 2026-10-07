# Windows 便携文件夹交付：Agent 执行方案

编写日期：2026-10-07。源项目：`D:\Program Files (x86)\PPT_presentation_video`。

## 1. 执行目标与交付边界

你需要实际完成代码调整、依赖准备、文件夹打包和验证，最终返回可复制到另一台电脑的完整文件夹路径。不要只提供建议或只有源码的 ZIP。

本次发行版暂时关闭两个功能：数字人配置/讲解、勾画标注。保留文章、分镜、图片、AI Mask、旁白与音频、MP4 和图片型 PPTX 输出，以及课程、账号、模型连接、创作配置、风格与提示词管理。

目标平台按 Windows 10/11 x64 设计。其他系统或 ARM 电脑需要另行构建，不能宣称本包适用。目标电脑双击 `启动.bat`，不需要安装 Python、Node、FFmpeg，不需要执行 pip/npm 安装。

“开箱即用”指运行环境已准备好；云端文本、图片、AI Mask、TTS 仍需要联网及有效的服务配置。不能将当前开发机上的外部本地服务地址当成已随包交付的服务。

本方案的默认数据策略是空项目库 + 可复用配置，不迁移历史项目和作品。默认凭据策略是无密钥交付，首次填写或导入配置；若用户明确要求沿用自己的现有密钥，执行 SelfUse 模式并携带凭据。两种模式都不得把源库清空或改写。不要因等待凭据选择停止代码调整、依赖准备和无密钥版本的验证。

用户当前只要求方案；本文本身不表示已生成或已验证便携包。接手 Agent 收到“按照方案实施”的任务后执行下面步骤。

## 2. 已核实的现有基础与缺陷

| 文件/资源 | 当前情况 | 本次处理 |
| --- | --- | --- |
| `scripts/build_portable_package.ps1` | 已有复制、SQLite backup、清空目标库项目数据、路径标记、预检和 ZIP | 改造并复用，不能原样执行后宣称完成 |
| `scripts/prepare_portable_runtime.ps1` | 下载脚本的默认值是 Python 3.13.0、Node 22.22.2，安装 requirements.txt；脚本注明未端到端验证 | 优先复用实际已验证运行环境；重新准备时对齐锁文件和经验证的版本 |
| `runtime/python` | 本次检查实际为 Python 3.13.5、完整目录布局，有 Lib/site-packages | 复制后验证可迁移；不要因旧脚本注释称 embedded 就假定实际有 ._pth |
| `runtime/node/node.exe` | 本次检查实际为 v24.12.0 | 记录实际版本；保持与实际渲染验证一致 |
| `requirements.lock` | README 指定的 Python 3.13 发布锁文件 | 使用锁文件，不默认升级成 requirements.txt 的浮动版本 |
| `scripts/remotion/package.json`、`package-lock.json` | Remotion 4.0.481 | npm ci + 锁定的渲染浏览器；打包 node_modules，目标电脑不能临时下载 |
| `scripts/remotion/node_modules/.remotion/chrome-headless-shell` | 已有内置渲染浏览器目录 | 必须保留并验证实际可执行文件 |
| `启动.bat` | 直接执行 server.py，固定延迟打开浏览器，路径迁移失败后仍继续 | 改为 start_server.py，迁移失败阻止启动，按真实就绪状态打开浏览器 |
| `停止.bat` | 搜索所有命令行含 server.py 的 Python 并强制停止 | 改为只操作本包拥有的进程，防止误杀其他程序 |
| `scripts/portable_relocate.py` | 仅重写 data 中 JSON/YAML 和数据库 settings/projects 的旧根路径 | 加完整性校验、外部路径审计和失败恢复；不能假定外部资源也已迁入 |
| 旧打包 HTML 转换 | 仍匹配 digital_human 的 checkbox/creation-config-check，而当前已是 radio/creation-config-pause-item | 旧转换会断言失败；重新设计，禁止用失效正则盲改 |
| 旧打包内容策略 | 额外移除 ComfyUI/IndexTTS、改成 MiniMax；携带凭据和 Agent token | 本需求只去掉两个功能；取消未经要求的 TTS 改写，明确控制凭据和令牌 |

这些是方案编写时的检查结果；接手时仍需读取 git status、AGENTS.md 和相关最新代码。

## 3. 必须遵守的仓库约束

1. 修改落在正常源码及现有职责模块中；server.py 只负责组合、依赖配置和路由注册，不新增业务实现。不恢复 app.js、sitecustomize.py 或运行期 monkey patch。
2. 源目录的 `data/`、`runs/`、`outputs/`、账号、密钥、历史项目不能因打包被改写。数据库整理只发生在目标快照中。
3. 生产继续单机单进程；不允许自动换端口后针对同一数据目录启动第二实例。测试包使用独立目录、独立数据库/运行目录。
4. 测试遵守 checks/conftest.py 的 `PPT_STUDIO_DB_PATH`、`PPT_STUDIO_RUNS_DIR` 隔离。不得通过导入源 server 进行打包预检或发现测试。
5. 新路径常量集中在 repository_paths.py。无条件保留 migrations/ 及其 checksum，不修改已应用 SQL。
6. 用户要求的精简版允许只显示六步。这是本次发行配置；完整版本在无精简配置时仍保留 AGENTS.md 定义的八个稳定可见位置。
7. 保留 `exact_rle_mask_with_manual_corrections_v6`、原图 raw/hash 配对、音频确认及 freshness 门禁。禁止为了验收成功跳过真实渲染校验。
8. runtime、依赖、数据库、测试产物不提交 Git。可复用打包脚本、功能开关源码、测试和说明可提交，但本任务不要求自动提交或推送。

## 4. 发行配置：统一关闭两项功能

### 4.1 建议实现

新增一个独立、只读的发行配置模块（例如 `distribution_profile.py`），配置路径由 repository_paths.py 提供。打包时在目标包写入 `config/distribution.json`：

```json
{
  "schema_version": 1,
  "edition": "portable_light",
  "features": {
    "digital_human": false,
    "handwritten_annotations": false
  }
}
```

缺少发行配置的开发环境默认完整功能；存在但损坏的配置应明确报错，不能静默恢复两项功能。这里的发行开关独立于项目的 enabled 设置，优先级高于创作配置、导入配置和历史项目。

Python 后端及构建子进程读取同一份配置。前端使用由这份配置确定性生成的 `static/distribution_profile.js`，加载顺序必须在 flow.js/workflow_state.js 之前。源码版本默认完整功能，发行脚本只在目标包生成精简配置。增加新脚本标签和前端质量 ownership guard。

建议直接使用静态配置传递，避免为此次打包额外扩大公共 API。如果选择新增 API 或修改对外 schema，执行本文第 9 节的 Agent 合同同步。

不要做成“只删两段 HTML”的方案：接口、一键流程、渲染仍可能消费旧启用设置。

### 4.2 前端具体接入点

| 模块 | 必须处理的行为 |
| --- | --- |
| static/flow.js | 基于发行功能选择有效 flow；显示编号、进度分母、前后步、解锁、编辑影响提示使用同一有效 flow |
| static/workflow_state.js | projectFlowContext 暴露发行可用性；共享状态不复制功能逻辑 |
| static/workspace_navigation.js | 跳过已禁用模块的状态恢复和数据加载；旧 current_step=9/10 有明确回退策略 |
| static/index.html | 隐藏相应导航、页面、OCR 配置区、创作配置选项、输出页数字人状态等入口；保留必要兼容 DOM，或补齐空节点保护后再删除 |
| static/creation_config_management.js | 不显示/执行勾画自动化选项及 annotation/digital_human 暂停点；导入旧配置不能重新启用禁用功能 |
| static/settings.js | OCR 输入缺失时加载/保存不报错，不把其他设置清空 |
| static/output_render.js | 禁用数字人时不查询 DigitalHumanPanel，也不因模块未加载阻止视频生成 |
| static/annotations_*.js、annotation_preview.js、annotation_audio_calibration.js | 发行禁用时不注册工作区、轮询或启动任务；先解除共享引用再决定是否不加载 |
| static/digital_human_panel.js | 发行禁用时不加载或初始化；清理对其全局对象的依赖 |
| static/prompt_help.js、相关说明/创作配置摘要 | 只展示本发行版可用功能；保留旁白 AI 语音标注及 AI Mask 的帮助 |

精简版侧栏显示六步，内部 data-step/API 编号保持：

| 显示编号 | 名称 | 内部编号 |
| --- | --- | --- |
| 1 | 准备文章 | 1 |
| 2 | 内容规划 | 2 |
| 3 | 图片生成 | 3，确认仍用 4 |
| 4 | AI Mask | 5 |
| 5 | 旁白与音频 | 6，TTS/确认仍用 7 |
| 6 | 作品输出 | 8 |

特别修正：flow.js 当前 `resolveProjectVisibleStep()` 在 internal 7 + audio_confirmed 时返回 10。精简版应转到输出 8；旧 9/10 项目根据音频有效确认情况回退输出或旁白，不落入不存在的页面。对任何禁用步骤的直接导航也要处理。

### 4.3 后端和渲染具体接入点

- 数字人：在对应服务操作入口实施发行开关，路由注册继续遵守现有边界；不能只限制浏览器。`video_render_service.py` 的 `_apply_digital_human_composite()` 必须在读取/校验数字人素材前退出，避免旧设置触发合成或阻塞。
- 勾画：在 annotation 服务/任务入口实施开关，禁用时不启动 OCR、规划、对齐或 ink worker。必要的读接口可返回明确不可用状态；写入口有清楚、一致的错误。Agent adapter 直接调用服务也要受限制。
- `scripts/build_remotion_props.py` 的 `_load_annotation_timeline_for_render()` 必须在读取旧 annotation_settings 或 timeline 前检查发行开关；关闭即不输出 annotation_timeline。旧损坏文件不能使已禁用模块阻塞导出。
- Remotion 的 `src/Video.tsx`/AnnotationOverlay 可能保留以兼容完整版本；精简版无 timeline 即无笔迹。不要在仍被 import 时删除 TS/JS 源文件。
- 一键流程当前 STAGES 为 preflight/storyboard/images/confirm_images/ai_mask/narration/tts/render，没有独立数字人/勾画阶段。不要凭名称误删 ai_mask。
- `_MANUAL_PAUSE_BEFORE_STAGE` 当前将 annotation 和 digital_human 映射到 render。发行禁用时忽略这两个旧暂停点；默认不要改用户源配置文件，运行时计算有效设置。
- narration_annotation 是语音/TTS 处理，ai_mask_annotation 是图片揭示；只有 handwritten_annotations/annotation_annotation 属于本次关闭范围。禁止全局替换含 annotation 的字段或文件名。
- 直接 CLI 构建、普通视频、速度变体、PPTX、配置导入和 Agent 入口都应读取同一可用性策略。

## 5. 打包数据与资源

### 5.1 默认空项目库

使用 SQLite backup API 从源数据库生成目标快照。只读源库，不能直接复制活动 WAL 数据库后删除源 WAL 文件。

从目标快照清除项目、课程、章节、local_jobs、artifact_records、Agent 幂等记录等历史数据；按实际外键依赖顺序清理。开启外键验证并执行 integrity_check/foreign_key_check；不能将所有 OperationalError 当成表不存在而吞掉。保留 schema_migrations、有效账号及与配置对应的设置。源库整理前后业务行数应一致。

配置可能引用 account_id、credential_ref、model id；不能只复制 creation_configs 而漏掉对应账号/模型/凭据记录。无密钥模式保留必要引用结构并明确未配置状态，不能留 masked-placeholder 当真实密钥。

SelfUse 模式可携带 API 凭据，但默认不复制现有 Agent access token、访问会话和幂等记录；如用户确需继续旧 Agent 接入再明确选择。不得在日志、报告或文件清单内容中输出密钥。

源库、快照、目标包所有预检连接各自路径必须明确。旧脚本通过目标 python `import database` 做预检，模块解析错误时可能触及源库；应先断言模块 __file__ 指向目标根目录，并在独立验证副本中执行会产生数据库副作用的检查。

### 5.2 复制策略

保留应用所有必要 .py 模块/包、static、config、schemas、templates、migrations、scripts、运行实际使用的 references 资源、Python/Node 运行时、FFmpeg/FFprobe、Remotion node_modules、内置渲染浏览器、字体及可复用素材。

推荐应用源码采用明确清单 + 必需资源目录，运行依赖完整复制。至少排除：

- .git、.venv、开发缓存、checks、非运行 docs、logs、scratch/work/.tmp、历史 outputs/runs。
- 源活动数据库及 WAL/SHM、临时数据库/备份、旧交付包、下载缓存 runtime/_download。
- 数字人模型/素材/启动脚本；仅在确认无其他使用者后排除 runtime/annotation_worker、runtime/annotation_models 等专用环境。
- 演示截图、ui_static_export_images、UI 提取参考、无运行引用的调研材料；不要直接清空整个 references。
- .env、敏感导出、临时密钥文件；SelfUse 模式凭据通过明确数据步骤带入。

重要：robocopy 的 /XD 裸目录名会匹配任意深度。根目录 runs、dist、build、outputs 必须用源根拼接的完整路径排除，不能误伤 openai.types.beta.threads.runs 和 node_modules 内部 dist。保留 `.remotion/chrome-headless-shell`，不能为了清缓存整目录删除 `.remotion`。

后端轻量兼容模块先保留，重量级专用环境可裁剪。禁止根据 digital/annotation 名称全局删除模块，server 和默认配置可能仍引用其中常量。

逐项验证各文件在目标根目录内才删除，PowerShell 使用 -LiteralPath；不拼接 cmd 删除命令。对未知大目录先查引用和体积，再决定是否入包。

### 5.3 外部依赖与可复用素材

审计数据里的绝对路径及服务地址，特别是音色参考、风格参考、IP 角色、字幕字体、TTS 命令、D:\PPT_Studio_Assets、localhost/127.0.0.1 外部服务。

实际素材复制到包内对应资源目录并更新目标副本引用；包外缺失资源输出不含密钥的清单并解决。portable_relocate 只替换旧根路径，不能解决根目录之外的资源。

本次没有授权去掉本地 TTS；移除旧打包脚本“comfyui_tts 自动改 MiniMax”的逻辑。若当前有效配置依赖未随包交付的本地 TTS，先准备其他可工作的现有连接或向用户确认是否另包本地服务。不能随意切供应商后称免配置完成。

## 6. 准备离线运行依赖

优先验证现有 runtime，避免无理由重新下载/升级。把版本、路径、依赖检查结果写入构建报告。若重建 Python，使用 requirements.lock，并验证 `pip check` 及关键导入。

所有构建工具用明确路径；示例：

```powershell
Set-Location -LiteralPath 'D:\Program Files (x86)\PPT_presentation_video'
& .\runtime\python\python.exe -m pip check
& .\runtime\python\python.exe -c 'import fastapi,uvicorn,sqlalchemy,PIL,numpy,pptx,yaml,multipart,httpx,openai,onnxruntime,pydantic'
& .\runtime\node\node.exe --version
& .\tools\ffmpeg\bin\ffmpeg.exe -version
& .\tools\ffmpeg\bin\ffprobe.exe -version
```

若确需重新安装依赖，在专用构建环境执行，不默认破坏目前工作的 runtime：

```powershell
& .\runtime\python\python.exe -m pip install -r .\requirements.lock
$env:PATH = (Join-Path (Get-Location).Path 'runtime\node') + ';' + $env:PATH
Push-Location -LiteralPath .\scripts\remotion
try {
    & ..\..\runtime\node\npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
    & ..\..\runtime\node\npx.cmd remotion browser ensure
    if ($LASTEXITCODE -ne 0) { throw 'render browser preparation failed' }
    & ..\..\runtime\node\npx.cmd tsc --noEmit -p tsconfig.json
    if ($LASTEXITCODE -ne 0) { throw 'TypeScript check failed' }
} finally { Pop-Location }
```

这些命令也需要核实本地 CLI 支持和实际下载浏览器路径。保留浏览器完整目录，不只拷贝 exe。若使用嵌入式 Python，确认 import site 和应用根相对条目；若使用当前完整 Python，验证 sys.prefix、site-packages 和应用解析迁移后都留在包内，不强加不存在的 ._pth。

FFmpeg 必须有 libx264，GPU 编码只作为可选加速；普通无独显目标机能够走 CPU。第三方 DLL/VC 运行依赖需要在干净 Windows 环境验证，缺失时依法随包携带可分发组件或说明实际前提，不能依赖开发机偶然安装的 DLL。

字体沿用 portable_install_fonts.ps1 当前用户注册方案，保留字体及授权说明。需要普通用户可执行，报告其会写 HKCU 和用户 Fonts 目录；不要声称整个包完全不在系统写入。选择一个包内字幕字体实测视频，不只验证字体目录存在。

## 7. 启动、停止与搬迁

### 7.1 启动入口

改造 `启动.bat`，复杂逻辑可放在独立 `scripts/portable_launcher.py`，避免复杂 cmd 括号/延迟展开损坏含空格、中文和 ! 的路径。

顺序：定位包根 → 设置本进程 PATH/环境 → 检查可写性及必需文件 → 检查本包单实例 → 路径搬迁成功 → 字体注册 → 执行包内 Python + start_server.py → 就绪后打开浏览器。

- PATH 前置包内 Node、FFmpeg 和系统 System32，不依赖全局 py/node/npx/ffmpeg。
- 明确 DB/runs 在本包，防止继承开发环境 PPT_STUDIO_DB_PATH/PPT_STUDIO_RUNS_DIR 指向源目录；其它外部工具变量也要审计。各 env 用真实服务支持的名称，验证 subprocess 实际解析路径。
- 固定 loopback 地址；端口冲突显示明确提示。本包实例已运行时可打开现有页面；若其他程序占用则退出，不自动另起同数据目录服务。
- 原子持有“规范化包根目录”对应的进程锁，覆盖检查至退出生命周期，不能仅依赖端口检查避免并发双击竞态。
- 浏览器打开依据服务 HTTP 响应和自身进程身份，不仅是等待 4 秒；未找到健康接口时用已存在的本地页面响应验证，不凭空写一个假 endpoint。
- 文件缺失/迁移失败时停住并显示可读错误，不能继续启动损坏配置。日志保存包内 logs，错误不闪退。
- 中文 .ps1 使用 UTF-8 BOM 或纯 ASCII；旧中文 .bat 是 GBK，读取/修改明确编码。优先 ASCII .bat + Python 中文输出，实际在系统 cmd 验证。

### 7.2 停止入口

持久化本包拥有的 PID、启动时间和命令/根路径身份。停止时同时验证这些身份，防止 PID 复用；不得按 python 名称、server.py 子串或端口盲目结束程序。

优先正常关闭，让任务终态与数据库状态被保存；需要强制结束时只作用于本包拥有的进程树，明确提示处理中任务会中断。渲染/TTS 子进程不应残留，重启后 local_jobs 恢复逻辑保持工作。

### 7.3 路径迁移

保留 data/.portable_root 的旧根标记，在目标包内原子更新配置和 DB。替换后解析 JSON/YAML 验证，不把反斜杠改写成非法 JSON。校验失败不能更新“已迁移”标记。失败保留可恢复副本并可重试。

迁移覆盖实际配置字段；不做任意全文改写密钥/提示词文本。打包空库时无 run artifact 迁移；若用户另行要求带历史项目，需单独扩展到 runs 中 manifest/audio/render sidecar 等路径和资源，不能沿用空库方案宣称完成。

## 8. 打包脚本的推荐接口与执行顺序

以下是建议新增/完善的接口，目前旧脚本没有全部参数。Agent 必须实现后才能执行，不能把示例当已有能力：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_portable_package.ps1 `
  -DestinationRoot 'D:\PPTStudioDelivery\PPTStudio_Portable' `
  -Edition Light `
  -CredentialMode Clean `
  -NoZip
```

`Edition` 默认 Light；`CredentialMode` 支持 Clean/SelfUse，默认 Clean；空项目库作为本任务默认。只有用户明确选自用密钥迁移后才用 SelfUse。

打包步骤固定为：

1. 检查源版本、工作区改动、有效运行依赖、外部资源清单、空间；目标不能是源/源子目录，已存在目标默认失败。
2. 在外部目标暂存目录复制应用、运行时及允许的素材，检查 robocopy 退出码（0–7 为成功，>7 失败）。
3. SQLite backup → 仅清理目标快照 → 完整性与引用验证 → 按凭据模式整理目标注册表。
4. 写入发行配置并生成对应前端开关；裁剪专用重资源。所有 HTML 转换有当前结构断言，不能 silently skip 必须修改的入口。
5. 写路径标记、使用说明、版本/依赖清单、第三方许可证、无秘密的构建报告；创建空 data/runs/outputs/logs 等必要目录。
6. 从目标包自身运行无副作用预检；业务/渲染验收使用独立验证副本。
7. 验证搬迁和完整工作流；验证通过后清除验证副本，不把样例项目/音频/视频回灌交付包。
8. 最终目录计算 SHA256 清单并报告总体积/最大目录。先完成静态所有文件再生成清单，不把会运行变化的日志/缓存列为不可变文件。
9. 如需 ZIP 则压完整文件夹，解压后再校验关键文件。用户本次要求文件夹，ZIP 可选。

体积目标依实测说明；旧脚本 1.6 GB 是历史预算，不是已实现大小或保证。超出时查是否误带专用模型、下载缓存和旧包，不删除必要依赖来凑体积。

## 9. 验证：必须有可检查证据

### 9.1 代码回归

先跑改动相关测试，再执行 AGENTS.md 的发布检查原命令；不得因方案中未逐条复制而忽略。包括 Python compile、flow/frontend、数据库/失效/源码边界、Agent 合同、Reveal 完整性、音频确认、TypeScript。

新增有价值的用例：完整发行缺少 profile 仍八步；Light 六步与进度；音频确认后跳输出；旧 9/10 回退；禁用步骤不可导航；旧暂停点不影响一键；两个功能直接任务入口不可执行；损坏旧数字人/勾画文件在禁用状态不阻塞 render；配置导入无法重新启用；搬迁失败不提交 marker；单实例与停止身份校验。

测试运行使用开发测试环境，不为了测试工具把整个 pytest 等开发栈当交付必需项。保持 checks/conftest.py 隔离。适当执行 checks/test_visible_flow.js、checks/test_frontend_quality.js、checks/test_one_click_visible_progress.js 和相应 pytest。

任何公共请求/响应 model、capability registry 变更必须：修改 agent_contract/models.py 和相应 adapter/parity mapping，提升相关 capability version/AGENT_API_VERSION，生成 docs/agent/capability-matrix.md，并运行 checks/agent 与 generate_agent_contracts.py --check。

发行开关若不改变公共模型，可保持公共能力注册结构，但返回可预测的不可用结果；若新增 availability 字段需走上述同步。保持现有 CHECKPOINT_STAGES 映射，实际跳过的管道阶段按既有约定报告 done；本次不凭空引入删除的阶段。

### 9.2 目标包运行验证

在目标包验证副本启动，不能借源 server 或共享源数据库。流程证据至少包含：

| 检查 | 通过标准 |
| --- | --- |
| 启动 | 只用包内运行时，普通用户，无 pip/npm 网络安装，无异常控制台错误 |
| UI | 六个步骤均可访问；没有两项功能入口或后台轮询；设置、创作配置加载保存正常 |
| 双击两次 | 同一数据目录始终只有一个实例；其它程序占用端口时明确失败 |
| 功能边界 | AI Mask 和旁白 AI 语音标注仍可用；禁用功能直接调用也不启动任务 |
| 16:9 小项目 | 两页，走文章/规划/图片/Mask/旁白/TTS/确认/MP4/PPTX，真实生成可播放 |
| 9:16 小项目 | 至少一页验证画布、字幕及输出比例，不能套用横版资源 |
| 渲染 | 音频未确认仍被拒绝；确认后能导出；Reveal pipeline version 正确 |
| 画面 | 播放视频看初始背景、分组揭示、音画和字幕；没有数字人或勾画笔迹 |
| PPTX | 可打开，页数、画布比例、图片完整，无白边/错位或缺图 |
| 持久状态 | 渲染/PPTX 成功写 persistent job/artifact registry，error 清空；sidecar 存在 |
| 重启 | 项目、设置、任务与作品正确恢复，无遗留子进程 |
| 搬迁 | 把验证副本复制到不同盘符和中文/空格路径，原目录不可访问时仍能运行 |
| 停止 | 只停止当前包，不结束源项目或另一个不相关 Python 服务 |

小项目优先用人工提供/确定性本地夹具测试渲染，避免费用和输出随机性干扰；云端连接/真实生成另用用户允许的配置实测。不能用手工伪造 audio_confirmed 或删门禁替代真实确认。AI Mask 若未实际完成真实调用，在报告中单独写未验证。

基础离线验收可以预先准备图片和音频，然后断网渲染/PPTX；云端生成在线验收单列，不能将在线成功描述为离线 AI 生成。

最好在另一台干净 Windows 电脑或 VM 验证不依赖源目录、系统 Python/Node、外部 DLL/字体和安装缓存。只有本机搬迁测试时报告明确写“本机搬迁验证通过；干净目标机未验证”，不得声称完成换机验证。

生产有 mask 的样例运行后执行：

```powershell
& .\runtime\python\python.exe .\scripts\validate_reveal_scene.py --run-dir '<验证副本实际run路径>' --repo-root '<验证副本根路径>'
& .\runtime\python\python.exe .\scripts\validate_run_assets.py --run-dir '<验证副本实际run路径>' --repo-root '<验证副本根路径>' --require-layered
```

检查命令 exit code、记录结果，不只保存控制台文本。不能在真实用户 runs 下插入测试项目。

## 10. 最终交付清单及完成条件

Agent 最终回答应提供：

1. 完整文件夹绝对路径；可选 ZIP 路径。
2. 文件夹大小、构建版本/源码 SHA 和所含未提交改动说明、Python/Node/Remotion/FFmpeg 版本。
3. 凭据模式、是否带历史项目、外部服务依赖、未解决资源。
4. 启动方式：复制完整文件夹到可写目录 → 双击启动 → 无密钥版首次填写/导入 API 配置；自用版采用有效已迁移配置。
5. 验证报告绝对路径、哪些验收实际通过、哪些未验证及具体原因。

包内至少交付 `启动.bat`、`停止.bat`、`便携版使用说明.txt`、`build-info.json`、`file-manifest.sha256`、第三方许可证及完整应用/依赖目录。使用说明包含：Windows x64 范围、云端联网要求、密钥模式、数据目录、关闭与备份方式、错误日志位置、字体注册行为。

完成条件：功能范围符合要求；交付目录自洽；源业务数据未修改；两个功能的旧设置不能影响输出；实际 MP4/PPTX 验收通过；所有声明与已有证据一致。若目标机验证或某个外部服务受限，仍生成可审核的包并明确缺口，不能把限制藏在“预检成功”里。

## 11. 可直接交给 Agent 的任务提示词

> 请在 `D:\Program Files (x86)\PPT_presentation_video` 按 `docs/plans/windows-portable-delivery-agent-plan.md` 实施并完成 Windows x64 便携文件夹交付。先读取 AGENTS.md 与方案，再检查 git status。暂时关闭数字人和勾画标注，完整保留 AI Mask、旁白/音频、视频/PPTX 等主流程。修复现有打包脚本、启动/停止和搬迁问题，采用统一发行开关，准备包内运行依赖，输出至源仓库以外的新目录。默认空项目库、保留可复用配置，无密钥模式；若我另行明确要求沿用自己的密钥则切 SelfUse。不要修改我的真实数据库、项目或素材，不自行切换 TTS 供应商，不使用源服务代替目标包验证。执行仓库要求的相关回归和实际 MP4/PPTX 验收。最终给出可复制文件夹的绝对路径、大小、启动说明、凭据策略和验证报告；只有本机测试就明确说明，不虚称另一台电脑已验证。请实际完成打包，不停留在建议阶段。
