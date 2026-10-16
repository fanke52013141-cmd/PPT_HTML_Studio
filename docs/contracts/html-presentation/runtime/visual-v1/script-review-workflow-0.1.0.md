# 讲稿核对与原课程继续 0.1.0

HPS-010/011/013—017；合同包0.9.58，Agent API1.38.0。沿用讲稿限定范围窄规则，不增加付费审核模型，不授予视觉或音频批准。

## 定义卡

| 项目 | 定义 |
| --- | --- |
| 入口 | 原Step2A生成、script/result读写、Step2B及compose；不新增平行生产入口 |
| 正式讲稿 | planning/slide_script_plan.json，仍是下游权威输入 |
| 核对候选 | planning/script_review.json当前记录；script_reviews/<review_id>.json保留原始问题候选，修正不覆盖历史问题稿 |
| 记录 | version0.1.0、随机review_id、创建时间/请求trace_id、article_hash、base_script_hash、candidate、issues、status；resolved追加resolved_script_hash |
| 身份 | 当前完整原文内容与标题、当前正式讲稿精确JSON摘要；生成期间变化则拒绝应用，读取时标记stale |
| 状态 | pending等待修正；resolved已通过现行检查保存；superseded为过期候选经显式新生成后替换的历史，不等于批准 |
| 生成风险 | 返回原409及script_review，候选落盘，正式讲稿/合同/音频不覆盖；当前候选未过期时重复生成在模型调用前拒绝 |
| 读取 | success=true、script_plan为正式讲稿或null、script_review独立返回；无正式讲稿但有核对候选可正常读取 |
| 保存 | 客户端附当前review_id，服务持有项目文件锁；原文/正式讲稿/候选身份过期则409。继续存在限定风险仍停止，无风险后沿原失效服务保存正式讲稿并标resolved |
| 一次提交 | 已解决的review_id拒绝再次提交；重新读取后普通编辑仍沿原规则检查，不复活旧候选 |
| 前端 | 原讲稿编辑器加载当前候选，显示页/原句/候选句；核对期间停用自动保存，明确点击保存修正讲稿。可视化与下一步禁用；成功后可继续，不自动生成 |
| 课程停点 | waiting_for_user/storyboard，review_checkpoint=script_review，production_stages.storyboard.state=content_review；保留原父任务ID、尝试次数、产物和原始问题记录 |
| 继续 | 当前核对必须resolved且非stale，才允许原课程重新排队；复用修正讲稿，跳过Step2A，必要时生成Step2B并合成。已有当前映射可复用；有效合同已完成时直接使用 |
| 未知结果 | 原intent/unknown、不确定子任务、取消及人工保护门禁保持，不因核对功能允许自动重发 |

## 所有权与兼容

storyboard_plan_store.py拥有候选文件、摘要和新鲜度；storyboard_service.py拥有生成返回、项目锁和写前门禁。storyboard_planning.py继续拥有保真纯规则。html_course_runtime.py把已知内容核对异常转换为等待边界；html_course_jobs.py持久化停点并验证继续条件。课程源闭包纳入实际规划/模板/存储模块。

static/storyboard.js拥有核对显示、明确保存和会话隔离，复用原API传输与原讲稿输入；one_click_extension.js在进入该停点时读取一次，后续轮询不覆盖输入。后台停点未取得新的证据前不清除；跨项目迟到响应不应用。当前候选过期时只显示对照，允许用户明确重新生成，旧问题稿保留。

原API路径、Step2A模型输出Schema、数据库、HTML作者scene/binding、原图片生产限制保持。响应新增script_review且script_plan允许null；409增加候选上下文。pipeline.run/resume能力1.5，status1.4。已有任务随源码身份变化仍成为历史，不迁移真实旧失败或unknown记录。

## 验证边界

隔离真实文件/服务和持久课程存储，使用模型替身验证一次生成→持久等待→重建协调器→修正→原任务继续，禁止第二次Step2A调用。验证旧正式稿/合同/音频不变、重复生成不付费、缺失/错误/已消费review_id、原文/正式稿变化及在途变化拒绝。真实浏览器验证候选重读、文字安全、自动保存禁止、明确保存、过期禁用与跨项目隔离；实际轮询函数验证停点只读取一次。

这是操作与恢复闭环，不是通用限定词语义蕴含证明；现行风险规则未命中不等于全面内容保真。跨进程同时运行、任意同义改写和真实供应商效果不由这些离线验证证明。记录写入故障仍失败关闭，不能假称修正完成；原未知请求继续保留。
