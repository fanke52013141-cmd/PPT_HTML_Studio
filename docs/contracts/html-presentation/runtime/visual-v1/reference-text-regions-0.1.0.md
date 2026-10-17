# 正文区域与背景容器区分 0.1.0

关联HPS-010/011/013–017/023–025/037，契约0.9.73。补充独立参考定位，不改审核facts、HTML渲染或原作者场景。

## 对象区域合同

design_reference_localization片段0.3.0，输入/输出reference-localization-*/0.3.0。模型每个targetId只报告container_box与text_boxes，取消含义混合的box输入。前者是背景/外框或完整模块，后者是实际正文逐行的紧框，含所有正文字符但不含图标、背景造型或大面积空白；没有独立容器允许null。仍只接收原图、原始image_size与内容身份/region_scope，不接HTML坐标或候选截图。

html_reference_localization.validate_region_locations严格检查坐标像素单位、边界、文字框位于容器内、逐对象完整性和缺失状态。located文字承载对象必须有非空可见转录与文字行框；not_found/ambiguous不得有任何框，not_found不得捏造可见文字。无文字的图片/形状不要求编造文字行。

程序按声明选最终box：visible_content文字对象和title_and_number取所有text_boxes包围盒；complete_card/complete_relation_module取container_box，非文字对象也使用container_box。文字缺框不能用容器代替；需要完整容器的对象也不能只用文字框替代。保留两层原始框及selected_source，原始响应不回写成派生输出。旧归档的0.1/0.2验证仍可读取，但本轮新定位严格要求分离协议。

框相等或合法并不证明语义正确：模型仍可能将背景作为一行文字。程序不伪装成OCR、不硬编码目标ID/坐标，不因单页失败放宽IoU或完整覆盖标准。固定参考原图和已预先保存的gold不改，三次模型请求加同一缺失对象负例，与原0.2返回坐标的0.2.1离线回放基线分开报告。

## 接入与兼容

最终选取的pixel_box仍供已有裁剪/总图及评分消费者使用，派生来源和原图/对象/运行片段hash可追踪。原有模型绑定、low/thinking、600秒、输出额度、未知不重发和生产修复轮次不变。定位结果仍model_proposed_unverified，不自动接回正式审核，不把几何评分当人工批准或跨页面能力。

实际固定三次新模型结果及未通过项见[验证报告](../../../../plans/html-backend-development/reference-text-regions-2026-10-17.md)：选定区域18/18达原阈值、缺失负例3/3，来源正文已不误取灰色底条；但两次遗漏实际背景框，完整容器识别和泛化仍未验收。
