# 目录跨机换行与独立 Agent 复验（2026-10-26）

基线8aa5695。上一轮catalog检查失败来自core.autocrlf=true检出导致35个源文件变为CRLF；35项原封存hash均匹配Git原始字节及LF版本。本轮不修改哈希算法、登记hash或生成目录。

## 修复

.gitattributes固定目录来源中的JSON、Markdown、HTML、注册布局/模板/主题及course-structures为LF。现有嵌套-text继续生效；额外为五个Git原始内容含CRLF或混合换行的封存源保留-text例外。仅对目录闭包执行本机换行恢复，没有全仓库重整、暂存或修改Git配置。恢复后源文件与Git内容一致，无业务内容变更。

catalog-assembler.test.cjs新增覆盖实际来源与产物的Git属性检查：text必须固定LF，或由-text保留原字节；LF路径检查实际工作区无CRLF。原catalog产物一致性检查仍核验逐字节hash。目录README说明例外与扩展约束。本批为检出策略修复，不新增HPS能力、API、数据或迁移；批准/人工编辑/运行语义保持。

## 验证

- node --test --test-name-pattern="catalog text source|build output and documentation" html_engine/tests/catalog-assembler.test.cjs：2项通过。
- node html_engine/tools/catalog-build.cjs --check：41文件current；snapshot 196c36f8faebdc231ca0ca1a9a270c99bd6c6cde2fd1d0bcbeedbd8374e6bb02，原目录未重建。
- 独立运行 .venv/Scripts/python.exe -m pytest checks/agent -q：519 passed，58.07秒，1条既有Starlette弃用警告。启动前确认没有其他pytest/逐帧/benchmark验收任务，本轮未并行运行其他验收。
- 前轮Agent为518 passed/1 failed，Pi任务30秒等待后仍running；单例复跑通过。本轮全套通过不抹去旧失败，也不足以确定负载是唯一原因；未放宽等待/断言。

本机日志位于outputs/line-ending-fix-20261026：catalog-tests-final.log、catalog-check-final.log、agent-isolated.log、agent-isolated.xml。中间检查暴露既有混合换行封存源及嵌套属性，失败日志保留，最终修复按上述结果复验。

未提交/推送、重启服务或部署，无真实供应商调用。原69项验收仍以逐项证据为准，本轮不提升真实课程、模型、人审或交付状态。旧验收包记录旧字节，保留历史，不作为修复后源码的新签章。
