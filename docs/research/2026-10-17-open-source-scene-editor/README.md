# RES-20261017-01：开源画布与动画编辑器借鉴

日期：2026-10-17，Asia/Shanghai。状态：已核对官方仓库、接口源码、npm发布元数据和本项目代码；**尚未安装依赖或运行集成实验**。本档是非规范调研，不新增已注册能力，不替代现行生产、语义动作、编辑保护和音频绑定契约。

实施方案见[开源组件驱动的还原与二次编辑优化](../../plans/html-backend-development/open-source-editor-optimization-2026-10-17.md)。来源、版本、发布包integrity和未验证状态见[sources.json](sources.json)。

## 官方来源与核对结论

| 借鉴ID | 来源 | 已核对的能力 | 拟采用方式 |
| --- | --- | --- | --- |
| OSE-01 | [Moveable](https://github.com/daybrush/moveable)，[包定义](https://github.com/daybrush/moveable/blob/master/packages/moveable/package.json) | DOM/SVG对象的drag/resize、吸附、群组事件；提供原生JS包；MIT | 直接集成原生JS包，控制拖拽和尺寸手柄；写回我们的presentation字段 |
| OSE-02 | [Selecto](https://github.com/daybrush/selecto)，[包定义](https://github.com/daybrush/selecto/blob/master/packages/selecto/package.json) | 鼠标/触摸拖框选择；原生JS包；MIT | 直接集成，选择结果映射成公开objectId；处理文字编辑/框选冲突 |
| OSE-03 | [React Timeline Editor](https://github.com/xzdarcy/react-timeline-editor)，[接口源码](https://github.com/xzdarcy/react-timeline-editor/blob/master/packages/timeline/src/interface/timeline.ts) | 动作移动/resize回调、游标、轨道、自定义动作渲染、engine参数、onChange；MIT | 直接集成局部React模块，作为时间轴交互层；适配现有actionId/beatId/共享播放器 |
| OSE-04 | [Scena](https://github.com/daybrush/scena) | 官方组合Scene.js、Moveable、Selecto、Guides、Ruler等；MIT | 借鉴选择/画布/属性/时间轴协作方式；局部源码复用时记录路径、commit与许可证 |
| OSE-05 | [Theatre.js](https://github.com/theatre-js/theatre) | 动画设计编辑方式；README区分Core Apache-2.0与Studio AGPL-3.0 | 本轮只研究编辑交互，不选为嵌入依赖；不复制Studio源码进入本项目 |

npm在调研时返回moveable 0.53.0、selecto 1.26.3、@xzdarcy/react-timeline-editor 1.0.0；最后一项发布包声明react/react-dom >=18。这些是待集成验证的锁定候选，不代表兼容性通过。上游master内容不等于npm发布包，实施必须用lockfile固定实际包与传递依赖。

Scena源码锁定eae65fb0b1f9a3b2989c3228c331dc7d0bf9211f；Theatre锁定6ea82b938ea49609489f6377ded693ccc6ee8f5b。GitHub REST限流后改用git ls-remote取得分支SHA，未猜测SHA或将浮动分支称作已封存安装。

## 本地集成事实

- `static/html_scene_editor.js`已经有属性、单对象选择、undo/redo、毫秒seek/逐帧和动作/讲稿绑定编辑，主界面是原生JS；目前没有Moveable/Selecto式画布手柄或轨道编辑器。
- `html_engine/visual/schema.json`现有presentation支持offsetX/Y、width/height；没有开放任意旋转、warp或自由CSS。现有边界仍严格检查，不能因库支持更多功能就绕过Schema。
- `html_engine/visual/renderer.cjs`的renderAt写动画transform；拖拽若只改DOM transform会被下一帧覆盖。位置拖拽须成为作者基础布局的patch。
- `html_scene_repair.py`已有set_presentation/set_text_style/set_motion/set_binding等受控操作；绑定动作不能直接修改startMs。`html_scene_editing.py`已有revision、语义身份限制、保护及最小重建。
- 新版scene0.6/0.7使用稳定actionId，binding0.2保存sourceBeats原句/hash；音频绑定服务负责派生实际秒数，作者文件不改成新音频的绝对时钟。
- 既有Anime.js对照已记录不替换生产时钟的决定，见[动作实验](../../../html_engine/motion-research/README.md)。本轮采用时间轴UI不自动推翻该决定。

## 待验证与采用边界

关联HPS-007/008/009/010/011/013/014/015/017/023–025/037。采用交互组件不等于注册新的视觉效果、任意层级或输出格式。首轮验证同源iframe中的坐标/事件、播放器重绘后的重新绑定、CSS缩放、包构建与React模块生命周期、禁用第二套动作播放引擎、UI秒与内部毫秒转换。

本轮不更换既有音频合成/对齐、数字人、HTML渲染及输出系统。实际采用及能力扩展按现行契约同步定义卡、消费者、source closure和验证；保留人工字段与历史作品。旧页兼容、效果支持和真实课程验收分别报告。
