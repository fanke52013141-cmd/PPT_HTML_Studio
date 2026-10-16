---
name: render-video
description: Render or export current PPT Studio projects through existing persisted jobs and backend-specific gates. Use for 导出视频、正式MP4、PPTX输出; exclude manual CLI bypass of approvals and do not redraw image-backend slide bodies.
---

# 正式输出

读取 [共用边界](../workflow-contracts.md)。输入为实际项目与目标格式，使用原video.render/输出任务服务，不直接用Remotion CLI绕过持久任务、注册和批准。

1. 检查当前backend、画布/帧率、页序及目标门禁。图片路线验证当前图片/Mask、已确认声音和reveal版本；HTML按formal-export及当前视觉/声音/A04签收读取就绪状态。
2. 图片正文只能PNG；HTML共享renderer与音频时钟，不套图片Mask门禁。可选数字人按已保存决定和发行版能力处理，禁用不阻断输出。
3. 提交一次原任务并恢复轮询；unknown/旧任务继续沿恢复规则，不新建替代。服务负责重建runtime、快照、staging、产物登记及失效。
4. 用ffprobe和完整解码验证实际输出，抽查开头/中段/结尾、字幕/尾音、画布/帧率/色彩及缺图。只跑CLI或有MP4文件不证明完成。
5. 回读下载/作品记录及artifact_state/historical；视频与sidecar同寿命。HTML快照PPTX为图片式，不宣称逐对象编辑。

未确认声音或HTML语义签收时报告缺项，不代签。尺寸、背景和时长用项目设置，不写死1920×1080或3–6分钟。
