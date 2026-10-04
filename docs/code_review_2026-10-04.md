# 代码审查报告 · 2026-10-04

**范围**:`D:\Program Files (x86)\PPT_presentation_video`
**规模**:152 个 Python 文件(57,833 行)+ 36 个前端 JS(约 1.5 万行)+ 18,608 行 CSS
**基线**:`a7f991d`,另有 12 个文件未提交改动
**方法**:AST 全量解析 + 跨目录引用验证(`static/` `templates/` `scripts/` `checks/` `docs/` `cli/` `mcp_server/` `agent_api/`)+ 关键结论运行时实测复验

---

## 摘要

| 级别 | 数量 | 说明 |
|---|---|---|
| 🔴 Blocker | **7** | 功能实际不可用 / 数据写错项目 / 安全边界缺口 |
| 🟡 Suggestion | **11** | 矛盾实现、重复代码、契约失效 |
| 💭 Nit | 若干 | 死常量、重复工具函数、孤儿 CSS |
| 可安全删除 | **约 260 处** | 已逐项验证零引用 |

**总体判断**:架构骨架是健康的 —— 4,705 个 Python 文件全部通过语法解析,`ruff check --select F401,F841,F821,E722` 零告警,`static/app.js` 单体已退役,模块边界基本清晰。问题集中在**四处收敛没做完**:前端 transport 收口失败、子进程治理收口失败、测试门禁与实现脱节、文档与代码脱节。

---

## 🔴 Blocker(建议优先修复)

### B1 · 前端 15 分钟超时被静默丢弃 → 数字人长任务必然超时
`static/digital_human_panel.js:611` 与 `:765`
```js
var res = await API.post(base() + "/export-audio", { gap_sec: 0.6 }, { timeout: 900000 });
```
`api_client.js:13` 只读 `options.timeoutMs`:
```js
options.timeoutMs || this.REQUEST_TIMEOUT_MS   // 120000
```
`timeout` 展开进 `fetch()` 成为未知属性被忽略,**实际仍是 120 秒**。Wan2.2 合成整段语音必然超过 120s。

**已实测确认**参数名不匹配。修复:`{ timeout: 900000 }` → `{ timeoutMs: 900000 }`(两处)。

---

### B2 · sessionStorage 兜底导致跨项目写错背景设置
`static/storyboard_background_extension.js:38-42`
```js
const current = window.state?.currentProject?.id || window.PPTStudio?.getCurrentProject?.()?.id;
if (current) sessionStorage.setItem(..., String(current));
return current || sessionStorage.getItem(...) || '';
```
两条路径**恒为 undefined**:`workflow_state.js:96` 是 `const state`(非 `window.state`),`window.PPTStudio` 只暴露 `.runtime`(无 `getCurrentProject`)。

**后果**:`saveBackground()` 用它执行 3 次写操作(上传 + 2 次 PUT)。用户退出项目 A 进入项目 B 后保存背景,**实际写进项目 A**。

---

### B3 · ffmpeg 渲染超时杀不掉进程树
`video_artifact_service.py:568-578`
```python
except subprocess.TimeoutExpired as exc:
    kill_process_tree(getattr(exc, "process", None))
```
**已实测**`subprocess.TimeoutExpired` 无 `.process` 属性(实际属性:`args / cmd / output / stderr / stdout / timeout`),`getattr` 恒为 `None`,`kill_process_tree` 第一行立即 return。

**后果**:`subprocess.run` 超时只终止直接子进程,ffmpeg 继续占 CPU 与磁盘句柄。渲染超时上限 `STEP8_RENDER_TIMEOUT_SEC=3600`,即卡死任务最长持续 **1 小时**。

项目已有 `runtime_support.run_subprocess_killable`(专为此问题而写)却未使用。同型遗漏还有 `narration_service.py:158`、`image_workflow_service.py:2234`。

---

