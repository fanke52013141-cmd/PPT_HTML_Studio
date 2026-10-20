# 2026-10-20 候选编辑与Pi Agent源码更新

本次向PPT_HTML_Studio/main发布候选画布/中文属性/保存版本恢复、联动修复与关联组采用、Pi固定接口M0–M5接线及GLM原生参数、设计图与冻结计划对应约束。契约0.9.108、API1.59.0；没有数据库迁移。

真实新设计已核对，Legacy理解ready后容量修复结果未知，Pi未启动；新页/音频/课程输出未验收，Legacy仍为默认。源码发布不含本地数据、凭据或服务部署。

安装、入口、所有权、真实试验终态和后续顺序见[本次handoff](../plans/html-backend-development/handoff-release-2026-10-20.md)。最终测试及提交信息在发布回执补录，旧handoff的“未发布”为历史状态。

首批源码已发布：[`1578d32`](https://github.com/fanke52013141-cmd/PPT_HTML_Studio/commit/1578d32c78e099e2d6f782b414aa55e94e87a0a5)。本机全量发现MCP/CLI新能力分发遗漏，已补严格通用分发与8种真实CLI请求回归，97项传输/合同测试通过；追加补丁与全量结果见handoff回执，未将首轮全量称为通过。
