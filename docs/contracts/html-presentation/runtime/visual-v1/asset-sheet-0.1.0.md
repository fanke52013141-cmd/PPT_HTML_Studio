# 多对象素材板提取定义卡 0.1.0

定义 ID：`hps.html.asset_sheet`。关联 HPS-026–030、036。维护归属：HTML 公共资产服务；主题只决定素材画风，不改变处理算法。首轮 N00-A。

定义状态 specified；实现与验证状态以 [开发记录](../../../../plans/html-backend-development/progress-2026-10-08.md) 为准。本卡定义确定性提取层，视觉模型识别、真实三路线对照、应用任务和人工批准另行验证。

## 输入与所有权

`extract_asset_sheet(source_bytes, specification, masks=None)` 消费 PNG 字节及以下严格对象，不读取任意文件、不访问网络、不写数据库。输出为候选资源，不能自动批准。槽位由设计清单提供，不能据位置声称已识别正确对象。

| 字段 | 类型/范围/缺省 | 所有者与影响 |
|---|---|---|
| format/version | `hps.html.asset_sheet` / `0.1.0`，必需 | 公共格式；未知版本拒绝 |
| id | `[a-zA-Z][a-zA-Z0-9_-]{0,63}`，必需 | 源板身份 |
| source_sha256 | 64 位小写十六进制，必需 | 原始字节摘要；不符拒绝 |
| slots | 1–16 个独立矩形槽位，必需 | 跨页资产批次，不改变每页预算；不允许重叠 |
| slots[].id/asset_id | 与板 ID 相同字符范围；各自唯一 | 槽位与期望资产身份分开 |
| slots[].role/need | 非空字符串，各最多 1000 字 | 内容实例；身份核对的语义依据 |
| slots[].rect | `[x,y,width,height]`，像素整数，完整在源板内 | 提取位置；不缩放、不旋转，保持板原始尺度 |
| slots[].method | `source_alpha` / `mask` / `boundary_color` | 处理选择；不根据图片偷偷切换 |
| slots[].background | boundary_color 时必需：`{rgb:[r,g,b],tolerance:0..64}` | 声明纯色背景；仅移除从槽位边界四连通的近色区域 |
| slots[].anchors | 缺省 `[]`；最多16个 `{id,x,y}`，坐标为整板像素整数 | 人工/权威语义锚点；必须在该槽位和保留前景中，转换只减槽位原点 |
| masks | mask 模式每槽一个 L 模式 PNG 字节，尺寸为整板尺寸 | 外部分割或人工遮罩；0排除、255保留，中间值按原 alpha 相乘；槽外非零拒绝 |

不接受未知字段、布尔值冒充整数、非法角色字段类型。源板不超过 16,000,000 像素、64MiB PNG 字节；单槽不超过现有独立资产的 4,000,000 像素。尺寸在解码前核对。mask 模式只裁当前槽位，原始 RGBA 颜色保持，alpha 与遮罩相乘；不将生成式补画包装成分割。

boundary_color 是声明纯色背景的有限工具，无通用精细抠图保证。保留主体内被轮廓包围的同色区；不能恢复白底上的白色轮廓、玻璃的背景污染或被遮挡部分。出现这些情况用 mask/独立重生并人工审阅。source_alpha 要求真实透明边缘，棋盘格 RGB 无透明不得当成功。

## 输出、几何与生命周期

结果 `{manifest, images}`；images 为按资产 ID 索引的独立 PNG 字节，manifest 格式 `hps.html.asset_sheet.extraction@0.1.0`。

- 源板摘要、源尺寸、处理器版本、spec hash 单独保存。
- 每槽成功记录：asset ID、槽位、角色、需求、输出摘要/尺寸/alpha bbox、板裁切矩形/偏移、scale=1、处理参数/遮罩摘要、转换后的像素及归一化锚点、source 追溯、`status=pending_review`。
- 所有成功项身份与边缘审阅仍为 pending；几何中心不得自动登记为科学语义锚点。公共像素范围是半开区间，alpha bbox 为 `[left,top,right,bottom]`。
- 单槽失败记录 ID、code、message，省略有效资源字节；同板其余槽位可以产生候选。板级非法输入整体拒绝，不产出部分文件。
- 完全透明、主体接触裁切框边界、前景遮罩越槽、锚点落空等阻断该槽位。边界接触是完整性诊断，用户可重新定义更宽槽位或重生，不自动裁掉失败边缘。
- 结果无动画时钟；独立 PNG 在现有 image 节点中显隐/移动，文字和关系仍由代码控制。最终输出能力取决于页面渲染器和已有视频/快照 PPTX 合同。
- 源板或槽位/处理参数改变产生新候选，不覆盖人工编辑或旧有效资源；缓存由源板、规范、mask hash 和处理版本决定。应用注册/失效/事务职责仍归 store、invalidation 与任务层，本纯模块不注册业务修改。

## 诊断与验证

