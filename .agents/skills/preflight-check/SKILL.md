---
name: preflight-check
description: Check PPT Studio inputs, model readiness and local dependencies before image or HTML production/export. Use for 环境预检、生成前检查、导出前诊断; read-only, no provider generation or approval.
---

# 制作前预检

先读 [共用边界](../workflow-contracts.md)，确定backend、目标、项目路径和画布。只检查，不调用模型、生图、TTS或导出；ready不表示连接成功或批准。

## 执行

1. HTML运行 `python scripts/ppt_studio_doctor.py --html-target <target> --json`，target从static_html/generate_existing/generate_new_images/snapshot_pptx/video选择。已有scene加--html-scene；视频加--run-dir。模型只传宿主解析的--model-readiness布尔声明，绝不传密钥。
2. 图片路线使用doctor的--run-dir/--stage检查实际阶段；核对当前canvas_ratio、配置/Schema、参考资源、raw/master配对和相关builder，不要求无关阶段的全部产物齐备。
3. 针对目标核对字体/浏览器/资源；输出再查Node/Remotion/FFmpeg/ffprobe、可写目录和空间。缺依赖先定位，不自动安装或改真实配置。
4. 交付检查命令、就绪/阻断、证据及未做的连接测试；测试DB/runs隔离。

例：静态HTML检查不要求真实音频；正式视频检查仍需当前声音和签收。配置存在不等于付费提供者已验证。
