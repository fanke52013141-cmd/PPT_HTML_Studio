# 真实旁白与音频刷新交接（2026-10-17）

承接[P3人工保护](handoff-editor-protection-p3-2026-10-17.md)与[P2时间轴](handoff-editor-timeline-p2-2026-10-17.md)。基线origin/main `2cfb2dcb8bb765c67e362d2342088b7e1cfa7e47`，分支`codex/editor-adapter-p0-20261017`，实际checkout `D:\Program Files (x86)\PPT_HTML_Studio`。所有本地增量未提交、推送或部署。

## 实现

- `html_scene_editing`复用`tts_artifacts.artifact_hashes`计算audio_revision，覆盖实际音频/时间轴/文字/metadata/字幕字节，识别同长替换。editor.read/preview返回指纹；preview/save可选expected_audio_revision，不匹配409 AUDIO_REVISION_CONFLICT。操作开始/校验结束各检查一次，保存前拒绝验证期间变化；省略字段兼容旧请求。
- 正式编辑器预览/保存携带指纹，开始音频播放前核对已加载媒体指纹、当前文档指纹、服务端指纹和原音频有效状态。旧媒体、时序不一致或陈旧状态暂停并使动作只读，保留本地草稿。
- 新增“刷新配音与时序”：暂停→读取当前revision/音频指纹→原preview校验现有草稿与绑定→按新指纹URL重载音频。保持scene/binding作者数据与undo；不自动重绑、不执行TTS、不批准。刷新期间隔离其它操作，关闭/迟到响应不激活新编辑器。场景修订冲突仍走原比较流程，音频冲突提示刷新。
- mediaRevision独立记录已经加载的实际音频版本，不能因为保存后的editor.read返回新指纹就把旧缓存当成新媒体。校验/保存期间刷新token与原播放器时钟/作者数据分离。
- Agent同步：API1.43，editor.read/write1.1、preview1.3；Web/Agent请求字段一致，旧调用省略新字段仍可用。新规范见[editor-audio-freshness-0.1.0](../../contracts/html-presentation/runtime/visual-v1/editor-audio-freshness-0.1.0.md)，契约0.9.83。
- generation快照新增原指纹实现`tts_artifacts.py`、`artifact_fingerprint.py`、`project_storage.py`源码依赖；不新增工作流失效原因或批准捷径。

## 验证及证据

- 后端/Agent相关整组486项通过（scene editing/repair/audio binder/snapshot/隔离编辑器及完整checks/agent）；Node16项、前端质量、语法、源/产物哈希检查通过。既有Starlette anyio弃用提示1条。
- 新服务反例：相同字节数音频替换导致token变化；旧token preview/save拒绝且目录逐字节不变；验证中替换音频拒绝作品写入。Web/Agent相同409 code，旧请求兼容。
- 真实已有旁白：只读复制本机`freezing-water`的旧0.3场景、0.1绑定、MP3及时间轴到新临时fixture。仅路由scene ID改成condensation，使用原内容/动作/音频，不将其冒充新版语义场景或新TTS。媒体实测19.67568秒，原时间轴内容19.582秒；在既有250ms容差内。
- 真实副本浏览器通过：动作延后300ms，原句绑定和作者duration500ms保持，保存重开；0/1000/5500/12000/19000ms乱序seek时音频currentTime与共享播放器DOM时间一致；播放暂停；显式刷新后保留编辑。仅验证播放/时钟和编辑持久化，不代表听感、逐句内容视觉QA或正式音频批准。
- 合成同长替换浏览器通过：保留尚未保存的动作偏移；旧媒体停止/动作只读、旧指纹保存409；刷新URL改变，草稿原句偏移保存成功；同值保存不增revision。脚本可重复运行，每次验证offset增加300ms，而非假定原偏移为0。
- 合成时序替换浏览器通过：音频/语块整体×1.25，轨道按原binder派生重算；binding、作者motion逐字保持，refresh与no-op save均不增场景revision。不是实际重新调用提供者配音。
- 原项目9个源文件在本批前后SHA256及mtime_ns完全相同。证据位于忽略输出`outputs/editor-audio-freshness/2026-10-17/`：source-before.json、source-verification.json、browser-results.json、preview.png。临时副本中的revision变化不作用于原run。

## 复现与后续

`checks/test_html_editor_audio_freshness.browser.mjs`导出verifyAudioFreshness、verifyRetimingRefresh，使用`checks/test_html_scene_editor_fixture.py <新临时目录> --presentation`及cua Tab真实UI操作；verifyExistingNarration使用fixture的`--real-audio-run <含freezing-water的原run>`只读复制入口。测试替换/retime控件仅在fixture加载；真实旁白模式禁止这些替换端点。

本轮完成真实旁白副本验证及操作时音频新鲜度补强。尚未做真实提供者重新配音、整课、听感批准或正式视频对应帧；P2/P3整体仍partial。指纹不是文件实时监控，也不声明外部无锁写入的跨文件原子快照。外部在操作后继续改音频会在下次预览/保存/播放检查时被发现。

下一轮可优先做正式视频对应帧与当前人工保护/最小重建的整页闭环，另补多DPR/40对象压力覆盖。任何真实重新配音/输出必须沿原任务、成本和批准路径，不以本轮fixture通过替代。
