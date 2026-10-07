# E1-SCENE / E1-LAYOUT

版本 0.1.0；公共格式与布局维护；HPS-001/006/007/010/014/018/020/026/027；定义 specified。实现/验证状态见索引。
用途：一个固定镜头的开放讲解场景，输入为结构化 JSON；不支持多场景、父组、语义概念块、真实音频模式或任意 HTML/CSS/script。

| 字段 | 必填、类型与约束 | 所有权/修改影响 |
| --- | --- | --- |
| format/schemaVersion/contractVersion | hps.e1.scene / 0.1.0 / 0.7.1；全必填，未知拒绝 | 公共格式；版本改变须显式迁移 |
| id/revision/title | 稳定 ASCII ID、正安全整数、非空纯文本 | 实例；宿主编辑递增 revision；不按数组位置重命名 |
| authoringMode | 仅 design-exploration | 公共；不接受 production，以免绕过模板审批 |
| canvas/safeInsets | 设计单位，有限整数尺寸；安全区总和小于画布尺寸 | 实例/公共约束；重排全部几何 |
| templateRef | layout.open-stage.e1 @0.1.0 | 受约束开放舞台；实例填对象框，不能任意扩展组件 |
| style | 明确版本的参数包；见原子卡 | 风格提供视觉值，硬约束不可覆盖 |
| assets/paths/nodes | 各命名空间 ID 唯一；版本和引用有效 | 实例；资源替换重验几何，路径修改重验运动 |
| durationMs/timingMode | 1..600000 整数毫秒；仅 manual | 实例；不冒充已有音频已对齐 |
| beats | 非重叠时间区间，纯文本讲稿与 screenText 分开，targetIds 有效 | 内容实例；改讲稿后未来按既有音频机制处理 |
| actions/keyframes | 有效目标与时段；关键帧含 0 和 durationMs | 实例；完整过程目标须提前登记 |

精确范围以 Schema 为准，所有字段拒绝 null 和未知属性，不接收 extensions。无隐式默认；输入完整，编译不覆盖作者数据。
各数组支持重排，身份不变；等层绘制按 ID 排序，避免数组次序成为身份或隐式层级。
本轮没有自动布局：box 是模板约束下的作者布局输入；编译检查范围、安全区与容量，不宣称任意内容都能自动排美。
同一个 caption 对象读取当前 beat.screenText；区间 [start,end)，页末取最后一个恰好结束于页末的语块，间隙显示空串。
输入最多 80 节点、160 动作等，超限先报 Schema 错误，不无限工作。根 revision 为手工输入，不实现应用持久化、锁定或影响任务。
正常两个例见 html_engine/examples；错误：旧 P01/未知版本→UNSUPPORTED_VERSION，重复 ID→DUPLICATE_ID，悬空引用→MISSING_REFERENCE，未知字段→INVALID_FIELD。
输出：编译快照/输入指纹/明确诊断，随后资源就绪才可 renderReady。HTML 原型已支持；视频读取相同求值；PPTX 本轮不支持。
兼容：新独立格式，不读取旧图片产物/P01；无旧运行数据迁移。数据/行为/视觉/输出仅限两个新输入，未改原图片应用。