### B4 · 数字人合成接口接受任意文件路径(路径穿越)
`digital_human_routes.py:824-834`
```python
base_video = str(body.get("base_video") or "").strip() or None
output = str(body.get("output") or "").strip()
if not output:
    output = str(_digi_dir(project) / f"composite_{slide_id}.mp4")
result = client.composite(..., base_video=base_video, output=output, ...)
```
**已实测确认**:`slide_id` 有 `_assert_safe_slide_id` 保护(第 261 行),但 `output` 与 `base_video` 完全无约束,直接进 ffmpeg `-i` 与输出路径。

**后果**:认证用户可让服务端在**任意可写位置**创建/覆盖 `.mp4`,并读取任意本地文件作为输入。

---

### B5 · AI Mask 完成态假阳性
`ai_mask_manifest_apply.py:346-410` → `ai_mask_engine.py:798`
```python
for collection in (groups, semantic):
    ...
    if 已人工接管: continue      # 两轮都跳过
updated += 1                      # 在循环之外,仍 +1
```
```python
complete = total_updated > 0 and len(slides_out) > 0
→ quality_status="passed" → annotation_status="completed"
```
**后果**:一个被人工完全接管、实际什么都没改的页面,被上报为"AI Mask 标注完成且质量通过"。这会让 UI 与下游 advance 逻辑以为可以继续推进 —— 最坏的一类假阳性。

---

### B6 · TTS 暂存目录异常路径永久泄漏
`tts_service.py:883` 创建,`1180` 清理,**不在 `finally` 中**:
```python
stage_dir = Path(tempfile.mkdtemp(prefix="tts-stage-", dir=Path(final_paths["audio"]).parent))
...
for job in pending_jobs:
    shutil.rmtree(job["stage_dir"], ignore_errors=True)   # 非 finally
```
**实证**:仓库根目录已存在泄漏实例 `tts-stage-7zmwa62_/`(空目录,2026-09-28),且 `git check-ignore` 确认**未被忽略** —— 一旦残留文件就会被误提交。

修复:`mkdtemp(dir=None)` 交系统 temp + `try/finally` 包裹 + `.gitignore` 补 `tts-stage-*/`。

---

### B7 · Prompt 字面守卫过期,4/5 条必然失败
`checks/test_narration_mask_and_workflow_ui.py:258-266` 对 `templates/prompts/step2_visual_system.md` 做 5 条**字面子串**断言,实测 4 条已随 v8 重构失效(如断言 `一个片段只绑定一个元素`,实际为 `每个元素恰好绑定一段…每段原文只出现一次`)。

**这类字面断言最误导** —— 它会诱导后续开发把新文案改回旧措辞,而不是承认契约已变。应改为断言语义标记(如 `ContractVersion` == `step2_visual_v8_mapping_only`)。

---

## 🟡 Suggestion(矛盾与重复)

### S1 · ComfyUI 工作流预检与实际解析的候选集不一致 → 一键流水线可被单个文件卡死
| 位置 | 查找的候选 |
|---|---|
| `one_click_orchestrator.py:849` 预检 | 仅 `data/digital_human/comfyui_tts_workflow.json` |
| `tts_service.py:606`、`generic_tts.py:578` 实际 | 两个候选(含 `config/indextts2_5_comfyui_workflow.json`) |

**已确认这两个 JSON 内容 100% 相同(md5 一致,`diff` 无输出)**。当 `data/` 那份缺失而 `config/` 那份存在时,一键流水线在预检阶段误报"工作流不存在"并**拒绝启动**,但单独跑 TTS 却能成功。

修复:抽 `resolve_comfyui_tts_workflow_path()` 单一函数三处共用;并二选一保留(建议留 `config/`,删 `data/`)。

### S2 · `start_render` 返回状态与内存真实状态矛盾
`video_render_service.py:304` 写入 `"status":"queued"`,`:349` 却返回 `"status":"rendering"`。前端首屏读返回值、后续读轮询值,**同一任务前后显示不同状态**。同文件 `_active_task_response:1121` 已正确区分,应对齐。

