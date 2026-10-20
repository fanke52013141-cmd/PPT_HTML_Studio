# 几何优先避让入口与候选预览 0.1.0

HPS-007/009/010/013/015—018/023—025，包0.9.113，API1.60.0 / html_repair.generate1.5。

- 原repair/generate增加可选strategy：默认model保持原任务及模型路径；geometry_first表示固定“箭头穿文字”的位置/尺寸任务，scope为1至4个不同现有对象。instruction必须为：`仅调整所选对象的位置与尺寸，解决箭头穿过文字；保留文字、关系、样式、动画和人工保护字段。` 其他目标使用model，防止几何通过却忽略用户指令。
- html_repair_orchestration为组合入口；html_geometry_repair保持几何候选所有权，html_scene_repair保持模型两轮预算、候选键、保护、原播放器检查及保存所有权。不改变模型或Prompt参数。
- geometry_first冻结当前作者/音频身份，先运行原有界几何试算；通过返回原候选，无故障返回unchanged。仅没有合法候选才惰性获取模型配置并进入原模型修复；不可将过期身份、保护或证据异常当作重试许可。模型候选也只接受set_presentation，并强制registered、完整时间范围、30fps output_frames。失败与unknown不自动重发。
- 结果附repair_path（来源、回退原因、几何次数/秒数）、changes（参数修改前后）、comparison（原检查截图及时间）。这些是审阅信息，不参与候选键或批准；save使用原request/candidate_key，重新检查当前身份与整页后创建原保存版本并触发原下游失效。
- static/html_local_repair.js独立拥有入口、截图/参数呈现及显式保存；编辑器只桥接选择、草稿、忙碌和生命周期。未保存草稿不能生成，页面切换后的迟到响应不显示；草稿/音频/修订变化后不能采用旧候选。用户可放弃候选，保存后可用原“读取保存版本/预览恢复所选版本”恢复为草稿，再另存新修订。无第二个渲染器，无自动作者写入或审美批准。
- Web/Agent/MCP/CLI沿用同一generate能力与请求模型，旧客户端不传strategy仍走model。无数据库迁移。真实模型回退质量、跨课程覆盖和人工视觉验收独立留证，不由替身测试推断。
