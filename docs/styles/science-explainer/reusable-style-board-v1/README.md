# 可复用 HTML 样式与版式参考图 v1

2026-10-08，按用户本轮要求制作：同一主题的一张完整样式与版式图跨页面复用；每页只替换内容及选用版式，不生成单页特定参考截图。

- `style-board.png`：真实注册播放器渲染的 header/text/card/figure/summary/annotation/arrow/badge/label 九类代码组件，以及 explanation-cards/process-stage/data-relation 三类版式。image 由独立插图区表示。不是任意 CSS 的全集，也不代表尚未实现的样式。
- `style-board.html`：图谱的浏览器导出文件，内含真实组件截图。
- `style-board.json`：注册引用、源文件与字体指纹、参考图哈希。
- `generation-rules.txt`：跨主题固定生成规则，固定纯色背景 #FBFAF8、画布与字幕区、组件白名单、禁用效果及独立插画要求。

生成器 `html_engine/tools/build-style-board.cjs` 使用源主题、注册库、播放器、样例和字体的指纹缓存图谱。相同源与字节哈希命中后不重新渲染。更新主题或组件时再更新参考图。

本轮为真实生图实验参考，尚未取得用户视觉批准，也尚未替换应用正常生产请求中的原始风格图与效果图谱。实验入口 `scripts/generate_html_style_trial.py` 只发送本图谱；固定规则与当前页内容分别保存，仍走现有连接与凭据解析器。

关联 HPS-031/032/033/035。当前图谱明确展示有限实现能力；图片生成结果仍需核对，文本中写固定色值不等于供应商逐像素执行。效果见 `docs/reviews/2026-10-08-reusable-style-board-trial/generated.png`。
