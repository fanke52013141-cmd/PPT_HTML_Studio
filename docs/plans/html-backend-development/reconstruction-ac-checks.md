# 原69项逐条执行清单

本轮状态来自outputs/engineering23-20261026/ac-verification-final.json；36 passed、0 failed、33 pending。23项工程补证完成；源码/规则/证据变化后须复验。工程通过不替代真实模型、人审及发布。

| AC | 原要求 | 层级 | 当前判定 | 精确检查选择器 | 完整性 |
|---|---|---|---|---|---|
| AC-001 | 原离线基准可重现 | evidence | pending | checks/test_html_optimization_acceptance.py::test_verifier_rejects_missing_stale_skipped_or_mock_evidence | supporting |
| AC-002 | 浏览器基准有实际截图与检查报告 | evidence | pending | checks/test_html_p0p2_layouts.py::test_new_templates_normalize_semantics_compile_and_full_frames | supporting |
| AC-003 | dataset 中每个引用 hash 验证通过 | evidence | pending | checks/test_html_paired_evaluation.py::test_tampered_source_or_gold_or_response_rejected | supporting |
| AC-004 | 留出页未用于调提示词/模板 | evidence | pending | checks/test_html_paired_evaluation.py::test_pair_denominators_and_holdout_are_separate | supporting |
| AC-005 | 缺少真实材料时 M0 可记录受限状态，但 T10 不得签发通过 | evidence | pending | checks/test_html_acceptance_criteria.py::test_all_69_rules_preserve_required_layers | supporting |
| AC-006 | 同一原报告重复归一化一致 | unit | passed | checks/test_html_reconstruction_diagnostics.py::test_diagnostics_deterministic_and_units_retained | complete |
| AC-007 | 未知 code 保留并停止，不能当容量错误 | unit | passed | checks/test_html_reconstruction_diagnostics.py::test_unknown_code_is_incomplete_not_capacity | complete |
| AC-008 | no_fit 与 budget_exhausted 分开 | unit | passed | checks/test_html_reconstruction_diagnostics.py::test_no_fit_budget_and_unknown_remain_distinct | complete |
| AC-009 | 单位不混算，像素溢出与行数超限分别排序 | unit | passed | checks/test_html_reconstruction_diagnostics.py::test_units_are_not_aggregated_or_rounded | complete |
| AC-010 | 无作者文件时可测量/求解 | integration | passed | checks/test_html_engineering_completion.py::test_multiple_objects_and_inherited_fonts_finish_with_original_full_frames | complete |
| AC-011 | 传入的 manual 实际参与拒绝 | integration | passed | checks/test_html_engineering_completion.py::test_manual_block_and_cancelled_search_preserve_document_and_evidence | complete |
| AC-012 | 已保存页 revision/audio 过期仍拒绝 | integration | passed | checks/test_html_engineering_completion.py::test_saved_unsaved_candidate_semantics_and_all_input_snapshots | complete |
| AC-013 | 两种适配得到相同候选语义及检查结果 | integration | passed | checks/test_html_engineering_completion.py::test_saved_unsaved_candidate_semantics_and_all_input_snapshots | complete |
| AC-014 | 输入对象不被原地修改 | integration | passed | checks/test_html_candidate_capacity_solver.py::test_cumulative_unsaved_repair_preserves_manual_and_requires_dynamic_pass | complete |
| AC-015 | 所有 INV-05 快照不变 | integration | passed | checks/test_html_engineering_completion.py::test_saved_unsaved_candidate_semantics_and_all_input_snapshots | complete |
| AC-016 | 两对象必须同时调整的夹具最终通过 | real_browser | passed | checks/test_html_engineering_completion.py::test_multiple_objects_and_inherited_fonts_finish_with_original_full_frames | complete |
| AC-017 | 三卡片各有缺陷时不丢失前步进展 | real_browser | passed | checks/test_html_engineering_completion.py::test_multiple_objects_and_inherited_fonts_finish_with_original_full_frames | complete |
| AC-018 | 默认字体也能修 | real_browser | passed | checks/test_html_engineering_completion.py::test_multiple_objects_and_inherited_fonts_finish_with_original_full_frames | complete |
| AC-019 | 输入目标顺序变化不造成对象饥饿 | real_browser | passed | checks/test_html_engineering_completion.py::test_target_order_cannot_starve_any_of_three_objects | complete |
| AC-020 | 重复状态不会再次测量 | real_browser | passed | checks/test_html_search_scheduling.py::test_duplicate_and_noop_candidates_do_not_consume_search_quota | complete |
| AC-021 | 超预算有独立终态 | real_browser | passed | checks/test_html_engineering_completion.py::test_real_browser_budget_has_distinct_terminal_state | complete |
| AC-022 | 单独某字段受保护时合法兄弟字段仍可修改 | real_browser | passed | checks/test_html_engineering_completion.py::test_leaf_protection_allows_sibling_height_and_preserves_sources | complete |
| AC-023 | 不可读字号/行距候选从不进入通过结果 | real_browser | passed | checks/test_html_engineering_completion.py::test_no_unreadable_typography_in_any_original_browser_candidate | complete |
| AC-024 | 终态正常但入场穿字的用例被拒 | real_browser | passed | checks/test_html_engineering_completion.py::test_entry_arrow_crosses_text_even_when_final_frame_is_clear | complete |
| AC-025 | point 路由通过且关系身份不变 | real_browser | passed | checks/test_html_linked_layout.py::test_declared_point_routing_real_browser | complete |
| AC-026 | anchor 不参与附着点搜索 | real_browser | passed | checks/test_html_engineering_completion.py::test_anchor_and_implicit_endpoints_are_excluded_on_actual_browser_evidence | complete |
| AC-027 | 不把缺陷转移到第三个标签 | real_browser | passed | checks/test_html_linked_layout.py::test_declared_point_routing_real_browser | complete |
| AC-028 | 动态报告缺帧/超时/缺失均不能通过 | real_browser | passed | checks/test_html_engineering_completion.py::test_actual_frame_evidence_cannot_be_truncated_or_relabelled | complete |
| AC-029 | 容量阻断动态时保留 blocked_by_capacity，而非误报全动态已通过 | real_browser | passed | checks/test_html_engineering_completion.py::test_real_capacity_blocks_dynamic_instead_of_claiming_full_pass | complete |
| AC-030 | 首次生产轻度溢出经确定性修复继续 | integration_real_browser | passed | checks/test_html_engineering_completion.py::test_initial_production_overflow_uses_zero_model_deterministic_repair | complete |
| AC-031 | 变体切换造成的溢出也经同一路径修复 | integration_real_browser | passed | checks/test_html_engineering_completion.py::test_variant_overflow_uses_same_zero_model_deterministic_path | complete |
| AC-032 | 修复模型调用为 0，其他理解/审核调用分开统计 | integration_real_browser | passed | checks/test_html_engineering_completion.py::test_initial_production_overflow_uses_zero_model_deterministic_repair | complete |
| AC-033 | 无解不覆盖旧作者 | integration_real_browser | passed | checks/test_html_candidate_capacity_solver.py::test_search_budget_is_not_no_fit | complete |
| AC-034 | 旧策略行为回归通过 | integration_real_browser | passed | checks/test_html_optimization_acceptance.py::test_empty_or_skipped_test_suites_do_not_pass | complete |
| AC-035 | 保护、取消、过期各自保持原语义 | integration_real_browser | passed | checks/test_html_engineering_completion.py::test_manual_block_and_cancelled_search_preserve_document_and_evidence | complete |
| AC-036 | 出站没有 HTML 几何 | file_evaluation_and_model | pending | checks/test_html_independent_review.py::test_relation_identity_does_not_leak_html_endpoint_coordinates | supporting |
| AC-037 | 大幅位移仍按身份正确配对 | file_evaluation_and_model | pending | checks/test_html_independent_review.py::test_independent_boxes_pair_displaced_target_and_reuse_only_same_identity | supporting |
| AC-038 | 模糊定位不进入自动尺寸修复 | file_evaluation_and_model | pending | checks/test_html_independent_review.py::test_unresolved_locator_stops_without_fidelity_or_retry | supporting |
| AC-039 | hash 不一致停止 | file_evaluation_and_model | pending | checks/test_html_independent_review.py::test_reference_source_tamper_rejected | supporting |
| AC-040 | 容器/正文不互相冒充 | file_evaluation_and_model | pending | checks/test_html_independent_review.py::test_card_body_is_a_required_localization_part | supporting |
| AC-041 | 审计页显示真实局部对照与原始报告引用 | file_evaluation_and_model | pending | checks/test_html_reference_api.py::test_web_agent_read_submit_and_completed_reuse_do_not_save_author | supporting |
| AC-042 | 同一未改变区域不能仅因新模型说 pass 清除问题 | integration_and_paired_model | pending | checks/test_html_review_cache.py::test_exact_cache_stable_screenshot_corruption_and_input_invalidation | supporting |
| AC-043 | 注册变体事实与模型建议不符时阻断 | integration_and_paired_model | pending | checks/test_html_design_agent.py::test_existing_variant_review_suggestion_is_flagged_without_passing_or_retry | supporting |
| AC-044 | 文字内容错误不由局部几何工具修 | integration_and_paired_model | pending | checks/test_html_design_agent.py::test_svg_issue_cannot_route_code_to_bitmap_generation | supporting |
| AC-045 | 原图错字不覆盖准确文本 | integration_and_paired_model | pending | checks/test_html_independent_review.py::test_card_body_is_a_required_localization_part | supporting |
| AC-046 | 重点裁图不会增加未登记的图片预算 | integration_and_paired_model | pending | checks/test_html_design_agent.py::test_generated_and_reused_images_require_exact_authoritative_owner | supporting |
| AC-047 | 前后配对实验单独量测该任务收益 | integration_and_paired_model | pending | checks/test_html_paired_evaluation.py::test_pair_denominators_and_holdout_are_separate | supporting |
| AC-048 | 卡片图标不能替代必要插图 | integration_and_model | pending | checks/test_html_design_agent.py::test_existing_figure_icons_are_distinct_from_optional_decoration_palette | supporting |
| AC-049 | 多插图超能力在接受前给出明确诊断 | integration_and_model | pending | checks/test_html_design_feasibility.py::test_real_fonts_text_projection_reports_capacity | supporting |
| AC-050 | 相同资产复用不发生额外生成 | integration_and_model | pending | checks/test_html_asset_reuse.py::test_cross_page_exact_binding_reuses_without_generation_and_preserves_source | supporting |
| AC-051 | 修改资源 hash 使相关候选失效 | integration_and_model | pending | checks/test_html_review_cache.py::test_exact_cache_stable_screenshot_corruption_and_input_invalidation | supporting |
| AC-052 | 更换图像不能继承未经验证的语义锚点 | integration_and_model | pending | checks/test_html_asset_reuse.py::test_reuse_rejects_wrong_identity_or_geometry | supporting |
| AC-053 | UI 展示原因且不自动批准 | integration_and_model | pending | checks/test_html_reference_api.py::test_web_agent_read_submit_and_completed_reuse_do_not_save_author | supporting |
| AC-054 | 同一状态只检查一次且来源变化不命中旧通过 | integration_fault_injection | passed | checks/test_html_engineering_completion.py::test_actual_browser_cache_reuses_only_exact_inputs_and_intact_evidence | complete |
| AC-055 | unknown 不自动补发 | integration_fault_injection | passed | checks/test_html_reference_api.py::test_unknown_reference_never_retries_or_changes_model_to_resubmit | complete |
| AC-056 | usage/cost 缺失为 null | integration_fault_injection | passed | checks/test_html_execution_metrics.py::test_legacy_and_unfinished_requests_do_not_invent_calls_time_or_cost | complete |
| AC-057 | 子阶段不能绕过总调用预算 | integration_fault_injection | passed | checks/test_html_page_budget.py::test_nested_stages_share_budget_and_never_retry | complete |
| AC-058 | 用户取消后不开始下一阶段 | integration_fault_injection | passed | checks/test_html_reference_api.py::test_cancelled_reference_never_starts_provider | complete |
| AC-059 | 恢复任务不重复保存或批准 | integration_fault_injection | passed | checks/test_html_reference_api.py::test_known_completed_receipt_recovers_database_without_provider_retry | complete |
| AC-060 | 同输入配对身份一致 | real_model_and_human_review | pending | checks/test_html_paired_evaluation.py::test_pair_denominators_and_holdout_are_separate | supporting |
| AC-061 | 所有失败进入分母 | real_model_and_human_review | pending | checks/test_html_paired_evaluation.py::test_failed_and_unknown_are_in_denominator_and_unknown_cost_is_null | supporting |
| AC-062 | 每个达标数字能追到页面、调用和报告 | real_model_and_human_review | pending | checks/test_html_paired_evaluation.py::test_tampered_source_or_gold_or_response_rejected | supporting |
| AC-063 | 上述门槛逐项 passed/failed/pending，不能只给总评分 | real_model_and_human_review | pending | checks/test_html_paired_evaluation.py::test_external_pass_claims_cannot_create_human_or_model_acceptance | supporting |
| AC-064 | 策略可回退且不重写已有作者 | release_and_real_end_to_end | pending | checks/test_html_build_snapshot.py::test_real_snapshot_render_stays_identical_after_asset_change | supporting |
| AC-065 | 保存重开和历史恢复通过 | release_and_real_end_to_end | pending | checks/test_html_reference_api.py::test_known_completed_receipt_recovers_database_without_provider_retry | supporting |
| AC-066 | Agent/Web 合同一致 | release_and_real_end_to_end | pending | checks/test_html_reference_api.py::test_web_agent_read_submit_and_completed_reuse_do_not_save_author | supporting |
| AC-067 | 相关快照与失效规则生效 | release_and_real_end_to_end | pending | checks/test_html_build_snapshot.py::test_old_qa_cannot_validate_new_scene | supporting |
| AC-068 | 原音视频链路实际验证 | release_and_real_end_to_end | pending | checks/test_html_build_snapshot.py::test_formal_video_requires_actual_approvals | supporting |
| AC-069 | 发布结论有具体 commit、命令、日志、未决项 | release_and_real_end_to_end | pending | checks/test_html_acceptance_criteria.py::test_missing_stale_skipped_evidence_never_passes | supporting |

所有必需facet和选择器以config/html_acceptance_criteria.json为准；本表只展示首个。新增矩阵测试共享真实浏览器夹具，禁止用单个文件名或测试总数签发通过；全部精确检查及来源须由统一验收包封存。剩余33项不满足时--require-all必须失败。
