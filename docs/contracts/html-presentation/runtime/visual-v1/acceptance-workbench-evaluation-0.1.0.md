# 逐项验收、诊断、内嵌定位与配对评测 0.1.0

2026-10-25，HPS-007/009—030/037。接续P0/P2，授权五项开发及验证。

1. 69项验收：每个AC独立规则包含原criterion/hash、required_level、明确检查选择器/命令、必需证据层级。校验器只读，不执行证据中的命令；严格校验唯一个体、源码/规则/证据hash、完整JUnit选择器与跳过/失败。工程层通过不代替model/human/release。证据不足为pending，损坏/过期为failed；任务级文件名不能签发AC。
2. 诊断：版本化错误码表区分capacity/geometry/resource/reference/budget/unknown/incomplete，保留目标、part、原测量、量纲和来源。未知码不进自动修复；no_fit与预算耗尽不合并。不改变原QA判定。静态、逐帧及本地修复入口共用投影，前端提供对应入口说明。
3. 定位交互：复用原workbench渲染器，在原图拖框、选择部件/容器、填写实际转录和身份；显式应用与提交。沙箱frame通过仅绑定本frame/window、会话hash和通道nonce的postMessage传递修正；原POST恢复合同及服务端完整性检查保持。可选JSON导出/导入兼容。主面板无需下载JSON即可提交，切页/过期消息无效。原图数据仅经已授权workbench响应进入沙箱，不新增文件读取接口。
4. 评测：固定dataset及gold/source hash、course/split、标签版本，训练/开发与留出不得内容重复；不可用测试数据调参。配对比较严格覆盖每个case/repetition/arm；失败/unknown纳入分母，单独报告定位、保真、工程成功、时延、usage/cost未知null。测量不由外部pass字段推断；真实质量必须有实际请求/图像/返回回执及独立人审。默认只读离线评分，零供应商调用。
5. 布局：以现有宽卡片、网格溢出案例新增明确注册的宽正文双卡片和三列对比结构；原文字与语义动作不变，复用原card/header/summary。多列下游summary位置提案不超过4对象，scope/protection/full30fps仍由原守卫执行；越界、长文无解显式停止，不放宽字号下限或自由CSS。

完成条件：逐项规则完整69/69及损坏证据负例；逐码/单位/未知码负例；真实浏览器主面板拖框→应用→原POST，错误会话/窗口/旧消息被拒；固定配对评测的分母/留出/unknown/费用/hash负例；新布局normalize→语义设计→compile→原静态与全帧QA、长文/越界和人工保护。兼容旧候选读取与导入，源码变更使旧证据按原hash失效，不迁移为当前通过。不触发作者写入的开发工具不产生下游失效；实际保存仍走原失效链。
