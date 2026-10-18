# 保留设计图的关系端点修复 0.1.0

契约0.9.91，Agent API1.49 / produce1.12，HPS-011/013/015—017/023—030/037。定义先于实现。

原reuse_design_candidate_key默认仍零模型调用、原计划内容不变。新增可选repair_relation_points说明必须与该key配对，禁止与接受、设计修改、素材返工或未知重发混用。仅适用0.2.0语义计划，只修原计划既有显式point关系的from/to归一化坐标；不改端点对象ID、节点、正文、图表数据、模板、动作或源合同。存在人工编辑覆盖时拒绝。

先验证原图、候选、参考包、合同、模型和revision；模型只消费该图、原关系/端点对象box及相关语句和表达，单次600秒请求，无自动重试，不生图/TTS。响应必须逐项覆盖所有可修关系，拒绝重复/未知ID、非有限/越界点与额外字段；用原normalize/A02再次验证。无变化不另存候选。

新参考包绑定修后计划和当前定义，图像字节保持；保留原候选和请求证据，返回新待审key，不继承任何接受或HTML/A04批准，不写作者场景。原unknown不得借此补发。能力变化进入Agent/Skill和原任务、源快照、恢复及定义身份闭包。

验证需证明只有坐标可变、图像不变、无生图/TTS/作者写入、坏响应阻断、人工覆盖阻断、正常复用仍零模型调用、新key待人审；离线结果不代替模型和语义验收。

## 0.9.92：视觉就绪与文本绑定刷新

发起端点修复前，冻结的项目text模型必须明确supports_images=true；否则409 HTML_VISUAL_MODEL_REQUIRED，零供应商调用。图像生成模型不改变，planning可单独保留原文本规划模型。请求指标单列relation_point_repair，不按普通文本规划统计。原unknown错误必须原样保留，不被复用错误遮盖。

显式复用可在图片模型摘要完全相同且其config_hash有效时刷新text/planning及binding_revision：原计划仍须原样通过normalize/A02；保留source_model_summary来源，新候选使用当前模型且仍待人审。任何图片模型变化、未知摘要字段或缺身份都拒绝。此规则不接受旧设计、不迁移未知请求，不修改原记录。

## 0.9.93：首次输出接口

Prompt relation-point-recovery/0.1.1在首次system消息提供完整严格输出Schema：唯一顶层changes数组，每项objectId/fromPoint/toPoint，各点仅x/y。共享适配器的schema_hint只供JSON语法恢复，不能替代首次消息。关系ID顶层映射继续拒绝，禁止在离线诊断中偷偷转换成有效生产结果；原请求预算、记录及接受边界不变。
