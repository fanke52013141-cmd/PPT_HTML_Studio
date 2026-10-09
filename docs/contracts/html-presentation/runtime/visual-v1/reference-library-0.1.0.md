# 标准组件视觉参考库定义卡（现行修订）

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
