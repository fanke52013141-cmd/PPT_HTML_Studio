# 重叠判定修复与真实课程复验 · 2026-10-20

目标是准确区分斜线外接矩形误报、合法关系端点接触和实际穿字；不是修改原课程以取得全绿。
基于main 00fb81d4及此前未提交优化，当前原应用源码目录为`D:\Program Files (x86)\PPT_HTML_Studio`。

## 实施

- 新增纯几何owner `html_engine/tools/vector-overlap.cjs`。读取同帧实际SVG path/变换/笔画，支持原renderer的线性路径；做完整线段交集与距离检测，不用空间稀疏抽样，也不再把整块斜线外接矩形当成涂画区域。
- 原temporal-review.cjs提取实际文字Range矩形；图表文字标明chart:min等来源。箭头通过任何对象的文字区域仍阻断；未支持的图元沿用保守矩形，不使用新端点豁免。
- 根据原scene显式from/to和同帧renderer端点，识别连续进入自身端点对象非文字区域的接触。原对象对、模板排除清单均保留，合法接触单独记录relationContacts；其他对象不能借用该规则。
- 箭头头部按原renderer短线段几何约束处理源容器边界回跨，线宽也进入安全区检测。箭头相互交叉采用线段距离，平行或未相交线条不因外接矩形相交误报。
- helper加入原生成快照源码闭包，并在snapshot QA执行前后与报告校验固定hash；修改helper或伪造其身份会使报告失效。
- 基准工作树身份包含Git可版本化的未提交新文件，避免新helper未提交时被漏出实验指纹。

合同包0.9.109、Agent API1.59.0；定义在[SVG重叠判定](../../contracts/html-presentation/runtime/visual-v1/vector-overlap-0.1.0.md)。作者Schema、音频、人工保护、批准、数据库和模型预算保持。

## 真实隔离复验

原课程scene/binding/音频未修改。已保留v1/v2中间结果；最终采样证据为`outputs/overlap-linear-20261020-v3`，30fps为`outputs/overlap-linear-30fps-20261020-v2`。
每次检查source_unchanged/code_unchanged以对应summary为准，CLI completed不代表每页通过。

| 页面 | 旧矩形法250ms记录数 | 新线段法250ms记录数 | 新法30fps时点/穿字记录数 |
| --- | --- | --- | --- |
| slide_001 | 1170 | 36 | 633 / 162 |
| slide_003 | 43 | 43 | 606 / 298 |
| slide_004 | 0 | 0 | 501 / 0 |

这些是跨时间重复记录，不是独立问题数量。剩余集中在两组：第一页obj-relation-2经过obj-anchor-label说明文字；第三页obj-relation-1经过obj-chart的chart:min坐标文字（-10刻度）。已实际查看过图表截图，不能因为该箭头指向图表而豁免图内文字。
第三页的目标非文字接触已单独留证，穿字仍如实失败；三阶段页逐帧通过。
30fps frame_complete=true仅表示该帧率全部输出时点及额外动作边界，不表示连续时间数学证明、听审或人工批准。

## 验证

真实浏览器正反例：0.5x舞台下的斜线空白区域、合法非文字端点、同位置穿字、非端点对象、路径越界；全部通过。纯几何覆盖相对/隐式路径、旋转变换、箭头平行/交叉、容器接触与未知曲线回退。
snapshot回归新增helper身份防篡改；最终专项40项通过，耗时55.98秒，日志`.tmp/overlap-final-tests-v2.log`。
全库canonical quick正在单独检查，终态另补，不把本批专项当作全量2775项结果。

本批未调用模型、未重发旧unknown请求、未改写或批准原课程，未提交/推送或启动正式服务。

## 下一步

重叠规则已能保留这两组实际穿字证据；接下来应在候选中调整关系端点/路由，保持所指对象与原语义、音频不变，再做同帧率复验。不要新增模板白名单掩盖问题。箭头曲线和复杂填充仍属保守回退范围，扩展时需另补定义与验证。

## 入场边界复核

首次30fps版本另外出现7条非文字接触记录：原renderer在绘制进度>99%时已绘制头部，但头部还未到最终to坐标。现按与原from/to一致的当帧主线进度和实际尖端验证短头部，新增99.5%进度正例与脱离主线的头部反例。v1证据保留不覆盖；最终v2只剩162/298条文字区域冲突，三阶段页0条。

最终30fps副本source_unchanged/code_unchanged均为true。全部原音频/作者保持。canonical quick前轮已通过，最终同范围复查日志`.tmp/overlap-quick-final.log`，终态完成后追加。

canonical quick最终执行完成，退出0，All requested checks passed；Ruff与git diff --check通过。代码质量复核确认：原检查器持有调用，新helper只做纯几何；路径解析有长度/数值边界，未知图元保守回退；helper已进入快照和报告身份校验，没有增加依赖或人工批准路径。
