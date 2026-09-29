# 优化实施完成报告：对照 review_2026-09-29_verification.md（2026-09-29）

实施基线：`62d5052`（验证文档制定时的代码）。实施完成：`fb92d8d`。
提交序列：`75ab771`（docs 归档）→ `f8029e9`（批一）→ `9cf9485`（批二）→
`ff61b3b`（批三）→ `5a21394`（批四）→ `fb92d8d`（批五：交叉验证修正）。

最终自动化验证：`python scripts/run_checks.py --level full` 退出码 0，
**1443 passed / 8 skipped / 0 xfailed / 0 failed**，ruff 0 错误，
Remotion `tsc --noEmit` 通过。8 个 skip 均为环境豁免（7 个 AI Mask
handoff 冻结样本缺失、1 个百度 OCR 真机 Key），全部解释。

## 第一批：恢复勾画基本功能并防止保存污染 —— 全部完成

| 验收条款 | 状态 | 证据 |
| --- | --- | --- |
| 所有新增路由使用实际服务装配测试 | ✅ | `checks/test_annotation_w3_routes.py`（8 用例，真实 `configure_annotation_service`，无方法级 mock），覆盖 text-layout GET/PATCH、jobs 提交/查询/取消、prompts GET/PUT、restore |
| 服务端已提交后覆盖层故障不重发 add | ✅ | `flushAnnotationsSave` 成功路径状态更新与 UI 渲染分离（annotations_workspace.js）；`checks/test_annotation_save_flow.js` R4-002 用例 |
| A 项目回调晚于 B 项目载入不改变 B 状态 | ✅ | 三重守卫（generation+projectId+slideId）；save_flow 的 cross-project stale-success/failure 用例 |
| 409/422 保留可恢复草稿，不无限重试或静默丢 | ✅ | 409 → conflict 保留批次+currentRevision，状态条点击"载入服务端版本并重放"（resolveAnnotationConflict）；422 → failedOps 隔离+状态条显式重试；save_flow 用例 |
| add 对"服务端已执行、客户端未收到响应"幂等 | ✅ | 操作携带 client_op_id；失败后重取服务端页面做内容去重（dedupeOperationsAgainstPage），已生效的 add 不重发；save_flow 幂等用例 |
| （文档要求的 script 顺序检查） | ✅ | index.html 补载 `annotation_playback.js` 并纳入 `checks/test_frontend_quality.js` 顺序断言 |

## 第二批：确认、新鲜度与导出一致性 —— 全部完成

- **R4-004** ✅：确认条目 target/anchor/style/timing 真实变化 → 重置 draft +
  删除 `annotation_timeline.json`（`_op_update` events.confirmed_reset →
  patch_slide unlink）；**删除已确认条目同样失效时间轴**（批五 B2 补充，
  验证员发现的遗漏）；同值保存与 locked 切换不重置（3+1 个测试）。导出门禁
  确认：enabled 且 timeline 缺失 → BuildError，被改/被删笔迹不再进视频。
- **R2-001 + PPTX 重试额外缺口** ✅：首发与重试共用 `_prepared_export_job`
  （账号继承项目行、digest/影响快照按提交时刻重建）；run_job 起止两处
  queued_digest 校验对重试任务同样生效；批五补充历史 payload 缺账号时
  回退项目行归属（不无条件 default）。测试含非 default 账号与越权 404 断言。
- **R1-002** ✅：重复 ID 在 `validate_slide_identifiers`（normalize 内，所有
  契约写入前）拒绝；空白 ID 因修复路径兼容性由 `reject_blank_slide_ids` 在
  用户手写保存入口拒绝；空 slides 列表合法。异常时零落盘/归档/影响副作用。
- **Step 2 CAS** ✅：GET 返回 `contract_sha256`；PUT 在 `project_artifact_lock`
  内比较，过期 409 携当前摘要且零副作用；前端回传摘要、409 刷新基线并提示。
- **R4-007** ✅：AnnotationOverlay 从 useVideoConfig 取 fps/width/height 传入
  共享采样器与 viewBox。

