# 场景编辑器定义卡 0.1.0

定义 `hps.html.scene_edits@0.1.0`，N02；细化 HPS-001、007、013、015–017，AC09/11/13/17。
现有 scene 0.1/0.2/0.3 经生产编译器读取；编辑器不创造新 scene 字段。

## 输入与能力

GET/PUT `/api/projects/{project_id}/html-visual/{slide_id}/editor`；PUT 必需
`scene`、`binding`（对象或 null）、`expected_revision`（非负整数），可选
`anchor_overrides`（缺省 {}，image node ID → 原图归一化锚点数组）。
每锚点 `{id,x,y}`，ID 遵守生产 ID 正则，坐标有限且 0≤x,y<1；最多16点。
更换图片必须重新选择该资源登记锚点，不继承原资源坐标。

对象身份/type/slot 在本编辑器固定；可编辑字段直接由生产 node Schema 提供。
motion 仅 enter/exit/emphasize，以生产 Schema、compiler 和 player 为准；实验
relation_draw 不暴露。绑定沿用 motion_binding 0.1.0 的 beatId/edge/offsetMs。
旁白语块从当前 visual_contract 读取，编辑器不改旁白、不重新 TTS。
无音频预览明确显示作者时钟；最终输出仍由既有 audio binder 解释。

## 持久化、人工保护与兼容

scene、binding、人工覆盖、资源清单、项目 revision 在同一项目锁内写入；普通异常
回滚，不声称进程崩溃原子性。相同内容 no-op，不改变批准/音频。修订过期返回409，
浏览器保留按项目/页隔离的会话草稿，提供服务器版本比较和显式重载。
保存基线与当前节点/动作/绑定差异保存在 edits-{slide}.json；重规划可以调用合并
函数，删除/类型变化产生明确冲突。未接入合并的旧写入口拒绝覆盖有人工修改的场景。
会话撤销/重做不等于历史版本恢复；人工字段默认保护，无隐式解锁。

锚点调整产生本页独立资产引用，复用已验证原图像素并保留原资产，资源 ID 由页、
节点、原资源和锚点摘要派生；不修改同板其他对象。审阅/输出消费普通 resources.json，
无需新播放器。旧场景无编辑记录时保持原保存行为。

## 预览与边界

iframe 使用原 shared player/data bundle，preview/apply/seek 不另写渲染器。
列表与画面双向选择；图片锚点使用播放器 contain 几何，文字选区由 DOM Range
测量并换算逻辑坐标，SVG 使用播放器 geometry。文字/SVG 目标测量用于诊断；当前
生产 annotation 只接受 image，因此不声称文字/SVG 批注可输出。禁止 OCR。
无效字段、悬空绑定、越界锚点、重复通道和容量问题明确报告，不能偷偷缩字。

定义完成；实现、工程测试、共同接入与真实服务/视觉签收分开见 scene-editor-handoff.md。
