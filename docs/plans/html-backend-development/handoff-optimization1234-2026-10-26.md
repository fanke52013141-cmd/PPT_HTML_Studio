# 还原优化1—4与验证交接（2026-10-26）

基于8aa5695，保留同会话目录换行修复。用户授权推进工程缺口、真实样本、定位评测和按实测优化，并选择优先本机课程。本轮是确定性修复与评测工具加固，不是1—4全部真实验收完成。

## 实现

1. html_capacity_repair.py原候选生成器在16项上限内按target/part/操作类别稳定轮询；修复首个文字部件的长字号梯度挤掉正文和行距候选的问题。原24px下限、scope/manual、原编译/完整30fps检查与预算停止保持。
2. html_paired_evaluation.py要求located部件状态一致；多行匹配从递归穷举改为增广路一对一匹配。汇总增加配对改善/退步/双方正确/双方错误/不可比较计数及完整分母返回率、unknown率、定位正确率、耗时观测数。无效/unknown不算改善；不推测费用或批准。
3. 既有prepare_reconstruction_dataset.py保留prior_exposure声明，增加--audit只读就绪报告，默认24页/3课程、开发/留出齐备、留出声明未曝光及原hash/标签结构；未就绪退出1。审计只核验声明与结构，不能认证独立人审。
4. 原统一验收入口补全原生产全帧、执行计量、设计Agent及生产恢复组；未更改69项规则完整性、required_level或supporting覆盖声明。

HPS-007/009/010/013/015—018/023—025/030/037的兼容补充已记入原验收定义、contract-index及CHANGELOG。包0.9.118/API1.64.0保持，无新增HTTP或数据库字段。旧实验按源hash过期，不续签或重发unknown。

## 可复现前后对照

outputs/optimization1234-20261026/before-after-controlled.json使用同输入和Git基线：

- 容量候选同为16项；原仅覆盖title的font/line_height两类，现覆盖title/body各font/line_height共四类。
- 部件声明ambiguous但带坐标的反例：旧离线评分correct=1/1，现0/1。属于受控评分缺陷修复，不能换算真实模型准确率。

## 本机真实样本

原图hash去重后3门课程5页（Token、水循环、遴选），按文章hash归并课程。仅使用实际reference.png及allocation-applied.json场景，保留原来源和hash，未修改原run或作者。

草稿位于outputs/optimization1234-20261026/real-dataset-draft；来源local-sample-origins.json，准备spec和原字节副本同目录。5页全是已曝光、未批准的历史候选，全部development。labels为pending_human_labels，未从HTML坐标填gold。

readiness=false：不足24页、缺未曝光留出课程、缺人工标签。CLI退出1实测。目标还缺至少19页；已有页不能改名充当留出。未调用真实模型，也未生成任何人工复核身份或批准。

## 验证

- 扩展定向回归33项通过；组间重叠，不与统一包相加。
- 统一7组252项通过，容量4例与关联布局6例真实浏览器受控基准全部通过。封存运行前后源一致，final-reverify为passed=true/errors=[]。
- 旧容量/候选Agent回归14项通过。
- canonical quick全套通过；其中既有AI Mask基准7项skip保持skip，不用于本轮完整验收。
- 无其他验收负载时Agent全套519项通过，93.50秒，1条既有Starlette弃用警告。
- catalog检查41文件current；Ruff定向和Git空白检查通过。
- 逐AC校验13 passed、0 failed、56 pending；AC-056因原计量测试加入封存执行补齐，未提升其他supporting。--require-all预期退出1。账本与执行清单同步。

全部本机日志在outputs/optimization1234-20261026，manifest封存源码/JUnit/浏览器报告，不提交运行数据。未推送、部署或重启正式服务。

## 仍未完成

1—4不能整体签收：24项工程缺口本轮仅新增AC-056完整证据，仍有23项待逐条完整覆盖；新三对象测试是受控逻辑验证，不能替代原全部真实浏览器极端矩阵。真实课程扩样、原图人工标注/独立复核、真实0.5.0/0.5.1定位配对及模型效果优化仍待对应证据。优先用现有5页完成原图标签并增加未曝光课程；实验经原项目工作台/模型/预算/回执入口，不绕过sealed_dataset或自动批准。
