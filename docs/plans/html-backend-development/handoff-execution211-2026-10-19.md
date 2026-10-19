# 执行2.1.1能力与交付修订

本地契约0.9.102/API1.55.1，能力hash为`1955ba5626df4f5b`，由`scripts/generate_agent_contracts.py`同步。未提交/推送、未换生产服务、未签发新外部任务。

## 起因与归属

输入2.1真实回传的148px/-39/22px局部方案在隔离副本通过原DOM、80个有限采样时刻和指定4组遮挡检查；该Agent声明不能看图，却因EXECUTION的“纯参数候选可交接验证缺口”旧泛化表述提交proposed，严格导入按必需能力拒绝。
任务goal/ENTRY和结构化required_abilities已明确硬门槛；执行有误，规范也有可消除歧义，不能为接受单例降低门槛。原ZIP和复核证据保留，不把主机工程成功算作外部自主成功。

## 修订与实施

- 正式所有者为`external-agent-workbench-0.1.0.md`的执行2.1.1勘误，关联HPS-001/007/009/010/013—018/023—030/035—037；ENTRY/EXECUTION/原2.0卡/README/报告模板同步。
- decision-input同源增加verification_required和required_abilities。入口先检查必需能力；缺能力返回needs_input/unsupported、operations=[]，不能用not_run/proposed或人工工作区绕过。
- 既有能力false拒绝保持，要求看图的严格候选新增baseline_visual_review=self_checked与非空证据记录完整性检查。不能证明模型真的看懂，真实外部/人审独立。
- 没有原预览接口时DOM/指定遮挡/after可not_run/unknown，仍可由原系统接续；不豁免原图理解。未要求看图且目标无需视觉判断的纯参数任务保留兼容。
- 本轮manifest及存在的trial-manifest必须核验；不与旧答案混淆。停止交付仍有三个主文件，不要求伪造预检/after。报告不把局部方案写成全局唯一可行域。

## 兼容与后续

task/result JSON0.2、verification1.0与0.1 SDK保留；export0.4.1/preview0.5.1，API1.55.1。无DB迁移、声音/renderer/业务失效改动，无付费调用。
规范/源码与能力hash改变使旧签名任务不再当前，必须从当前作者状态重新导出；不重写旧试验ZIP、不更改旧result的task_id、不迁移旧批准。
需要后续真实验证时，用有实际看图能力的Agent和新输入包；如要支持无视觉Agent，应另外定义目标/能力/人工验收责任并重新签发，不能回填本次能力声明。

## 验证记录

- 相关任务包/便携预检/严格交付/人工工作区/Web及Agent路由73项通过；新增8个场景覆盖缺看图能力、缺预检能力、原图未审/证据空白拒绝，合法停止留档但不采用，以及明确非视觉任务允许not_run。
- 其余Agent接口/CLI/MCP/合同同步443项通过；快照/编辑器夹具/真实浏览器导出导入保存15项通过，共531项。测试使用隔离临时数据，不调用真实供应商，不代表新Agent实际看图已验证。
- Ruff、能力矩阵同步、Git空白检查通过；最终正式卡工作区边界措辞复核后，单项任务包封装校验重跑通过（不重复计入531项）。
- 原输入2.1及用户delivery ZIP不改写；本轮不发新任务、不改变真实作者页、音轨或批准。
