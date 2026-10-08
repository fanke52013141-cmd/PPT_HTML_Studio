# Token 单页：主题接入、真实音频及输出验证

2026-10-08；N00-A / N01，HPS-005、013、015、017、023–030、035–037。本轮是隔离的单页产物验证，不代表五页课程、用户数据库项目或应用任务端到端验收完成。

## 用户确认与实际状态

后续反馈（追加、不覆盖以下当时状态）：用户明确认为整体声音、字幕及卡片出现节奏没有问题，但整页精美度仍不足；随即授权先生图整页设计参考、确认后再还原 HTML。记录为听看反馈通过、整页美术 changes_requested；本轮不新合成音频或发布旧画面。整页设计定义见 [设计参考 v1](token-design-reference-v1.md)，确认后复用现有音频/beat ID 并重验新构图。

- 用户认可暖白琥珀稿：“这个效果就很不错了，我觉得还比较OK”，随后要求继续。记录为该页静态布局/配色通过，不扩展为全部模板已批准。
- 用户单独回答：“接受灯泡的身份和边缘”。已通过真实 `review_candidate` / `accept_candidate` 记录人工审阅并注册资源，没有绕过候选 seal 或人工门禁。
- 原灯泡 PNG 字节保持 SHA256 `2a4c3cff82353b5b6ac87bb3b0cae233c515c5678231b5943f19512aa03d6018`。新候选明确登记几何中心 focus=(994,547)，用于概念配图引线，不声称科学部件识别。
- `approve_stored_scene` 绑定已保存的当前 Token 场景、正式资源、登记主题和运行输入；`approval_status` valid=true。
- 已生成真实音频、有声审阅 MP4 和单页批准版快照 PPTX。音频/字幕/动作仍待用户试听确认；未创建虚假的 audio_confirmation，未提交正式应用视频任务。

## 主题接入与兼容

[暖白琥珀定义卡](../../styles/science-explainer/amber-science.md)先于源登记完成。新增 `html_engine/visual/themes/amber-science.json`，ID `amber-science@0.2.0`；沿用当前外观字段、字体与公共组件，不修改 Schema/renderer 或添加 Token 业务分支。

实际 build 输出 4 scenes / 3 themes / 5 layouts。registry、预览数据与 bundle 从源重新构建，没有手改生成物。旧 soft-science / neutral-science 源及实例引用保留；当前生成编排器默认仍是 soft-science，本轮没有项目主题选择入口。不要把注册主题表述为所有自动生成页面已经使用新配色。

扩充现有主题切换测试：neutral-science 和 amber-science 均保持场景节点语义、实际文字测量及几何一致，重复 seek 回终态像素一致。播放检查以有界等待实际 timeMs>100 替代固定 250ms 等待，保留原断言，避免繁忙机器上固定延迟误判。

## 真实音频与时间边界

只读本机 settings 和凭据存在性，没有记录密钥，也未写用户数据库。使用已有 `tts_provider_service` 参数/环境适配和 `generic_tts.py` → `minimax_tts.py`，不是新语音方案。实际服务返回 success；模型 speech-2.8-hd、既有音色 Chinese (Mandarin)_Soft_Girl、速度 1.2；MP3 16.032 秒，24000 Hz，旁白来自本轮手工填写的四句 Token 讲稿。

音频 SHA256 `e6b3eb2ad1fd5ddeba383c912fd62021093d485c32a437507fddc053e7b8008a`。供应商实际返回 **2 个粗时间区间**，现有字幕代码分为 5 条显示语块；区间内切分含时间分配，并非逐词测量。保留供应商原始区间及音频 hash，不能因 timing_source 字段为 provider_sentence_timestamps 就声称五条均精确测量。当前待逐句试听；需要修正时复用现有时间校准入口，不伪造 ASR 成功。

通过真实 `bind_scene_to_audio` 绑定动作，card-1 / card-2 / card-3 分别引用讲稿对应语块，summary 与最后一段绑定；全部 11 个动作有显式 beat ID，没有使用旧相对缩放兼容模式。绑定输出 16032ms，静态容量/字幕检查通过。

## 实际输出

根目录：`outputs/image25-sheet/token-production-v1/`。

| 产物 | 实际检查 | 限制 |
|---|---|---|
| `planning/html_visual/resources.json` | 真实审阅服务登记 accepted 灯泡，来源/锚点可追溯 | 独立实验目录，非用户项目数据库资源 |
| `human-review-evidence.json` | 人工素材/静态批准记录及真实用户回答 | 不批准音频或动态 |
| `slides/token-closure/voice.mp3`、metadata、SRT、timeline | 真实 MiniMax 调用成功、本地 ffprobe 时长 | usage/费用未返回，unknown；待试听 |
| `audio-review-preview/token-review-only.mp4` | 30fps、481帧、1600×900、H264/AAC、bt709、16.033333 秒；ffprobe 与完整 FFmpeg 解码退出0 | 审阅用预览，音频未确认；不是正式发布视频 |
| `audio-review-preview/token-review-only.pptx` | 实际单页快照输出 | 草稿资源上下文、供审阅 |
| `approved-static-export/token-approved-static.pptx` | 导出前 html_readiness ready；ZIP 完整性、python-pptx 重开、1页/1图通过；实际快照与用户认可配色稿逐像素一致 | 图片式 PPTX，不可逐对象编辑、无原生动画；未在 PowerPoint/WPS 打开 |

用户 2K/low 要求在此前图像输入中保持；本轮生成调用0次。1600×900 是既有 HTML 运行/视频工具的实际输出，不将其称为2K视频，也未擅自改公共视频尺寸。

## 验证与未完成项

- `node html_engine/visual/build.cjs` 退出0。
- 指定本机 `HPS_CHROME` 后 `node html_engine/visual/tests/verify.cjs` 最终串行运行：13 checks / 4 scenes / 0 page errors。
- `pytest checks/test_html_visual_review.py checks/test_html_asset_sheet_review.py checks/test_html_audio_binder.py checks/test_html_pptx_snapshot.py -q`：20 passed。
- 新脚本 Ruff 通过；真实音频/预览脚本退出0；正式静态导出校验退出0。
- 首次新增 seek 测试调用不存在的 shot 帮助函数，修正为现有 stage screenshot；固定延迟播放检查失败后改为等待实际进度。并发视频与浏览器测试时还出现一次 Array buffer allocation failed，最终串行验证通过；不将失败删除或宣称压力稳定性已验证。

待完成：用户试听确认 → 保存真实音频确认 → 正式视频任务/产物登记与播放验收；PPTX 目标软件打开；真实模型文章到分镜；更多结构和课程覆盖。当前状态 `partial / awaiting_audio_review`，不是完整生产流程 passed。没有启动/迁移应用、commit、push 或发布。
