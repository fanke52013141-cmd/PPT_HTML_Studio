# A/B 发布与 C/D 开发交接

2026-10-10。用户授权将 A/B 实现发布到 PPT_HTML_Studio 的 origin/main，并新开 C、D 两个开发对话。实际工作目录统一为 D:/software/PPT_HTML_Studio。

## 本次发布

A：增加只读七阶段状态投影、Web/Agent 共用状态、目标输出门槛区分、任务生命周期摘要与缓存/人工编辑保护回归。Agent API 1.16.0、状态能力 1.1、契约包 0.9.16；不改数据库格式或原八位置导航，不伪造 H1/H6 人工批准。

B：标准库 1.0 复核、两个真实来源/测试主题样页、三套配色共六张实际截图、样页验证器与 Pillow 兼容修复。静态样页不是已注册生产模板，用户审美签收保持待审。双概念两图布局、曲线路径和字体生产映射仍是提案。

具体实现和测试见 deliveries/A.md、deliveries/B.md 和 integration-status.md。发布前主对话复跑 A 的流程/输出/Agent 定向回归，B 的样页及标准像素验证，Agent 生成同步与 visible flow 检查；结果以命令输出为准。保留多页并发 revision、真实供应商、真实课程/数字人以及用户视觉批准的未完成状态。

## C/D 文件边界

用户追加方向：黑灰白是默认基础标准风格；后续再探索、优化其他风格。C 的固定实验先使用中性代码基线；D 装配器未指定 palette/style 时必须明确选择中性基线，彩色方案仅显式启用。现有六张彩色样图用于可选配色验证，不改变默认风格。

主对话发布前复验：134 项 Python 流程/输出/Agent 回归通过（一个第三方 deprecation warning）；verify-samples、verify-standard-pixels、Agent contracts --check、visible flow 均 exit 0。六张 B 样图随源码发布；暂存内容凭据扫描无发现。

C：已有音频绑定、动作编辑和时间求值盘点；在当前实际模块上补确定性与人工覆盖验证，做独立开源方案对照。可修改 html_audio_binder.py 和已有 C 专属动作模块；新增模块放 html_engine/motion-research/，专属测试 checks/html_motion_v1/，记录 deliveries/C.md。先核对实际文件，旧文档中不存在的模块不能当实现证据。

D：建立分类参考检索和离线装配器，区分静态标准库、生产注册能力和实验演示。新增源放 html_engine/visual/catalog/、专属工具 tools/catalog-*、专属测试 tests/catalog-*、参考资产说明 docs/assets/code-art-references/catalog-v1/，记录 deliveries/D.md。现有 reference-library/ 默认只读，不改 B 样页或标准截图。

二者均不得修改公共 schema/compiler/renderer/player/registry、Agent 合同、入口、迁移或 A/B 实现；需要接线时写明确增量给集成负责人。不得自行提交推送或切换/清理分支。不要启动第二个连接真实数据的服务。各自必须提供验证命令、结果、真实产物、剩余项；工程通过不代替用户审美或节奏签收。

## 本轮完成标准

C：同环境同输入同时间结果一致，乱序 seek/倒退/重播不累积；人工覆盖和身份冲突得到保护；动作修改不触发 TTS；开源候选记录许可证、实际固定实验与采用理由。先实现已有能力缺口，不预设新时钟或强接框架。

D：编号/版本/源码/截图一致，可按表达任务只选择相关分类图、独立配色和统一风格；输出可实际读取的附件包，记录哈希与理由；参考变化准确失效，不支持项明确诊断。不把离线装配器成功等同 E 线真实供应商请求已经接入。

完成后由主对话做跨模块集成复核；E/F 的真实生成与完整课程验收另行推进。
