# C 线交付：动作、语块绑定与逐帧对照

日期：2026-10-10（Asia/Shanghai）
工作目录：D:\software\PPT_HTML_Studio
基线 HEAD：bb6dbbebf55b8075e439f9c1a059ae5c74b0ff31。开工时工作区干净。
接口基线：scene 0.4.0 / theme 0.2.0；hps.html.motion_binding@0.1.0；公共动作定义卡 08-timeline-actions.md 版本 0.1.0。A/B 已发布至 origin/main；本线未切分支、reset、clean、stash、全仓暂存、commit、push，也未启动真实应用服务。

## 范围与文件归属

- C 独占实现：html_audio_binder.py。唯一修复是对绑定格式、引用目标、语块 ID、edge 和 offset 做 binder 边界校验，避免上游校验被绕过时静默降级为绝对时间。
- C 专属回归：checks/html_motion_v1/。黑灰白固定场景仅含 4 个文字/形状节点。
- C 独立实验：html_engine/motion-research/。Anime.js 锁定 4.5.0、MIT；本目录依赖不接入生产包。
- 本交付记录：deliveries/C.md。
- 未修改 html_action_editing.py、html_scene_editing.py、static/html_scene_editor.js 和共享 html_engine/visual/{schema,compiler,renderer,player,preview,generated}。计划中的 motion editor / audio preview / motion service 文件当前不存在，因此未创建空壳。D 线同时产生的 html_engine/visual/catalog/、html_engine/tools/catalog-*.cjs、html_engine/tests/catalog-assembler.test.cjs 与 docs/assets/ 保持原样。

## 动作能力矩阵

| 能力 | 当前真实支持 | 边界 / 结果 |
|---|---|---|
| enter | V1 Schema/compiler/renderer 已有；按传入时间以 smoothstep 计算显隐和位移 | offsetX/Y、时间字段已实现；位移几何由现 renderer 输出 |
| exit | V1 renderer 已有 opacity 退场 | 实际 compiler 未检查对象是否为临时对象。旧纯 html_action_editing.normalize_object_actions 有 is_exit_object 门禁，但不是 V1 scene 的执行路径。需 A 定义稳定生命周期身份后接入公共 Schema/compiler |
| emphasize | V1 renderer 已有，smoothstep 上移 8px 再回位 | 位移幅度固定；每个 targetId:type 单槽，重复同类动作报 ACTION_CHANNEL_CONFLICT。如需同类重复动作，应先定义新版本/扩展，不覆盖现绑定 |
| SVG 批注描线 | V1 annotation node 绘制圆环和指向文字 label 的 SVG leader，按 annotation enter 进度改变 stroke-dashoffset | 需图像锚点；不是通用文字 underline、自由手绘路径或 relation_draw。后者只在旧纯校验模块注册 |
| beat 绑定 | html_audio_binder.py 消费已确认的 audio_timeline.json；按 targetId:type 绑定 beatId、start/end 和 offsetMs | 秒→毫秒在绑定边界完成；偏移必须为有符号整数且结果不能越出音频时长；binding 文档中未绑定的装饰动作保留作者绝对时间 |
| 手工覆盖/冲突 | 共享 merge_manual_edits 在稳定目标上保留人工修改；目标删除或节点类型改变返回 MANUAL_TARGET_CONFLICT。保存另有 revision 冲突保护 | 本线用隔离用例核实；没有改共享编辑器。目标语义身份字段仍需 A 的接口决策 |
| 时间求值 | renderer.cjs 内 renderAt(ms) 每次按输入时间重算；浏览器 visualPlayer.seek(ms) 同时更新 DOM/几何 | 本线实测乱序、倒退、暂停、重新播放及同刻重定位；通用视频导出一致性仍交 F |

旧 html_action_editing.py 是纯对象动作校验模块，允许 enter/exit/emphasize/relation_draw 的结构验证及人工 override 冲突诊断，但当前 V1 compiler/editor/render path 没有调用它。相关 UI/服务预案中的 html_audio_preview_service.py、html_motion_service.py、static/html_motion_editor.js/.css 当前不存在；现有入口由 A 线 html_scene_editing.py / static/html_scene_editor.js 所有。

## 真实修复与兼容

修复前，binder 通过真假值判断 link：空对象 {} 会被视作没有绑定；任意非法 edge 会隐式走 start；小数 offset 会被 int() 截断。正常 UI 保存路径有 _validate_binding，但 readiness/render 等直接调用 binder 时没有同等的 fail-closed 防线。