### S3 · `doclayout_enabled` 默认值在同文件两处相反
`ai_mask_engine.py:64` `DEFAULT_SETTINGS: True` vs `:449` `normalize_settings` fallback `False`。因第 414 行先做了 merge,fallback 永不可达,实际行为是开启。但两处写着相反的值,任何人删掉那行 merge 行为就会静默翻转。让 `DEFAULT_SETTINGS` 成为唯一真相源。

### S4 · AI 建议条目的输入版本证据永久缺失
`annotation_planner.py:313` 构造 `AnnotationInputs(image_hash=None, ...)`;而 `plan_slide` 签名(`:63-64`)**接收了** `image_hash`/`narration_hash` 两参,函数体内一次没用。
配套 `annotation_jobs.py:37-38` 的 `replace(item.inputs, image_hash=item.inputs.image_hash)` 是 **no-op**(用自己覆盖自己,已实测)。
后果:`scripts/build_remotion_props.py:566` 的过期检查因 `inputs.get()` 为 None 短路,**这些条目永远绕过 stale 检测**。

### S5 · 模块文档承诺的重启恢复能力实际不存在
`annotation_job_store.py:193` `interrupt_orphaned` docstring 承诺"把上一进程遗留的 queued/running 任务标 interrupted",**生产代码零调用方**。进程重启后 `annotation_detect`/`annotation_plan` 任务永远停在 `running`,`cancel()` 也救不回来。同文件 `:143` `latest_active` 同样零引用。

### S6 · 强调等级枚举字面量出现 4 次,无单一来源
`annotation_contracts.py:80` 定义了 `EMPHASIS_LEVELS` 但**零引用**;实际的 `weak/moderate/strong` 裸字典在 `annotation_planner.py:31`、`annotation_prompt_templates.py:165`、`annotation_service.py:1253`、`annotation_jobs.py:297` 各写一份。

### S7 · ffmpeg 定位有 3 套不同实现
`scripts/media_tools.py:49` / `digital_human_routes.py:871` / `scripts/validate_render_color.py:52`,候选目录与优先项全不一致。`server.py` 已把 `resolve_media_tool` 注入依赖树,数字人导出却完全绕过 → **同一台机器上渲染能找到 ffmpeg,数字人导出可能 503**。

### S8 · `storyboard_service` 与 `server.py` 架构门禁余量已归零
用门禁**同源口径**(非空逻辑行)实跑 `checks/test_architecture_size_boundaries.py`:**2 passed**。
```
storyboard_service.py  1294 / 1350  (余量 56)
server.py               1100 / 1100  (余量 0)   ← 已贴脸
ai_mask_engine.py        770 /  770  (余量 0)   ← 已贴脸
```
门禁当前是绿的,但后两项**再加一行就红**。且门禁只覆盖 4 个文件,`config_portability_service.py`、`agent_api/routes.py` 体量已超 `server.py` 限额却无约束。建议在限额表旁加 `# 变更需在 PR 说明理由`。

### S9 · 两份未提交的 UI 规划文档互相打架
`docs/ui-redesign-plan.md`(10-03)提出"工具栏按钮一律纯文字",与 `docs/ui-consistency-plan.md`(09-30)依 `ui-spec.md` 保留 14px 图标**方向相反**。需明确覆盖范围或加 superseded 标记。

### S10 · 启动脚本资产根变量名分叉,文档只记了一个
`launch.bat:67` / `start_here.bat:104` 用 `PPT_STUDIO_ASSETS_DIR`,`scripts/start_digital_human_stack.ps1:3` 用 `PPT_DIGITAL_HUMAN_ASSETS_ROOT`,默认值相同。用户按 `docs/environment.md:29` 设置后运行 `启动数字人服务.cmd` **静默不生效**。

### S11 · `checks/` 22 个"脚本伪装成测试",pytest 静默收集 0 个
文件名 `test_*.py` 但用顶层 `assert`(`test_background_color.py:27` 等)。`python -m pytest checks/test_background_color.py` **收集 0 个测试并返回 exit 0** —— CI 上的绿灯是假的。建议重命名为 `verify_*.py`。