结构/版本/hash/预算错误抛带 code 的 `HtmlAssetSheetError`；单槽错误进入 failures。缺 mask、错误 mask 格式或尺寸、遮罩越槽、无前景、裁边、锚点错误分别有诊断。

验证覆盖：多槽真实 PNG、遮罩乘 alpha、锚点换算、白色封闭区域保留、重复/重叠/越界/未知字段、哈希、像素与字节预算、单槽失败保留其他候选、输入不可变和重复输出一致。身份、美感和真实模型质量需 AS01/02/04/06 的实际证据，不由这些单元测试推导。

数据/行为：新增独立格式，不改变 scene 0.3.0、E1/E2 或既有 produce_asset。视觉/输出：本层无页面外观改变，调用方显式采用新候选后重新审阅。Agent：本层暂为内部纯函数，无新公共路由；应用接入时同步能力/模型/版本，不能只生成文档冒充 API。

候选存储补充：`html_asset_sheet_store.persist_sheet_candidates` 在项目锁内将完整暂存目录原子改名到 `planning/html_visual/asset-sheets/<sheet_id>/<request_key>/`，保留 source.png、spec.json、extraction.json、独立 asset PNG、传入 mask PNG 和文件摘要清单 candidate.json。相同请求逐文件核对后返回缓存命中；字节损坏阻断，不覆盖已有候选。写入失败不发布半成品目录。该层不注册 resources、不改场景修订/批准/音频，不将 pending_review 变成 approved。上层鉴权和模型/人工审阅接入仍需实现。

## 服务编排增量：生成及分割接线

`html_asset_sheet_generation.generate_sheet_candidates(plan, run_dir, provider, model_config_hash, segmenter=None, checkpoint=...)` 为内部服务函数。plan严格包含format=`hps.html.asset_sheet.plan`、version=0.1.0、id、width、height、direction（V01—V08）、slots；slots与提取定义一致。板矩形、尺寸、身份来自计划，不让模型返回内部ID或决定几何。model_config_hash为64位摘要；凭据不进入输入/日志/缓存。板尺寸正整数、总像素<=16m。生成Prompt唯一来源为该模块的版本化常量，输入只含板尺寸、允许风格、槽位矩形和角色/需求，不含文章全文、代码文字、时间线、凭据或生成摘要。

同板采用一致处理：透明底用于source_alpha/mask；boundary_color生成声明的统一纯色底，不与透明底混用。同板boundary_color槽位须背景rgb一致。返回PNG必须匹配板尺寸，不缩放以凑数。生成结果按计划/Prompt版本/模型摘要冻结缓存，缓存来源摘要必须匹配。失败不覆盖旧候选，调用前后检查停止信号。

需要mask时segmenter必需；接口`segmenter(source_bytes, slots=...) -> {slot_id: L-PNG bytes}`，消费实际图和固定槽位，返回严格整板灰度遮罩，后续服从同一提取门禁。不得把重新生图或RGB背景替换当作准确分割。外部分割服务尚未配置时明确SHEET_SEGMENTER_REQUIRED，而非伪造成功。生成缓存与分割缓存分离；分割结果变化可形成新候选。此函数不暴露公共API、自动识别/批准、注册资源或重写人工场景；实际提供者与UI/任务/Agent接入另验。

## 内部审阅与接受服务

`html_asset_sheet_review`先按源图/规范/遮罩重算候选及request_key并核验字节，再读写独立reviews.json。每个有效资产分别记录identity、edge（approved/rejected）及最多1000字note；expected_revision为严格非负整数，409式冲突不写入，完全相同审阅no-op。提取失败资产不可审阅。此接口仅记录人工选择，不声称自动科学身份核验。

只有两个门槛均approved的有效候选可显式accept；接受时核验预期审阅revision，再将该单个不可变PNG及来源/裁切/锚点记录注册到既有resources.json。资产ID已存在且来源不同则拒绝，不覆盖人工资源。已接受资产审阅锁定；重复accept no-op。注册与接受记录使用项目锁及异常回滚；源候选仍可追溯。新增未引用资源不改scene revision，不取消已有批准/音频；选择资源后的scene保存由原失效入口处理。暂无公共路由、任务/UI或Agent承诺，后续接入须共享同服务和账号/HTML门禁。

## 公共接入增量（第三轮）

Web `/api/projects/{project_id}/html-asset-sheets` 与 Agent对应前缀共享同服务；list、generate、read、review、accept五能力。generate严格请求`{plan}`，计划经既有验证后提交持久html_asset_sheet_generate任务，返回task；提交时冻结图片配置，仅安全摘要入库，凭据仅内存。复用已有HTML executor和任务store，任务查询/停止沿用html-review/tasks接口；启动恢复为interrupted，显式重提获得新快照，最多三次尝试。无数据库新字段。

