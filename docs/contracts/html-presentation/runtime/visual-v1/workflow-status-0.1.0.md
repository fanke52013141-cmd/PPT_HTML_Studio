# S07 用户状态与同源接口定义卡 0.1.0

2026-10-12；HPS-010/011/014/015/017/030。Agent API 1.20.0；沿用 LocalJob、原生产服务、作者数据与 artifact_records。

| 项目 | 定义 |
|---|---|
| 任务读取 | 原 task_status 增加 slide_id、stage、source_revision、progress、input_state、recovery；原 html_visual.status 的 workflow.tasks 提供项目概览；新 task_current 在 SQL 按页过滤后查询最新任务，不受概览20条限制。旧任务缺版本时为 unknown，不推断当前完成 |
| 进度来源 | ProductionStages 持久记录实际结果复用；候选 Agent evaluate 边界记录实际轮次和已校验 Skill 身份，不预测耗时或虚构百分比 |
| 当前版本 | 详情读取复用 ProductionStages 的只读冻结快照与实际源码/定义/素材字节校验，再核对当前分镜摘要。task_status 以作者 revision 核对 source_revision 或成功 result.saved.revision；不匹配为 stale。任务 succeeded/design_review 仅表示停在设计确认；静态通过不表示视觉批准 |
| 恢复请求 | POST Web/Agent .../html-review/tasks/{job_id}/resume，空 body；MCP ppt_html_task_resume、CLI html task-resume --project --job。账户/项目/后端守卫沿用原接口 |
| 恢复执行 | 仅场景生产任务；读取原固定 contract/options，核对当前内容与 revision，再经原 submit 对账、快照身份与预算校验。active/succeeded 复用原任务；取消、未知请求、坏回执、预算耗尽或输入/模型/代码变化拒绝直接续跑。没有新增供应商重发旁路 |
| 页面恢复 | 按当前项目和页找到生产任务，读取原 task_status 并继续轮询；连接失败重连。项目/页切换令旧响应失效，清空旧候选、截图、任务和操作参数 |
| 编辑影响 | 原 editor preview/read/save 的 rebuild_plan 在界面呈现逐页重做/复用与课程影响；修改后的实际预览完成后才能保存，显示无变化与复用仍需核验。不自动生成音频或新增批准 |
| 输出展示 | 原视频/PPTX 列表增加只读 export_evidence 摘要：snapshot_id、pages.slide_id/reused；不返回工作目录或文件系统快照路径。结合原 artifact_state 与 historical 展示当前交付、历史候选、缺失/损坏，原导出按钮门禁保持 |
| 非本轮 | 不实现 S04 连续时间 QA、无进展停止、全阶段自动重建、缓存 GC、真实课程/音画/审美签收 |

验收：刷新恢复、迟到响应和项目隔离；继续原选项、不重复活跃任务；unknown/cancelled/stale/耗尽拒绝；Web/Agent/MCP/CLI一致；编辑影响保存前可见；历史成功不冒充当前交付，图片路线原显示保持。

GET Web/Agent `.../html-review/{slide_id}/task/current` 返回当前页最新任务或 null；MCP `ppt_html_task_current`、CLI `html task-current --project --slide`。详情校验当前依赖，项目概览不逐任务重读所有依赖，也不能用概览认定当前交付有效。