---

## 事件重复累积(前端,易被忽略的一类)

| 位置 | 问题 |
|---|---|
| `ai_mask_extension.js:573` | `setInterval(boot, 500)` 的清除条件 `step5-btn-ai-mask` 若一直不存在(用户未进 Step 5),定时器**永不 clear**,每 500ms 累积一批 `addEventListener` → 进 Step 5 时遮罩预览回调指数级重复 |
| `one_click_extension.js:525` | `boot()` 双路径注册且无幂等标记 → `visibilitychange` 监听器累积 2 份,每次切回前台触发两次轮询 |
| `narration_audio.js:351` | 完整复制了 transport(含重试循环)却**没有 AbortController**,长旁白保存会永久挂起 |

---

## Transport 收口失败(违反 AGENTS.md 约定)

`AGENTS.md:97-100` 规定 `api_client.js` 是唯一 transport,实际 **5 个模块各写一份 `parseResponse` + `fetch` 回退**:

```
ai_mask_extension.js:46-61                project_profile_extension.js:21-50
storyboard_background_extension.js:6-31   style_reference_manager_extension.js:14-51
narration_audio.js:351-355                ← 无 AbortController
```
外加 **4 份逐字符相同的 `esc()`**(`one_click_extension.js:95`、`project_profile_extension.js:57`、`style_reference_manager_extension.js:58`、`ai_mask_extension.js:92`),其中 `ai_mask_extension.js` 那份**漏了 `'` 转义**,与 `ui_foundation.js:101` 的 `escHtml` 语义不一致。

修复:`api_client.js` 补 `postForm(url, formData)` 与 `withTimeoutMs()` 后统一收口,删除全部副本。

---

## 可安全删除清单(已逐项 Grep 验证零引用)

### Python 死代码
| 位置 | 内容 |
|---|---|
| `ai_mask_contracts.py:155-163` | `LAYOUT_STATUSES` |
| `ai_mask_contracts.py:167-177` | `AI_MASK_ANNOTATION_STAGES` |
| `ai_mask_assignment.py:30-35` | `_int()`(`_float` 保留,被使用) |
| `annotation_contracts.py:83` | `DEGRADATION_KINDS` |
| `annotation_contracts.py:106` | `_SLIDE_ID_RE` |
| `annotation_prompt_templates.py:34` | `LEGACY_BUILTIN_DEFAULTS = ()`(空元组,迁移机制未实现) |
| `annotation_planner.py:66` | `replace_all` 参数 + docstring 对应半句 |
| `annotation_jobs.py:51` | `service_get_slide_ids` 字段 + `annotation_runtime.py:90` 及 2 处测试注入 |
| `annotation_job_store.py:143-154` | `latest_active()` |
| `digital_human_service.py:153` | `JOB_STATUS_UNAVAILABLE`(⚠️ 见下方"需决策") |
| `ai_mask_component_detection.py:921-923` | 元素切片 PNG 落盘 —— `auto_mask/elements/*.png` **全项目无读取方**;每页 60 个元素 = 60 次 PNG 编码 + 60 次创建 + 60 次删除,全写进没人看的目录。建议连带删 `:1094-1097` 的 mkdir + glob unlink |
| `one_click_orchestrator.py:837-846` | `try/except TypeError` 双参回退(签名恒接受两参,分支不可达;`:840` 反而把默认值丢成空串) |

### 前端死代码
| 位置 | 内容 |
|---|---|
| `static/digital_human_panel.js:671-691` | `generateSlide`(整段化改造残留) |
| `static/workspace_navigation.js:167-180` | `selectProductionMode`(`:161` 注释明写制作方式已不在工作区切换) |
| `static/courses.js:717` | `unchapteredCount`(`:780` 又重算一次) |
| `static/workflow_state.js:32` | `step2GenerationRequirement`(+ `storyboard.js:664` 赋值) |
| `static/workflow_state.js:42-54` | `storyboardRoles` 11 项(后端已返回 `roles`,前端从不消费;角色表实际由 Python 侧维护 → **前后端双份,前端这份是死的**) |
| `static/index.html:299-300` | `#step2-slide-card` / `#step2-slide-fields` 死标记(连带 **24 条**失效 CSS) |

