# 外部 Agent 执行、能力与验收合同 2.0.0

2026-10-19；契约0.9.100/API1.54，细化HPS-001/007/009/010/013—018/023—030/035—037。
定义specified；本批实现逐对象事实、同源静态预检、逐项验证/能力声明及原服务采用保护。外部实际新Agent效果独立验证。
此卡补充可携带任务0.2.0；原result JSON仍0.2.0，旧客户端按缺省宽松文件模式兼容，不偷偷改变其JSON字段。
当前执行2.1.1按[输入/人工工作区的勘误节](external-agent-workbench-0.1.0.md)澄清能力门槛；本卡的not_run接续不能豁免本任务必需能力。

## 阶段和角色

- 静态修复：只改scope内注册presentation/字阶/变体，保留内容、关系、素材、全部motion/binding。
  “静态”指禁止改动作，不表示验收忽略动作；布局改变后的保留入场位移仍须满足内容安全区。
- 动画修复：必须原音轨/真实时间轴，沿原actionId/beatId和受保护repair；便携工具不实现音频绑定或DOM播放，相关检查交原系统。
- 设计参考：没有可编辑场景，禁止输出可保存局部操作；素材/能力缺口分别归原生产阶段。
- 外部Agent提出候选并声明真实能力；官方便携预检覆盖已列结构条件；原系统检查当前输入、保护、容量、时序和指定遮挡；人工决定画面/语义/采用。
  一个阶段通过不能替代另一阶段；缺工具或缺能力的合法结果可以是needs_input/unsupported，不强迫编造成功。

## 输入中的可执行信息

每包新增constraints.json（与task.context.execution等值）、verification.schema.json、verification-template.json、
tools/check_task.py、tools/html_repair_static.py、tools/preflight.cjs。源输入和工具进task.files/manifest的hash；模板含task_id，不进循环身份输入。

约束从当前生产compiler、overlapPolicy、作者scene、解析layout和登记能力派生，不靠Agent猜测：

| 信息 | 语义 |
| --- | --- |
| slot_box | 未加实例覆盖的登记槽位，逻辑画布px |
| current_author_box | 当前作者实例覆盖后的box；截图缩放或动画变换不反写源坐标 |
| retained_actions | 保留actionId/type/start/duration/offset；静态任务不可变 |
| 硬边界 | 作者box在1600×800内容区；enter位移端点也在该区。全画布1600×900，下100px为字幕区 |
| 组合限制 | 仅原Schema和对象实际兼容变体/公开部位；padding/列权等组件内部参数不是任意可写CSS |
| 字号验收 | font_requirements逐项指定唯一id、scope内targetId、公开part、minimum_px；验作者显式字号下限，DOM容量与可读性另验 |
| 遮挡覆盖 | temporal_spec明确pairs/policy/250ms；overlap_coverage记录实际pairs/exclusions和来源。空列表表示未检查指定对象对，不表示无遮挡 |
| 保留项 | 原文/数据/关系/身份/素材字节、人工保护、声音及静态任务motion/binding均保持；无隐式审批 |

例如实例底边793+保留enter.offsetY12=805，超过800，即使终态容得下也不合法。
这只是解释当前生产规则，校验执行共用原compiler；不为一个样例改安全线。

ExportRequest可指定font_requirements、overlap_pairs/overlap_policy、require_verification和require_image_understanding。
不从goal散文自动猜验收阈值。界面新导出默认勾选严格交接；兼容调用缺省require_verification=false时须如实标为兼容模式。

## 能力协商与环境

verification.json的abilities必须显式声明can_view_images、can_listen_audio、can_run_preflight、can_access_original_preview。
需要看图的任务若不能看图，proposed不被接受，返回needs_input/unsupported、operations=[]并说明能力缺口；像素扫描不替代图像理解或审美。要求看图的候选还必须记录实际原图审阅和证据，不能只勾选能力true。
严格静态任务要求可运行官方预检。Python3.10+、Node20+；包已带编译器/Schema依赖，不需要npm/pip或联网。
如果环境不满足，返回合法停止结果并记录未运行项，不自行下载、换渲染器或猜测通过。
声音不存在时静态候选不声明音画同步；动画任务仍在导出前拒绝缺少真实声音。

## 便携预检与原系统

在解压根目录运行：

```text
python tools/check_task.py --task task.json --result result.json --out preflight.json
```

工具使用生产html_repair_static.apply_static的原样源文件应用静态操作，使用原AJV与生产compiler构建的独立Node包。
它检查材料/任务身份、操作范围/Schema、作者字号条件、原生产编译（含保留enter安全区），不打开数据库/写作者/联网。
返回hps.html.preflight@1.0.0、preflight_passed、逐检查状态、未运行清单，绑定result_file_sha256。
退出0只代表所列便携检查通过；退出1需查看具体错误。它不声称浏览器文字容量、指定遮挡、审美、音频、人工保护或批准通过。
不得改工具、输入、Schema、manifest、范围或安全线来让测试变绿，也不以自写半套检查器取代此报告。

导入/预览继续用原repair/播放器。temporal_spec进入实际请求，系统检查并展示真实覆盖；作者字号条件在服务端另验。
目标未达到即便原几何通过也不能取得通过回执。其余未机器化的业务/审美条件由明确的人工验收负责，不能默认成功。

## 输出与采用

严格任务交付ZIP根：result.json、report.md、verification.json；静态proposed还必须有preflight.json，可选evidence/。
verification.json必须符合包内Schema，task_id一致，每个criterion_id恰好一次，不能漏项、重复或添加未经定义的条件。
Agent记录self_checked/failed/not_run/unknown；不得自己写system_passed。外部工具产物与声明均为未信任证据，原服务仍独立复核。
有已知failed项不能交付拟采用的proposed；失败就修订或停止。not_run允许用于文件模式的原播放器/修改后画面/人审项，由交接方接续，不能算违规或通过；不能覆盖required_abilities或要求看图时的原图理解。

原输入身份/版本核对通过后留档交付；严格候选必须有完整能力/验收记录及绑定当前result字节的通过预检。
预览未写作者。候选通过后记录result_hash对应的严格交付资格；save还需原候选key/hash和当前源身份、资格均匹配。
直接调用旧preview或改task_id不能绕过严格任务的交付资格。内容/素材/源码/API变化须重导出，旧结果保持历史。
检查失败提供带task_id/result_hash的原系统反馈；至少包含错误码、阶段、实际覆盖/未运行项，不伪造after截图。
保存仍不等于画面/语义/声音批准或正式输出。JSON单文件入口为旧模式兼容，严格任务使用完整ZIP。

## 兼容与验证

无DB迁移，不改图片后端、renderer或TTS，原save/invalidation和人工保护不变。静态操作纯逻辑提取保持原字段/版本/错误语义；
所有调用共用一个owner，便携文件由源构建，不单独手改生成代码。验证正/负例、缺能力/漏验收/伪造system_passed、
字体不达标、越界、指定遮挡范围及严格save绕过。真实包不含其他Agent的答案，外部新执行效果另记。