## 第三批：账号闭环、ZIP 与历史数据 —— 全部完成（含验证员发现的 5 处补漏）

- **R5-001/R5-002** ✅：`project_or_404` 加账号过滤（127 处统一生效）；交叉
  验证发现的 5 处绕过 helper 的查询点（pptx_service.get_project、
  storyboard_background、visual_settings_service、ai_mask_routes、
  ip_character_service）在批五全部补齐，`checks/test_project_lookup_helper.py`
  新增守卫断言防回归。后台调用者逐一核实均有 set_current_account_id。
- **R2-004/R5-003** ✅：detect/plan 提交记录账号进 payload，worker set/reset；
  历史任务回退项目行归属（含 pptx run_job 同规则）。
- **R5-004/R5-005** ✅：config.json 8MB、全包解压 80MB、512 条目上限；
  重复与规范化等价条目拒绝；批五再补读侧有界流式读取（防 ZipInfo 谎报）。
- **R5-006** ✅：新增连续修复迁移 `0016_repair_presentation_mode_backfill.sql`
  （mask_enabled=1 且 full_frame → reveal，幂等；不修改 0014、不覆盖用户
  显式选择）；迁移测试清单同步更新。

## 第四批：检查门与剩余可靠性 —— 全部完成

- **R0-001** ✅：45 项 ruff 逐项修正（F821 按实际调用改，无忽略规则），
  `run_checks.py --level full` 全链恢复通过。
- **R2-008** ✅：`_write_json` 原子契约（批五重落地——上一提交信息与实际
  不符，由交叉验证抓出并修正），带回归测试。
- **R2-006** ✅：渲染 worker 只释放显式移交的锁；账号上下文 finally 必复位。
- **R2-012** ✅：调速"检查-生成-校验-发布"全程持 `project_artifact_lock`。
- **两条 xfail** ✅：TTS 低 RPM 预留改为"满桶放行+债务跨窗口结转"分段预算
  （cost=1 的 image/llm 路径语义不变，19 个 governor 专项测试通过）；超大图
  按异常类型归类不可重试。两测试移除 xfail 标记并转绿。

## 文档明确"不是缺陷/不需要修"的项（遵照未动）

R1-001（调速变体历史保留）、R3-002（is_island 闭包）、R4-009（OCR 密钥
环境变量为已实现的过渡装配）、R4-010（occurrence/置信度定位修正）、
R5-007（legacy checksum 白名单为兼容规则）。

## 交叉验证（3 个独立 subagent）结论汇总

1. **全局红线域**：full 检查/tsc/提交内容/红线清单全部达标，"代码与自动化
   验证层面全部达标"；提醒 storyboard_service 行数门禁 1350/1350 零余量。
2. **服务端域**：10 项中 9 项通过，发现 N1–N7（批五全部处置）；确认
   Agent 通道账号由 token 固化、启动恢复不受账号过滤影响。
3. **勾画域**：6 项全部通过，发现 B1（saveInFlight 停摆，高）、B2（删除
   确认条目不失效时间轴，中高）、B3/B4（低）——批五全部修复并带回归。

## 遗留的放行差距（需真实环境，自动化无法替代）

1. 真实浏览器走查：勾画的识别/规划/编辑/保存/冲突/切页交互（当前以
   W3 路由装配测试 + Node VM 保存时序测试替代）。
2. 横竖屏各一份含勾画输出的真实 MP4/PPTX 人工检查。
3. 非 default 账号 PPTX 失败重试的真实端到端（已有测试级覆盖）。
4. 7 个 AI Mask handoff 指标测试需要 `outputs/ai_mask_optimization_handoff_20260920`
   冻结样本才能运行（环境性豁免，与本次改动无关）。

## 遗留建议（不阻塞）

- `storyboard_service.py` 行数门禁 1350/1350 零余量，后续改动前先做拆分预留。
- `docs/audits/review_2026-09-28_R0.md` 记录了审查期间的隔离 temp 路径
  （历史文档性质，无功能性影响）。