### 孤儿 CSS(231 条无任何引用)
`style.css` 225 条 / `stitch.css` 18 条 / `annotations.css` 1 条。成体系的簇:

| 选择器簇 | 位置 | 状态 |
|---|---|---|
| `.step3-video-background-*` | `style.css:1740-1764, 3486-3494` | 已迁移到独立弹窗 |
| `.vn-*`(12 条) | `style.css:5201-5615` | 旧 Step2 视觉-旁白映射编辑器 |
| `.step-section-heading/-note/-index` | `style.css:2326-2349` | 旧步骤分段 |
| `.step7-audio-title/-script` | `style.css:2429-2434` | Step7 已并入可见 Step6 |
| `.reference-image-grid/-item` | `style.css:1348-1375` | 无引用 |
| `.mask-visual-anchor/-title/-note` | `style.css:2031-2093, 3595` | 旧 Mask 可视化 |
| `.creation-config-choice*`、`.project-profile-*` | `style.css:5864-5884` | 旧弹窗卡片 |
| `#step2-btn-generate` | `style.css:3092-3105` | 已拆为 `-script` / `-visual` |
| `.annotation-thumb` / `.annotation-thumb.active` | `annotations.css:76-78, 95-97` | 已被 `annotation-page-tab` 取代 |
| `.toast-success` / `.toast-warning` | `style.css:4092-4102, 7012-7026, 12516-12517` | `ui_foundation.js:30` **只渲染 error**,这两色永不可达;`.toast-info` 甚至从未定义 |

> `.sidebar` 等热点选择器在 `style.css` 内被定义 **9 次**(行 249→2751→3217→4199→4504→6593→9553→10204→11970),层层覆盖。**这是 AGENTS.md 描述的分层叠加设计,建议保留**,但中间 7 个版本已完全被覆盖,属可净化的死重量。

### 项目卫生
| 文件 | 依据 |
|---|---|
| `UI优化方案.md` | **0 字节**空壳,却被 git 跟踪(需 `git rm --cached`) |
| `hand off.md` | 基线 `66c38c8`(9-16),自述"建议尚未实施",应移入 `docs/audits/` |
| `tts-stage-7zmwa62_/` | B6 泄漏残留,可删 |
| `checks/rebuild_project_reveal.py`、`checks/run_project_ai_mask.py` | 全仓零引用 |
| `run_local.bat:43` | `%APPDATA%\TRAE SOLO CN\...` ffmpeg 兜底 —— 特定 IDE 环境残留,任何其他机器上都是无效探测 |

**明确不要删**:`checks/agent/`(AGENTS.md 指定的契约平价门禁)、`e2e_one_click_run.py`(被导入)、`make_contact_sheet.py`(被调用)、`docs/audits/dead_code_review_2026-09-19.md`(含"装饰器注册的函数不能按名字零引用判死"的重要教训)。

---

## AGENTS.md 与实际代码矛盾

**类别 1:12 个前端模块(7,839 行 = 前端 JS 的 26%)在模块边界章节一字未提**
`creation_config_management.js`(1659)、`courses.js`(1437)、`style_reference_manager_extension.js`(743)、`one_click_extension.js`(527)、`ip_character_manager.js`(452)、`project_profile_extension.js`(407)、`account_management.js`(372)、`storyboard_background_extension.js`(322)、`select_menus.js`(162)、`ai_mask_auto_state.js`(101)、`ai_mask_extension.js`(578)、`digital_human_panel.js`(1079)。

尤其 `ai_mask_extension.js` / `ai_mask_auto_state.js` 是 AGENTS.md 花 57 行描述的「Automatic AI Mask Contract」的前端落点,却未在前端边界章节出现。

