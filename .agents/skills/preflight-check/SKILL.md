---
name: preflight-check
description: Validate repository resources, run inputs, credentials, schemas, and local render dependencies.
---

# Purpose

HTML 后端先使用独立分支：`python scripts/ppt_studio_doctor.py --html-target static_html --json`。
目标支持 static_html / generate_existing / generate_new_images / snapshot_pptx / video。
已有场景加 `--html-scene <scene.json>`；视频再加 `--run-dir <project_run>`。
生成模式以 `--model-readiness <json>` 提供宿主解析后的 text/image 布尔就绪标记，不能输入密钥；它只证明配置声明，不证明连接成功。
需要新图片才要求 image 就绪；静态检查不要求音频；视频核验实际确认和绑定。
检查实际浏览器与主题字体、资源渲染、输出权限及磁盘预算；不调用生图/TTS，不授予视觉或音频批准。
报告的 ready 仅为本地前提条件，不是正式导出授权；原输出门禁继续执行。
HTML 规则见 `docs/contracts/html-presentation/runtime/visual-v1/preflight-0.1.0.md`。

以下为原图片后端规则：

在生成和渲染前检查当前 v3 生产链路。此阶段只检查，不调用生图、TTS 或视频渲染。

# Required Files

- `config/pipeline_profiles.yaml`
- `config/style_tokens.yaml`
- `references/style_reference/PPT模板.png`
- `references/style_reference/PPT示例.png`
- `schemas/slide_plan.schema.json`
- `schemas/scene.schema.json`
- `schemas/animation_timeline.schema.json`
- `schemas/video_manifest.schema.json`
- `scripts/write_visual_prompts.py`
- `scripts/build_reveal_scene.py`
- `scripts/validate_reveal_scene.py`
- `scripts/bind_reveal_timeline.py`
- `scripts/build_remotion_props.py`
- `scripts/validate_run_assets.py`
- `scripts/minimax_tts.py`
- `scripts/remotion/`

# Checks

1. `runs/<run_id>` 和输入文章存在且可读。
2. 固定配置、参考图、schema 和生产脚本存在。
3. JSON/YAML 配置可解析。
4. 需要 TTS 时只检查 API Key 是否存在，不记录真实值。
5. `node`、`npm`、`ffmpeg` 和 `ffprobe` 可用。
6. Remotion 依赖可安装，TypeScript 可通过检查。
7. 输出 `runs/<run_id>/logs/preflight_report.md`。

# Blocking Conditions

- 输入文章为空。
- 固定风格资源、schema 或生产脚本缺失。
- 需要 TTS 时没有凭据。
- 需要渲染时 Node、FFmpeg 或 Remotion 不可用。

# Security

不得把 API Key、Token、Cookie、Authorization Header 或 `.env` 内容写入日志。
