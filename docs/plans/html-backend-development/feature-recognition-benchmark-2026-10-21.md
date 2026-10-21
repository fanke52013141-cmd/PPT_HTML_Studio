# 固定参考集与漏检率基线 · 2026-10-21

目标是测量系统是否发现问题，非逐页修复。首批冻结一门水循环课程的3张原设计图和11个对象；模型原请求、原响应、参考图、逐对象标签均逐文件SHA-256封存。数据在本机`outputs/feature-recognition-fixed-20261021/dataset.json`，标签定义纳入`checks/fixtures/feature-recognition-labels.json`。不公开课程运行数据，不含凭证/数据库，不写作者/批准，不调用供应商。

## 标注与两个不同指标

标注由本次Agent实际查看三张参考图后整理，authority=assistant_visual_review，不冒充人工真值或用户设计签收。4个独立插图需求、6个装饰图标负例、1个模糊弃权；云雨图形介于图标与插图间，明确不计入确定分母。标签针对当前参考内容，不把图内语义关系移交图片。未来人工复核或扩充必须发布新标签/数据版本，不修改同一已测清单。

1. **特征声明召回**：目标是否在原模型required_features明确声明independent_illustration。没有声明的完整ready响应为否；缺失/非法/unsupported响应为未决，不扫appearance自由文字猜特征。旧Schema没有此特征选项时整项标为未决，不以缺字段声称100%漏检。
2. **组件能力缺口拦截**：参考明确需要独立插图，而当前目标不是image时为缺口正例；其余确定标签为负例。原ready为未拦截，目标级unsupported_presentation为拦截；其它停止/缺失/非法为未决。拦截只证明目标被停止，不证明模型说对了视觉原因。图标负例和已支持image主体都不应因缺口被拦截。

两指标均输出TP/FN/FP/TN、正负未决、确定判断漏检/误报率、全部正例上的确认召回和“漏检或未决”比例、判断覆盖率；分母为0返回null。模糊项弃权不计入确定分母，未知结果不消失。archived_model、controlled_fixture、new_model_capture分别统计，标注权威分别统计，不将同课对象当多门独立课程。

## 历史真实响应基线

采用冻结的原设计理解响应回放，无新请求。最终有效结果在`outputs/feature-recognition-baseline-v2-20261021/summary.json`；数据集hash为`aafd793d6c648ea6b083935a233e2ab96a3e0eeb7103231cdc7657742ffeeb6e`。较早baseline目录保留初始指标探索，尚未区分旧Schema是否请求新特征，不能用于正式结论；v2纠正了这个口径。

| 指标 | 结果 | 解释 |
|---|---|---|
| 能力缺口拦截 | TP0、FN2、TN8、FP0、未决0 | 两个缺口都在第4页的场景卡片，原模型均ready |
| 确定判断漏检率 | 2/2 = 100% | 仅历史响应、这一批目标，不是系统总体漏检率 |
| 确定判断误报率 | 0/8 = 0% | 含六个图标与两个已有image主体负例 |
| 特征声明召回/漏检率 | 未决10；确定漏检率null | 原Schema不含新特征，不能公平比较新字段召回 |
| 模糊项 | 1项排除 | 第4页云雨图形，保留理由与原图 |

3张页均来自同一课程，两个缺口正例均来自同一页；证据高度相关，不能推断跨主题/跨模板泛化。新Prompt0.7.3的真实漏检率尚未测量。该集合用于诊断/开发，已经曝光给优化过程，不能宣称独立留出测试集。

## 工具与复测

`scripts/evaluate_feature_recognition.py --dataset <dataset.json> --output <新目录>`默认且仅支持文件评测，复用原Understanding严格Schema，不启动服务或提供商。检查图像与原请求附件hash一致、标签目标存在、路径不越界、每项证据hash一致；输入改变或旧输出目录均拒绝。结果保留逐对象预测与理由；测试替身不得混入真实模型分母。

新增新模型响应时，保留同一参考图、目标和标签，另建new_model_capture数据集及新输出目录；记录实际运行片段、模型配置摘要、响应和未知结果。标签不得送入模型。原schema与新schema差异单列。供应商调用需沿原理解入口和有界预算执行；本次没有自动发起实时评测，也不重发已有unknown。

验证：计分器10项及现有系统诊断5项共15 passed（1.05秒），覆盖未知/模糊分母、旧Schema公平性、特征声明与阻断区分、所有证据哈希、越界、旧输出拒绝、非法/缺失响应。最终加入原facts回归共34 passed（0.88秒）；全仓ruff、Agent契约同步及git diff --check通过。本批只建立并测量历史基线，没有改变生产Prompt或修复作者。

## 同图同标签新版真实复测

