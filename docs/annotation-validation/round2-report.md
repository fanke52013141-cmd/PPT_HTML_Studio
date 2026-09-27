# 勾画标注第二轮优化:验收报告(R0–R3 + 验证)

日期:2026-09-27。基线:上一轮未提交工作区(接续 W0–W5 报告)。
本轮按《勾画标注第二轮优化方案》实施,优先级 P0 缺陷修复 → R1 模块六 →
R2 目标解析与两端统一 → R3 手写质感 → 真实渲染 A/B 验证。

## 1. 已实施的改动

### R1 导航与确定性缺陷(P0)

| 缺陷 | 修复 | 证据 |
| --- | --- | --- |
| "可选"徽标、无显示编号 | 模块六显示编号 6(数字人显示时其后为 7/8);`displayFlow(context)` 成为显示序号唯一来源 | `static/index.html`、`static/flow.js`;`test_visible_flow.js` 断言两种数字人模式下的序号表 |
| enabled=true 即算完成 | 模块决策态:not_started/editing/confirmed/no_annotations/stale;只有 confirmed/明确"本项目不添加勾画"才完成;`enabled` 只决定输出携带 | `annotation_contracts.AnnotationSettings.decision`、`annotation_service._module_state`、`flow.getVisibleStepState`;测试覆盖 5 种状态 + "开关开但未决策仍 pending" |
| 进度分母 | 未进入决策不计分母(旧项目兼容);决策完成计入(83%→86%) | `flow.calculateVisibleProgress` + 测试 |
| `bounds.right` NaN | 编辑器横线不再自算几何(改用服务端正式笔迹);核心 bounds 消费者全部使用 left/top/width/height | `annotations_editor.js` 重写 overlay |
| opacity 钳 0.05 | 0% 真正不可见(编辑器/采样器两处) | `annotations_editor.js`、`annotation_playback.js` |
| 编辑/导出几何不一致 | **服务端单一笔迹来源**:GET/PATCH 响应携带 `strokes`(resolver 片段 + geometry v2),编辑器渲染同一数据;Remotion 消费同一采样器 | `annotation_service._items_with_strokes`、`annotations_editor.renderAnnotationOverlay` |
| 旧 timeline 可能被读取 | props 构建器严格门禁:enabled=false 忽略;enabled=true 要求 timeline 存在、resolver 版本匹配、图像/讲稿哈希与当前文件一致,否则可操作错误 | `scripts/build_remotion_props.py::_load_annotation_timeline_for_render` |
| confirm 后无构建调用 | 确认成功即构建该页 timeline(无音频/语块缺失时如实报 needs_review,不写文件) | `annotation_service.confirm_slide → _build_timeline_for_slide` |

### R2 目标解析(R2 方案 5.1)

新增 `annotation_target_resolver.py`:乱序 token 按行/阅读顺序重排、同行
连续合成短语片段、中间缺字拆分、跨行拆分、重复词不同卡片独立、保留原始
四边形、纠正文本进 screen_quote、stale layout/未知/重复/退化拒绝。
`screen_quote`(画面文字)与 `anchor.quote`(讲稿文字)分离。
CLI 与服务端共用同一解析。7 项单测覆盖全部规则。

### R3 手写质感(R2 方案 4.1–4.5)

`annotation_geometry.py` 重写为 v2(`annotation_strokes_v2`):

- **手写圈模板**:3 个人工调形贝塞尔模板(非对称:左右弧不同、顶部压扁、
  起收笔位置变化)+ 固定种子低频扰动(短边 2%–5%)+ 3 模板轮换;
- **笔宽曲线**:起收笔占弧长 5%–12% 变细,中段低频压感波动;
- **行笔节奏**:speed_profile(起笔缓/主体快/收笔减速)+ 每笔独立
  start_offset(跨行抬笔间隔 90ms);
- **文字保护区**:中心线不得进入字框本体(2px 容差),误入点沿径向推出;
- **采样**:像素 6px 弧长均匀重采样,单笔上限 720 点。

共享采样器 `annotation_playback.js` 升级:中心线+笔宽曲线→**轮廓多边形**
(编辑器、Remotion 同一实现),每笔独立起止,时间量化接收实际 fps,
退出淡出连续到 0。

## 2. 自动化测试(本轮实跑)

