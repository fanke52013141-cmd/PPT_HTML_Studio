# 共享呈现细节与GLM截图审阅交接

2026-10-14，D:/software/PPT_HTML_Studio。承接设计Agent七项差异与GLM模型分流。本轮完成下一批共享能力，未替用户批准旧设计、音频或作品。前一轮模型绑定本地改动保留，均未提交推送。

## 实现

- 新增text-card-label：主题灰阶圆形SVG底托，原文字首个冒号之前粗体、正文常规；原run/文案/ID/动作不变。注册最小尺寸和真实文字预算。
- 新增summary-relationship-panel：已有主题灰阶填充、三分区与两竖分隔、伸展SVG长箭头、原term置于下方；各公开文字部位独立测量。新增check-plain，不改旧check图案。原text-card-outline/soft和summary-panel保持。
- 场景仍0.7，新增注册ID通过原set_variant/set_text_style执行，无新编辑权限或自由CSS。图标适用性按统一注册元数据验证，理解先应用变体；不足尺寸的未保存初稿可进入diagnostic截图，但正常审阅/保存严格拒绝。
- 规划图标读取兼容带引号的连字符ID；修正旧8图标测试清单为实际12个明确注册图标，不放宽未知图标拒绝。
- 定义、Schema、编译器、共享渲染、注册目录、参考映射、构建产物与新夹具同步。定义卡presentation-details-0.1.0，契约0.9.38，注册包0.2；原公共接口与Agent API1.26保持。

## 产物与验证

fixture位于html_engine/visual/fixtures/presentation-details/，包括原scene、通过受保护编辑API应用的operations、新scene、binding及contract。属于工程示例，开发者选择了呈现和参数，不将它冒充模型自动生产。可通过共享预览的JSON编辑器加载scene.json。

本机可看outputs/presentation-details-2026-10-14/index.html、final.png。旧真实参考图与16.776秒配音不在本机；线上Git不含这些运行产物，所以没有原图保真对照或真实音频重验。

浏览器新增6组检查通过：源内容/动作保护、合法图标/格式、真实粗细字重与灰阶圆底、子区域溢出拒绝、旧变体保留和乱序seek像素一致。设计Agent/受控还原/规划接口Python联合28passed。旧引擎14checks/5scenes/pageErrors0。首次箭头受旧SVG宽度规则压缩及超长负例先触发Schema已分别修正；不抬高正文长度上限。新Agent夹具的函数名/status错误已纠正，最终联合通过。

真实GLM-5.3-Flash通过现有生产JSON适配器观察final.png，对七项可见性要求返回pass，耗时15.418秒；原图保真比较未执行，usage/HTTP实际次数/费用未收集，保留null，不编造改善比例。详细去敏证据见evidence/presentation-details-2026-10-14.json；原调用附件仅在上述outputs/glm-review。没有人工批准、TTS或生图；不认为终态截图通过就意味着A04逐句语义通过。

## 下一批

1. 如要与此前模型做同输入保真对比，需恢复原design-reference.png及当时音频/输入；也可另外建立明确标记的新设计研究输入，不能声称等同旧实验。新能力可供Agent选择，后续须实测完整理解→还原→独立原图审核，不手改模型结果。
2. A04仍按原handoff独立实现：真实音频窗口开始/中点/结束帧＋原句＋视觉意图/对象/预期状态，工程/语义/听审/人工分开门禁。
3. 后续A05仍复用原项目任务与恢复/快照/审批停点，不把当前开发验证脚本当成整课调度器。多主体拆分仍独立规划。

补充回归记录：最终旧引擎14项/5场景/0pageErrors通过。此前两轮主题seek截图Buffer不一致的assert.deepEqual展开差异耗尽内存；改为等价Buffer.equals检查并在失败时保存原截图后，能够明确报告neutral-science不一致。之后一次同源码完整运行通过，根因未确认，保持间歇性风险记录，不称已修复渲染器。没有删除确定性断言或放宽像素差异。新增组件独立seek检查持续通过。

2026-10-14 A04 后续纠正：此前“原配音不在本机”的判断来自未搜索 ignored outputs，已发现并复用 outputs/a03-semantic-runtime-2026-10-13-final/run 的真实配音。原图保真比较仍未执行；新增组件终态截图不追认为原图保真通过。A04 已完成逐句门禁及真实正反例，详见 [A04 交接](handoff-a04-2026-10-14.md)，本文保留前序执行时的历史记录。
