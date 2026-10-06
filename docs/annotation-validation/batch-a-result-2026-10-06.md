# 批次 A 实施记录

已实现：属性变更立即捕获值，待提交编辑可强制提交；保存屏障等待正在进行的请求并排空后续操作；切条目提交原条目的编辑；预览和确认拒绝处理中产生的新编辑；明确讲稿关联按钮；未关联且未显式修改时间的草稿不能通过前端预览/确认；后端能力版本与前端就绪检查。

正式服务：确认持久任务与一键任务没有运行项后，备份 SQLite 至 outputs/annotation-batch-a/projects-before-restart.db，重启唯一端口 8000 服务。运行版本 annotation_batch_a_v1，ready=true；播放器资源 HTTP 200。浏览器实际进入现有项目的 Step 6，关联按钮可见，未选区时提示正确，浏览器错误为空。未向正式项目新增测试标注。截图 outputs/annotation-batch-a/formal-workspace.jpg。

验证：Python 标注及诊断回归 221 通过、1 跳过；Node save_flow、edit_recovery、workspace、playback 及 frontend_quality 通过；git diff --check 通过。新增行为覆盖立即提交未结束的属性防抖、保存期间撤销后的操作排空、切页等待保存、未关联默认起笔禁止确认。测试中 overlay boom 是刻意注入的渲染故障，用于验证保存恢复，不是正式浏览器错误。

范围：本轮网页为正式环境只读冒烟及提示检查；快速编辑的写入场景由隔离 VM 回归验证，尚未新增一轮浏览器快速编辑录像。AI/OCR、动态 Mask、100 短语独立真值与大页性能属于后续批次。前端能力版本用于接口兼容检查，不是完整源码构建哈希。新增触发保护在前端执行，API 仍允许显式 manual 时间。
