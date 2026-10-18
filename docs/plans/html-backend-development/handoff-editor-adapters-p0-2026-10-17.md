# 开源编辑组件 P0 开发交接

日期：2026-10-17，Asia/Shanghai。延续 [上一份 handoff](handoff-open-source-editor-2026-10-17.md) 指定的 P0；没有要求人工逐页标注，没有供应商调用。

## 代码基线与范围

本机实际仓库为 `D:\Program Files (x86)\PPT_HTML_Studio`，桌面 `html动画` 是历史实验文件夹，不是应用仓库。检查原工作区干净后执行 fetch 与 fast-forward：main 和 origin/main 同为 `2cfb2dcb8bb765c67e362d2342088b7e1cfa7e47`。随后在 `codex/editor-adapter-p0-20261017` 开发；本文件记录的是本地未提交增量，没有 push、merge 或部署。main 指针仍保持远端基线。数据库、runs、凭据及运行依赖未被覆盖。

本批新增 `editor_ui/` 局部构建包，输出到 `static/editor_ui/`，只在 `/adapter-test` 隔离 fixture 消费。正式 `static/html_scene_editor.js` 和应用模板加载顺序未接线。P0 最小接线已验证，整体 P0 仍为 **partial**（许可文本缺项、语义新版/完整矩阵待验证）；P1—P5 未完成。

## 实现和证据

| 项目 | 状态 / 实测 |
| --- | --- |
| 精确版本、本地构建 | passed：Moveable0.53.0、Selecto1.26.3、Timeline Editor1.0.0、React/ReactDOM18.3.1；lock integrity 与研究档案一致；官方 registry npm ci 后重建成功 |
| 作者坐标 | passed（隔离页）：0.5倍屏幕移动10/10→作者20/20；1倍10/10→10/10；1.5倍15/15→10/10；2倍20/20→10/10；测试中页面发生横纵滚动。不是全DPR/任意矩阵认证 |
| iframe 选择和 resize | passed（单对象）：共享冷杯场景非annotation对象；card-1宽度850→830、height102，通过原preview和共享renderer；不使用文字scale |
| 连续手势事务 | passed（本地）：一次结束产生一次撤销；撤销/重做重新经原preview渲染。未实现多对象原子群组变换 |
| 绑定偏移 | passed（旧格式隔离页）：header:enter拖动+0.3秒，binding.offsetMs=300，beatId=b1、edge=start，作者startMs=0、durationMs=800保留；原preview解析 |
| 保存/重开 | passed（fixture原服务）：修订1→2保存header位置20/20，修订3保存offset300，修订4保存card宽830；刷新读取保持。不是实际课程签收 |
| 单时钟 | passed（P0接线）：Timeline无effects、autoReRender=false，不暴露play；点击时间刻度经回调跳转原播放器，实测2004ms。这里只用作者时钟，真实音频和输出帧同步未测 |
| 销毁 | passed（一次实际检查）：辅助层1→0，React时间轴文本清空；实现同时移除观察器/scroll监听并清除100ms游标观察定时器。尚无长期内存/40对象性能结论 |
| 构建/适配测试 | passed：`npm.cmd test --prefix editor_ui` 10项，含源/产物哈希、版本integrity、四种坐标比例、异常范围和绑定元数据保留 |
| 应用回归 | passed：scene_editing、scene_repair、audio_binder、rebuild_plan、runtime_skills 5文件91项；Starlette既有弃用warning1条 |
| 快照回归 | passed：`checks/test_html_build_snapshot.py` 12项；与上方10+91共113项测试通过 |
| 其它检查 | passed：fixture JS语法、Python编译、frontend_quality、focused diff whitespace；官方registry npm audit返回0条已知漏洞 |
| 许可证 | partial：生成第三方元数据、完整可用LICENSE及bundle版权注释；部分上游npm包漏带全文，notice明确缺项，产品发行前补核。Scena/Theatre没有复制源码或加入依赖 |
| 真实模型/音频/正式输出 | not_run；未发模型请求，没有费用或Agent效果提升结论。用户视觉签收 pending_review |

浏览器当前可用，旧handoff中的禁用状态不再适用于本次会话。实测通过 Codex in-app browser 执行 UI 点击/拖拽，非最小DOM替身；2倍场景过宽时locator点击中心失败，改用已观察的可见区域坐标完成拖动，不表示场景自动居中/窄屏交互已验收。

本机原始证据（忽略目录，不随Git发布）：`outputs/editor-ui-p0/browser-observations.json`、`outputs/editor-ui-p0/preview.png`。截图和交互主链采集后还补了非法语块窗口有限数检查、销毁后update防护；这两个防护经纯函数/构建回归，未新增第二轮完整浏览器矩阵。产物以当前 `static/editor_ui/manifest.json` 为准。单bundle约671KB，gzip约203KB；iframe和父页面目前各加载同一个包，P1可拆画布/React入口，未声称性能优化通过。

## 换机时发现并修复的基线问题

首次相关回归46过/1失败：`RUNTIME_SKILL_HASH_MISMATCH`。核对Git blob与本地文件哈希完全相同，而四个登记值恰好对应同文件CRLF版本；`.gitattributes`规范要求LF。因此只修正 `config/html_runtime_skills.json` 四个登记值，没有改Prompt内容/版本，没有弱化hash核验或批量改换行。修复后上述91项通过。此修正会按原快照闭包规则让相关旧快照失效，不能据此绕过未知请求保护。

## 下一轮直接做什么

1. 完成上述缺失的上游license/notice全文核对及可重复浏览器自动验收脚本，保留P0证据与失败项。
2. P1接入原编辑器：布局模式、对象列表/属性/选择同步、受控presentation操作、旧场景兼容，注册消费者/source closure和frontend_quality。新语义scene0.6/0.7保持稳定actionId；不可把本fixture对旧格式的通过外推。
3. 覆盖文字、卡片、独立图片比例、关联引线、隐藏对象辅助轮廓、吸附、范围/容量拒绝、群组原子撤销和切页销毁。整套能力仍按原计划20+行为验收。
4. P2再接真实音频/语块窗口、作者与实际生效时长、动作resize和跨句阻断；P3走原revision/人工保护/无关重建复用；P4才作固定Agent对照，P5作正式视频/整课验证。

运行方式见 [editor_ui README](../../../editor_ui/README.md)。定义卡为 [editor-adapters-p0-0.1.0](../../contracts/html-presentation/runtime/visual-v1/editor-adapters-p0-0.1.0.md)，契约0.9.79。自查按 code-review-and-quality 的正确性、可读性、架构、安全和性能五维完成；修正了坐标事件数组展开、iframe手柄命中及销毁后的更新问题。此记录不是独立模型审查或merge批准。
