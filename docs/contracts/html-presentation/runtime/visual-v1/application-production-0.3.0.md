# E：参考输入、设计停点与局部返工 0.3.0

2026-10-10。关联 HPS-011/013/023—028/031—037。应用级增量，scene 0.3.0、theme 0.2.0、binding 0.1.0 不变。Agent API 1.17.0。与 application-workflow 0.1/0.2 叠加；本文件替代旧生产入口自动从设计参考继续素材的行为。

## 定义卡

| 项目 | 定义 |
|---|---|
| 身份 | E-PRODUCTION-REFERENCE 0.3.0；应用生产入口，不是新作者格式 |
| 输入 | 当前分镜；已规范化注册模板计划；D reference-request-package 1.0.0；提交时冻结的模型；项目修订；严格 HtmlProduceRequest |
| 内容归属 | 文字/数值/槽位来自 plan；分类图只借鉴外观。样例文字、编号和参考布局不能成为生产数据 |
| 风格 | 新生成场景默认 neutral-baseline@0.2.0；所有色值、渐变与阴影为灰阶，白色背景。复用已有注册能力、几何、字体与播放器，不修改历史主题 |
| 控制 | 首次生成有图片需求的页面停在 design_review；明确携带候选 key 才继续。最终 HTML 人工审批独立 |
| 几何/预算 | 当前注册模板、字幕区及每页一个新独立主体保持；参考图不改变槽位，不反向 OCR 定稿 |
| 资源 | 分类别 PNG 实际附件；包内内容、指导、manifest、文件大小/哈希/尺寸均校验；透明主体仍走既有资产检查 |
| 验收 | 模型替身、真实文件/浏览器/SDK边界各自留证；外部模型响应、2K实际尺寸与用户审美需另验 |
| 兼容 | 无 DB/迁移，无图片后端或音频替换；旧场景/批准不补写新 provenance。新生产输入变化使新批准/输出指纹失效 |

两处公共组件的硬编码蓝灰阴影修正为已定义的 shapes.shadowRGB。soft-science 值相同；其他主题按其既有 token 生效。播放器/目录重建可能使已有批准指纹过期，必须重新审阅；不改写旧批准或保证它们仍有效。

## 参考选择与提示词 I/O

生产首先按注册计划中的类型选取 D 分类页：文字层级 component-01；arrow 加 component-02；card/figure/summary 加 component-03；annotation/badge/label 加 component-05。选择是有限、确定的视觉线索，不是这些参考组件已经全部拥有生产适配器。当前生产只使用 D 的 standard + neutral-baseline；D 的独立彩色探索仍是离线能力，尚未成为生产参数。

D 装配器校验真实源并缓存；E 再核对 manifest 身份/自哈希、全部文件哈希与大小、附件解码/尺寸及路径归属。每次恢复与实际落盘前重新检查。破损包明确失败，不静默采用旧总图，也不删除或重建用户文件。

PromptVersion `html-design-reference/0.3.0` 的唯一任务是完整页面设计参考。稳定规则：黑灰白、白底、16:9、字幕留白、代码与图片职责和不复制样例。变量：准确注册槽位内容、主体需求、风格描述和显式修改方向。准确内容只序列化一次；审计 hash、目录身份、讲稿全集和 effects 全注册表不进入模型。产出为可验证图像字节，消费者为设计候选与后续独立主体生成；图片文字不进入 scene。

设计请求缓存绑定 Prompt、模型摘要、brief、实际附件字节、D cacheKey 和生成政策；设计缓存还核对响应哈希。主体缓存绑定 need、Prompt、参考字节、模型与生成政策。参数缺失的旧通用资产请求保留既有缓存字段形状。

## 请求与设计停点

2026-10-10显式输入素材复用增量（HPS-001/011/013/023—028）：visual_groups可提供available_assets数组，每项assetRef为{id,version}，description仅作模型上下文。这是用户已提供素材的声明，不能由生成计划自行授予。只有计划image_asset身份、对应图片槽位assetRef、输入版本与注册/项目真实资源均一致时才复用；项目PNG按现有资源加载器校验路径、字节hash、大小、alpha边界和锚点，注册资源在实际渲染前验证。坏版本或引用拒绝SUPPLIED_ASSET_INVALID。复用保留image_asset归属和原字节，新provenance记录supplied_asset_ids；不改变人工审批、不签发设计批准。只含这些素材时无需新设计/生图；新素材仍走原停点。asset_instruction显式返工不适用复用；默认旧输入无此字段，旧生成行为保持。

2026-10-10 真实验证修复：Prompt 0.3.0 的 layoutGeometry 从匹配版本的注册布局展开 canvas 与本页活动槽位框，按比例适配输出。生图不能猜测卡片方向或字幕边界；全部正文、标签与说明均须保留。此字段为参考输入，不修改 scene、API 或模板几何。定义指纹变化会阻止旧设计直接恢复；原候选保留。

