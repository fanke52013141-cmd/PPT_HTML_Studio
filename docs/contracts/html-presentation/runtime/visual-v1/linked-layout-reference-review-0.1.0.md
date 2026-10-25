# 关联布局与独立原图保真审核 0.1.0

2026-10-25；HPS-007/009—013/015—018/023—025。内部实现增量，包/API版本及作者/批准权限保持。

## 生产修复

`html_linked_layout.solve_production_layout` 在未保存候选上复用累计容量求解；静态合格但原完整动态检查失败时，可以继续关联布局或显式 point 端点路由。容量阶段此时返回 needs_revision/GEOMETRY_REPAIR_REQUIRED 和不可保存的中间候选，不把中间状态签发为通过。

- 关联布局按注册槽位识别同一列的 2—3 张 card 及其下方一个 summary，最多 4 个对象；保留原顺序、文字、尺寸、横向位置，只将冲突后的行向下推到合法间距。超安全区、不属于该列或缺空间不生成提案；不宣称支持任意网格重排。
- 关系避让复用原 propose_endpoint_routes 和完整动态报告，只改已声明 point 的附着点，不改 objectId、anchorId、方向、文字或动作；原候选操作/人工保护校验仍执行。
- 默认几何阶段至多 8 次完整检查、120 秒共享浏览器预算；容量阶段仍有自己的有界预算。未声称全任务共享模型/浏览器预算已完成。
- 只接受当前 raw_report_sha256 对应的原动态证据；缺失或变化即停止。候选始终重新运行原严格静态与作者时钟、30fps/registered、全输出时段/动作边界检查，不能用预筛通过代替。
- 原新页编译后、组件分配后两个入口，及还原操作后第三个入口均复用该所有者。第三个入口不增加模型修复轮数；失败仍走原剩余反馈/停止，不自动批准。
- 原 repair_candidate 的直接调用默认保持旧模式；内部 deterministic_first 入口在 candidate/unchanged 时直接返回，通过之外继续保留原模型回退，blocked/stale 仍阻断。

## 原图定位与证据

生产还原后的保真审核启用 localized_reference；旧 direct review_fidelity 默认、旧同坐标窗口实验及原 1.0.2 片段继续可读。

1. `localize_reference` 仅接收参考图、准确 targetId/身份/文字路径、原图尺寸；不接收 HTML 几何。生产首版定位范围为 text/header/card/summary/label/badge。图片主体、关系、figure 等仍由整图审核，不冒充已精确定位。
2. 文字身份增加 body、tag/note 的文本路径；普通独立调用的 arrow 端点身份只含 objectId，不泄漏当前 point 坐标。定位仍按原严格逐文字片段、容器、范围和转录校验；这只证明结构合法，不证明识别准确。
3. 参考区域使用独立定位框，HTML 区域使用原实际对象框；按 ID 配对，记录裁切范围、归一化中心差、部位和未决项。两侧范围/缩放可能不同，不凭缩略图尺寸认定字号或比例相同。
4. 两张完整图始终保留，至多追加两张重点对照板（最多八对）；其它对象明确标未选入局部板，整图仍覆盖其审核责任。单张板小于现有像素预算。
5. 所有定位框保持 model_proposed_unverified，不能变成作者坐标。ambiguous、not_found 或当前 HTML 几何缺失会进入 evidence_review，保留证据、零自动重试，不自动推断为素材缺陷。
6. 同参考 hash、同准确 targets hash、同定位运行片段身份时可复用定位；新的候选 scene hash 通过明确的同目标派生记录关联，保留 source_scene_sha256。内容、作用域或定位版本变化必须重新定位，不沿用旧对应关系。

## 审核协议与计量

新增可信片段 `design-fidelity-review/1.1.0`，阶段 design_fidelity_review_grounded、输入 design-review-input/0.4.0；输出仍是严格 design-review-facts/0.1.0。稳定规则说明整图/局部图角色、独立定位的证据边界、未定位类型、禁止自动套坐标和不确定处理。原事实覆盖、差异分类、连续问题保留、语义/资源路由及人工审阅边界不变。

定位是单独的模型决策，正常路径每组冻结目标一次，后续同目标复用；不静默增加原共享模型预算，超预算依原任务守卫停止。定位请求用 reference_localization 单列计量，usage/费用缺失保持 null。

运行片段及注册 hash、Python 实际消费者、关联布局与几何/定位证据所有者进入原设计/生成来源闭包。相关来源变化按原规则重验，历史批准不自动升级。无新公共 HTTP 请求字段或数据库迁移。

## 验证边界

`test_html_linked_layout.py` 用原真实浏览器验证列联动、point 路由、人工保护；`test_html_design_reconstruction.py` 验证第三检查点实际恢复容量并接续原审核；`test_html_independent_review.py` 验证独立负载、错位配对、缓存/身份变化、未决停止和内容完整性。定位/保真响应替身只证明调用合同，不证明真实模型准确率。

`scripts/benchmark_linked_layout.py --output <新目录>` 留存受控三卡片、关系路由和保护场景的前后图、操作及原动态报告。真实跨课程定位召回、误报、人工接受率与完整 M3 发布门槛仍待真实样本单独验收。
