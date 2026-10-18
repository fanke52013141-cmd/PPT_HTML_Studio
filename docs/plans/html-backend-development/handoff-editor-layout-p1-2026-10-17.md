# P1 正式布局编辑交接（2026-10-17）

基线为 origin/main `2cfb2dcb8bb765c67e362d2342088b7e1cfa7e47`；本机实际 checkout 为 `D:\Program Files (x86)\PPT_HTML_Studio`，分支 `codex/editor-adapter-p0-20261017`。P0 与本批均为未提交本地开发，未推送、部署或修改线上。后续机器使用自己的实际 checkout，勿复制桌面历史目录。

## 已实现

- 正式 `static/html_scene_editor.js` 接入布局开关、吸附开关、画布/列表/属性联动，单对象移动和右/下/右下缩放，图片等比例；Shift/框选及最多20对象原子移动。
- `static/html_editor_canvas.js` 管理 iframe 辅助层生命周期；`editor_ui/src/canvas.js` 使用 Moveable/Selecto，只改辅助框。手势结束通过原 preview 校验才更新草稿，一次群组移动对应一次撤销。容量失败、过期响应保留原草稿；关闭/重开拒绝迟到结果。annotation 不独立变换，继续跟随锚点。
- 共享 renderer 增加独立 layout 求值，使未入场/已退场节点可编辑并有轮廓；播放/seek 退出布局，不改变动作、字幕、原播放器时钟和默认导出路径。修正非图片几何在各次求值间滞留的问题。
- 保存继续 expected_revision、人工保护、no-op 和最小重建。preview 增加可选 expected_revision，Web/Agent 同样返回409；Agent API 1.40、preview capability 1.1。
- 生产 canvas bundle 与 React/时间轴拆分。来源、锁文件、调用方、产物和许可证哈希纳入构建 manifest 及 generation/render snapshot 的 tooling 闭包，缺失/篡改拒绝。未把编辑器源文件加入 HTML 输入 manifest，因此不会仅因 UI 改动自动失效原批准；真实 scene 修改继续已有 html_scene_changed 路径。
- 旧0.3/0.4仅实际修改时升级0.5，0.6/0.7保持格式与 actionId/beatId/sourceBeats。P2时间轴仍在隔离原型，不是产品能力。

定义：[布局编辑0.1.0](../../contracts/html-presentation/runtime/visual-v1/editor-layout-0.1.0.md)。模块归属：主编辑器拥有草稿/事务/历史，bridge拥有生命周期，canvas拥有手势代理，commands拥有纯转换，renderer/player拥有布局求值/时钟；无 workflow_state 业务逻辑。

## 验证证据与边界

- 相关后端及完整 checks/agent 回归549项通过；唯一提示为既有 Starlette anyio 弃用警告。
- editor_ui Node 14项通过，包含坐标/群组原子/no-op/生产依赖及源闭包。visual构建、前端质量检查、语法检查、Agent契约生成核对通过。
- 隔离服务加载正式编辑器，真实浏览器0.3与0.6场景各12项通过：拖动、缩放、群组单次撤销、保存重开、容量失败回滚、图片/引线、语义绑定保持、隐藏轮廓/seek清理、同值保存、409草稿恢复、反复开关/重开。另验证图片缩放比例、延迟500ms preview期间关闭重开、annotation排除多选。
- 浏览器验收脚本为 `checks/test_html_editor_layout.browser.mjs`，fixture为 `checks/test_html_scene_editor_fixture.py`，测试控件只在fixture加载。均不调用模型/TTS、不使用应用数据库。运行隔离fixture后，通过 cua Tab 调用 `verifyEditorLayoutSteps(tab)` 分阶段执行；`--semantic`启用0.6语义场景，`verifyLateLayoutPreview(tab)`检验迟到响应。
- 收尾时本机 Work 设置禁用了浏览器控制，未能追加导出本轮截图/JSON；上述结论来自已返回的浏览器执行结果，不冒充已存档截图。0.7实际浏览器、框选/吸附专项、多DPR、40对象性能及真实课程/MP4尚未验收。P1整体仍为partial，工程通过不表示视觉/音频批准。

## 后续顺序

