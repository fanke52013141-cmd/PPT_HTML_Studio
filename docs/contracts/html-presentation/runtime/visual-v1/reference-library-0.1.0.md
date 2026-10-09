# 标准组件视觉参考库定义卡（现行修订）

## 标准库 1.0 静态交付增量

2026-10-09：现行截图入口改为 html_engine/reference-library/standard/，24 张 1920×1080 白底黑白灰分类页。覆盖 32 基础组件、16 呈现变体、28 效果、18 组合与 5 字体。standard-pages.json 拥有页归属；standard-library.css 拥有统一美化外观；standard-library.js 复用既有语义渲染并提供离线参考 DOM 调用；build-standard-library.cjs、export-standard-library.cjs、verify-standard-pixels.py 拥有构建、全页导出与像素/哈希验证。

采用内置生图设计研究的字阶、留白、边界与阴影，代码复刻而非整图背景。独立配色不变，旧组件图保留作历史证据但不作为默认输入。静态 Agent 审阅记录 STANDARD-REVIEW.md；用户审美签收和生产适配未完成。没有新增 scene 字段、应用 API 或动效能力，P01/E1 和原已认可作品保持独立。

2026-10-09；关联 HPS-019、023–028、031–037。组件目录 0.2：中性标准组件、独立配色角色、统一风格描述共同作为生图参考。HTML 仅内部渲染；不交付另一套风格专属模板。

## 归属与输入输出

components.json 拥有原 24 项，components-extensions.json 拥有 8 项固定关系/数据示例；components.js/CSS 实现参考外观；palettes.json 拥有颜色角色。build-components 与 component-query 同源合并 32 项。effects.json 的 28 项静态效果和 static-catalog 的 18 项组合不算新语义组件。

PNG 导出由 export-reference-input.cjs、export-style-description.cjs 拥有，输出 reference-input-v2。准确内容与关系优先于组件结构、配色和质感；标签/示例不得作为真实内容。最小输入装配器尚未实现，不把目录视作生产 Schema 或公共 API。

## 能力与限制

文字、基本形状、容器、关系和精确数据由代码控制；少量复杂主体由图片承担。R/D 新项为固定示例，不能接任意数据或拓扑。只做静态，不引入动态能力；手绘主风格仍排除。默认主体预算与现行 HPS 规则一致。

## 状态与兼容

定义已记录，参考实现可构建/查询/截图；工程边界、字体、资源检查由 verify-components 留证。新参考的审美反馈和新版多参考真实生成仍待验证，生产规划/scene 适配未接入。PAIR-02/03 的用户认可只针对历史静态实例。

本次移出被否定的七页模板、soft-depth 自建模板与旧动效实现，统一入口和计划；不修改已认可作品、P01、E1、scene/API/数据库或音频输出。生成 HTML/PNG 随源重建。运行兼容不变，参考调用入口统一为 component-query；旧 REF-* 探索接口退役，不能映射成新增生产能力。字体随包和跨环境验证待做。

源码与使用入口：html_engine/reference-library/README.md。执行计划：docs/plans/html-backend-development/visual-reference-roadmap-2026-10-09.md。

## 静态精修增量

保留 32 项身份与语义，移除样例外层灰色圆角展示框，避免 AI 把展示容器误认为组件；修复 section 类名导致的小标题额外上边距。精修字重、解释语边线、卡片留白、分层柔影与编号形态。仅参考外观变化，无 scene/API 变化；美感待实际截图审阅。

## 呈现变体定义（PV01–PV16）

关联 HPS-002、023、025、031–037。presentation-variants.json 拥有 16 项参考呈现身份、parent componentRef、className、用途与样例内容。复用 T01/T05/T07/C01–C04/N01–N02，新增外观不增加语义组件数量。ComponentAtlas.render(id, value, variantId) 可选第三参数；变体必须属于该组件，未知/错配明确拒绝。原二参数调用保持兼容，36 字符上限不变；只是参考输入预算，不保证任意 36 字符在展示槽中排下。字体资源仍需本机实际存在。

中性总图与四类变体细节 PNG 从同一组件 DOM 生成；独立配色图仅修改角色变量。效果板沿用原 28 项静态实现。灰阶先可读，再应用配色，不把装饰变体默认为全部内容的样式。所有呈现仅供静态设计选型，不是 scene/生产 API；视觉 pending_review，实际边界、资源和字体证据随验证更新。旧 ID/语义与批准作品保持，无迁移。