**类别 2:职责重复声明**
- `normalization`:AGENTS.md 同时声称 `mask_workspace.js:133-137` 与 `mask_reveal.js:130-132` 都拥有。实际 `mask_reveal.js` 仅 70 行,只做预设与传播。
- `event_bindings.js:171` 声称拥有 "all page-level event binding",实际 `courses.js`(65 处)、`creation_config_management.js:1561-1590`、`digital_human_panel.js:930-960` 等都在自行 `addEventListener`。

**类别 3:`flow.js` 是唯一没有职责条目的核心模块**
它定义 `VISIBLE_FLOW` / `isVisibleStepUnlocked` / `getDownstreamEditImpact` 等 18 个函数、被 `checks/test_visible_flow.js` 独立测试,还在 `:330-367` 安装 Step 3→5 点击守卫 —— 是**行为规则**而非纯数据,但 AGENTS.md 未提。

**类别 4:已文档化的拆分未同步**
`AGENTS.md:5-12` 已定边界(`storyboard_planning` / `storyboard_profiles` / `storyboard_prompt_templates` / `storyboard_llm`),但 S8 显示 `storyboard_service.py` 仍有 1294 逻辑行。

---

## 对本次审查的两处纠正(避免无效返工)

1. **架构门禁当前是绿的,不是红的。** 有报告称 `storyboard_service.py` 1497 行超 1350 限额 —— 那是用 `wc -l` 数总行数,而门禁口径是**非空逻辑行**(`line_count()` 过滤纯空白行)。用门禁同源口径实跑:`pytest checks/test_architecture_size_boundaries.py` → **2 passed**。真实风险是 S8 说的余量归零,不是已越界。

2. **Toast 只显示 error 是三次连续提交的有意决策**(`0b540a3`→`f7d8c01`→`a7f991d`),不是"被丢弃的 bug"。`ui_foundation.js` 永不可达的 success/warning CSS 属于**决策与实现不同步的残留**,定性问题应交回产品决策 —— 要么恢复多 tone 渲染,要么清理死 CSS。**不要当 bug 静默"修"掉。**

---

## 建议修复顺序

| 优先级 | 项 | 理由 |
|---|---|---|
| **P0** | B1(一行改动) | 止数字人功能不可用 |
| **P0** | B2 | 跨项目数据损坏 |
| **P0** | B4 | 任意文件写入 |
| **P0** | B3 | 进程泄漏,影响长期稳定性 |
| **P1** | B5, B6 | 假阳性 + 仓库污染 |
| **P1** | B7, S11 | 门禁失效会让后续所有 CI 结论不可信 |
| **P2** | S1-S3, S5 | 功能性故障与矛盾实现 |
| **P2** | Transport 收口 | 消掉 5 份 fetch + 4 份 esc |
| **P3** | 死代码清理 | 建议在 `checks/test_frontend_quality.js` 加 ownership guard 防回潮 |
| **P3** | AGENTS.md 补 12 模块 + 修 4 处矛盾 | 文档债会持续产生误导 |

---

## 遗留待决策项(不宜盲删)

| 项 | 需确认 |
|---|---|
| `creation_config_management.js:779` `setDefaultPackage` | 完整实现"设为账号默认配置"并调刷新,但**无调用点** → 是入口漏做还是功能已下线?后端端点 `/api/accounts/{id}/default-config` 存在 |
| `storyboard_prompts.js:157` `refreshStep2PromptTemplates` | 无调用点 → 模板列表外部变更后不刷新,是功能缺失 |
| `docs/ui-redesign-plan.md` vs `ui-consistency-plan.md` | 明确覆盖范围或加 superseded 标记 |
| `.toast-success` / `.toast-warning` CSS | 恢复多 tone 渲染,或清理死 CSS |
| `static/annotations.css:76-78` `.annotation-thumb.active` | `ui-consistency-plan.md` P0-1 残留,随收尾一并删 |