框选/吸附与0.7隔离浏览器已补验，见末节；多尺寸覆盖仍待完成。下一开发项为P2真实音频时间轴：复用原音频/播放器时钟，动作以原句beat相对偏移表达，预览/保存继续同一服务和保护校验。勿引入第二播放时钟或把timeline原型直接作为生产完成。真实课程与视频输出分别验收。

依赖完整文本与来源见 editor_ui/licenses/records.json 及生成notices；cfcs原发布gitHead不可取，使用明确登记的上游固定提交；croact由已发布版权与MIT声明重建notice；timeline-engine的ISC元数据与上游MIT差异保留且不进入生产canvas。记录来源不等于法律认证，发行前仍需按实际发行范围审核。

## 本轮补验准备

- fixture新增`--presentation`，使用真正0.7语义场景和`header-badge`/`text-emphasis-bold`呈现变体；`--semantic`仍为0.6，默认仍为旧0.3。
- 新增`checks/test_html_editor_layout_acceptance.py`，独立临时服务走真实preview/save：0.7版本、变体、动作/原句绑定/可见集合保持，preview不写入、人工保护、重开、no-op及preview/save过期409。连同现有scene editing共12项通过；这是服务层证据，不是浏览器或视觉验收。
- `verifyMarqueeAndSnapSteps(tab)`新增框选精确两个卡片/排除annotation、群组单次撤销、吸附开关落点对比、偏离槽位的其它对象边缘吸附；原完整浏览器套件新增0.7非布局呈现属性保持断言。
- 此阶段浏览器曾被Work设置阻止；设置界面已开启，但工具状态直到重启客户端后才恢复。以下补验结果替代此处先前的待执行状态。

## 本轮实际浏览器补验结果

2026-10-17，重启后浏览器连接恢复，隔离`--presentation`服务加载正式编辑器及最终canvas构建：

- 框选精确选中card-1/card-2、annotation无编辑代理；两对象共同移动，一次撤销恢复二者，通过。
- 槽位边缘吸附开关落点对比通过：画布显示比例0.464375，开启吸附最终作者offsetX约-0.2153（屏幕约-0.1px），关闭约-6.4603（屏幕约-3px），与指针像素取整一致。其它对象偏移离开登记槽位后，其边缘仍能单独吸附，通过。
- 初次测试从右接近时落在标题/插图另一条更近的有效参考线上，原断言不足以区分参考线；改为从左接近排除竞争参考线后通过。这不是已证实的吸附算法缺陷，未保留诊断日志或试验性transform改法。生产仅显式关闭库默认的gap吸附，使范围保持为既定画布/槽位/对象边缘。
- 0.7完整浏览器13项通过：位置编辑/撤销重做/保存重开，缩放及容量失败保留草稿与历史，群组单次撤销，图片引线刷新，header-badge与text-emphasis-bold及其它非布局呈现属性保持，动作/原句hash/资源/可见集合保持，隐藏轮廓与seek清理，同值保存不增revision，409草稿恢复与版本比较，开关/关闭/重开清理。
- 另通过500ms延迟preview期间关闭重开；只剩一个iframe/辅助层，无迟到响应污染，annotation排除多选。
- 可复现脚本见`checks/test_html_editor_layout.browser.mjs`；两个generator分别用新tab运行（框选套件撤销后的状态文本不是初始“修订”）。修正了跨浏览器桥接数组原型导致的strict deepEqual误报，改用值序列比较。
- 本机证据：`outputs/editor-layout-p1/acceptance-2026-10-17/browser-results.json`及`preview.png`，属于忽略的验收输出，不进入Git。JSON存实际返回的四项框选/吸附、十三项0.7及迟到响应结果。

本次所请求的框选、吸附和0.7隔离浏览器验收已完成。多DPR/40对象性能、真实课程、正式视觉/音频批准与视频输出仍未验收，P1整体保持partial；未提交、推送或部署。后续可推进P2真实音频时间轴，并按计划补剩余P1压力覆盖。

最终产物复核：editor_ui Node 14项通过；本轮服务/scene editing/build snapshot共26项通过（既有Starlette弃用提示1条）；前端质量、脚本语法、源/产物指纹和git diff空白检查通过。
