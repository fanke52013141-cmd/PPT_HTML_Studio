# 原设计图复用为新待审参考 0.1.0

2026-10-18，HPS-011/013/015—017/023—030/037；契约0.9.87，Agent API1.46。定义先于实现。

能力更新后，旧候选key仍不能直接用于当前还原。显式reuse_design_candidate_key只把原模型生成的计划与原图复制为**当前定义下的新待审参考**，不签发设计接受、HTML视觉或A04批准；新key仍需独立接受后走完整理解/还原/审核。旧候选和失败记录不改写。

| 边界 | 规则 |
|---|---|
| 身份 | 同项目/同页；原记录、原图、参考包hash严格核验；当前contract、模型摘要、基础作者场景及revision必须仍匹配 |
| 计划 | 用当前注册模板/布局/语义规则重新规范化；除派生registered元数据外的计划内容必须完全不变。不能借复用修改正文、对象、动作、素材引用或讲稿 |
| 输入 | HtmlProduceRequest新增可选reuse_design_candidate_key；与设计接受/修订、素材返工、未知请求实验互斥；仅创建新待审候选 |
| 执行 | 原HTTP/Agent/任务状态机；当前源快照；参考包按当前定义重建，原图字节原样复制；不调用规划、生图、TTS，不写作者场景。记录源候选key及image hash |
| 批准 | 返回approval_status=not_recorded；不能自动接受新key，不能沿用旧视觉/声音/A04决定。用户声音批准若音轨未变继续由原服务核验 |
| 兼容 | 旧load_design的DESIGN_STALE规则完全保持；普通produce无新参数时保持原行为，无数据库迁移 |

同批补齐annotation-ring-dashed（虚线圈/实线引线）、annotation-line-dashed（实线圈/虚线引线）、annotation-solid（可显式返回实线）；旧annotation-dashed仍为全虚线带箭头。figure标签/说明图标继续来自原准确内容，icons仅是可选装饰选择列表，不代表当前内容图标缺失。几何、绑定、正文与人工保护不变。

验证须包含字节/来源保持、旧key继续stale、任何篡改/内容或作者变化拒绝、新候选仍待审、零provider/TTS调用，以及现有接受后的完整生产路径。

## 0.9.95：其他页保存后的显式参考复用

只在显式reuse路径：调用方revision须等于当前项目revision；旧记录revision较小但本页基础作者hash完全一致（包含尚无作者的null）且无人工覆盖时，可复用旧图/计划创建当前revision的新待审key。旧记录必须显式含base_scene_sha256；同页变化、过期调用revision和人工覆盖拒绝。contract/模型/图片/参考包/normalize守卫保持。普通load_design接受门禁不变，不能接受旧key或继承批准；一次授权修复预算也不变。
