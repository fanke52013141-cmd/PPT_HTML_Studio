---
name: generate-audio-subtitles
description: Generate or validate PPT Studio TTS, subtitles and audio timelines from current authoritative narration using existing project providers. Use for 配音、TTS、字幕时间轴; do not rewrite narration from images or bypass audio confirmation.
---

# 配音与字幕

读取 [共用边界](../workflow-contracts.md)。两个backend共用既有声音服务，读取当前项目模型/音色/声音设置，不强制切换MiniMax或写死emotion。

1. 从原旁白入口加载当前页planning/narration_beats.json并核对visual_contract；源文案不符回规划/旁白编辑，不根据图片、OCR或旧scene重写讲稿。
2. 用narration.update和tts.synthesize/原TTS任务生成。允许的语音标记由现有normalizer决定，清洗后文字必须保持原句；字幕不能出现控制标签。
3. 复用需校验当前TTS输入、模型配置与产物hash，不因文件存在就认定当前。读取任务终态及真实voice.mp3、tts_text.txt、tts_metadata.json、subtitles.srt、audio_timeline.json。
4. 保留实际timing_source；估算不能冒称强制对齐或已同步。UTF-8回读，核对缺字、异常问号、时长、字幕和听感；字幕样式/每行预算读取项目配置。
5. 只有用户确认当前声音才走原确认入口；模型建议/任务成功不代签。

TTS超时查原任务，未知不补发。HTML进入原音频动作绑定，图片进入PNG时间轴绑定。声音问题改音色/标记不改事实；图片和旁白冲突交QA路由。
