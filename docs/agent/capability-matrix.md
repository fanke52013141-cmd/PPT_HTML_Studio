# Agent Capability Matrix

- **Agent API Version**: 1.46.0
- **Contract Hash**: `ef3725b89f849d28`
- **Total Capabilities**: 65

This document is auto-generated from `agent_contract/capabilities.py`.
Do not edit manually — run `python scripts/generate_agent_contracts.py`.

## Capability Table

| Capability ID | Version | Status | Method | Agent API Path | MCP Tool | MCP enabled | CLI Command | Service Ref | Long-running | Destructive |
|---|---|---|---|---|---|---|---|---|---|---|
| `html_sheet.list` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/html-asset-sheets` | `ppt_html_sheet_list` | Yes | `html sheet-list` | `html_asset_sheet_routes.sheet_list` | No | No |
| `html_sheet.generate` | 1.0 | stable | POST | `/api/agent/v1/projects/{project_id}/html-asset-sheets/generate` | `ppt_html_sheet_generate` | Yes | `html sheet-generate` | `html_asset_sheet_routes.sheet_generate` | Yes | No |
| `html_sheet.read` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/html-asset-sheets/{sheet_id}/{request_key}` | `ppt_html_sheet_read` | Yes | `html sheet-read` | `html_asset_sheet_routes.sheet_read` | No | No |
| `html_sheet.review` | 1.0 | stable | PUT | `/api/agent/v1/projects/{project_id}/html-asset-sheets/{sheet_id}/{request_key}/{asset_id}/review` | `ppt_html_sheet_review` | Yes | `html sheet-review` | `html_asset_sheet_routes.sheet_review` | No | No |
| `html_sheet.accept` | 1.0 | stable | POST | `/api/agent/v1/projects/{project_id}/html-asset-sheets/{sheet_id}/{request_key}/{asset_id}/accept` | `ppt_html_sheet_accept` | Yes | `html sheet-accept` | `html_asset_sheet_routes.sheet_accept` | No | No |
| `html_sheet.assess` | 1.0 | stable | POST | `/api/agent/v1/projects/{project_id}/html-asset-sheets/{sheet_id}/{request_key}/assess` | `ppt_html_sheet_assess` | Yes | `html sheet-assess` | `html_asset_sheet_routes.sheet_assess` | Yes | No |
| `html_sheet.retry` | 1.0 | stable | POST | `/api/agent/v1/projects/{project_id}/html-asset-sheets/{sheet_id}/{request_key}/{asset_id}/retry` | `ppt_html_sheet_retry` | Yes | `html sheet-retry` | `html_asset_sheet_routes.sheet_retry` | Yes | No |
| `html_semantic.submit` | 1.0 | stable | POST | `/api/agent/v1/projects/{project_id}/html-review/{slide_id}/semantic/submit` | `ppt_html_semantic_submit` | Yes | `html semantic-submit` | `html_semantic_review_service.review` | No | No |
| `html_semantic.status` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/html-review/{slide_id}/semantic/status` | `ppt_html_semantic_status` | Yes | `html semantic-status` | `html_semantic_review_service.status` | No | No |
| `html_semantic.decision` | 1.0 | stable | POST | `/api/agent/v1/projects/{project_id}/html-review/{slide_id}/semantic/decision` | `ppt_html_semantic_decision` | Yes | `html semantic-decision` | `html_semantic_review_service.decide` | No | No |
| `project_model_binding.read` | 1.2 | stable | GET | `/api/agent/v1/projects/{project_id}/model-binding` | `ppt_project_model_binding_read` | Yes | `html model-read` | `project_model_binding_service.get_project_model_binding` | No | No |
| `project_model_binding.write` | 1.1 | stable | PUT | `/api/agent/v1/projects/{project_id}/model-binding` | `ppt_project_model_binding_write` | Yes | `html model-write` | `project_model_binding_service.save_project_model_binding` | No | No |
| `html_repair.preview` | 1.5 | stable | POST | `/api/agent/v1/projects/{project_id}/html-visual/{slide_id}/repair/preview` | `ppt_html_repair_preview` | Yes | `html repair-preview` | `html_scene_repair.preview_repair` | No | No |
| `html_repair.save` | 1.5 | stable | POST | `/api/agent/v1/projects/{project_id}/html-visual/{slide_id}/repair/save` | `ppt_html_repair_save` | Yes | `html repair-save` | `html_scene_repair.save_repair` | No | No |
| `html_repair.evidence` | 1.1 | stable | POST | `/api/agent/v1/projects/{project_id}/html-visual/{slide_id}/repair/evidence` | `ppt_html_repair_evidence` | Yes | `html repair-evidence` | `html_scene_repair.evidence` | No | No |
| `html_repair.generate` | 1.3 | stable | POST | `/api/agent/v1/projects/{project_id}/html-visual/{slide_id}/repair/generate` | `ppt_html_repair_generate` | Yes | `html repair-generate` | `html_scene_repair.generate_repair` | No | No |
| `html_editor.read` | 1.1 | stable | GET | `/api/agent/v1/projects/{project_id}/html-visual/{slide_id}/editor` | `ppt_html_editor_read` | Yes | `html editor-read` | `html_scene_editing.load_editor` | No | No |
| `html_editor.write` | 1.1 | stable | PUT | `/api/agent/v1/projects/{project_id}/html-visual/{slide_id}/editor` | `ppt_html_editor_write` | Yes | `html editor-write` | `html_scene_editing.save_editor` | No | No |
| `html_editor.preview` | 1.3 | stable | POST | `/api/agent/v1/projects/{project_id}/html-visual/{slide_id}/editor/preview` | `ppt_html_editor_preview` | Yes | `html editor-preview` | `html_scene_editing.preview_editor` | No | No |
| `generation.status` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/generation/{stage}/status` | `ppt_generation_status` | Yes | `generation status` | `generation_control.status` | No | No |
| `generation.stop` | 1.0 | stable | POST | `/api/agent/v1/projects/{project_id}/generation/{stage}/stop` | `ppt_generation_stop` | Yes | `generation stop` | `generation_control.request_stop` | No | No |
| `identity.get` | 1.0 | stable | GET | `/api/agent/v1/identity` | `ppt_identity_get` | Yes | `identity` | `agent_api.auth / account_service` | No | No |
| `project.create` | 1.6 | stable | POST | `/api/agent/v1/projects` | `ppt_project_create` | Yes | `project create` | `project_service.ProjectService.create` | No | No |
| `html_review.produce` | 1.9 | stable | POST | `/api/agent/v1/projects/{project_id}/html-review/{slide_id}/produce` | `ppt_html_produce` | Yes | `html produce` | `html_workflow_jobs.HtmlWorkflowJobs` | Yes | No |
| `html_review.design_current` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/html-review/{slide_id}/design/current` | `ppt_html_design_current` | Yes | `html design-current` | `html_design_candidates.current_design` | No | No |
| `html_review.manual_candidate` | 1.1 | stable | GET | `/api/agent/v1/projects/{project_id}/html-review/{slide_id}/manual-candidate/{job_id}` | `ppt_html_manual_candidate` | Yes | `html manual-candidate` | `html_manual_candidate_review.inspect_candidate` | No | No |
| `html_review.manual_candidate_decision` | 1.1 | stable | POST | `/api/agent/v1/projects/{project_id}/html-review/{slide_id}/manual-candidate/{job_id}/decision` | `ppt_html_manual_candidate_decision` | Yes | `html manual-candidate-decision` | `html_manual_candidate_review.decide_candidate` | No | No |
| `html_review.task_status` | 1.4 | stable | GET | `/api/agent/v1/projects/{project_id}/html-review/tasks/{job_id}` | `ppt_html_task_status` | Yes | `html task-status` | `html_workflow_jobs.HtmlWorkflowJobs` | No | No |
| `html_review.task_current` | 1.3 | stable | GET | `/api/agent/v1/projects/{project_id}/html-review/{slide_id}/task/current` | `ppt_html_task_current` | Yes | `html task-current` | `html_task_store.current_slide_task` | No | No |
| `html_review.task_resume` | 1.0 | stable | POST | `/api/agent/v1/projects/{project_id}/html-review/tasks/{job_id}/resume` | `ppt_html_task_resume` | Yes | `html task-resume` | `html_workflow_jobs.HtmlWorkflowJobs.resume` | No | No |
| `html_review.task_cancel` | 1.0 | stable | POST | `/api/agent/v1/projects/{project_id}/html-review/tasks/{job_id}/cancel` | `ppt_html_task_cancel` | Yes | `html task-cancel` | `html_workflow_jobs.HtmlWorkflowJobs` | No | No |
| `html_visual.status` | 1.1 | stable | GET | `/api/agent/v1/projects/{project_id}/html-visual/status` | `ppt_html_visual_status` | Yes | `html status` | `html_creation_workflow.project_status` | No | No |
| `html_visual.scene_read` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/html-visual/{slide_id}` | `ppt_html_scene_read` | Yes | `html scene-read` | `html_visual_store.load_scene_with_revision` | No | No |
| `html_visual.scene_write` | 1.0 | stable | PUT | `/api/agent/v1/projects/{project_id}/html-visual/{slide_id}` | `ppt_html_scene_write` | Yes | `html scene-write` | `html_visual_store.save_scene` | No | No |
| `html_review.plan_generate` | 1.2 | stable | POST | `/api/agent/v1/projects/{project_id}/html-review/{slide_id}/plan/generate` | `ppt_html_plan_generate` | Yes | `html plan-generate` | `html_visual_review_service.generate_scene_plan` | No | No |
| `html_review.review` | 1.0 | stable | POST | `/api/agent/v1/projects/{project_id}/html-review/{slide_id}/review` | `ppt_html_review` | Yes | `html review` | `html_visual_review_service.review_scene` | No | No |
| `html_review.approve` | 1.0 | stable | POST | `/api/agent/v1/projects/{project_id}/html-review/{slide_id}/approve` | `ppt_html_approve` | Yes | `html approve` | `html_visual_review_service.approve_scene` | No | No |
| `html_review.approval_status` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/html-review/{slide_id}/approval` | `ppt_html_approval_status` | Yes | `html approval-status` | `html_visual_review_service.approval_status` | No | No |
| `project.list` | 1.4 | stable | GET | `/api/agent/v1/projects` | `ppt_project_list` | Yes | `project list` | `project_service.ProjectService.list` | No | No |
| `project.get` | 1.3 | stable | GET | `/api/agent/v1/projects/{project_id}` | `ppt_project_get` | Yes | `project show` | `project_service.ProjectService.get` | No | No |
| `project.update` | 1.3 | stable | PATCH | `/api/agent/v1/projects/{project_id}` | `ppt_project_update` | Yes | `project update` | `project_service.ProjectService.update` | No | No |
| `source.set` | 1.1 | stable | POST | `/api/agent/v1/projects/{project_id}/source` | `ppt_source_set` | Yes | `source set` | `article_service.import_article / generate_article_from_topic` | No | No |
| `pipeline.run` | 1.5 | stable | POST | `/api/agent/v1/projects/{project_id}/runs` | `ppt_pipeline_run` | Yes | `run start` | `one_click_orchestrator.start_one_click` | Yes | No |
| `pipeline.status` | 1.4 | stable | GET | `/api/agent/v1/projects/{project_id}/runs/latest` | `ppt_pipeline_status` | Yes | `run status` | `one_click_orchestrator.get_one_click_status` | No | No |
| `pipeline.resume` | 1.5 | stable | POST | `/api/agent/v1/projects/{project_id}/runs/latest/resume` | `ppt_pipeline_resume` | Yes | `run resume` | `one_click_orchestrator.start_one_click` | Yes | No |
| `pipeline.stream` | 1.1 | stable | GET | `/api/agent/v1/projects/{project_id}/runs/latest/stream` | `ppt_pipeline_stream` | No | `run stream` | `agent_api.routes.agent_pipeline_stream` | Yes | No |
| `checkpoint.approve` | 1.1 | stable | POST | `/api/agent/v1/projects/{project_id}/checkpoints/{checkpoint}/approve` | `ppt_checkpoint_approve` | Yes | `approve` | `one_click_orchestrator (stage gating)` | No | No |
| `stage.get` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/stages/{stage}` | `ppt_stage_get` | Yes | `stage get` | `various service read functions` | No | No |
| `image.regenerate` | 1.1 | stable | POST | `/api/agent/v1/projects/{project_id}/images/{slide_id}/regenerate` | `ppt_image_regenerate` | Yes | `image regenerate` | `image_workflow_service.generate_slide_image` | Yes | No |
| `narration.update` | 1.1 | stable | PATCH | `/api/agent/v1/projects/{project_id}/narration/{slide_id}` | `ppt_narration_update` | Yes | `narration update` | `storyboard_service.update_narration` | No | No |
| `tts.synthesize` | 1.1 | stable | POST | `/api/agent/v1/projects/{project_id}/tts` | `ppt_tts_synthesize` | Yes | `tts synthesize` | `tts_service.start_synthesis` | Yes | No |
| `video.render` | 1.1 | stable | POST | `/api/agent/v1/projects/{project_id}/videos/render` | `ppt_video_render` | Yes | `video render` | `video_render_service.start_render` | Yes | No |
| `artifacts.list` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/artifacts` | `ppt_artifacts_list` | Yes | `artifacts list` | `database.ArtifactRecord` | No | No |
| `artifact.get` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/artifacts/{artifact_id}` | `ppt_artifact_get` | Yes | `artifact get` | `database.ArtifactRecord` | No | No |
| `diagnostics` | 1.0 | stable | GET | `/api/agent/v1/diagnostics` | `ppt_diagnostics` | Yes | `diagnostics` | `agent_api.routes.get_diagnostics` | No | No |
| `digital_human.config.get` | 1.1 | stable | GET | `/api/agent/v1/projects/{project_id}/digital-human/config` | `ppt_digital_human_config_get` | Yes | `digital-human config` | `digital_human_routes.router` | No | No |
| `digital_human.config.update` | 1.1 | stable | PATCH | `/api/agent/v1/projects/{project_id}/digital-human/config` | `ppt_digital_human_config_update` | Yes | `digital-human config --set` | `digital_human_routes.router` | No | No |
| `digital_human.health` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/digital-human/health` | `ppt_digital_human_health` | Yes | `digital-human health` | `digital_human_client.get_digital_human_client` | No | No |
| `digital_human.generate` | 1.0 | stable | POST | `/api/agent/v1/projects/{project_id}/digital-human/generate-full` | `ppt_digital_human_generate` | Yes | `digital-human generate` | `digital_human_client.get_digital_human_client` | No | No |
| `project.delete` | 1.0 | stable | DELETE | `/api/agent/v1/projects/{project_id}` | `ppt_project_delete` | Yes | `project delete` | `project_service.ProjectService.delete` | No | Yes |
| `checkpoint.list` | 1.1 | stable | GET | `/api/agent/v1/projects/{project_id}/checkpoints` | `ppt_checkpoint_list` | Yes | `checkpoint list` | `agent_api.routes.agent_list_checkpoints` | No | No |
| `image.get` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/slides/{slide_id}/image` | `ppt_image_get` | No | `image get` | `image_workflow_service.get_slide_image_file` | No | No |
| `audio.get` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/slides/{slide_id}/audio` | `ppt_audio_get` | No | `audio get` | `tts_service.get_slide_audio_file` | No | No |
| `video.latest` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/videos/latest` | `ppt_video_latest` | No | `video latest` | `video_render_service final_video_download` | No | No |
| `artifact.download` | 1.0 | stable | GET | `/api/agent/v1/projects/{project_id}/artifacts/{artifact_id}/content` | `ppt_artifact_download` | No | `artifact download` | `agent_api.routes.agent_download_artifact` | No | No |

