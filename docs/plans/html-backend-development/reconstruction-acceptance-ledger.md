# 图片转HTML原69项验收对账

逐项列明实现、测试证据和缺口。partial不等于passed，真实模型、人审和发布门槛不由离线测试替代。

| AC | 任务 | 原验收要求 | 要求层级 | 状态 | 已有实现/测试 | 剩余事项 |
|---|---|---|---|---|---|---|
| AC-001 | T00 | 原离线基准可重现 | evidence | partial | scripts/verify_reconstruction_v2_acceptance.py；测试：checks/test_html_optimization_acceptance.py | 真实跨课程dataset/留出页证据尚未完成 |
| AC-002 | T00 | 浏览器基准有实际截图与检查报告 | evidence | partial | scripts/verify_reconstruction_v2_acceptance.py；测试：checks/test_html_optimization_acceptance.py | 真实跨课程dataset/留出页证据尚未完成 |
| AC-003 | T00 | dataset 中每个引用 hash 验证通过 | evidence | partial | scripts/verify_reconstruction_v2_acceptance.py；测试：checks/test_html_optimization_acceptance.py | 真实跨课程dataset/留出页证据尚未完成 |
| AC-004 | T00 | 留出页未用于调提示词/模板 | evidence | partial | scripts/verify_reconstruction_v2_acceptance.py；测试：checks/test_html_optimization_acceptance.py | 真实跨课程dataset/留出页证据尚未完成 |
| AC-005 | T00 | 缺少真实材料时 M0 可记录受限状态，但 T10 不得签发通过 | evidence | partial | scripts/verify_reconstruction_v2_acceptance.py；测试：checks/test_html_optimization_acceptance.py | 真实跨课程dataset/留出页证据尚未完成 |
| AC-006 | T01 | 同一原报告重复归一化一致 | unit | passed | html_reconstruction_diagnostics.py；测试：checks/test_html_reconstruction_diagnostics.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-007 | T01 | 未知 code 保留并停止，不能当容量错误 | unit | passed | html_reconstruction_diagnostics.py；测试：checks/test_html_reconstruction_diagnostics.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-008 | T01 | no_fit 与 budget_exhausted 分开 | unit | passed | html_reconstruction_diagnostics.py；测试：checks/test_html_reconstruction_diagnostics.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-009 | T01 | 单位不混算，像素溢出与行数超限分别排序 | unit | passed | html_reconstruction_diagnostics.py；测试：checks/test_html_reconstruction_diagnostics.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-010 | T02 | 无作者文件时可测量/求解 | integration | passed | html_saved_layout_repair.py, html_capacity_repair.py；测试：checks/test_html_saved_layout_repair.py, checks/test_html_candidate_capacity_solver.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-011 | T02 | 传入的 manual 实际参与拒绝 | integration | passed | html_saved_layout_repair.py, html_capacity_repair.py；测试：checks/test_html_saved_layout_repair.py, checks/test_html_candidate_capacity_solver.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-012 | T02 | 已保存页 revision/audio 过期仍拒绝 | integration | passed | html_saved_layout_repair.py, html_capacity_repair.py；测试：checks/test_html_saved_layout_repair.py, checks/test_html_candidate_capacity_solver.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-013 | T02 | 两种适配得到相同候选语义及检查结果 | integration | passed | html_saved_layout_repair.py, html_capacity_repair.py；测试：checks/test_html_saved_layout_repair.py, checks/test_html_candidate_capacity_solver.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-014 | T02 | 输入对象不被原地修改 | integration | passed | html_saved_layout_repair.py, html_capacity_repair.py；测试：checks/test_html_saved_layout_repair.py, checks/test_html_candidate_capacity_solver.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-015 | T02 | 所有 INV-05 快照不变 | integration | passed | html_saved_layout_repair.py, html_capacity_repair.py；测试：checks/test_html_saved_layout_repair.py, checks/test_html_candidate_capacity_solver.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-016 | T03 | 两对象必须同时调整的夹具最终通过 | real_browser | passed | html_capacity_repair.py；测试：checks/test_html_candidate_capacity_solver.py, checks/test_html_search_scheduling.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-017 | T03 | 三卡片各有缺陷时不丢失前步进展 | real_browser | passed | html_capacity_repair.py；测试：checks/test_html_candidate_capacity_solver.py, checks/test_html_search_scheduling.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-018 | T03 | 默认字体也能修 | real_browser | passed | html_capacity_repair.py；测试：checks/test_html_candidate_capacity_solver.py, checks/test_html_search_scheduling.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-019 | T03 | 输入目标顺序变化不造成对象饥饿 | real_browser | passed | html_capacity_repair.py；测试：checks/test_html_candidate_capacity_solver.py, checks/test_html_search_scheduling.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-020 | T03 | 重复状态不会再次测量 | real_browser | passed | html_capacity_repair.py；测试：checks/test_html_candidate_capacity_solver.py, checks/test_html_search_scheduling.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-021 | T03 | 超预算有独立终态 | real_browser | passed | html_capacity_repair.py；测试：checks/test_html_candidate_capacity_solver.py, checks/test_html_search_scheduling.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-022 | T03 | 单独某字段受保护时合法兄弟字段仍可修改 | real_browser | passed | html_capacity_repair.py；测试：checks/test_html_candidate_capacity_solver.py, checks/test_html_search_scheduling.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-023 | T03 | 不可读字号/行距候选从不进入通过结果 | real_browser | passed | html_capacity_repair.py；测试：checks/test_html_candidate_capacity_solver.py, checks/test_html_search_scheduling.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-024 | T04 | 终态正常但入场穿字的用例被拒 | real_browser | passed | html_linked_layout.py, html_geometry_repair.py；测试：checks/test_html_linked_layout.py, checks/test_html_production_preflight.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-025 | T04 | point 路由通过且关系身份不变 | real_browser | passed | html_linked_layout.py, html_geometry_repair.py；测试：checks/test_html_linked_layout.py, checks/test_html_production_preflight.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-026 | T04 | anchor 不参与附着点搜索 | real_browser | passed | html_linked_layout.py, html_geometry_repair.py；测试：checks/test_html_linked_layout.py, checks/test_html_production_preflight.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-027 | T04 | 不把缺陷转移到第三个标签 | real_browser | passed | html_linked_layout.py, html_geometry_repair.py；测试：checks/test_html_linked_layout.py, checks/test_html_production_preflight.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-028 | T04 | 动态报告缺帧/超时/缺失均不能通过 | real_browser | passed | html_linked_layout.py, html_geometry_repair.py；测试：checks/test_html_linked_layout.py, checks/test_html_production_preflight.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-029 | T04 | 容量阻断动态时保留 blocked_by_capacity，而非误报全动态已通过 | real_browser | passed | html_linked_layout.py, html_geometry_repair.py；测试：checks/test_html_linked_layout.py, checks/test_html_production_preflight.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-030 | T05 | 首次生产轻度溢出经确定性修复继续 | integration_real_browser | passed | html_production_service.py, html_design_reconstruction.py；测试：checks/test_html_design_reconstruction.py, checks/test_html_production_recovery.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-031 | T05 | 变体切换造成的溢出也经同一路径修复 | integration_real_browser | passed | html_production_service.py, html_design_reconstruction.py；测试：checks/test_html_design_reconstruction.py, checks/test_html_production_recovery.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-032 | T05 | 修复模型调用为 0，其他理解/审核调用分开统计 | integration_real_browser | passed | html_production_service.py, html_design_reconstruction.py；测试：checks/test_html_design_reconstruction.py, checks/test_html_production_recovery.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-033 | T05 | 无解不覆盖旧作者 | integration_real_browser | passed | html_production_service.py, html_design_reconstruction.py；测试：checks/test_html_design_reconstruction.py, checks/test_html_production_recovery.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-034 | T05 | 旧策略行为回归通过 | integration_real_browser | passed | html_production_service.py, html_design_reconstruction.py；测试：checks/test_html_design_reconstruction.py, checks/test_html_production_recovery.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-035 | T05 | 保护、取消、过期各自保持原语义 | integration_real_browser | passed | html_production_service.py, html_design_reconstruction.py；测试：checks/test_html_design_reconstruction.py, checks/test_html_production_recovery.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-036 | T06 | 出站没有 HTML 几何 | file_evaluation_and_model | partial | html_reference_localization.py, html_review_evidence.py, html_reference_routes.py；测试：checks/test_html_independent_review.py, checks/test_html_reference_api.py | 工程/模拟响应不证明真实模型定位准确率 |
| AC-037 | T06 | 大幅位移仍按身份正确配对 | file_evaluation_and_model | partial | html_reference_localization.py, html_review_evidence.py, html_reference_routes.py；测试：checks/test_html_independent_review.py, checks/test_html_reference_api.py | 工程/模拟响应不证明真实模型定位准确率 |
| AC-038 | T06 | 模糊定位不进入自动尺寸修复 | file_evaluation_and_model | partial | html_reference_localization.py, html_review_evidence.py, html_reference_routes.py；测试：checks/test_html_independent_review.py, checks/test_html_reference_api.py | 工程/模拟响应不证明真实模型定位准确率 |
| AC-039 | T06 | hash 不一致停止 | file_evaluation_and_model | partial | html_reference_localization.py, html_review_evidence.py, html_reference_routes.py；测试：checks/test_html_independent_review.py, checks/test_html_reference_api.py | 工程/模拟响应不证明真实模型定位准确率 |
| AC-040 | T06 | 容器/正文不互相冒充 | file_evaluation_and_model | partial | html_reference_localization.py, html_review_evidence.py, html_reference_routes.py；测试：checks/test_html_independent_review.py, checks/test_html_reference_api.py | 工程/模拟响应不证明真实模型定位准确率 |
| AC-041 | T06 | 审计页显示真实局部对照与原始报告引用 | file_evaluation_and_model | partial | html_reference_localization.py, html_review_evidence.py, html_reference_routes.py；测试：checks/test_html_independent_review.py, checks/test_html_reference_api.py | 工程/模拟响应不证明真实模型定位准确率 |
| AC-042 | T07 | 同一未改变区域不能仅因新模型说 pass 清除问题 | integration_and_paired_model | partial | html_design_agent.py；测试：checks/test_html_design_agent.py | 完整配对模型实验尚未完成 |
| AC-043 | T07 | 注册变体事实与模型建议不符时阻断 | integration_and_paired_model | partial | html_design_agent.py；测试：checks/test_html_design_agent.py | 完整配对模型实验尚未完成 |
| AC-044 | T07 | 文字内容错误不由局部几何工具修 | integration_and_paired_model | partial | html_design_agent.py；测试：checks/test_html_design_agent.py | 完整配对模型实验尚未完成 |
| AC-045 | T07 | 原图错字不覆盖准确文本 | integration_and_paired_model | partial | html_design_agent.py；测试：checks/test_html_design_agent.py | 完整配对模型实验尚未完成 |
| AC-046 | T07 | 重点裁图不会增加未登记的图片预算 | integration_and_paired_model | partial | html_design_agent.py；测试：checks/test_html_design_agent.py | 完整配对模型实验尚未完成 |
| AC-047 | T07 | 前后配对实验单独量测该任务收益 | integration_and_paired_model | partial | html_design_agent.py；测试：checks/test_html_design_agent.py | 完整配对模型实验尚未完成 |
| AC-048 | T08 | 卡片图标不能替代必要插图 | integration_and_model | partial | html_design_feasibility.py, html_asset_reuse.py；测试：checks/test_html_asset_reuse.py, checks/test_html_design_feasibility.py | 已有工程路径；真实模型和视觉判断仍独立 |
| AC-049 | T08 | 多插图超能力在接受前给出明确诊断 | integration_and_model | partial | html_design_feasibility.py, html_asset_reuse.py；测试：checks/test_html_asset_reuse.py, checks/test_html_design_feasibility.py | 已有工程路径；真实模型和视觉判断仍独立 |
| AC-050 | T08 | 相同资产复用不发生额外生成 | integration_and_model | partial | html_design_feasibility.py, html_asset_reuse.py；测试：checks/test_html_asset_reuse.py, checks/test_html_design_feasibility.py | 已有工程路径；真实模型和视觉判断仍独立 |
| AC-051 | T08 | 修改资源 hash 使相关候选失效 | integration_and_model | partial | html_design_feasibility.py, html_asset_reuse.py；测试：checks/test_html_asset_reuse.py, checks/test_html_design_feasibility.py | 已有工程路径；真实模型和视觉判断仍独立 |
| AC-052 | T08 | 更换图像不能继承未经验证的语义锚点 | integration_and_model | partial | html_design_feasibility.py, html_asset_reuse.py；测试：checks/test_html_asset_reuse.py, checks/test_html_design_feasibility.py | 已有工程路径；真实模型和视觉判断仍独立 |
| AC-053 | T08 | UI 展示原因且不自动批准 | integration_and_model | partial | html_design_feasibility.py, html_asset_reuse.py；测试：checks/test_html_asset_reuse.py, checks/test_html_design_feasibility.py | 已有工程路径；真实模型和视觉判断仍独立 |
| AC-054 | T09 | 同一状态只检查一次且来源变化不命中旧通过 | integration_fault_injection | passed | html_page_budget.py, html_reference_jobs.py, html_review_cache.py；测试：checks/test_html_page_budget.py, checks/test_html_reference_api.py, checks/test_html_review_cache.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-055 | T09 | unknown 不自动补发 | integration_fault_injection | passed | html_page_budget.py, html_reference_jobs.py, html_review_cache.py；测试：checks/test_html_page_budget.py, checks/test_html_reference_api.py, checks/test_html_review_cache.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-056 | T09 | usage/cost 缺失为 null | integration_fault_injection | passed | html_page_budget.py, html_reference_jobs.py, html_review_cache.py；测试：checks/test_html_page_budget.py, checks/test_html_reference_api.py, checks/test_html_review_cache.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-057 | T09 | 子阶段不能绕过总调用预算 | integration_fault_injection | passed | html_page_budget.py, html_reference_jobs.py, html_review_cache.py；测试：checks/test_html_page_budget.py, checks/test_html_reference_api.py, checks/test_html_review_cache.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-058 | T09 | 用户取消后不开始下一阶段 | integration_fault_injection | passed | html_page_budget.py, html_reference_jobs.py, html_review_cache.py；测试：checks/test_html_page_budget.py, checks/test_html_reference_api.py, checks/test_html_review_cache.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-059 | T09 | 恢复任务不重复保存或批准 | integration_fault_injection | passed | html_page_budget.py, html_reference_jobs.py, html_review_cache.py；测试：checks/test_html_page_budget.py, checks/test_html_reference_api.py, checks/test_html_review_cache.py | 本条所需层级的独立检查已通过；不代替其他AC或整体验收。 |
| AC-060 | T10 | 同输入配对身份一致 | real_model_and_human_review | not_run | ；测试： | 待真实模型及人工配对评测；不得用mock或离线报告签发通过 |
| AC-061 | T10 | 所有失败进入分母 | real_model_and_human_review | not_run | ；测试： | 待真实模型及人工配对评测；不得用mock或离线报告签发通过 |
| AC-062 | T10 | 每个达标数字能追到页面、调用和报告 | real_model_and_human_review | not_run | ；测试： | 待真实模型及人工配对评测；不得用mock或离线报告签发通过 |
| AC-063 | T10 | 上述门槛逐项 passed/failed/pending，不能只给总评分 | real_model_and_human_review | not_run | ；测试： | 待真实模型及人工配对评测；不得用mock或离线报告签发通过 |
| AC-064 | T11 | 策略可回退且不重写已有作者 | release_and_real_end_to_end | partial | html_build_snapshot.py；测试：checks/test_html_build_snapshot.py | 尚未发布；正式音视频与具体发布commit待验 |
| AC-065 | T11 | 保存重开和历史恢复通过 | release_and_real_end_to_end | partial | html_build_snapshot.py；测试：checks/test_html_build_snapshot.py | 尚未发布；正式音视频与具体发布commit待验 |
| AC-066 | T11 | Agent/Web 合同一致 | release_and_real_end_to_end | partial | html_build_snapshot.py；测试：checks/test_html_build_snapshot.py | 尚未发布；正式音视频与具体发布commit待验 |
| AC-067 | T11 | 相关快照与失效规则生效 | release_and_real_end_to_end | partial | html_build_snapshot.py；测试：checks/test_html_build_snapshot.py | 尚未发布；正式音视频与具体发布commit待验 |
| AC-068 | T11 | 原音视频链路实际验证 | release_and_real_end_to_end | partial | html_build_snapshot.py；测试：checks/test_html_build_snapshot.py | 尚未发布；正式音视频与具体发布commit待验 |
| AC-069 | T11 | 发布结论有具体 commit、命令、日志、未决项 | release_and_real_end_to_end | partial | html_build_snapshot.py；测试：checks/test_html_build_snapshot.py | 尚未发布；正式音视频与具体发布commit待验 |
