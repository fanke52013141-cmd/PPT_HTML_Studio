# 有界几何候选、原验收与扩样结果 · 2026-10-20

基于main 00fb81d4及累计本机未提交优化。实际应用源码`D:\Program Files (x86)\PPT_HTML_Studio`；附件工作区`C:\Users\Administrator\Desktop\html动画\PPT_HTML_Studio`。包0.9.112/API1.59.0，定义见geometry-repair-0.1.0.md。

## 1. 候选生成

新增内部owner `html_geometry_repair.py`。只支持当前scope内的单对象平移及卡片宽度，处理显式线性关系箭头穿文字。位移每轴≤96px，宽度75%—115%；整数有限步长，最多4个scope对象。保留原文、字号/样式、端点身份、动作、binding和音频。不新增节点/路由或CSS，不放宽模板/重叠规则。

原报告真实几何/文字矩形用于粗预测；至多24个均匀帧做排序，不是验收范围。只给预测无穿字者排序，按相对改动及16px以内邻居间距损失打分；原本在figure内的对象继续在该figure内。resize可能改变文字换行、箭头头部和动作无法由粗预测保证，都交回原检查器。

通用内部调用`geometry_repair(run, slide, request)`，request包含expected_revision和scope，可指定expected_audio_revision；缺省音频锁在开始时冻结。返回candidate/unchanged/needs_revision，无模型请求、作者保存或批准。尚未自动接入网页按钮或替换原模型generate入口；当前完成的是可复用服务和CLI评测链，不宣称正式产品默认已切换。

## 2. 原检查器筛选

每个候选沿原repair.preview_repair，source=ai，复用scope/人工保护/编译/静态容量/音频守卫；不直接写作者。按排名逐个进行原registered全页sampled预览，再立即做原30fps完整输出/动作边界检查；完整通过就停止。最多6次sampled及3次full。sampled通过而full失败继续保留记录并验证后续候选；全部失败回needs_revision，不冒充成功。

传入局部time_range不缩减最终验收，服务固定整页time_range_ms=None。基线检查本身也使用完整30fps；正常页通过后无操作。结束再核对作者没变化，候选持有原candidate_key/request，未来另行显式save还须原门禁重验。新owner已加入生成源码闭包，无数据库/Agent接口迁移，无新增下游写入/失效理由。

## 3. 扩样与数据

完整最终证据`outputs/geometry-expanded-20261020-v3/geometry-summary.json`，可视报告`report.md`。CLI：`python scripts/evaluate_geometry_repair.py --source-run runs/ec60bbd4_010236 --output outputs/全新目录`。默认就是无provider的隔离实验，输出必须新建；原资源拷贝沿现有受限基准owner。

| 分组 | 样本 | 结果 | 中位耗时 |
| --- | --- | --- | --- |
| 真实原故障页 | 2 | 2/2候选完整通过 | 13.117秒 |
| 同内容受控扰动 | 4 | 4/4候选完整通过 | 15.692秒 |
| 正常/已修复页 | 2 | 2/2保持unchanged | 4.6115秒 |
| 范围不支持反例 | 2 | 2/2正确needs_revision，不算修复成功 | 5.147秒 |

不是10个独立课程；只有两张独立故障页，4个扰动只是标注初始Y±12px、卡片初始宽±16px。正常页和能力反例不得算入修复成功率。所有候选/失败记录保留，provider_calls=0。

原第一页15.292秒，标注下移64px，文字1→1行，保持figure内；633时点完整通过。原第三页10.942秒，卡片宽630→486、不移动，正文2→2行，最小外部卡片/图表盒间距20→20px；606时点完整通过。两页终帧已实际查看，箭头/文字指向保持。标注页的盒间距指标为0来自原image对象包围盒交叠，不应解释为文字碰撞；它不是审美度量。human_visual_acceptance仍pending_review，frame_complete=true不表示continuous_time_verified。

label-down12中一个候选sampled通过而full失败，随后候选完整通过，证明粗筛没有代签全帧验收。最终六个故障输入全部preserved=true；原作者/音频/批准/生产数据库不改。source_unchanged/code_unchanged均true，工作树指纹`343776c5fcb21ce3d11990b9eff8d29526b27d1a063366e95496101b30c7d602`。最后补缺省音频锁属于运行结束后变更；最终实验每次本已明确携带同一音频锁，不反签历史指纹。

历史v1尝试的横向标注靠近边缘，v2容器边界修复后的卡片下移导致底栏间距压缩，都保留不覆盖。v3有限增加仍在比例内的宽度候选，得到不移动卡片的通过方案。没有按课程/节点ID写算法特例。

与此前同原图表页真实模型Legacy224.043秒/Pi272.192秒相比，当前几何10.942秒仅作历史量级参考；方法、候选和机器负载不同，不是随机重复速度因果对照，不合并分母。没有追加模型或重复unknown请求。

## 验证与交付边界

48项相关回归通过，45.40秒，`.tmp/geometry-regression-v3.log`；最后8项几何/音频专项复核通过，0.66秒，`.tmp/geometry-audio-final.log`，重复项不累计。覆盖确定性/绝对值/范围、容器、尺寸比例、输入不变、原人工保护拒绝、sampled不能代签full、6/3检查预算、全页范围、正常无操作、过期音频拒绝。Ruff和git diff --check通过；canonical quick通过、退出0，`.tmp/geometry-quick-v3.log`。最后音频缺省锁不改变本轮显式音频请求，已单独复核。不引用旧2775项全量为本批结果。

按code-review-and-quality检查：预测/验收owner分离，原保护/保存权威保持，候选数量及数值搜索有界，正常页/失败不修改作者；有限尺寸下文字重排仍由原容量硬检查；实验失败/原页/扰动/反例分母分开。新增内部服务不读取密钥或调用provider，不复制运行材料到Git。

后续可将该内部策略接入原候选入口做可见预览，再扩充独立课程、多对象冲突/其他模板；超出当前能力交回原模型或人工，不自动重试或审批。本批未启动正式服务、提交或推送，源码同步两处本地目录，outputs只留实际应用目录。
