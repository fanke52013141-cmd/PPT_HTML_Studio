# DEF-READINESS：就绪、诊断与验收层次

版本 0.1.0；公共运行/校验协议；HPS-005/007/009/013/017/018。
定义 specified；实现 not_implemented；验证 partial（文档）；P03/04 随样板实现。

用途：告诉调用方能否测量、预览或正式导出，避免用 DOM 加载完成代表全部就绪。
输入为固定源修订、已解析参数、资源/字体、几何、时间、输出意图和审阅记录。

## 检查结果字段

ReadinessReport 为 `{inputFingerprint,checks,layoutReady,previewReady,exportReady,diagnostics}`。
checks 每项 `{checkId,stage,status,evidenceRefs}`，stage 为 structure/references/content/assets/
layout/timing/export/visual，status=passed/failed/skipped/pending，evidenceRefs 为包内记录路径
数组；无证据不能填视觉 passed。可跳过的项必须写诊断原因，跳过不是通过。

layoutReady：结构/引用/内容要求与字体/素材满足测量前提，基础布局和目标已解析；
未支持输出格式不影响这个字段。previewReady：layoutReady 且所选预览模式的时间结果
有效，没有阻断预览的诊断。草稿资源占位可以有 `previewReady=true`，但对应检查明确
失败/待处理，且资源占位模式必须显式启用；它不能成为正式截图/导出依据。
exportReady：固定 RenderBundle 完整、必要检查 passed、正式资源可用、风格 product/
specified、视觉参考与该作品审阅达到要求、输出能力策略满足。三个值是派生布尔值。

缺字体时只能展示可诊断的草稿回退，不做正式文字几何结论，layoutReady=false。
缺图有已知槽位可继续草稿测量但正式 asset 检查不通过；需由实现明确占位模式。
timeoutMs 是运行调用选项，不在作品源数据：>0，具体默认与环境在 P03 记录；超时
RENDER_NOT_READY，不能无限等待或拿半加载画面宣布成功。

## Diagnostic 固定字段

必填 `{code,severity,stage,objectRef,fieldPath,ruleIds,message,repairHint,blocks}`。
severity=error/warning/info；objectRef={kind,id}，kind=document/slide/node/asset/action/anchor/style；
fieldPath 为源数据 JSON Pointer（派生问题指向对应源输入）；ruleIds 非空 HPS ID[]；
message/repairHint 非空字符串；blocks 为 layout/preview/export 的子集，可 []。
块范围由当前处理阶段决定，不能以 severity=warning 自动允许所有输出。
示例：`{code:"STALE_ANCHOR",severity:"error",stage:"references",objectRef:{kind:"anchor",
id:"anchor.html-control"},fieldPath:"/textAnchors/0/textRevision",ruleIds:["HPS-004"],
message:"文字修订已变化",repairHint:"重新确认范围与上下文",blocks:["export"]}`。

## 首轮统一诊断码

| code | 发生条件 / 修复归属 | 默认阻断 |
| --- | --- | --- |
| INVALID_FIELD / DUPLICATE_ID | 值非法、未知字段/ID 重复；实例 | 相关结构处理及正式输出 |
| UNSUPPORTED_VERSION / UNKNOWN_CAPABILITY / UNKNOWN_VARIANT | 未登记版本/类型/变体；定义或实例 | 相关解析及正式输出 |
| MISSING_REFERENCE / INVALID_SLOT / CONTENT_RELATION_MISMATCH / CONTENT_UNCOVERED | 悬空引用、槽位、关系、必讲遗漏；实例/规划 | 相关解析及正式输出 |
| MISSING_TARGET / TARGET_UNRESOLVED / TARGET_CAPABILITY | 目标缺失、无几何或动作不支持；实例/实现 | 相关动作及正式输出 |
| INVALID_TEXT_RANGE / STALE_ANCHOR | 范围非法、旧文字/素材锚点；实例 | 相关定位及正式输出 |
| STYLE_INCOMPLETE / STYLE_UNSUPPORTED | 风格缺字段或不支持组合；风格 | 相关解析及正式输出 |
| PARAMETER_NOT_ALLOWED / PARAMETER_CONFLICT / CONSTRAINT_CONFLICT | 未允许覆盖、同层双写、硬约束冲突；实例/风格 | 相关解析及正式输出 |
| ASSET_UNAVAILABLE / ASSET_HASH_MISMATCH / ASSET_CROP_UNSAFE | 资源未就绪、字节变化、不安全裁切；资源/实例 | 正式输出；草稿另声明占位 |
| FONT_UNRESOLVED / FONT_GLYPH_MISSING | 实际字体未加载或缺字；字体资源 | 可信测量及正式输出 |
| TEXT_OVERFLOW / LAYOUT_CAPACITY | 文字越界或分配空间不足；布局/风格/实例 | 正式输出；草稿显示溢出诊断 |
| ACTION_CONFLICT / TIMING_OUT_OF_RANGE / UNRESOLVED_TIMING | 同通道冲突、超页、时间无效；动作/时间 | 正确播放及正式输出 |
| TARGET_OCCLUDED | 重点目标被隐藏/遮挡；实例/构图 | 初期 warning，必要内容看不到时 CONTENT_UNCOVERED 阻断输出 |
| RENDER_NOT_READY / VISUAL_REVIEW_PENDING | 未就绪、未审阅；运行/设计 | 正式输出 |
| REVISION_CONFLICT / MANUAL_LOCK_CONFLICT | 旧修订提案或锁定字段被改；编辑 | 本次提交，不丢原有效作品 |
| UNSUPPORTED_EXPORT / EXPORT_DEGRADED | 格式不支持或采用允许降级；输出策略 | 前者阻断该格式，后者记录报告 |

诊断不是吞掉异常的成功结果；错误由最小责任层报告，保留原有效修订/资源。
机器校验涵盖结构与客观条件；美感需要参考画面和人工审阅；P01 不产生视觉 passed。
输入相同时重新求就绪；任何依赖变化使相关检查 pending，不继承无关旧通过状态。
正常未来完整 RenderBundle；当前夹具期望 exportReady=false，至少字体/视觉未通过。
验收 C01/C09/C10/C24/C25/C26/C28；无独立视觉/动画目标，诊断 UI 不进视频或 PPTX。
