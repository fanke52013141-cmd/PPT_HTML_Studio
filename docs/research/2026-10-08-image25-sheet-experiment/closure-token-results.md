# RES-20261008-04：单页 Token 收束实验

2026-10-08。关联 HPS-026–030、036，N00-A / N01；本轮不新增公共能力或修改生产契约。

## 结论与停止条件

后续用户反馈：该页“整体的布局还OK”，但配色不满意。布局仅获该实例的限定认可，原配色 changes_requested；[配色纠偏稿](token-palette-review.md)保留布局和同一素材，新主题仍 pending_review。原样稿、门禁与音频未完成的证据保留，不追认为整页已批准。

素材实验收束为一页实际浏览器样稿：真实 Image2.5 局部参考灯泡候选 → 不可变候选存储及复核 → 已注册 HTML 模板 → 保存场景 → 11 对象静态检查 → 三个时间点的真实截图。此段通过；人工素材审阅、页面视觉批准及正式输出仍待完成。不得记为完整生产闭环或 AC20 通过。

本轮新增生图调用 0 次，复用此前 2K / low 输出。局部参考的单次成本改善已有对照证据；批量板 v2/v3 仍不能稳定达到四对象严格提取。停止继续调整板 Prompt，不推广 v3，也不宣称总体生产效率提升。当前建议以局部参考单对象作为可审阅候选路线，批量板保持实验选项；正式采用仍需人工审阅与后续生产验收。

## 实际输入与产物

- 源：`outputs/image25-sheet/toapis-bulb-reference-v1/extraction-2-clean/source.png`，2048×1152，实际 Image2.5 / low；沿用相邻 `spec.json` 中显式微噪声清理参数。
- 候选输出 SHA256：`2a4c3cff82353b5b6ac87bb3b0cae233c515c5678231b5943f19512aa03d6018`，与上一轮清理输出相同。主体仍不是原图逐像素恢复；身份、边缘由用户审阅。
- 隔离实验根：`outputs/image25-sheet/closure-token-v1/`，没有写入用户项目数据库。
- `closure-evidence.json`：实际候选 seal、请求摘要、静态检查、截图哈希与门禁结果。
- `planning/html_visual/scene-token-closure.json`：手工填写真实 Token 内容，复用 `explanation-cards-v1@0.1.0` / `science-explanation-v1@0.2.0` / `soft-science@0.2.0`，仅一张主配图。
- `planning/html_visual/review/review-token-closure.png`：真实终态截图；11 对象测量通过，浏览器错误为 0。
- `draft-frames/snapshot-000.png`、`001.png`、`002.png`：1200 / 7000 / 18000 ms，三个不同哈希，实际预览尺寸 1592×896。这是浏览器样稿尺寸，不是声称完成 2K 视频输出。
- `planning/draft_preview/narration.json`：四段待合成讲稿，未合成或确认音频。

页面内容由本轮手工填写，未测试真实 LLM 文章到分镜调用。动作沿用模板实例时间，仅验证 seek 与阶段显示，不代表真实语音对齐。正文保持代码对象，没有把完整 Token 信息图贴进页面。

## 审阅与正式输出边界

候选仍 pending_review。实验调用真实 `accept_candidate`，得到 `SHEET_REVIEW_REQUIRED`；正式 `planning/html_visual/resources.json` 不存在。草稿渲染使用单独的 `planning/draft_preview/resources.json`，字节、哈希、alpha 包围盒由实际资源读取器校验；没有伪造已接受状态。

原候选没有语义锚点。草稿添加 alpha 包围盒几何中心作为演示 focus，明确记录为派生的预览锚点，未写回候选规范或正式资源。终态的“概念配图”标注不代表灯泡具有科学部件定位语义。

真实 `approval_status` 返回 `valid=false / no_approval`；真实视频 runner 音频入口报告缺少已确认 `voice.mp3`。未提交正式 MP4/PPTX 导出任务，未编码、ffprobe、解码或目标软件验收。不得把这几个局部门禁检查描述为正式导出服务端到端验收。

下一步需要用户分别评价灯泡身份/边缘和这页布局。依据 `application-workflow-0.1.0.md` 的“用户检查实际画面后批准”，认可后才记录具体批准、接受素材；之后使用现有语音服务生成并确认真实音频、绑定动作、正式导出并验证。如画面需改，修改此页实例，不为一个样例扩展公共组件或恢复全页手绘路线。

## 可复现验证

```powershell
.venv/Scripts/python.exe scripts/close_image25_token_experiment.py
# 本实验目录已存在时，明确 --resume；不可变候选仍逐文件复核
.venv/Scripts/python.exe scripts/close_image25_token_experiment.py --resume
$env:HPS_CHROME='C:/Users/Administrator/AppData/Local/ms-playwright/chromium-1228/chrome-win64/chrome.exe'
.venv/Scripts/python.exe -m pytest checks/test_html_asset_sheet_review.py checks/test_html_visual_review.py checks/test_html_render_runner.py -q
```

实际：实验脚本退出 0，14 tests passed，脚本 Ruff 通过。首次快照调用因 `timeout` 与实际工具的 `timeout_sec` 参数不一致失败，修正并完成重跑；首次测试未指定本机 Chromium 路径时 3 个浏览器测试失败，显式 `HPS_CHROME` 后 14/14 通过，未更改测试断言或生产浏览器探测策略。实验没有修改引擎源码或生成包。

规范声称的 canonical checkout 路径当前不可用；本轮仅在用户给定 `D:\software\PPT_HTML_Studio` 做离线检查，未启动或迁移应用。当前主题沿用登记版本，仍须本页视觉审阅，不追认为全项目已批准风格。
