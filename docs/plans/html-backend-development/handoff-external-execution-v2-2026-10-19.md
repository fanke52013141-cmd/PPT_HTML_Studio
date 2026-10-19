# 外部执行合同2.0与独立真实输入

2026-10-19；契约0.9.100、API1.54、输入/结果JSON仍0.2.0；外部执行合同2.0.0。
本地源码未提交推送，未切真实服务，无新provider/生图/TTS调用，无原项目作者/声音/批准写入。

## 本批补全

- `html_handoff_execution.py`从原compiler/overlapPolicy派生逐对象约束和检查覆盖，生成constraints、验收Schema/模板及便携工具。
- `html_repair_static.py`提取原repair静态变更语义，由生产repair与包内Python工具共用；原字段、版本与错误边界保持。
  新模块已加入生成snapshot、设计身份、评估及对照源码闭包。
- `scripts/check_external_task.py`与打包自原AJV/compiler的Node工具仅做静态结构预检，不要求pip/npm/联网，不替代DOM/视觉/音频验收。
- 字号业务条件、指定遮挡范围进实际服务预览；导出基线也运行同一指定范围，不能拿空pairs报告充当“已无遮挡”。
- 严格交付需verification能力/逐项记录与绑定结果原字节的预检；缺能力、漏项、虚报system_passed、字号不达标或绕过交付不能保存。
  旧JSON兼容模式保留，界面默认严格，真实审批仍独立。

## 新Agent真实测试包

`outputs/external-agent-new-agent-20261019/New-Agent-Token-Slide003-v2.zip`，23个文件，约2MB。
当前task_id=`dbe7bc1c71f984822c959f8a38b84486b61eeda7536cf517e9b20df404faa4b0`；
SHA256=`35b6ebb9009effa8d223fd9b9b2b9f1890d3ea2e8e0f789711c0da839cf82a8d`。

仍来自真实Token项目d1f5885a_122521/slide_003的历史未保存还原候选与原PNG；隔离run独立于第一位外部Agent的试验。
scene/binding/准确内容保持基线，revision1；原源文件hash复核，无真实音轨，只验作者时钟静态修复。
包内有START-HERE、详细TEST-BRIEF、正式CONTRACT/EXECUTION、实际截图/素材、约束和官方工具。
不分发先前Agent的交付/修复参数、主Agent可行性对照答案或真实项目数据库/凭据。

验证解压副本可仅用Python/Node执行官方工具：正例通过；终态793+enter12=805的负例被原compiler拒绝。
原系统严格导入/预览正例通过，3项作者字号条件与4组指定遮挡通过，未保存、未批准。
这些是明确主Agent构造的可行性/协议对照，不是新外部Agent自主修复成功；对照产物不在交付ZIP。

## 构建与原流程保护

扩大回归发现本机editor_ui未安装锁定依赖且旧指纹与源文件不一致。对未改内容、规范化后与HEAD逐字节一致的文件恢复原Git字节，
对已修改消费者仅规范换行且保留文字改动；随后npm ci按锁安装72依赖、npm build重建，16项编辑器测试通过。
没有手改manifest hash、降低快照守卫、改许可证或替换依赖版本。

## 最终验证记录

- 2026-10-19最终隔离回归：170 passed，155.23秒；覆盖新执行合同、交付ZIP、原repair、Web界面、Agent/CLI/MCP契约、快照与运行技能、架构边界及路由清单。仅有Starlette依赖的弃用警告。
- editor_ui锁定依赖构建成功，16项测试通过；Ruff、前端质量检查、Agent能力矩阵生成一致性和git diff --check通过。
- 正式包已复制到桌面`外部Agent独立测试_规范2.0_20261019/新Agent独立测试包_规范2.0.zip`，附发给新Agent的指令、输入包校验和正式执行规范。
- 以上为本地工具、集成与主Agent对照验证。新外部Agent尚未执行；其返回结果仍须原系统复核和人工审阅，不能据此宣称真实课程生产验收完成。
