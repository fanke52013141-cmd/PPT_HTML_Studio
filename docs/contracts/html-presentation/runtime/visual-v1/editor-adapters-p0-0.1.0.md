# 开源编辑适配 P0 定义卡 0.1.0

细化 HPS-007/009/010/011/013—017/023—025/037。范围为隔离适配验证，不表示正式编辑器入口、整课程或生产验收已完成。输入仍为既有 scene、motion_binding、revision、resources；不增加业务 Schema 或 Agent API。

- `editor_ui/` 仅构建；精确锁定 Moveable 0.53.0、Selecto 1.26.3、React Timeline Editor 1.0.0、React/ReactDOM 18.3.1。本地 bundle、许可证登记和源/产物哈希由 `build.mjs` 生成；禁止外部 CDN。
- 画布适配器在共享播放器同源 iframe 内实例化。手柄作用于独立辅助框，拖动结束生成既有 `set_presentation` 操作形状；不写动画 transform、不新增旋转/warp。作者尺寸来自所选 layout.canvas，屏幕位移按 stage 实际宽高换算，原点/页面滚动不参与相对位移。
- 仅非 annotation 且当前可见节点参与 P0 选择。Shift 多选仅验证选择，不允许群组变换；隐藏对象辅助轮廓、吸附和批量事务留待 P1。拖动或 resize 只在结束时提交一次本地事务；尺寸触发原共享渲染器重排/容量验证，失败恢复原数据；不截断到合法值。
- Timeline 只消费已有动作和只读语块窗口；拖动修改原 binding.offsetMs，resize 修改原 durationMs，保留 actionId/beatId/edge/hash 和原 startMs。越窗/无绑定拒绝，不自动跨句。`effects={}`、`autoReRender=false`，适配器不暴露 play；游标请求原 seek，外部时钟只更新其游标。
- 原 editor preview/save 保有校验、revision、人工字段记录及重建所有权。P0 fixture 不代表新公开写入口；正式 Web/Agent 接线及保护/音频/输出全链由 P1—P5 验收。
- 销毁必须移除选择框、Moveable/Selecto、ResizeObserver、scroll 监听、React root 和游标观察定时器；不将辅助层混入正式 scene 或导出。

源闭包：P0 开发依赖由 `static/editor_ui/manifest.json` 绑定源文件/lockfile/bundle；目前生产未加载这些文件，故未纳入生产 render/generation snapshot。P1 正式接线时必须同步实际消费者、生产源闭包和前端所有权检查，不能仅加载 bundle 即宣称完成。

实现与实测见 [P0 交接](../../../../plans/html-backend-development/handoff-editor-adapters-p0-2026-10-17.md)。真实供应商、语义动作新版、真实声音和正式输出仍为 not_run；用户视觉签收为 pending_review。