## Pipeline Checkpoints

| Checkpoint | Label | Internal Stage | Description |
|---|---|---|---|
| `storyboard_review` | 分镜审查 | `storyboard` | 分镜规划完成，等待确认后再生成图片 |
| `image_review` | 图片审查 | `confirm_images` | 图片生成完成，等待确认后再进行 Mask 标注 |
| `mask_review` | Mask 审查 | `ai_mask` | Mask 标注完成，等待确认后再生成旁白 |
| `narration_review` | 旁白审查 | `narration` | 旁白生成完成，等待确认后再合成音频 |
| `audio_review` | 音频审查 | `tts` | 音频合成完成，等待确认后再渲染视频 |
| `video_review` | 视频审查 | `render` | 视频渲染完成，等待最终确认 |

## MCP Tool Summary

The MCP server exposes **60** stable tools:

- `ppt_html_sheet_list` — List account-scoped HTML sheet candidates and latest persisted task for recovery.
- `ppt_html_sheet_generate` — Submit a bounded HTML sheet task; freeze image model at submission, keep credentials only in memory. Mask requires configured exact segmentation. Query/stop using HTML task APIs.
- `ppt_html_sheet_read` — Verify source/spec/mask/output hashes and read per-object reviews, revision and acceptance. No automatic identity approval.
- `ppt_html_sheet_review` — Record manual identity and edge decisions with expected_revision. Conflict 409, accepted objects locked; no resources published.
- `ppt_html_sheet_accept` — Accept one verified object only after both review gates; additive resources registration, no same-ID overwrite or scene/audio changes.
- `ppt_html_sheet_assess` — Submit multimodal advisory task on verified candidates with frozen text model. Empty body; advice never approves resources. Use existing task query/cancel.
- `ppt_html_sheet_retry` — Regenerate only one unaccepted declared object into an independent candidate. Expected revision, optional corrected need/direction; original assets and human edits preserved.
- `ppt_html_semantic_submit` — Submit persistent independent audio-bound beat/frame semantic QA with frozen multimodal model and expected_revision; no human/audio approval. Unknown requests never blindly repeat.
- `ppt_html_semantic_status` — Read current per-beat semantic evidence and separate engineering/audio/human states; verify original source and frame hashes, stale evidence cannot pass.
- `ppt_html_semantic_decision` — Record an explicit human semantic approval/rejection of the current report key with revision and note. Engineering failures and semantic omissions/contradictions cannot be approved.
- `ppt_project_model_binding_read` — Read account-scoped HTML project model references and redacted effective summaries; legacy/inherit/fixed modes, no credentials or endpoints.
- `ppt_project_model_binding_write` — Save HTML project visual text/image and optional independent planning model references (omitted planning preserves its binding) with expected_revision and explicit rebind. No-op preserves work; changes apply to future generation only. Stale revision returns 409.
- `ppt_html_repair_preview` — Bounded HTML local repair preview; shared leaf-field manual protection with conflict paths, registered instance styles/actions, frozen revision, sampled or output-frame temporal checks with registered overlap policy and stagnation stops. Does not approve aesthetics.
- `ppt_html_repair_save` — Bounded HTML local repair save; shared leaf-field manual protection enforced again at final AI persistence with conflict paths, registered styles/actions, frozen revision and temporal checks. Does not approve aesthetics.
- `ppt_html_repair_evidence` — Bounded HTML local repair evidence; registered instance styles and actions, frozen revision, protected manual fields, actual sampled or output-frame temporal checks with registered overlap policy and stagnation stops. Does not approve aesthetics.
- `ppt_html_repair_generate` — Bounded HTML local repair with scope-specific protected leaf and ancestor paths in model context; retain precise capacity triggers, original budgets, frozen revision, shared candidate/save protection and sampled/output-frame checks. Conflicting protected goals stop without overwriting; no automatic aesthetic approval.
- `ppt_html_editor_read` — Read stored HTML author scene, motion binding, capabilities, validated resources, manual overrides and audio artifact revision under the project lock.
- `ppt_html_editor_write` — Save validated HTML edits and source-image normalized anchors with manual protection. Reject stale scene revision or optional expected_audio_revision with 409; preserve audio artifacts.
- `ppt_html_editor_preview` — Validate draft and resolve read-only beat timing, effective durations and clipping reasons or author clock. Return audio artifact revision; reject stale scene or optional audio revision with 409. No save, TTS or approval; output gates remain.
- `ppt_generation_status` — Read the active cooperative generation control for a project stage. Controls are process-local; durable TTS/video results remain in their job APIs.
- `ppt_generation_stop` — Request a safe-boundary stop for the exact active operation ID. In-flight provider requests and render stages finish before stopping.
- `ppt_identity_get` — Return the creative account and scopes associated with this Agent connection.
- `ppt_project_create` — Create a project with canvas, production/presentation mode, versioned creation configuration, and optional course/chapter ownership.
- `ppt_html_produce` — Bounded stagnation checks retain precise capacity triggers and effective limits, including saved report details, without increasing repair budgets. Generate a design first. Explicit reuse_design_candidate_key revalidates unchanged original image/plan into a new unapproved review checkpoint without provider calls; never accepts stale keys or carries approvals. Source design_candidate_key plus design_instruction revises that design with its original image and plan, without replanning or acceptance; key alone continues reconstruction. Production authority and registered tools determine intervention routes, including design_review; explicit stage timeouts are preserved and measured. Independent fidelity review and human approval remain separate.
- `ppt_html_design_current` — Read the current immutable design checkpoint, image URL and stale status; never approves a design or HTML scene.
- `ppt_html_manual_candidate` — Read one current unsaved candidate after a failed or interrupted unqueryable JSON outcome, including unresolved intent; bounded repair replay, original task, design and engineering facts stay distinct from approval. Never retries or saves author content.
- `ppt_html_manual_candidate_decision` — Record an explicit human accept/reject with evidence note for the exact unsaved candidate. Does not save author scene, retry provider, or grant visual approval.
- `ppt_html_task_status` — Read persisted HTML task, page, stage, repair/Skill progress, reuse, input freshness and recovery advice; includes measured adapter calls, reuse, partial timing, actual read/total timeouts, last-chunk/silence and sanitized stream failure verification routes; success is not visual approval.
- `ppt_html_task_current` — Read the latest persisted production task for this page, independently of the project history limit; validates frozen input freshness. Includes adapter measurements, actual read/total timeouts, last-chunk/silence and sanitized stream failure verification routes. Returns null when absent.
- `ppt_html_task_resume` — Explicitly continue the original frozen production request. Unknown outcomes, cancellation, changed inputs and exhausted budgets remain blocked; active submissions reuse the same task.
- `ppt_html_task_cancel` — HTML production workflow: task_cancel; persisted task and registered render gates.
- `ppt_html_visual_status` — Read shared Web/Agent HTML workflow stages, current visual approval readiness, and PPTX/video-specific gates.
- `ppt_html_scene_read` — Read one slide's stored html scene document with its revision and content hash.
- `ppt_html_scene_write` — Write one slide's html scene document with expected-revision optimistic concurrency (409 on conflict); html-backend projects only.
- `ppt_html_plan_generate` — Generate a constrained scene plan through the configured LLM, including registered code-owned illustration labels and relations; record AC06/AC07 evidence. No automatic acceptance or author save.
- `ppt_html_review` — Compile, measure, and screenshot one html scene through the shared bundle; returns object-level diagnostics.
- `ppt_html_approve` — Approve one html scene; the record binds scene/theme/template/layout/asset/runtime hashes and fails on any static-review error.
- `ppt_html_approval_status` — Read the current approval validity and invalidation reason for one slide.
- `ppt_project_list` — List all projects with optional status filter.
- `ppt_project_get` — Get project details including article/contract status, slide IDs, and mask mode.
- `ppt_project_update` — Update project name, description, AI mode, production mode, or presentation mode.
- `ppt_source_set` — Set project source content — either direct article text or a topic for AI generation.
- `ppt_pipeline_run` — Content-review candidates persist separately; explicit current review_id correction resumes the same course without regenerating the script. Source-to-script scoped-negation risks stop before saving or downstream generation; no automatic retry. Start or resume the automated pipeline. HTML courses coordinate persistent original stage jobs and require existing per-page approvals; HTML restart/start_from bypass is refused; explicit child cancellation pauses, manual storyboard contention waits for user verification.
- `ppt_pipeline_status` — Includes script_review waiting checkpoint; current corrected script is distinct from the retained problem candidate. Get current pipeline status, stage progress, blocking errors and HTML course child task IDs/current versus historical state.
- `ppt_pipeline_resume` — Content-review candidates persist separately; explicit current review_id correction resumes the same course without regenerating the script. Source-to-script scoped-negation risks stop before saving or downstream generation; no automatic retry. Resume the original pipeline; HTML cancelled/busy storyboard requires verified current completion, cancelled children are never revived or replaced, unknown submissions remain blocked.
- `ppt_checkpoint_approve` — Approve or reject an image pipeline checkpoint. HTML courses require original per-page design, visual, audio and semantic decisions; generic approval is refused.
- `ppt_stage_get` — Get detailed data for a specific pipeline stage (storyboard, narration, etc.).
- `ppt_image_regenerate` — Regenerate a single slide image with optional modification instruction.
- `ppt_narration_update` — Update narration text for a specific slide.
- `ppt_tts_synthesize` — Start TTS audio synthesis for specified or all slides.
- `ppt_video_render` — Start video rendering for the project.
- `ppt_artifacts_list` — List all artifacts (images, audio, video, pptx) for a project.
- `ppt_artifact_get` — Get details and download URL for a specific artifact.
- `ppt_diagnostics` — Get system diagnostics including API version, capabilities, and health checks.
- `ppt_digital_human_config_get` — Get digital-human configuration for a project.
- `ppt_digital_human_config_update` — Update digital-human configuration for a project.
- `ppt_digital_human_health` — Check digital-human service availability and model readiness.
- `ppt_digital_human_generate` — Trigger full digital-human video generation for all slides.
- `ppt_project_delete` — Delete a project and all of its derived artifacts. Destructive and irreversible.
- `ppt_checkpoint_list` — List project checkpoints; HTML lists original stage approval capabilities or Web audio confirmation path.

## Resource URIs

MCP resources use the following URI scheme:

```
ppt://projects/{project_id}/summary
ppt://projects/{project_id}/slides
ppt://projects/{project_id}/slides/{slide_id}/image
ppt://projects/{project_id}/slides/{slide_id}/audio
ppt://projects/{project_id}/videos/latest
ppt://projects/{project_id}/runs/{run_id}/logs
```
