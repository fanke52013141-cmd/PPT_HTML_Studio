# 2026-10-08：HTML 后端修复、生产流程接入及工程验收

## 从哪里获取代码

- [`html-studio` 分支](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/tree/html-studio)：应用源码和本轮 HTML 后端修复。开发 Agent 请以此分支为代码基线。
- [`main` 分支](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/tree/main)：项目规范、独立 HTML 引擎、调研和验收证据。此分支保持原精选发布范围，不包含完整应用。

本次同步已提交的修复；本地其他继承的未提交修改没有混入发布。线上源码不能被描述为本地所有未提交文件的完整快照，启动和依赖仍须按实际环境核对。

## 主要变化

1. 接通受约束分镜→带真实效果参考的设计请求→独立图片资产→注册模板编译→实际浏览器审阅→人工批准。模型不生成可执行 HTML/JavaScript，不自动批准。
2. 修复场景保存、修订冲突、账户权限、当前场景批准和页面就绪状态。内容、已使用资源、字体、定义或音频动作绑定发生改变时，批准和输出会失效。
3. 持久生产任务实际接入应用，支持进度查询、协作式取消、重启恢复及显式重试；晚到的旧尝试不能覆盖取消或新尝试。
4. 动作按稳定 beat ID 绑定句子音频窗口；新 HTML 视频要求显式动作绑定。旧比例时间方式仅供明确兼容。
5. HTML 视频与 PPTX 使用本后端门禁。PPTX 接回原任务、产物登记和下载链，是整页图片快照，不能宣称逐对象可编辑。
6. 修复第三步 HTML 面板位置、页选择及刷新循环；Web/API/MCP/CLI 同步生产、查询、取消能力，Agent API 为 1.12.0。
7. 效果图改为标明 ID、CSS/SVG 与作用的独立效果样本，缓存包含实际内容摘要。当前注册库为 7 个 CSS/SVG 效果，尚未提供 Canvas 样本全集。

## 提交索引

| 提交 | 用途 |
|---|---|
| [`21ffb51`](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/commit/21ffb51) | 当前批准、共享输入指纹、音频绑定、项目资源、视频与 PPTX 输出修复 |
| [`ac823f3`](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/commit/ac823f3) | 受约束生产、持久任务、真实参考附件、应用面板及回归验收 |
| [`13db945`](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/commit/13db945) | 优化报告、应用契约及逐 AC 账本纠正 |

main 的精选发布提交采用独立历史，以上链接指向 html-studio 的源码提交。

## 验收与边界

本轮主回归 **524 项通过**，补充原视频/图片/PPTX 路线 **31 项通过**。真实浏览器面板 6 项通过，视觉引擎 13 项、4 场景、0 页面错误。实际生成三页 1600×900、30fps H.264/AAC 视频，核对时长、音轨、yuv420p 和 bt709 三项色彩标签；实际验证快照 PPTX 的任务/登记/下载/删除。

五页三模板生产测试使用模型替身和真实浏览器；视频音频为合成静音。这些只证明工程链，不证明真实模型质量、真实课程或审美通过。

尚未完成：真实 LLM/图片服务（密钥未配置）、用户视觉评审、真实课程及讲稿试听、数字人合成、PowerPoint 打开；完整对象/动作/语义锚点编辑器、项目独立模型绑定仍需完善。取消按阶段边界生效，多文件写入进程崩溃尚无事务日志恢复。

## 下一位 Agent 的入口

先读 [优化与验收报告](../reviews/2026-10-08-html-optimization.md)、[应用生产流程契约](../contracts/html-presentation/runtime/visual-v1/application-workflow-0.1.0.md)、[开发交接包](../plans/html-backend-development/README.md) 和 [逐项验收状态](../plans/html-backend-development/task-ledger.json)。开源借鉴仍以交接包的固定版本映射为准。

遵循公用/风格/模板/实例/派生的所有权，沿用已有 TTS 和数字人；补齐真实课程验证后再判定产品签收。不得将 partial、blocked、pending_review 或 not_run 改成无证据的 passed。