现在 bind_scene_to_audio 要求明确 binding 符合既有 hps.html.motion_binding@0.1.0：对象 envelope、actions 映射、有效动作身份、beatId、edge、整数 offset（±120000ms）都经过本模块验证。坏记录报 AUDIO_BINDING_INVALID，已删除目标报 AUDIO_BINDING_TARGET_GONE，不存在的语块报 AUDIO_BEAT_MISSING。有效 binding 算法不变：仅显式连接的动作取语块边界加 offset；显式 binding 中未绑定动作保持作者时间；无 binding 的旧实验输入继续比例缩放。输入场景和 audio timeline 均不修改。该路径没有 TTS 调用。

相关 HPS：HPS-004、008、009、011、012、014、018；相关 AC：AC05、AC09、AC11、AC12、AC13。未新增公共动作、场景字段、Schema 版本、数据库字段或迁移，故没有修改契约索引/CHANGELOG。

## 候选对照实验与结论

实验 ID：RES-20261010-C01 / BOR-20261010-ANIMEJS-01。官方资料与许可证证据见 [独立实验说明](../../../../html_engine/motion-research/README.md)。

同一黑灰白文字/形状 fixture 对照实际 V1 renderer 与 Anime.js 4.5.0 时间线。固定随机外输入；动作边界含 337ms、1114ms、2501ms、6001ms，并采样分数毫秒及前进、倒退和重复定位。Node v24.11.0、Microsoft Edge 154.0.4258.62：

- 当前 renderer 与 candidate 的 22 个样本都从同一时间直接计算；候选 reset 包装后的最大数值差 0.0000448031，来自 CSS 变换序列化精度。
- 将候选状态写到隔离的克隆 DOM，与当前 renderer 截图逐像素比较，22 个时间点 totalChangedChannels=0。
- Anime.js 不先 reset 的原始 backward seek 在 7300→2501ms 复现 opacity 差 1.0；逐次 reset() 再 seek(ms) 后一致。实际 SVG leader 7 个边界/乱序点的 dash-offset 最大误差 0。
- Anime.js 具备时间线、毫秒 seek、自定义 easing、MIT 许可，适合作为独立研究候选；项目当前 runtime 已有纯时间求值。reset 包装增加中间状态及第二套运行时依赖，未发现足以替换当前实现的能力缺口，因此不采用为生产时钟/依赖。

截图、逐点数字、环境/源码哈希及 fixture SHA-256 见 html_engine/motion-research/results/verification.json。图像是工程比对产物，不是动效美感或风格审批。

## 命令与结果

在仓库根目录，隔离到本地项目 .venv 与独立 motion-research npm 包；没有真实用户 DB、TTS 或服务请求。

| 命令 | 退出码 | 结果 |
|---|---:|---|
| npm.cmd install --prefix html_engine/motion-research --ignore-scripts --no-audit --no-fund | 0 | 单独安装锁定 Anime.js 研究依赖 |
| $env:HPS_CHROME='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'; npm.cmd --prefix html_engine/motion-research run verify | 0 | 22 帧文字/形状与像素对照；7 点 SVG stroke；保存 4 张 PNG 与 verification.json |
| .venv\Scripts\python.exe -m pytest checks/html_motion_v1/test_motion_contracts.py -q | 0 | 9 passed |
| $env:HPS_CHROME='C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'; .venv\Scripts\python.exe -m pytest checks/html_motion_v1/test_motion_contracts.py checks/test_html_audio_binder.py checks/test_html_action_editing.py checks/test_html_scene_editing.py -q | 0 | 31 passed；1 个第三方 Starlette deprecation warning |
| git diff --check | 0 | 无 whitespace 错误 |

实际逐帧入口：[verify.cjs](../../../../checks/html_motion_v1/verify.cjs)。可直接查看 [强调峰值图](../../../../html_engine/motion-research/results/emphasize-peak.png) 和 [实验明细](../../../../html_engine/motion-research/results/verification.json)。

## 交给 A 的集成提案与未完成项

1. 在 scene 定义明确“临时对象”的稳定语义字段或公开目标能力，再由 A 决定对应版本迁移；共享 compiler 应拒绝对普通持久对象应用 exit。当前 UI 显示 exit 与编译器门禁并不一致。
2. 明确 V1 annotation leader 与旧 relation_draw 校验词汇之间关系。若需要可自由绑定的线条绘制，先定义版本化目标/路径/时间语义，不把旧词汇直接等同已实现效果。
3. C 没有共享 Editor、Schema、Agent/API/UI 接线。A 完成接口决策后需要共享编译/人工保存/播放入口验证；C 当前回归是冻结 fixture 的单页技术验证。
4. F 尚未用实际视频导出抽帧核对本动作序列；没有真实旁白试听、用户节奏批准、完整课程/视频验收。上述工作均未标为通过。
5. 本线没有验证重复同类型动作、按帧率编码器的所有边界、所有平台字体/浏览器和长课程表现；这些不由 22 样本推导。
