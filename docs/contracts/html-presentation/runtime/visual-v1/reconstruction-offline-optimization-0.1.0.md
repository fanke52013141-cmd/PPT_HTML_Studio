# 图片还原离线工程优化 0.1.0

2026-10-25；HPS-007/009—013/015—018/023—025/026—030/037。兼容内部增量，公开 HTTP/Agent Schema、数据库、批准职责及契约包版本保持。本文定义七项实现范围，不代替原69项AC、真实模型准确率或视觉签收。

## 定义卡与实现范围

| 项 | 所有者/输入 | 行为与边界 | 验证 |
| --- | --- | --- | --- |
| 1 搜索 | html_capacity_repair / 原容量实测 | 同对象/种类/part的绝对赋值合并；先经原编辑器验证、状态去重，再消费每状态4个测量名额。仍保留目标/类型轮询、32状态/4深度等上限；无新合法候选和预算耗尽分开 | 重复/no-op前缀、净操作、原多对象浏览器案例 |
| 2 预算 | html_page_budget / 当前整页上下文 | 新生产、独立还原、模型候选与确定性求解的直接入口创建上下文；嵌套不重置。默认900秒、80次检查子进程、12次模型入口调用（底层HTTP尝试仍由原传输所有者计量）；预留20秒及2次子进程用于严格最终检查。JSON出站与子进程按剩余时间截断；图片传输保留原接口，只在前后合作检查，不声称远端已取消。unknown不重发 | 嵌套、超时、迟到结果、最终保留区、上下文恢复 |
| 3 验收 | scripts/verify_reconstruction_v2_acceptance.py | O7-01—07执行原pytest和两组真实浏览器基准，记录HEAD与实际工作树源hash、JUnit、逐文件hash。执行前后源变化阻断；跳过、空测试、缺失/改变证据、来源变化、成功案例缺完整30fps证据不能通过。原69项AC可导入，但本入口不认证的项保持not_run | 破坏性证据负例、完整新目录执行与二次verify |
| 4 布局 | html_layout_groups + html_linked_layout / 注册槽位、受影响ID | 新增同排2—4卡片、同排图文对与最多4卡片的多行位置提案；原槽位必须行内/行间不重叠，顺序固定，间距12，只改offset，不改尺寸/内容/关系。原编辑器人工保护及整页动态QA决定是否采用。现有纵列与point路由保留 | 注册三阶段横排真实浏览器；图文/多行受控策略测试。当前未新增2×2生产模板，也不宣称任意图文版式可修复 |
| 5 可实现性 | html_design_feasibility / compile_plan输出 | 新设计付费出图前，通过原浏览器、字体及注册槽位测量文字投影；剔除尚无素材的image及其关系，不写回scene。容量问题回内容分配/布局；基础Schema/基础准备不完整阻断。不检验插画可实现性、整页关系和设计定稿后的变体容量 | 普通/过短容器的真实字体测量、生产出图前阻断 |
| 6 复核恢复 | html_reference_workbench / 原图、当前截图、报告、独立定位 | 定位未决自动导出本地并排图/文字框及可编辑JSON。导入校验会话hash、准确文字/身份/范围、原图、当前作者/人工覆盖及运行定义；每次修正另存回执，并重新生成与修正框一致的文字边缘诊断。resume_review复用原review_fidelity，仅重做证据/保真，不生图、不重规划、不保存作者、不批准。CLI仅支持明确的离线响应回放，不把它记为真实供应商质量 | 一次恢复只调用保真；原图/作者/身份/转录/会话变化阻断；本地浏览器交互 |
| 7 素材/缓存 | html_asset_service、html_asset_geometry、html_review_cache | 命中素材缓存还核对实际尺寸/透明边界；匹配缓存损坏停止，不自动付费重生。输出主体可见尺寸、占比、命名锚点是否在可见范围的诊断，不裁切/改锚点。整页内严格同输入复用审阅：实际来源/字体/资源/渲染器/QA/环境与诊断模式组成键，截图归档为稳定文件，逐次验证截图/动态报告hash；变化或损坏重新检查。ROI按几何问题、归一化位移、ID排序，仍最多8对象/2表，不减少完整审核清单 | 缓存破坏/字体变化/模式变化、素材边界/缓存元数据、原独立审核回归 |

## 生命周期与副作用

- 沿用html_production_service事务及rollback；预算报告、复核回执和截图只属于证据，不是作者或批准状态。没有新项目写入入口，无需新增invalidation reason。
- html_design_candidates与html_build_snapshot固定上述所有新增生产模块。原人工保护、已接受设计身份、revision、音频来源和最终严格检查保持。
- 定位人工确认仅确认映射资料；仍为待视觉审阅，不直接改HTML坐标。CLI回放明确execution_mode=offline_supplied_response，真实提供者调用0。
- 默认运行提示片段及输出Schema不修改；证据选择优先级、复核替换与预算由代码执行。已存在1.1.0保真片段继续固定身份。
- 缓存只在本次整页上下文内复用；不实现跨任务浏览器结果复用、跨页模糊素材复用或自动合板。

## 可执行验证

仓库根目录，使用新的输出目录：

```powershell
python scripts/verify_reconstruction_v2_acceptance.py --output outputs/optimization7-final
python scripts/verify_reconstruction_v2_acceptance.py --verify outputs/optimization7-final
```

需要保留原计划未完成状态时，加 `--original-plan <原验收清单-v2.json>`。默认没有任何线上调用。工程测试中模型响应替身和实际共享浏览器检查分别记载，不能推导真实模型或美学通过。

定位未决后打开diagnostic.json中的workbench.path，在页面修正并下载correction.json；真实配置执行器调用共享 `html_reference_workbench.resume_review(folder, correction, run_dir=..., deps=原配置依赖)`，不要导入server另启服务。离线已给定响应的复放命令：

```powershell
python scripts/replay_reference_review.py --run-dir <run> --session <workbench目录> --correction <correction.json> --response <ReviewFacts响应.json>
```

复核是本地产物工作台/内部恢复函数，本批没有给产品面板新增按钮或公开HTTP恢复接口。真实质量、跨课程、产品用户走查和视觉批准仍独立。
