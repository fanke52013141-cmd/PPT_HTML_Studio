# Token 编辑式 HTML 还原 v1

后续用户结论：实际HTML/视频效果已获认可，原话“我觉得这个效果就可以了。美感的话，我觉得还是需要在做设计稿的时候就把它做好。”下方pending保留为交付时状态；当前对话视觉接受与存储中的正式资产/场景审批记录区分，未批量改写审批数据。下一步见[handoff](../../plans/html-backend-development/handoff-2026-10-08.md)。

EX-IMAGE25-TOKEN-EDITORIAL-01；2026-10-08。关联 HPS-005、007、013、015、017、023–030、035–037。

用户以“认可”批准整页设计参考，授权重建HTML并复用原音频。参考批准不代替当前HTML、新灯泡边缘及新版视频批准；这些仍为 pending_user_visual_review，未写入正式接受/生产批准。

定义见[编辑式三栏卡](../../contracts/html-presentation/runtime/visual-v1/editorial-three-columns-0.4.0.md)。scene 0.4.0增加通用shape；旧0.3词汇、旧模板及旧适配保留。标题、正文、编号、纸张、抽象单元、分隔线和箭头为独立代码对象；灯泡为唯一PNG。33个对象经现有save_scene保存到新隔离run、revision=1，并绑定原5个字幕语块，三栏保留原第二、第四、第五语块的出现时刻。自动规划器仍输出0.3，其目录过滤需要shape的新模板，不声称新构图已支持自动生成。

灯泡首轮边界提取因邻近色块被SHEET_EDGE_CONTACT拒绝，失败候选保留。第二轮使用确定性边界颜色遮罩并显式排除邻近色块，经现有mask提取输出430×440透明PNG；保留主体RGB和封闭高光，处理参数与mask-provenance.json可追溯。这是确定性处理及人工遮罩修正，不是多模态AI分割。本轮新增生图0次。

## 实测证据

隔离产物：`outputs/image25-sheet/token-editorial-v1/`，Git忽略，不写用户数据库。

| 验证 | 结果 |
| --- | --- |
| visual build | 5场景、4主题、6布局，通过 |
| visual/tests/verify.cjs | 14组检查、5场景、页面错误0；旧版本shape拒绝、非法字段、随机seek、容量、字幕区及非Token替换场景通过 |
| planning/review/audio binder/PPTX pytest | 26 passed |
| scene editing/editor fixture/production integration pytest | 14 passed，1条既有依赖弃用警告 |
| Ruff：作者脚本、规划器、规划测试 | passed |
| 实际浏览器审阅 | 33个几何对象、14个文本测量对象；最多2行，无溢出，页面错误0 |
| 独立HTML | 离线打开、终态及修改文字重新渲染通过，页面错误0 |
| 音频 | MP3 SHA256 `e6b3eb2ad1fd5ddeba383c912fd62021093d485c32a437507fddc053e7b8008a`；原文字/metadata/SRT/timeline逐字节复用，沿用用户明确声音批准，无新TTS |
| 视频 | 1600×900、30fps、481帧、16.033333秒、H264/AAC、bt709；ffprobe与完整FFmpeg解码通过 |
| 阶段快照 | 1500/7000/10000/13500/16032ms，通过共享seek实际输出 |
| PPTX | 图片式快照1页，python-pptx重新读取确认1张图片；目标软件打开未执行，不承诺逐对象编辑 |

初次审阅基础设施超时：新增主题排序成为首项，与旧默认场景不兼容。已修复通用初始化按场景声明主题，以及场景切换时回退到兼容主题，并增加浏览器回归。显式不兼容主题仍拒绝。失败报告另存initial-infrastructure-failure.json。一次播放检查3秒超时，原样重跑全部检查通过，记为时序波动，未放宽资源/容量门禁。快照首次调用方未建目录而失败，建目录后通过。

## 交付与后续

`html-review/index.html`使用共享渲染器及独立可编辑场景，是静音动作预览；`bound-scene.json`是视频实际输入，`final.png`与`frames/`为真实截图，`token-editorial-review.mp4`带原旁白字幕，`token-editorial-review.pptx`为图片式快照。整页设计图没有成为运行资源。

状态：definition completed / implementation completed（手工权威场景范围）/ technical verification passed / actual visual approval pending。单页“整页生图参考→单主体提取→可编辑HTML→原音频动画→视频/快照”已跑通；本例仍有人工布局定义和一次遮罩修正，未测量批量课程总耗时，不承诺效率提升比例。下一步审阅实际HTML/视频后接入自动规划，再以不同内容复测；保留旧模板、人工修改及音频。