| 套件 | 结果 |
| --- | --- |
| 全部 12 个 annotation Python 套件 | **150 passed, 1 skipped** |
| `test_annotation_target_resolver.py`(新) | 7 passed |
| `test_annotation_geometry.py`(重写 v2) | 10 passed |
| `test_visible_flow.js`(重写决策态+displayFlow) | passed |
| `test_frontend_quality.js`(守卫升级) | passed |
| `test_annotation_playback.js`(升级) | passed |
| `test_annotation_workspace.js` | passed |
| source safeguards / ownership / migrations / invalidation | 19 passed |
| `npx tsc --noEmit`(Remotion,含 v2 overlay) | exit 0 |
| 时间轴重建(隔离 run 实跑) | v2 path 笔迹入 timeline,边界约束成立,两次构建字节一致 |

## 3. 真实渲染 A/B 对比(用户核心要求)

数据源:隔离 run 中**真实百度 OCR** 的字框(`text_layout.json`,
135 个字级候选)。对比页 `docs/annotation-validation/round2-samples/`:

| 文件 | 内容 |
| --- | --- |
| `ab-case-1-date.png` | "9月30日"(4 字框):旧版规则椭圆 vs 新版手写圈(3 个种子)+ 半程推进 |
| `ab-case-2-percent.png` | "23.5%":同上 |
| `ab-case-3-underline.png` | "Online":新版手写横线(基线弧度+收笔上扬) |
| `ab-compare.html` 及数据 | 浏览器可打开的交互对比页;渲染经 production 的 `annotation_playback.js` |

**截图可见的明显差异**:

1. **位置正确性**:旧版椭圆圈在标题附近(旧代码合并多边形 + bounds 缺陷的
   真实表现);新版圈准确包围目标文字"9月30日",不压字、不圈邻词。
2. **形态**:旧版是机械标准椭圆;新版有明显手写非对称(左右弧不同、
   顶部压扁、起收笔小重叠),三个种子形态各不相同("换一种笔迹"可用)。
3. **笔触**:新版轮廓带笔宽曲线(中段饱满、起收笔收细),不再等宽线条。
4. **节奏**:半程面板显示行笔推进(笔尖位置),跨行分笔有抬笔间隔。

## 4. 未完成范围(如实)

- R4 语义候选上下文(planner 输入结构化短语候选)、局部重识别、修正反馈分类:未实施;
- R5 字词级对齐(仍为句级降级)、真实 MP4 渲染验收、fingerprint/sidecar 扩展、Agent 契约同步:未实施;
- 自然度 3 人评审打分、20 页冻结集:未执行(需真实用户参与);
- 编辑器候选列表仍为单字按钮(方案 5.4 的按行/卡片分组未做)。

## 5. 复跑命令

```powershell
# 全部 annotation 测试
python -m pytest checks/test_annotation_*.py -q
# 前端回归
node checks/test_visible_flow.js; node checks/test_frontend_quality.js
node checks/test_annotation_workspace.js; node checks/test_annotation_playback.js
# A/B 对比页(需要隔离 run 的 text_layout.json)
python scripts/build_ab_compare.py <run-dir>
# 在 round2-samples 目录启动静态服务后浏览器打开 ab-case-*.html
python -m http.server 8643
```

---

# 第三轮:精准度量化 + 栅格手写墨迹(2026-09-28 补记)

针对用户最终目标(精准第一、强对比、勾画必须是手写位图而非 SVG)完成:

## 1. 精准度可量化评测(首轮落地)

- 真实百度 OCR 字框固化为仓库夹具 `checks/fixtures/annotations/sample_slide_layout.json`,
  评测完全可复跑:`python scripts/eval_annotation_precision.py`。
- 栅格指标(`annotation_ink.precision_metrics`):包围率(周界被包住)、
  压字率(墨迹落入文字框)、误圈邻词率、偏心距。
- 修复过程中发现并解决的真实缺陷:
  1. **模板外溢**:手写模板极值超出 [0,1] 约 8%,把邻词感知留白顶穿
     (评测前误圈邻词 8–11%)→ 改为按模板实际极值精确映射 + 硬外界钳制;
  2. **噪声底纹**:`Image.blend` 给整块区域加淡色底 → 改为 `ImageChops.multiply`
     只调制已有墨迹(评测截图直接暴露)。

