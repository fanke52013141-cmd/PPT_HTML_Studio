# Qwen 正式接入

正式音频对齐只使用 Qwen/Qwen3-ForcedAligner-0.6B，固定版本
`c7cbfc2048c462b0d63a45797104fc9db3ad62b7`。原 WhisperX 推理代码已删除，当前工作环境已卸载 WhisperX。原供应商词级数据保留用于历史兼容与诊断，不再作为正式对齐入口的另一条执行路径。

旧权重缓存的递归删除被自动审批以“blocked by policy”拒绝，仍留在磁盘上；它不被正式引擎读取。旧测试报告、人工标签和实验音频保留作追溯依据。

## 运行保护

- 音频合成并确认后定位；人工校准保留并优先。
- 独立进程，进程内全局单任务门闩，CPU两线程、bfloat16；600秒超时。取消在等待和单页安全边界检查，运行中的一页不会假称立即停止。
- 请求仅使用本地固定版本权重，禁止标注时联网下载。
- 缓存绑定音频、讲稿、实际发音文本哈希、模型和引擎版本。旧模型的自动时间不能静默复用，需要重新执行音频定位。已有人工时间不因此覆盖。
- SDK补值过的区间不作为有效自动时间；相同原文范围的发音扩展只要一部分无效，整体交由人工处理。
- 完整文本序列按顺序映射，区分重复词。未映射的TTS改写不猜原文位置；多字词的局部选区不按字数拆秒数。
- 没有虚构置信度。有效输出仍受正区间、音频长度、字符时长和时间顺序保护；这些结构保护不等于精度保证。

## 部署

解释器由 `repository_paths.ANNOTATION_WORKER_PYTHON` 或 `PPT_ANNOTATION_ALIGN_PYTHON` 指定，默认 `runtime/annotation_worker/Scripts/python.exe`。生产主解释器无需安装语音模型库。

核心环境：Python3.12、CPU torch2.8.0、transformers4.57.6、qwen-asr0.0.6、accelerate1.12.0、nagisa0.2.11、soynlp0.0.493、librosa0.11.0、soundfile0.13.1、sox1.5.0；本机实际环境记录见 `qwen-worker-lock-20261006.txt`。Qwen包同时声明网页演示依赖；本项目只使用Python强制对齐入口，不运行其网页服务。

安装准备阶段使用 huggingface_hub.snapshot_download，将上述模型固定版本缓存到 `runtime/annotation_models`。不得在服务器启动或请求中下载权重。

## 精度边界

原独立实验结果为19/24在150ms内、P95为235ms、最大822ms。采用此模型不代表所有时间偏差已解决。对复杂数字、英文、倍速仍须额外人工标签验证。正式链路24条复验记录在 `outputs/annotation-bcd/qwen-production`。

正式链路复验已完成：24/24有有效定位，19/24误差≤150ms，中位81ms、P95为235ms、最大822ms，与独立实验逐条一致。仍需复核a003、a004、a031、a032、a049。测试使用复制的音频与讲稿，没有写入用户的正式项目。

相关回归266项通过、1项跳过；末次离线环境/编码变更后的Qwen专门测试8项通过，`git diff --check`通过。正式8000服务已重启激活。

真实Qwen定位结果已走完整勾画编译：音频起点4.32秒、页面音频延迟0.5秒，30fps调度至4.8333秒；人工校准4.258秒时调度至4.7667秒，覆盖Qwen。18张实际透明笔迹PNG从0增加到6981个非透明像素，逐帧不倒退，最后完整闭合。结果保存于 `outputs/annotation-bcd/qwen-native-video/integration-verification.json`。本轮未新增完整MP4导出验收，不把笔迹编译当作视频端到端验收。
