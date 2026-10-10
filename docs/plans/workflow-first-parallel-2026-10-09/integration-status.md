# A 线集成状态

## 2026-10-10 C/D 收束增量

C/D 实现和固定证据已由主对话复验，发布交接见 [CD-RELEASE-EF-HANDOFF.md](CD-RELEASE-EF-HANDOFF.md)。C 的严格 binder 与旧简写 fixture 有冲突，现已用既有合法格式修正测试输入；89 项联合回归通过。D 的离线目录/参考装配 8 项测试与41文件一致性检查通过。没有接入真实供应商、没有采用 Anime.js 生产时钟；exit 生命周期、生产参考包接线与真实导出/课程签收仍未完成。默认黑灰白基线保持，E/F 尚未启动。

更新：2026-10-10。基线：`7499e4a5b4f40842f6dd4d559a8067550b15a86e`；实际工作区 `D:\software\PPT_HTML_Studio`。事实来源和接口见 [interface-baseline.md](interface-baseline.md)，写入边界见 [ownership.json](ownership.json)，实现证据见 [A 线交付](deliveries/A.md)。

| 范围 | 定义与实现状态 | 验证结论 |
|---|---|---|
| WF-01 七阶段业务汇总 | 已定义于应用工作流状态 0.2.0；`html_creation_workflow.project_status` 从项目、分镜、场景/批准、音频、binding、可选数字人与持久任务派生状态。 | 空项目、七阶段 ID/状态、Web/Agent 同载荷通过。没有把后端七阶段映射到八个 UI 位置或写回 `Project.step_status`。 |
| WF-02 音频先于场景 | 音频确认与场景/视觉审批状态独立；动画和 MP4 继续依赖有效确认。 | 无场景已有音频确认时，audio=`ready`、design=`not_started`，PPTX/视频均未解锁；HTML 视频服务无确认仍返回 400。 |
| WF-03 视觉范围与批准 | PPTX/视频都要求当前已保存 HTML scene 和逐页批准指纹；无批准/过期/坏场景分别呈现。设计参考、技术审阅不能创建人工批准。 | 测试覆盖当前批准、binding 修改后审批过期、重新批准。既有 science 风格 `changes_requested` 状态不变，不登记为视觉通过。 |
| WF-04 job 幂等和手工保护 | `HtmlWorkflowJobs` 使用完整 submission key；状态接口只汇总安全任务生命周期字段。 | 同输入 cache hit 复用同任务且 provider 调用数保持 0；合法输入改变后 cache miss 实际运行，任务发生人工修改冲突，旧手工 scene/revision 原样保留并保存 conflict 诊断。 |
| WF-05 revision 并发 | 保留现有全项目 revision 和冲突保护，本轮未进行多页并发负载/重提路径重现。 | 此风险仍待独立复测，不据本轮单页手工冲突测试宣称已消除。 |
| WF-06 合同/Agent 同步 | 新增应用合同 0.2.0、契约包 0.9.16、Agent API 1.16.0、`html_visual.status` 1.1；生成 capability matrix。 | Agent 生成文件 `--check` 通过，Agent/MCP/CLI 合同回归通过。没有向 remote 发布。 |
| WF-07 真实供应商和课程验收 | 本轮仅运行 fixture/provider 替身；没有发起外部生成请求，也没有请求用户视觉/课程审阅。 | 未验证/未签收；参考样页、美感、真实数字人和完整课程结论不从工程测试推导。 |
| B 标准库样页映射 | B 已提供两页静态样页、六张配色截图和生产映射提案，记录在 [B 线交付](deliveries/B.md)。 | A 未把样页登记为生产模板或接入 scene/Schema。双概念比较需要显式版本布局和最多两个资产槽；曲线路径尚无公共 path 能力；V1 主题字体与样页字体不同。均保持为定义/视觉审阅缺口，不以静态样页绕过现有模板预算。 |
| 输出目标 | `html_snapshot_pptx` 仅要求当前视觉批准；`mp4_video` 另要求当前音频确认、逐页合法 beat binding，且启用数字人时需对应媒体。 | 合法 visual + audio + binding：PPTX 可执行；损坏 binding：PPTX 可执行而视频阻塞；binding 改动令批准过期后两者都阻塞。禁用/未启用数字人状态为 `skipped`。 |
| 旧图片流程与工作区 | `static/flow.js` 和图像后端状态不改；HTML 只读汇总在现有 HTML 路由中。 | `node checks/test_visible_flow.js` 通过；图像路径的 video render 组件、持久任务和幂等回归一并通过。 |

## 可复用页面路径证据

现有五页工作流验收实际组装三种受约束模板，检查场景保存、beat binding、实际 PNG 资源加载和过程关键帧。样例中 3 页请求设计参考、2 页不请求设计参考；主体图像请求按需生成并校验透明背景。同输入/资源缓存复用也被断言。provider 是测试替身，HTML/资源装配和技术 review 使用本机运行代码；这只能证明可达工程路径，不构成真实供应商、用户设计审阅或完整课程签收。

本机未找到配置中的 Playwright Chromium 1247 路径；使用已安装 Microsoft Edge 经 `HPS_CHROME` 跑过浏览器依赖回归。浏览器技术通过不是用户美感批准。

## 旧审计迁移说明

源审计记录来自不同 HEAD，其中 `checks/test_html_motion_service.py` 和 `checks/test_html_audio_preview.py` 在当前 checkout 不存在。当前对应实现是 `HtmlWorkflowJobs.submit` + `html_task_store`；新增测试在合法变化后的输入上断言真实生成、cache miss 和人工冲突保存。基线浏览器命令因配置路径不存在而失败，后续 Edge 环境下的最终目标套件通过；旧命令路径差异不改写为业务失败或通过。
