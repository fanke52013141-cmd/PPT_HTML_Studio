# CI 连续失败修复交接 · 2026-10-21

## 结论

GitHub Actions 自 2026-10-19 17:46 的 `5964561` 起连续 8 次 push 失败，均卡在
`Basic static checks → Run canonical full checks`。只读拉取真实 job 日志后确认不是
“1 error”级别的偶发，而是三个可解释项：

| 项 | 证据 | 性质 |
|---|---|---|
| `test_html_external_handoff_ui.py` 失败 | #68/#69/#70 均 `Error: spawn ...\.venv\Scripts\python.exe ENOENT` | 长期红根因，自 10-19 起每次失败 |
| `test_html_e_production.py::test_unsupported_allocation_stops_before_paid_subject_and_author_write` 失败 | #69/#70 `DESIGN_UNDERSTANDING_INVALID != DESIGN_ALLOCATION_UNSUPPORTED` | 59da921 引入的测试替身滞后，非生产回归 |
| `test_html_single_page_video.py::test_edited_single_page_video_matches_frozen_preview` 失败 | 仅 #70 `EXPORT_PAGE_FAILED` | 5 个近期 run 只出现 1 次，按环境性 flake 保留观察 |

真实结果：#68 `1 failed, 2819 passed`；#69 `2 failed, 2879 passed`；#70 `3 failed, 2878 passed`。
历史日志仅用于诊断，不入库、不随 Git 同步。

## 根因与修复

1. **硬编码解释器**：五个检查脚本用 `path.join(root,'.venv/Scripts/python.exe')` 启动
   fixture bridge；CI 用 setup-python 全局安装依赖、没有仓库 `.venv`，因此必然 ENOENT。
   新增 `checks/browser_python.cjs`：优先 `PPT_STUDIO_PYTHON`，其次仓库 `.venv`，最后 PATH
   的 `python/python3`；`checks/test_html_external_handoff.browser.cjs`、
   `test_html_local_repair.browser.cjs`、`test_html_scene_editor.cjs`、
   `test_html_instance_editor.cjs`、`test_html_audio_review_runtime.cjs` 统一改用该解析器；
   `test_html_external_handoff_ui.py` 显式传 `PPT_STUDIO_PYTHON=sys.executable`。
   顺带去掉 `test_html_scene_editor.cjs` 里写死的 `C:/Users/Administrator/...chromium-1228`
   本机路径，改回共享 `captureLaunchOptions`。
2. **替身滞后**：理解运行片段 0.7.5 要求 unsupported 也返回完整 `feature_observations`，
   而 `test_html_e_production.py` 的替身仍返回空对象表，先被结构校验拦成
   `DESIGN_UNDERSTANDING_INVALID`。修复只补替身的观察表，不改变生产校验、不放宽
   `DESIGN_ALLOCATION_UNSUPPORTED` 断言，目标测试恢复通过。

## 验证

- `pytest checks/test_html_e_production.py::test_unsupported_allocation_stops_before_paid_subject_and_author_write`：1 passed。
- `scripts/run_checks.py --level quick` 全通过；五个修改脚本 `node --check` 通过；
  `git diff --check` 通过。
- 本会话沙箱禁止管道式子进程，Playwright 用例本地必然 `spawn EPERM`，因此浏览器回归
  不能在本机代签；以远端 CI 终态为准，不用沙箱失败冒充产品失败。

## 未决

`test_edited_single_page_video_matches_frozen_preview` 在 #70 的 `EXPORT_PAGE_FAILED`
尚未定位（stderr 被生产错误信息截断为 400 字符，真实 Playwright 原因不可得）。5 个近期
run 中仅出现一次，未改断言、未加重试掩盖；下一次 CI 若复现，再按导出/浏览器资源问题
单独排查。生产 API、Schema、数据库、契约包 0.9.113 / Agent API 1.60.0 均未变化。

## 发布回执（2026-10-21 补录）

- 源码提交 `6a763c4`（检查夹具解释器/理解替身修复）：GitHub Actions run
  [39603007717](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/actions/runs/39603007717)
  `completed / success`；job `Basic static checks` 全量检查 45.6 分钟通过。
- 评测提交 `0b15706`（标签 0.2.0 与溢出/穿字冻结集）：run
  [39604748082](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/actions/runs/39604748082)
  `completed / success`；全量检查 33.6 分钟通过，`single_page_video` 本批未再出现
  `EXPORT_PAGE_FAILED`，仍保留原断言与失败可见性。
- 两次 run 均包含 `scripts/run_checks.py --level full`（quick + 独立脚本检查 + 全量 pytest）
  与编辑器构建；发布回执以远端终态为准，不以本地沙箱结果代签。
