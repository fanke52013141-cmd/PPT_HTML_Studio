# 真实分级诊断：JSON、单图、整页全部通过 · 2026-10-20

基于main 00fb81d4及本机累计未提交优化。实际应用源码`D:\Program Files (x86)\PPT_HTML_Studio`；附件工作区`C:\Users\Administrator\Desktop\html动画\PPT_HTML_Studio`。本批新增评测脚本和记录，合同包0.9.111/API1.59.0保持。

## 实测结果

用户授权按最小JSON→单图→整页逐级真实测试。2026-10-20北京时间22:09—22:18完成；6次真实调用，无重试，无unknown，未达到预设最多8次上限。

| 层级 | Legacy总耗时 | Pi总耗时 | Legacy总token | Pi总token | 结果 |
| --- | --- | --- | --- | --- | --- |
| 最小JSON | 2.027秒 | 5.904秒 | 55 | 317 | 两侧严格返回ok=true |
| 单张真实截图 | 2.024秒 | 7.242秒 | 1926 | 2182 | 两侧正确读出最低刻度-10 |
| 整页重叠修复 | 224.043秒 | 272.192秒 | 35959 | 43388 | 两侧1轮候选通过606时点检查，0冲突 |

总token83827，费用均null；未按token估价。全部作者保持，source_unchanged/code_unchanged=true。前两级都通过才升级；整页沿原generate_repair/preview，不保存作者或批准。

原始`outputs/repair-staged-20261020-v1/`保留protocol、report.json/report.md、paired-validation.json，每级inputs/output/result/progress和原逐帧检查。基线工作树指纹`2cb4596f9c2c9b4958f2565185ea260ca2a388ca3836a473a180790cd3e961be`；后续文档记录不反写该指纹。每级两侧首轮system/user/schema及图片字节hash一致。

## 数据解释

两侧基础文字调用和单图读取可用，不能继续笼统称为两个执行器都不行。本轮增长集中在整页局部修复的推理阶段：

- Legacy首流片段2.725秒，首次正文216.101秒，流完成216.277秒。输出20562token中推理20525，约99.82%；正文只约37token。累计推理56301字符，最终JSON125字符。
- Pi首个SDK可见事件5.433秒，首次工具参数264.351秒，适配器完成264.386秒。SDK累计推理79237字符、工具参数132字符；仅提供总token43388，没有同粒度推理token，不按字符估算。
- 两种首事件测量定义不同，不把SDK事件当网络首字节。任务耗时包含SDK/检查等开销，不能全部算成供应商推理。
- 本整页样本Pi多48.149秒（21.49%）、总token多7429（20.66%）。每侧一页一次配对，不能推广为长期优劣或切换默认依据。
- 三层同时改变文字量、图片数量和任务复杂度，因此不能单独归因于某个输入字段。持续推理可排除本轮“全程无响应”的描述，不能反推旧unknown任务当时同样在推理。旧180/600秒失败历史完整保留，不并入本批成功率。

## 画面与候选

原scope仅obj-card-2，文字、字号、样式、关系端点、图表数据、动作及音频绑定保持：Legacy提出width695/offsetY10，Pi提出width440。两者均避开chart:min文字，全部606个30fps输出/动作边界时点通过，frame_complete=true但continuous_time_verified=false。

已实际看过终帧：Legacy第二张卡片较宽、下移后靠近底栏；Pi卡片较窄，正文换行。完整截图在report.md及legacy-after.png/pi-after.png。工程通过不代表用户审美或听审批准，human_visual_acceptance=pending_review。

## 可复用脚本与验证

`scripts/diagnose_repair_stages.py --source-run runs/ec60bbd4_010236 --output outputs/全新目录 --live`。默认dry-run；目录必须新建，不能重放旧任务。运行导入前设置独立DB/run root；原配置/凭据只读，不导入server。

同一冻结glm-5.3-flash，thinking enabled、65536、温度1.0。Legacy沿绑定reasoning_effort=max，Pi沿原native thinking/submit_json封装；只保证业务输入相同，不保证HTTP字节相同，不代表完整Pi无人工具工作流或新页生成。每级前两层每侧最多1次，整页最多2次，格式回退和JSON修复也占物理预算。未知终止余批，不重发；错误不删分母。

新增2项分级验证和相关回归共16项通过，1.47秒；Ruff与git diff --check通过。canonical quick完成并退出0，All requested checks passed；日志`.tmp/repair-staged-quick.log`。没有生产Prompt、默认执行器、Schema或数据库迁移。五维自审检查了严格探针输出、fail-closed升级、物理调用预算、配置隔离、无保存/批准及原始失败留证。

## 下一步

优先实现几何避让候选的确定性试算，并由原检查器验收，减少模型自行搜索坐标。另做独立固定输入的请求级low effort对照时，保留thinking/65536/温度与原预算，以原检查成功率、语义保护、耗时和token共同决定是否采用；当前未修改生产推理配置，也未追加此类调用。

本批原课程/音频/批准/生产数据库不写入，未启动正式服务、提交或推送。源文件同步两处本地目录，模型材料和运行结果仅留应用outputs。
