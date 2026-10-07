# DEF-EDIT / DEF-OUTPUT：编辑、失效与输出

两卡版本 0.1.0；公共编辑/输出协议；HPS-006/010/011/012/014/015/016/018。
定义 specified；实现 not_implemented；验证 partial（文档）。文件编辑样板 P03，任务/编辑器 P07。

## DEF-EDIT：有范围的源数据编辑

EditProposal 必填 `{documentId,expectedRevision,operations}`；operations 非空数组。
首轮操作目录为 set-content、replace-asset、set-parameter、set-layout、set-style、set-action、
reorder-slides、duplicate-slide、delete-node。每项 `{operationId,kind,target,payload}`；
operationId 为 Id，target 指所属对象 `{kind,id}`；payload 必须按操作类型定义，拒绝任意路径写入。
本卡声明最小编辑语义；应用/API 请求与响应模型在 P07 映射，P01 不新增端点。

| 操作 | payload | 保留与失效 |
| --- | --- | --- |
| set-content | {value:string}，目标 content | 保留 contentId/nodeId；文字修订递增，重排/锚点/内容检查；讲稿没改可留音频但不自动判一致 |
| replace-asset | {assetRef}，目标 node | 改 Image 或 Concept.figure 引用；锚点复验、几何/画面更新；原资源保留 |
| set-parameter | {path,value}，目标 document/slide/node | 仅允许字段；颜色重画、字体/间距重排、动作默认变动重编时间 |
| set-layout | {layoutRef,slotMapping}，目标 slide | 节点 ID 保留，槽位完整；重排/标注/画面 |
| set-style | {styleRef}，目标 document | 内容/身份保留；支持、素材、锁定检查与重排；讲稿音频可复用 |
| set-action | {action}，目标 action | 同 ID 完整替换，不能改 typeRef 偷换职责而不验证；时间/画面重编 |
| reorder-slides | {slideOrder}，目标 document | ID 保留；全片时间/页码/跨页关系检查，本地内容复用 |
| duplicate-slide | {sourceSlideId}，目标 document | 宿主分配并返回 ID 映射，复制内容/关系/语块/节点/动作/锚点；页外引用显式检查，资源版本共享 |
| delete-node | {}，目标 node | 列出悬空绑定；不自动删除/改绑相关必讲内容，相关有效性失败 |

每节点/页面 locks 为 `{domain,fieldPath}`[]；domain=content/layout/style/asset/timing。
fieldPath 为该对象源字段的 JSON Pointer 前缀；覆盖其本身或子字段即冲突；
不能把派生坐标锁成用户输入。操作跨节点访问锁定后代时同样检查。
显式用户解锁是另一次源操作，在 P07 定义界面与权限；模型不能在提案里删除锁。
expectedRevision 不同 → REVISION_CONFLICT；任何操作触锁 → MANUAL_LOCK_CONFLICT，提案拒绝，
不部分覆盖旧输入。合法提案先做源字段/引用校验再提交新修订，后续排版失败可保留明确
invalid draft 供作者修正，但不能自动标 confirmed 或正式输出成功。

规范化内容完全相同为 no-op，不增加 revision/不失效。任务结果固定启动快照；
过期结果另存为旧修订产物，不覆盖当前最新。undo 恢复源修订内容和引用，宿主建立新
当前修订记录，不把 revision 倒拨；恢复资源按有效依赖重新检查。
派生状态不由编辑操作填；输出错误返回原输入及诊断，不丢人工修改。
正常 set-content 保留 ID；无效旧修订/未知样式路径；验收 C18/C19/C20/C21/C25。
旧图片编辑模式保留，HTML 操作不直接修改 OCR/Mask 文件。

## DEF-OUTPUT：固定输入和分级能力

outputIntent 必填 `{formats,video,pptx}`；formats 非空、无重复，允许 html/mp4/pptx。
video 为 `{width,height,fps:{numerator,denominator},codec}`，w/h 正整数且与画布同长宽比，
fps 两值正整数，codec 首轮 h264；本例 1920×1080、30/1。真正编码参数在 P06 登记实测。
pptx 为 `{mode,degradationPolicy,snapshotTimes}`；mode=image-final/image-steps/native-basic，
degradationPolicy=allow-images/require-editable；snapshotTimes 为 `{slideId,timeMs}`[]，
time 在 [0,pageDuration]，image-steps 必填非空，按页序和时间排序且无重复。
image-final 取页 duration 边界；require-editable 与 image 模式冲突直接报 UNSUPPORTED_EXPORT。
native-basic 暂不支持，不能用图片成功结果替代。输出不接任意 shell 参数。

RenderBundle 必填 `{documentId,sourceRevision,contractVersion,schemaVersion,definitionRefs,
styleRef,resources,resolvedParameters,resolvedLayout,resolvedTimeline,environment,outputIntent,
inputFingerprint}`。resources 固定实际引用的图片/字体版本、路径/hash；
environment `{rendererVersion,browserVersion,platform,fontResolverVersion}` 必填非空。
参数/几何/时间的输入摘要匹配各自依赖；固定快照不得随用户编辑变动。

inputFingerprint 规范：对实际依赖的规范化 JSON（对象键排序、数组保序、UTF-8、
无多余空白、禁止非有限数）与资源 SHA256 记录计算 SHA256；计算对象排除自身指纹、
任务 ID、墙钟、作者无关备注，包含全部影响结果的参数/版本/环境。具体依赖集每个派生
模块声明，先使用完整有关输入，P07 再按证据细化局部缓存；不凭感受删除依赖。
不宣称该草案已经实现跨语言通用 canonical JSON；P03 固定序列化实现和黄金例。

| 输出层级 | 计划支持 / 验收阶段 | 必须说明 |
| --- | --- | --- |
| HTML 预览 | P03 静态，P04 定时 | 真实文字、资源和时间控制；离线分发依赖另打包 |
| MP4 | P06 | 复用现有 Remotion/编码路线，关键帧、音频、时长与同修订预览实测 |
| 图片型 PPTX | P06 | 每页最终截图，文字不是可编辑对象 |
| 分步快照 PPTX | P06 | 多张阶段截图，不代表原生 PPT 动画 |
| 基础可编辑 PPTX | P10 优先 | 文字/图片/基本形状映射；复杂效果明确局部转图/不支持 |
| 原生动画/媒体/母版/公式 | 以后独立任务 | 不由上述输出成功推导支持 |

CapabilityReport 为 `{format,mode,status,items}`；status=supported/degraded/unsupported/
not-implemented/not-verified，items 为 `{nodeId,feature,result,reason}`。
执行产物还需 `{artifactId,path,sha256,sourceRevision,inputFingerprint,capabilityReport}`；
未支持效果按允许策略列出，失败页不能默认为空白成功。P01 全部运行能力 not-implemented。
数字人/字幕未来为独立合成轨，复用已有产物，只定义 HTML 构图/版本绑定，首轮样例为空。
正常 outputIntent 的 image-steps；无效 native-basic+未实现 → UNSUPPORTED_EXPORT。
验收 C24/C26/C27/C28；兼容升级需保留旧导出和源快照，不改原文件冒充最新版。
