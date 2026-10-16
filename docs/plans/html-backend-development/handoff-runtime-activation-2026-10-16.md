# 本机8010换版完成 · 2026-10-16

## 操作与当前版本

用户明确要求由助手关闭旧开发服务后，重新核实8010的进程34872确为当前checkout的 `.venv/Scripts/python.exe start_server.py`。持久任务及两个项目的process-local五类控制均无活动，先备份数据库并记录运行文件SHA，再仅停止该进程。此次明确授权后的窄范围操作获准执行，未操作其他便携版进程。

确认端口释放后，以当前checkout的start_server.py隐藏启动，显式绑定127.0.0.1:8010、当前data/projects.db与runs。没有创建新运行副本或静默拉取远程代码。

实际HTTP meta核对：API1.39.0，合同hash2f9000d34a3b464d；此前“8010仍1.37.0”的记录是换版前历史，阻塞现已解除。

## 验收

- index.html、storyboard.js、one_click_extension.js、api_client.js、html_review_panel.js、stitch.css：HTTP字节与磁盘一致，全部no-store。
- 真实浏览器首页：pageErrors=0、非读取请求=0。
- 启动前后2个项目、1959个运行文件SHA、数据库10张表记录均相同，active_jobs=0。
- 数据库备份、启动日志与HTTP/浏览器/数据核对位于ignored `outputs/runtime-activation-20261016/`，不提交运行数据。

当前新版服务已加载讲稿核对闭环、容量进展判断和Web冲突转译修正。此前隔离完整应用TCP验证及30项固定清单继续作为对应实现证据，见[隔离运行交接](handoff-runtime-smoke-2026-10-16.md)。本次未在真实项目上发起生成、修正保存、配音或导出，未重发原遴选unknown；服务换版成功不能替代真实模型选策、语义/审美或完整课程验收。

## 后续

无需用户手动关闭旧进程。下一阶段是经明确允许的新真实案例实验；继续保留“暂不重发”约束。代码仍未commit/push，远程仓库不因本机换版而更新。