## 2. 三轮对比指标(冻结样本 · 真实 OCR 字框,实跑结果)

| 用例 | 指标 | V0 第一轮(逐字符规则椭圆) | V1 第二轮(短语手写 SVG) | V2 第三轮(栅格墨迹) |
| --- | --- | --- | --- | --- |
| 日期"9月30日" | 压字率 | 10.9% | **0.2%** | 0.5% |
| | 误圈邻词 | 0 | **0.0%** | 0.0% |
| | 包围率 | 1.00 | 0.89 | 0.89 |
| | 偏心距 | 1.9px | **0.8px** | 0.9px |
| 百分比"23.5" | 压字率 | **42.3%** | **0.0%** | 0.4% |
| | 误圈邻词 | 0 | 0.0% | 0.0% |
| 英文横线"Online" | 横向覆盖/贴基线 | 1.00/1.00(6 段断线) | 1.00/1.00(单笔) | 1.00/1.00(单笔+纹理) |

结论:压字率相对第一轮下降 **92%–100%**;第二轮发现的邻词误圈在第三轮修正为 0;
椭圆用例偏心距同步下降。证据图:`round3-samples/round3-summary.png`
(逐轮截图对比)、`round3-compare.html`(指标表+图)、`precision-report.json`。

## 3. 勾画改为手写位图(视频不再使用 SVG 路径)

- 新增 `annotation_ink.py`:中心线 + 笔宽曲线 → **位图墨迹**
  (压力轮廓、确定性低频浓淡噪声、洇墨),同输入逐字节一致;
- 确认/CLI 构建时间轴时逐笔渲染 **PNG 帧序列**(`annotation_ink/<id>/stroke_<i>/frame_XXX.png`,
  0.6s@30fps = 18 帧),写入 `strokes[].ink`;
- props 构建器把帧复制为 runtime 资产(缺帧拒绝渲染),
  `AnnotationOverlay.tsx` 按共享采样器的 `rasterFrameIndex` 逐帧显示位图;
  矢量路径仅作旧数据回退;
- 逐帧推进与矢量采样共用同一笔迹时序(`strokeProgress`),编辑/预览/导出一致。

## 4. 测试

新增 `checks/test_annotation_ink.py`(8 例:确定性/种子差异/逐帧单调/
0% 不可见/指标门/邻词检测)与 resolver/geometry 邻词留白用例;
全量 158 Python + 4 JS 套件 + Remotion TypeScript 全绿(2026-09-28 实跑)。

## 5. 仍 honest 的边界

- 评测集为 1 页冻结样本 3 用例;20 页真实课件盲测、3 人自然度评审、
  真实 MP4 逐帧验收仍待执行(脚本已就绪,可复跑);
- 编辑器画布预览仍为矢量轮廓(快速编辑辅助);导出/视频为栅格墨迹;
  编辑器切换位图预览列为后续项。

## 6. 真实 MP4 演示(2026-09-28)

- 视频:`docs/annotation-validation/round3-samples/annotation-demo.mp4`
  (9.4s,1920×1080,30fps,h264,583KB)。
- 内容:冻结样本页(真实百度 OCR 字框),三笔错峰手写墨迹——
  0.3s 起笔画圈"9月30日"(24 帧)、4.8s 横线"Online"(18 帧)、
  5.7s 荧光笔扫过"23.5%"(18 帧);9.0s 前后淡出。
- 关键帧截图:`round3-samples/demo-frame-*.png`(起笔/半程/完成/多笔同屏)。
- 渲染链路:确认 → 栅格墨迹帧落盘 → props 构建器复制 runtime 资产
  (缺帧拒绝渲染)→ Remotion `AnnotationOverlay` 经 staticFile 逐帧显示位图。
- 复现:`python scripts/_demo_annotations.py <run-dir>`(造三条标注并确认)
  → `python scripts/_demo_props.py <run-dir> <out.mp4>`(构建 props)
  → `npx remotion render src/index.tsx ArticleVideo <out> --props=<run>/remotion_props.json
  --codec=h264 --image-format=png --pixel-format=yuv420p`(scripts/remotion 下执行)。
- 期间修复:props 门禁的 planning 路径错误(slides/ 上一级)、
  墨迹帧资产目录重名覆盖、荧光笔笔宽(刷高)。