用户随后授权直接比较。通过原`understand_design`入口运行当前理解片段0.7.3，对比归档0.7.2响应；使用项目绑定的glm-5.3-flash和原适配器（600秒、low推理、流式）。三页均从原candidate plan重新编译，验证原scene seal及对象完全相同，图像和标签逐文件hash不变。变化包含理解Prompt、组件能力事实和输出Schema，属于新版整体对比，不是单一Prompt变量实验；历史基线是归档响应，未重新调用旧版，也不是多次随机性试验。标签仅由计分器读取，未送模型。

实际3次HTTP、3次理解决策全部返回，无结构修复、无unknown、无补发，合计模型决策耗时30.991秒；无新图、无作者写入、无批准。供应商usage/费用未采集，不能写成0；离线计分器summary中的provider_calls=0仅指计分环节。三个新响应分别ready、ready、unsupported。原始响应独立封存，未用系统校验转换后的结果代替模型输出。

| 固定标签上的指标 | 历史0.7.2 | 新版0.7.3 |
|---|---|---|
| 能力缺口拦截 | TP0、FN2、TN8、FP0 | TP2、FN0、TN8、FP0 |
| 确定漏检率 | 2/2 = 100% | 0/2 = 0% |
| 确定误报率 | 0/8 = 0% | 0/8 = 0% |
| 缺口判断覆盖 | 10/10 | 10/10 |
| 显式插图特征声明 | 旧Schema不适用，10未决 | TP0、FN2、TN6、FP0，正例未决2 |

新版原模型已对obj-stage-2/3给出unsupported_presentation/capabilities，证据明确指出独立场景插图不能由registered_icon_only卡片替代；因此本批确实改善了缺口发现。它也拦住模糊的obj-stage-1，但原固定标签仍弃权，不能事后改标签记作正确。六个装饰图标与两个已有image主体都未被误拦。

仍有缺口：两个已有image主体未显式声明independent_illustration，按预定口径算FN2；unsupported页两个正例没有对象分配表，特征声明记未决2，不能从自由文字补成TP。新版特征声明确定判断漏检率为2/2，确认召回为0/4，覆盖率8/10；这与缺口拦截改善是两个独立结论。后续优先验证声明完整性，并扩充未曝光的跨课程样本；本批一门课程、正例集中一页，不能推广为总体0%漏检。

封存新输入/响应：`outputs/feature-recognition-new-20261021/dataset.json`（hash `cebb61039067a920fee7692837b38ce7a4c6493d1a73dcb6cd86b1b0a300ef3b`）；同分母配对核验及调用摘要：同目录`comparison.json`、`capture-summary.json`；同一计分器新结果：`outputs/feature-recognition-comparison-new-20261021/summary.json`。本次计分器与系统诊断回归15 passed（0.74秒）。本节追加真实复测，不改写上方历史基线和当时未测状态。

## 逐对象观察优化与最终复测（理解0.7.5）

根因：旧协议unsupported必须清空objects，导致同页其他观察无处保留；已有image虽然有素材分工，却仍可省略required_features。现将看图事实与分工独立：新请求必需feature_observations，对每个输入对象明确present/absent/uncertain及短证据，两种分工状态均完整返回。原Understanding保持历史读取兼容，出站ObservedUnderstanding及原理解入口强制完整；程序从明确present和实际组件事实派生能力缺口，原表原响应不改写。不确定保留hash并停止核验，不能自动重试或算作absent；缺/重/未知对象及矛盾声明才沿原一次结构修复。未增加业务阶段或模型参数额度。

观察范围必须属于对象自身承担的内容：已有image承担的照片不能重复认领为外框、标题或标注的独立插图；没有其它输入对象承担的卡片场景仍应识别。0.7.4第一轮虽在固定标签内TP4/TN6，却把第3页figure外框也标present，系统误拦该页（不在11个原标签内）。该失败独立保留在`outputs/feature-recognition-observed-20261021/`，不混入最终版分母、不补改原标签。该轮3页4次HTTP，第4页额外notes字段触发原一次合法结构修复。不能凭原标签内零误报忽视完整响应中的新缺陷。

0.7.5增加对象自身/图片容器归属及严格顶层字段规则后重新真实测试。同三图、同原对象与scene seal、同固定标签hash；glm-5.3-flash、600秒/low/流式和原项目绑定保持。3次HTTP/3次决策均正常返回，无修复、无unknown；前两页ready，第4页unsupported。总计两轮7次HTTP，最终轮决策47.213秒，usage/费用未采集为null；没有作者、生成新图或批准写入。

