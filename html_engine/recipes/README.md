# E2 受约束配方

定义依据：[E2 定义卡](../../docs/contracts/html-presentation/runtime/e2/README.md)。作者输入为 hps.e2.recipe 0.1.0；编译产物仍是 hps.e1.scene 0.1.0。配方层在 Node 构建时执行，浏览器直接载入派生场景，不执行模型脚本。不是通用自动排版。

公共配方逻辑：固定槽位、坐标、出现节奏、路径预设；风格属性：字体、色彩、背景及字级，沿用 E1 science-study；实例属性：文案、讲稿、来源和资产文件。E2 目前固定一个风格，尚未验证任意风格切换。资产由哈希/透明范围登记，动作始终关联对象身份。

## 输入和操作

- [课程概念](course-water.recipe.json)：蒸发与凝结，左右概念依次出现。
- [生活情境](course-everyday.recipe.json)：相同知识目标的生活应用；沿用水容器机制插图，并明确不是衣物实物图。
- [对象运动](e2-cloud.recipe.json)：更换云朵，复用预设路径。
- [配方目录](catalog.json)：两个配方版本、预算、变体、视觉状态。

修改 recipe 文件后，在 html_engine 执行 `npm run build:e2`；再重新打开预览。`npm run test:e2` 验证配方、裁切和浏览器状态，`npm test` 验证旧 E1。直接修改生成的 examples/course-*.scene.json 不会回写配方，下次构建会覆盖；需要人工改版时保存为独立 E1 实例，不伪称仍符合配方。

输入共同字段：format/version/id/revision/template/variant/title/subtitle/source。双概念要求 concepts 恰好两项，项字段为 name/relation/body/asset/narration；开放场景要求 mainAsset 和三个 narration 项（text/screenText）。未知字段拒绝，id/revision及派生运行结构继续由 E1 Schema 校验。

## 约束与失败处理

标题 18、副标题 38、术语 6、关系 12、解释 28 码点为前置上限；实际字宽仍由浏览器门禁决定，最大字数不是“必定排得下”。不自动缩字、不截断、不增加新卡片。完整讲稿不上屏。图片槽只填独立插图，方向关系由准确文字箭头呈现，本轮未实现独立 SVG 箭头原子。

长标题回内容规划；缺图回资产选择；超出两概念或路径预设回配方扩展。不要靠增加自由坐标字段接受一个特殊例子。配方均 pending-user-review，仅用于设计探索。

## 资产工具

`node scripts/asset-tool.cjs audit assets/cloud-small.png assets/cloud-small-v2.png` 输出哈希、尺寸、两级 alpha 范围、边界接触、留边。

`node scripts/asset-tool.cjs crop manifest.json` 只执行明确矩形提取；manifest 为 `{version:"0.1.0",source:"assets/board.png",slots:[{id:"plane",output:"assets/plane-new.png",rect:{x:0,y:0,width:627,height:627}}]}`。输入限 assets 直属 PNG；输出不覆盖已有文件，槽位与输出唯一。返回裁切偏移及新资源审计，锚点为裁切画框中心；这不是自动语义命名/抠图，人物关节等语义锚点须另行定义。多文件写入遇到磁盘故障可能留下已生成的部分文件，尚未接任务事务。

`src/recipe-diagnostics.cjs` 提供 visibleContent/rects 包围框重叠提示；本轮由检查工具调用，尚未接浏览器侧栏，不替代逐帧美术审阅。

## 真实用户课程扩展

新增 [hero-steps 定义](../../docs/contracts/html-presentation/runtime/e2/hero-steps.md)，恰好三项 steps(label/detail/narration/summary) 和 heroAsset。新配方不接受旧概念/运动槽位，旧配方也拒绝新字段；hps.e2.recipe 格式仍0.1.0，目录扩为0.2.0。见 [Token 课程](../courses/token/README.md)。
