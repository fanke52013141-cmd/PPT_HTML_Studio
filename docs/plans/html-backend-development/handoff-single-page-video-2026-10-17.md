# 单页视频输出验证（2026-10-17）

承接[音频刷新交接](handoff-editor-audio-freshness-2026-10-17.md)。本批仅补充验收与证据，无生产 API、Schema、批准规则或 Prompt 变更；契约仍0.9.83、Agent API仍1.43。本地未提交/发布。

## 验收范围与规则

复用 HPS-007/009—017 的身份、时间、输入完整性及输出一致性规则，以及 `semantic-qa-0.1.0.md` 的新语义场景人工门禁。沿原 HtmlRenderRunner→freeze_course→共享播放器seek→编码/concat→全量解码路径，候选留在私有 staging，正式发布继续由原视频任务负责。测试中的显式test_fixture批准不适用于真实run。

## 已通过

新增 `checks/test_html_single_page_video.py`：隔离单页0.5旧格式兼容场景，header位置14/8、原句动作延后300ms，保留作者数据；合成静音1.2秒，30fps/36帧，1600×900、H.264/AAC、yuv420p/bt709、全量解码通过。真实配音、新语义0.7签收不在此测试内。

对帧0/9/15/24/35，以相同时间在冻结预览截图并抽取MP4解码帧；RGB平均绝对误差分别约0.688/0.688/0.732/0.954/1.447，固定容差4。额外检查前后画面确有变化，避免把静态空白误作动画通过；核对原句字幕、动作时间、布局及音轨尾部帧数。有限采样不证明所有帧、听感或逐句语义。

首次渲染不改作者场景、绑定及音频文件。再次移动对象后，正式导出因原批准过期拒绝，原视频字节不变；隔离夹具显式重新批准后cache key变化、实际重建，输出字节变化。测试不批准真实内容，不替代发布任务验证。

验证：single_page_video、build_snapshot、export_publication共21项通过（41.91秒）。证据在忽略目录 `outputs/single-page-video/2026-10-17/`：single-page-fixture.mp4、preview.png、video-frame.png、evidence.json。没有新增生产能力，因此无Agent版本或下游失效原因变更。

## 真实页面状态与下一操作

只读检查现有run `c16bc2b3_203534` / `freezing-water`：音频确认有效，digital human跳过；视频ready=false，唯一返回问题为`no_approval`。旧0.3场景语义状态legacy_not_evaluated，不声称0.7语义通过。

生成当前html_preview快照及工程审查：快照 `30ef20fa177e11349e43942d0c732654f8817cc91e3f103559a76639250add4d`，engineering passed、approval_granted=false。仅新增派生快照/审查证据，未修改作者内容或音频。当前终帧复制到 `real-page-preview.png`，原门禁结果为 `real-page-readiness.json`。静态终帧供视觉审阅，不是实际音频逐帧预览。

**整体partial**：工程闭环已验；真实页面须用户审阅当前画面并明确视觉批准后，沿原批准服务和视频任务完成正式输出及对应帧复验。禁止为完成导出自动填写批准。真实提供者重新配音、整课、新0.7语义签收仍分别待验。