| 同一固定标签上的指标 | 上一版0.7.3 | 最终0.7.5 |
|---|---|---|
| 显式插图识别正例 | 声明0/4，含FN2与未决2 | 观察4/4，FN0、未决0 |
| 图标负例 | TN6、FP0 | TN6、FP0 |
| 确定目标观察覆盖 | 8/10 | 10/10 |
| 系统派生能力缺口拦截 | TP2、FN0、TN8、FP0 | TP2、FN0、TN8、FP0 |
| 原模型严格typed缺口声明 | TP2，未决0 | TP0，正例未决2 |

两种显式识别协议不同：0.7.3读取required_features，0.7.5读取独立观察表；计分器仅采纳显式机器字段，不从外观自由文字推断。用同一新版计分器重放0.7.3结果在`outputs/feature-recognition-v073-rechecked-20261021/`，原分数未改变。完整新观察38条（16/11/11），固定标签仅11条且云雨1项仍排除；没有为了得分改变gold，也不把其余27条未经固定标注的观察宣称全部正确。第3页figure最终为absent，未再误拦，但尚无独立冻结容器标签，只能记本例修正证据。

必须区分系统与原模型：0.7.5原模型虽明确看出插图，但第4页三个问题requirement写成asset_identity，严格原模型typed-stop指标仍有2个确定正例未决，不能记成原模型TP。程序依据present观察和注册能力独立追加unsupported_presentation，正确提前阻断；报告保留原问题分类与派生问题，不以转换后的结果冒充原响应。这说明观察完整性已在本开发集改善，模型问题分类一致性仍待优化。

最终封存：`outputs/feature-recognition-observed-final-20261021/dataset.json`，hash `9eea529ccfd73f73cffebbb1c2642286579a47f4ffcdf03f08a284469f25a224`；同目录`comparison.json`明确原模型/系统分母、同图同标签同对象以及当前代码重验与原运行记录完全一致。原计分结果在`outputs/feature-recognition-observed-final-score-20261021/summary.json`。一门课程开发集、单次版本响应，未验证跨课程或重复稳定性；下一步应扩展未曝光样本，并在新标签版本增加容器/标注归属负例，保持原集不可变。

实现验证：新增观察/覆盖/冲突/uncertain及修复后uncertain/历史兼容/严格Schema/计分不缩分母与错误类型派生回归；相关108项运行107通过，1项因执行期间片段升级正确触发RUNTIME_SKILL_CHANGED_DURING_RUN，冻结后单独重跑通过（15.34秒），未放宽来源保护。最后的小范围新增用例结果见下方补录；本机应用未重启，当前CLI加载的是新版源码，未提交/推送。

最终补录：包含错误requirement命名仍由观察派生能力缺口的新增回归，观察/计分/系统诊断相关28 passed（1.55秒）；全仓ruff、Agent契约同步及git diff --check通过。测试数有重叠不累加为独立覆盖数；只修正观察协议、原能力判定与诊断，不变更渲染器或作者数据。

## 跨布局受控标签版本 0.2.0（2026-10-21 追加）

已测 0.1.0 集保持不变。新增受控夹具 `checks/fixtures/feature-recognition-controlled-v0.2.0/`：
两页不同布局的确定性示意图（卡片+主体；figure 容器包围主体+云雨装饰），请求对象/能力表由真实场景结构生成，
标签 authority/provenance 均为 `controlled_fixture`，**不是真实课程页、不是模型输出、不是人工签收**。
计分器支持 dataset/labels `0.2.0`：逐目标 `ownership ∈ image/container/icon/annotation/text/ambiguous`，
模糊项必须 expected=null 且给出 `ambiguous_reason`；0.1.0 输出字段保持不变。

数据集 hash `d24ec48df0439b74815054f80daa9395c6b0928ad18ad5ad175472c2325606af`，2 个布局/2 页，
21 个确定目标 + 1 个模糊弃权。B 页响应故意复现 0.7.4 的 figure 容器误认，用于证明归属负例会计入误报：

| 指标 | 结果 |
|---|---|
| 总体 | TP2、TN18、FP1、FN0，模糊弃权 1 |
| image（插图归图片） | TP2、FN0、未决 0 |
| container（容器不得重复认领） | TN1、**FP1**（受控复现 0.7.4 误认） |
| icon / text / annotation | TN5 / TN10 / TN2，无误报 |
| ambiguous | 排除确定分母，原因原文保留 |

工具：`scripts/evaluate_feature_recognition.py --dataset <dataset.json> --output <新目录>`；
v0.2.0 会校验标签版本、ownership 取值、模糊项理由，并输出 `by_ownership` 与 `ambiguous_reasons`。
验证：标签/计分相关 13 passed。

必须保留的边界：这些都是受控夹具，只证明计分器与归属分母可用，**没有任何真实模型或真实跨课程泛化结论**。
真实未曝光课程页仍需另一台电脑按图片/对象/标签 hash 封存移交，再按 0.2.0 标注；不得修改已测 0.1.0 清单充数。
