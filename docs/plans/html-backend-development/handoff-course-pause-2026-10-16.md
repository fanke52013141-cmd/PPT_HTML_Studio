# 课程父子暂停修复

用户明确选择先修父子任务暂停，暂不重发原未知供应商请求。本批承接[流等待诊断](handoff-stream-wait-diagnostics-2026-10-16.md)，规范为[课程父子暂停0.1.0](../../contracts/html-presentation/runtime/visual-v1/course-pause-0.1.0.md)，当前契约0.9.55/API1.36.0。

## 已修复

原CourseActions.storyboard仅检查success=false，使generation_control明确返回的cancelled=true落入ValueError，父任务记HTML_COURSE_STAGE_FAILED；这是原遴选案例中的已知控制状态缺陷。

现先识别cancelled/busy：取消使父任务paused、error=null，停止后续visual/compose；已有手动操作占用使waiting_for_user，课程不接管或停止该操作。一般失败、外部异常/未知仍保留原阻断，不能把任何错误都改作暂停。

明确停止/占用在原分镜阶段账本保存cancelled/busy、attempts和requires_review。没有有效当前合同时，直接继续返回STORYBOARD_REVIEW_REQUIRED，不重新调用分镜；原入口核实完成后继续同父ID、跳过分镜。已取消持久子任务保留原ID并暂停父任务，不恢复或创建替代任务。分镜停点不再错误标audio_review。

## 验证与边界

课程/评估器定向 **25项通过**，包括原课程完整链、设计待审、原父子ID/进程恢复、unknown禁重发、取消父任务不复活以及新增适配层取消/占用、手动分镜锁和取消子任务不替换。新测试初次漏Path导入导致2项setup失败，补导入后全组通过，没有改产品门禁接受坏数据。

固定清单0.5.0 **23/23通过**，Python **57项**及两个浏览器检查通过，报告在ignored `outputs/workflow-evaluation-20261016-v5/`；课程/Agent联合 **453项通过**。Ruff、JS语法、Agent矩阵与契约索引检查通过。旧22项/52个Python检查和浏览器通过记录单独保留，不跨清单计算提升率。

全部使用隔离DB/运行文件、明确阶段替身与真实进程内控制锁；没有发出模型/TTS/生图/导出请求，也没有修改原项目任务来把历史失败变为暂停。真实提供者取消或完整课程仍未重新实测。

此批不会让已取消子任务重新成功，也不自动修复其产物；继续仍由当前真实scene/合同/音频/签收核验决定。原未知规划请求保留，不重复实验。

服务启动前核实原8010未监听、真实active_jobs=0，直接从本checkout启动start_server.py，仍为127.0.0.1:8010和原DB/runs，隐藏后台启动。日志在ignored `outputs/stream-pause-fixes-20261016/`。meta确认API1.36.0/hash a3b1b07bcd0b0d6d；真实项目仍2个、active_jobs=0、原案例作者scene=0。源码尚未提交/推送，不修改旧线上发布记录。

## 后续

下一独立工作是文章/讲稿限定词保真和容量诊断；模型连接稳定性与新标签真实规划仍需另行核实/授权实验。完整HTML质量、逐句语义QA、音频、数字人及正式导出仍分别验收。
