# 评测版本：标签 0.2.0 与溢出/穿字冻结集 · 2026-10-21

仓库 [PPT_HTML_Studio](https://github.com/fanke52013141-cmd/PPT_HTML_Studio)，main。
证据与边界见[标签 0.2.0 段落](../plans/html-backend-development/feature-recognition-benchmark-2026-10-21.md)
与[溢出/穿字评测](../plans/html-backend-development/overflow-crossing-benchmark-2026-10-21.md)。

## 行为变化

- `scripts/evaluate_feature_recognition.py` 支持 dataset/labels `0.2.0`：逐目标声明
  `ownership`（image/container/icon/annotation/text/ambiguous），模糊项必须有理由并排除确定分母，
  输出 `by_ownership` 与 `ambiguous_reasons`；`0.1.0` 结果字段保持不变。
- 新增 `checks/fixtures/feature-recognition-controlled-v0.2.0/` 两页受控示意图与
  `checks/fixtures/overflow-crossing/` 七例冻结测量；新增
  `scripts/evaluate_overflow_crossing.py`，直接复用生产 `capacity.cjs` 与 `vector-overlap.cjs`
  谓词，按类输出 TP/FN/TN/FP、决定率、未决计数与实际耗时。

## 实测与边界

标签受控集 2 布局/页、21 确定目标 + 1 模糊：TP2、TN18、FP1（故意复现 0.7.4 容器误认）、FN0；
container TN1/FP1，image TP2，icon/text/annotation 无误报。溢出/穿字：`text_overflow` 与
`arrow_text_crossing` 各 TP1/TN2/FN0/FP0，未决 1；直线核心耗时约 0.65 毫秒。

以上均为受控夹具或按文档数值重放，**不是真实模型、真实课程或人类签收**。真实未曝光课程页与
真实穿字对不在本机 Git，需另一台电脑按图片/对象/标签或 scene/证据 hash 封存移交后追加；不改已测
0.1.0 清单、不用同页扰动冒充多课程。

## 兼容与验证

无数据库迁移、公开 API、Agent 参数或契约版本变化（包 0.9.113 / API 1.60.0 保持）。相关测试
16 passed（标签/计分 13、冻结评测 3），ruff、compileall、`node --check` 与 `git diff --check` 通过。
本机沙箱不能运行 Playwright，浏览器与真实课程终态仍以远端 CI 和另一台机证据为准。

## 回执

评测提交 `0b15706` 的 run [39604748082](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/actions/runs/39604748082) completed/success，`Run canonical full checks` 33.6 分钟；本批未重发供应商请求、未写作者、未签发批准。
