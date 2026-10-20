# 几何优先入口与候选审阅交接

2026-10-20，包0.9.113 / API1.60.0 / html_repair.generate1.5。本批完成用户确认的第1、2项；未提交或推送，正式服务未重启。

## 实现

- 原repair/generate新增可选strategy，默认model兼容；geometry_first为固定箭头穿文字避让任务，instruction及scope约束见[契约](../../contracts/html-presentation/runtime/visual-v1/geometry-repair-entry-0.1.0.md)。成功几何候选完全绕过模型配置读取。无合法候选才惰性进入原模型两轮修复，回传来源及回退原因；异常不自动重试。回退也只允许位置与尺寸，并进行完整registered/30fps检查。
- 编辑器增加“箭头与文字避让”：先保存草稿、选择1至4对象、生成候选；展示同一时刻前后原检查截图、修改参数、范围、来源和检查数量。放弃不写原页；用户明确点击保存后才使用原candidate_key/request复验及保存，下游失效仍由原Web适配器处理。
- 原历史版本读取/预览恢复入口继续使用；恢复先进入草稿，再显式另存。页面切换的迟到响应被丢弃，草稿/修订/音频身份变化不能采用旧候选。不新增渲染器，不写批准状态。
- 新JS进入编辑器源指纹闭包；构建输出重新生成。.gitattributes也固定LF，避免autocrlf造成跨机身份差异。Web/Agent共享组合服务，MCP/CLI通过原注册表获得新可选策略。

## 数据与验证

本机`outputs/geometry-entry-20261020-v1/entry-report.json`及两页完整result.json：从上一批冻结原课程文件复制到新isolated-run，经过新组合入口；未触及真实runs或批准。两张原页均geometry来源、0模型调用、作者完全不变，前后截图按同一时刻配对：

| 原页 | 实际修改 | 几何耗时 | 全量检查时刻 | 问题 |
|---|---|---:|---:|---:|
| slide_001 | obj-anchor-label offsetY -48→16 | 13.032秒 | 633 | 0 |
| slide_003 | obj-card-2 width 自动槽位→486px（原实测630px） | 10.005秒 | 606 | 0 |

每页各1次sampled候选检查和1次output_frames复验。耗时为本机单次，不作为跨机器或跨课程性能保证；几何成功不代表人工审美验收。

测试：

- `pytest checks/test_html_repair_orchestration.py checks/test_html_scene_repair.py checks/test_html_repair_feedback.py checks/test_html_geometry_repair.py -q`：44项通过，之后新增的模型异常不重放测试另测通过。包括旧默认、自定义目标、scope/修订/音频拒绝、无解回退、限制样式修改、匹配时刻及未知异常。
- Web/Agent新入口及Agent契约/MCP/CLI测试42项通过；最后异常增量连同Web/Agent11项通过。
- `node checks/test_html_local_repair.browser.cjs`通过：真实编辑器/原渲染器/完整检查/候选键/显式保存/历史恢复；仅提案选择为脚本替身，没有模型调用。前后截图、不自动保存、放弃、脏草稿拒绝及切页迟到响应均通过，无页面错误。截图及报告位于OS临时`hps-editor-browser-local-repair-Xu1zqO`。
- `npm run build --prefix editor_ui`、`npm test --prefix editor_ui`（17项）、前端质量检查、Ruff与`git diff --check`通过。规范快速检查`scripts/run_checks.py --level quick`完整通过，记录`.tmp/geometry-entry-quick.log`。

真实模型回退没有追加调用：本批只验证了共享原模型路径的工程行为，不宣称新入口上的真实供应商成功率。下一步可收集更多真实课程无解案例，按冲突类别统计几何命中率、回退原因和修复质量，再决定是否扩展搜索能力。