list返回候选身份及本项目最近素材板任务，用于重开恢复；read返回manifest、审阅revision/decisions和accepted映射；read及PNG预览核验实际来源，不接受任意文件路径。review路径含sheet_id/request_key/asset_id，请求`{identity,edge,note,expected_revision}`；accept请求`{expected_revision}`。未知字段/布尔修订拒绝，账号不匹配404、非HTML400、修订冲突409。UI显式打开素材板面板，输入少量对象需求；候选逐对象查看身份/边缘、保存审阅再接受，未通过不能接受。初期支持真实alpha或声明纯色边界处理；mask适配仍需注入准确分割提供者，不将框选/换背景宣称为AI抠图。

## 微透明噪声与辅助审阅增量（第四轮）

关联HPS-026–030、036。槽位新增可选`alpha_cleanup`，仅source_alpha支持；严格包含threshold（整数1–4）、guard_radius（整数2–8）、max_removed_fraction（数值0–0.05）。未声明时旧输入、处理结果、摘要和候选验证保持逐字节兼容；旧处理器版本不变，新增清理子版本独立记录。

清理只排除alpha在1..threshold且距离alpha>threshold主体超过guard_radius（切比雪夫像素距离）的微弱像素。主体和保护区内RGB/alpha逐字节保留；不增强alpha、不删实体、不缩放、不补画。删除像素数/槽像素数超过budget或全槽没有alpha>threshold主体则该槽失败。源板仍不可变，候选processing记录参数、子版本、删除像素数、alpha总质量与清理前后bbox。原完整性/锚点门禁在清理后照常执行；新spec导致新key，不覆盖旧候选。参数进入提取规范，不发送给生图模型。

辅助审阅内部输入为经候选seal核验的独立PNG、槽位需求及可选原始参考图；严格输出identity=match/mismatch/uncertain、edge=clean/defect/uncertain、extra_content布尔、reason最多500字。由程序推导accept_candidate/regenerate/manual_review建议；其中accept_candidate仅为建议，不改变reviews、accepted、resources或批准。Prompt单一版本来源，模型不猜内部ID/坐标/哈希；reference缺失时不得断言逐像素忠实。提供者/结构异常阻断建议保存并隐藏原错误细节。

建议按源候选key、模型配置摘要、Prompt版本、reference hash形成请求指纹；保存在候选目录独立advisory文件，read验证指纹/严格枚举后展示。初期为内部注入式服务及显式实验入口，任务生成不自动增加文字模型调用；Web/Agent既有read可返回可选advisory，不新增写能力。实际多模态服务无凭据时不伪造调用或结论。

## 审阅任务与单对象重试增量（第五轮）

关联HPS-015、017、026–030、036。新增Web/Agent POST候选`/{sheet_id}/{request_key}/assess`（严格空body）和`/{sheet_id}/{request_key}/{asset_id}/retry`（expected_revision非负严格整数，need可选1–1000字，direction可选V01–V08默认V05）。assess先核验候选再冻结text模型，复用持久任务/executor，按候选key/模型摘要/Prompt版本幂等；不提供任意reference路径，只发送已核验候选及need。建议仍不是审批。

retry针对原spec里声明的一个asset（包括提取失败对象），拒绝已接受对象、修订过期、不存在ID或缺mask服务。保留原槽method/background/cleanup，生成独立1024×1024单槽新候选；使用已核验父板作参考、选定need作身份需求，不生成其他资产。父key/asset/need/direction/重试Prompt版本派生独立板ID，沿用原asset ID供显式采用；原板、其他候选、人工review/accepted/resources/scene/audio均不覆盖。已接受/人工审阅在运行期间改变则checkpoint阻断，不发布迟到重试结果；已生成缓存可保留。任务result/payload保留父身份追溯。

两类任务在提交时冻结所需模型，凭据只在内存，复用原任务查询/cancel/recover/最多3attempt。UI显式按钮发起、轮询/停止/重开恢复，失败对象可重试；Web/Agent/MCP/CLI同步两能力，写CLI须--file。不自动运行AI或付费重试；真实服务、模型视觉/成本和单对象采用仍另验。

## Image2.5 VIP 传输与2K实验增量（第六轮）

关联HPS-026–030、036。ToAPIs模型gpt-image-2.5-flare-vip / gpt-image-2.5-sunburst-vip使用WIDTHxHEIGHT像素值，省略resolution；quality默认low，支持供应商六档值。明确透明请求附background=transparent，普通请求省略该字段；HTML configured_image须转发选择。旧模型的比例/resolution行为保持。候选生成继续严格检查返回尺寸；不缩放补造通过，不将有alpha通道等同边缘干净或人工批准。

用户本轮2K实验采用长边2048：四槽素材板2048×2048，各槽1024×1024；完整图2048×1152。单槽400万像素预算不改变；2048平方单槽超预算，不可直接将旧1024重试硬改为2048满槽。现有面板尺寸和单对象重试默认仍为前轮定义，后续2K产品默认需定义符合预算的槽位。实验使用内存凭据及独立outputs目录，不写用户设置、数据库、场景或resources；费用以完成任务billing为实证，效率需同质量、同对象有效分辨率基线。
