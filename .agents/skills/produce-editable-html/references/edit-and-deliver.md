# 局部编辑、声音与交付

需要编辑/音频绑定/语义QA/正式输出时按任务读取对应小节，不把本文件全传模型。

## 编辑

先html_editor.read冻结revision。明确对象scope和actionId；调用html_repair.preview或generate，使用实际测量/截图。注册set_presentation/set_text_style/set_variant只改允许部分，set_motion/set_binding需实际动作；内容/节点增删回规划。preview不写作品，save重新核对candidate_key/revision/人工保护/真实浏览器；409重新读取，不能改source=human绕保护。

时间证据使用真实共享播放器和音频时钟；有限采样/未指定遮挡对不证明整个动画无遮挡。静态几何不替代审美。检查rebuild_plan和实际资源hash，只有真正改变的产物才失效；同值保存不重TTS。失败原场景保持。

## 声音与逐句QA

generate-audio-subtitles走原TTS服务、项目连接与确认。HTML使用html_audio_binding_service校验原句、资源和actionId，不走PNG层时间轴。没有真实声音不能以作者等分冒充。

A04使用html_semantic.submit/status/decision，expected_revision绑定当前scene与真实voice/timeline；每句start/mid/end由共享播放器取证。omitted/contradiction/工程失败不能批准，uncertain待审。只有用户明确决定当前report_key/note才记录人工签收。新编辑/声音/代码使旧报告stale。

## 交付

正式PPTX/视频走原任务入口与formal-export卡：固定有序整课快照、staging验证、hash及实际解码；数字人合成后也需最终验证。复用分段仍须有效，不手工搬缓存或强开legacy绕门禁。

PPTX是图片式页面，不能宣称逐对象可编辑；MP4也不是可编辑HTML。historical=true保留为旧输入交付，不能算当前完成。作品需视觉、声音、A04签收等当前门禁；不能用任务succeeded替代。