Web 和 Agent 使用同一严格模型、相同服务。POST 既有 `.../html-review/{slide_id}/produce` 可以不带 body 或带 `{}`。

| 请求 | 行为 |
|---|---|
| `{}` | 生成规范计划。有新图片需求：实际参考请求后返回 design_review，不生成独立素材、不替换场景。纯代码页直接经过技术 review 保存，仍需人工批准 |
| `{"design_instruction":"增强标题层级"}` | 生成新的设计候选；旧候选与旧场景保留。不能与确认 key 同时提交 |
| `{"design_candidate_key":"64位小写SHA"}` | 明确确认该设计用于重建；不重调规划/设计模型。生成透明主体、展开注册 scene、合并人工 deltas、技术检查及修订检查后保存 |
| `{"design_candidate_key":"64位小写SHA","asset_instruction":"简化主体细节"}` | 单主体局部返工，复用设计与计划，只修改主体请求。没有 key 时拒绝；人工编辑存在时明确冲突，保护人工资源 |

未知字段、无效 key、互斥参数在 HTTP/MCP 请求层拒绝。CLI `html produce --file request.json` 使用相同字段，AgentClient/MCP 同步。

设计任务生命周期成功表示候选任务完成：`status=succeeded, stage=design_review, result.stage=design_review`，不表示产品、素材或 HTML 已完成。结果包含 `design.key/file/sha256/reference_package_key/approval_status=not_recorded` 和 `saved.changed=false`。任务幂等身份增加项目修订、参考源定义、选项及模型；项目修订变化必须形成新任务，不能复用过期成功任务。

GET `.../design/current` 只读当前候选状态/key/stale/image_url；Web、Agent、MCP、CLI 均可读取。Web `.../design/{key}/image` 校验图片与候选哈希后供查看，响应 no-store。UI 恢复当前待审候选，提供修改/确认与单主体返工；项目、页面切换清空候选及修改方向，迟到响应不串页。

## 文件与恢复

灰阶设计参考不发送运行时 tone 键：blue/green/pink 等是语义 token，不能让生图将其解释为配色。只移除 tone 字段，保留正文里的颜色事实、原计划和 scene 的语义。设计提示和包内容因此改变，旧候选不自动迁移或批准。

`planning/html_visual/reference-packages/{输入身份}/`：D 完整包与真实图片，候选运行数据不提交仓库。

`candidates/{slide}/designs/{key}/candidate.json + design-reference.png`：候选身份由整个记录确定；包含 plan/brief、内容哈希、模型摘要、定义身份、图片哈希、D 包位置及 manifest hash、开始修订和原场景 hash。模型请求身份也记录，两个不同修改请求即使返回相同字节仍有不同候选。

`candidates/{slide}/current-design.json`：最近候选指针；不等于批准。

`candidates/{slide}/design-acceptance.json`：显式确认请求成功生成后记录候选 key、保存修订、实际 scene hash、provenance hash；语义仅为设计用于重建。失败回滚保留旧回执。可以据此对未被修改的当前页面做单主体返工；人工保存、内容/定义/模型变化或哈希破损会阻止旧 key 恢复。

`production-provenance-{slide}.json`：成功场景的模型、主题、设计 key、D cacheKey 以及包/参考实际文件 hash。与场景/绑定/计划/资源/修订同一回滚范围。批准和输出输入指纹读取该记录及真实引用字节；任何损坏或来源变化均不能仍视为当前批准。没有该文件的旧场景保留旧指纹形状。

主体请求失败、技术 review 失败、并发修订或人工冲突都保留候选，并保护当前已保存页面；候选资产缓存可能存在，但不能据此获得资源批准。网络请求不能被取消已提交的远端工作，沿用既有阶段边界协作停止。

相同输入与资源的重复恢复是 no-op；cache hit/miss 遥测不写入作者资源。即使 scene 字节相同，只要正式 binding、plan、资源或 provenance 改变，项目修订与下游失效仍更新；不能因为图片字节相同而遗漏素材请求或来源变化。

## 生成默认值与验证边界

配置中的 GPT image 请求采用 low；`gpt-image-2.5` 兼容端请求 metadata.resolution=2K。ToAPIs 采用 toapis_resolution=2k / toapis_quality=low。普通其他模型不注入未知 metadata。设计不要求透明，主体要求透明。设计调用仍使用1536x1024、主体1024x1024参数；这些请求尺寸与2K提示的供应商优先级未实测，必须记录实际返回尺寸，不能把提示登记为已获2K。

本轮验证不调用真实供应商，不产生用户审批。F 接收工程小交付后，应使用当前配置完成真实多参考请求、测量实际尺寸、设计与 HTML 对照、主体边缘确认、真实音频/视频/PPTX与课程签收。双主体模板、自由路径与新字体映射仍需定义，不能从 D 分类图或 B 样页推导为可执行能力。
