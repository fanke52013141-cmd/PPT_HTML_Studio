# DEF-ASSET：独立素材、字体与资源版本

版本 0.1.0；公共资源协议维护，文件由资源包拥有；HPS-003/007/009/011/018。
定义 specified；实现 not_implemented；验证 partial（示例文件/哈希检查，不含浏览器解码）。
P03 接固定资源；P08 接已有 provider，不新增生成供应商选型。

资源用途、请求、文件版本、使用引用分开。P01 样例只包含文件版本与引用；
生成请求模型后续定义，不把空文件视为已产出素材。

| AssetVersion 字段 | 类型 / 必填 | 默认、范围与跨字段规则 | 归属 / 修改影响 |
| --- | --- | --- | --- |
| assetId, version | Id, semver / 是 | 资源版本不可原地换字节 | 资源身份；实例固定引用 |
| kind, purpose | 枚举 / 是 | kind=image/font；purpose=illustration/icon/body-font/title-font | 资源语义；kind 与用途一致 |
| state | 枚举 / 是 | pending/processing/review/available/failed | 宿主任务管理，不由模型宣布成功 |
| file | 对象 / available 时必填 | {path,mimeType,sha256}；包内相对路径，无 ..、盘符、URL；SHA256 64 位小写十六进制 | 字节证据，宿主映射真实路径 |
| intrinsic | 对象 / image available 必填 | {width,height} >0；原图尺寸，SVG 用 viewBox 单位 | 文件测量；显示比率 |
| alphaBounds | 矩形 / image available 必填 | {x,y,width,height}，原图单位，范围在 intrinsic 内；实际非透明边界 | 文件数据；不得猜成槽位边界 |
| safeRegion | 矩形 / image 必填 | 归一化 [0,1]，宽高>0，完全在单位方框内 | 素材构图；裁切验收 |
| anchors | 对象[] / 可缺省 | []；每项见下 | 资源版本局部定位 |
| styleCompatibility | Id[] / image 必填 | 风格 ID 白名单；不以“都是透明图”推导兼容 | 资源审阅 |
| provenance | 对象 / 是 | {kind,description}；kind=authored/generated/uploaded，description 非空 | 资源来源；生成模型/请求以后扩展 |
| fontMetadata | 对象 / font 必填 | {family,weights,requestedScripts}；weights 非空 100..900 整数，scripts 首轮 ["Hans","Latin"] | 字体需求；不等于实际覆盖通过 |

非 available 可以省 file/intrinsic/alphaBounds，不能放伪哈希；font 无图片几何或锚点。
available 必须实际文件存在、哈希匹配、宿主审阅状态允许使用。P01 SVG 的 available
只描述文件准备状态；decode/readiness 由未来渲染器验证，不能由它推导 renderReady。
首次字体只保留 pending 的需求，不默默使用系统字体作正式结果。

anchor 为 `{anchorId,kind:"rect",rect:{x,y,width,height},coordinateSpace:"normalized"}`，
均在 [0,1]，正面积。首轮只登记矩形，点/路径后续扩展。使用引用必须带资源版本。
单素材换版保留旧文件；旧 anchor 不自动继承，同名也需复验和显式重新绑定。

槽位先给出用途、允许 fit、比例和安全区，再找素材。独立控制粒度为整个文件；
两个对象要独立出现就分别使用两个资产，图内 rect anchor 仅定位强调/勾画。
草稿占位保留槽位和诊断，正式输出不可带 pending/failed 资源。失败重试生成新候选，
原有效资产保留；其他页面/音频不被连带重做。

字体加载后记录实际 family/weight、加载成功、缺字/采用回退。P02 要选择可获取字体文件
及允许回退；P03 在固定环境实测。若需回退，作者须显式确认新字体版本并重排，
不能在导出时悄悄变更已确认字体。许可等来源要求附 provenance，不提前宣称某字体可用。

资源不提供节点 ID；目标从引用它的 Image/Concept 获得。裁切/变换按 DEF-TARGET。
HTML/视频和 PPTX 均记录实际文件版本；离线输出打包实际字节，不称外链为自包含。
正常例两个手绘 SVG 和 pending 字体；非法缺文件/hash错 → ASSET_UNAVAILABLE/ASSET_HASH_MISMATCH。
替换图片失败旧版仍可用；验收 C09/C10/C11/C12/C13/C24/C25。
