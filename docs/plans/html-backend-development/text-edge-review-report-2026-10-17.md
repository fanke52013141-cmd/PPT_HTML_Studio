# 文字边缘证据审阅页：2026-10-17

## 本轮目标和实现

从“JSON里有疑似截字”推进到“审核者能逐行看到证据”。定位成功后自动生成`text-edges.html`，并在结果中附`edge_report`（报告hash、原图hash、定位结果hash、区域数、分类计数）。支持用CLI给历史结果生成独立审阅目录。

审阅页内嵌完整参考图和局部观察窗，红框为原文字框，蓝框为跨界墨迹包围盒，逐行保留targetId/partId/region_index、原转录、坐标、不确定原因、方向和框外像素数。默认全部显示，支持状态筛选和1/2/4倍局部放大；图和脚本均在单文件内，不加载外站。未定位目标和零可检查区域单独展示，不把“未见跨界”标作完整通过。

归属：`html_text_edge_report.py`负责报告；`html_reference_localization.py`负责成功定位后的派生接线；`scripts/report_html_text_edges.py`负责只读离线回放。契约0.9.77，运行Skill、定位Schema与像素诊断阈值保持。模块已加入生产源闭包；升级后旧生产快照按原来源规则处理，不能越过过期检查。

## 同案例可量化变化

同一已封存真实页的三次定位记录（`outputs/reference-parts-realpage-20261017/localization-{0,1,2}/audit/result.json`）及相同SHA-256原图，离线生成新目录`outputs/text-edge-review-report-20261017`。不重新请求模型。

| 指标 | 本轮之前 | 本轮之后 |
| --- | --- | --- |
| 逐文字行图文证据审阅页 | 无，需自行对照JSON/原图 | 3份，39/39区域带身份、原框、局部墨迹 |
| 疑似/不确定/未见跨界 | 23 / 7 / 9 | 23 / 7 / 9，诊断不变 |
| 新增模型调用 | 0 | 0 |
| 原始记录修改 | 0 | 0，前后hash相同 |
| 本地生成耗时 | 无报告产出 | 0.539 / 0.621 / 0.445秒 |
| 单文件体积 | 无报告产出 | 1,197,503 / 1,202,195 / 1,200,608字节 |

产物：`trial-0.html`、`trial-1.html`、`trial-2.html`及`manifest.json`。图像/响应/HTML均为忽略的运行产物，不提交Git。3份区域数均13；具体分类8/2/3、9/2/2、6/3/4。

改善证据限于可展示覆盖与派生耗时。未测量真实人工复核耗时，不声称误报/漏报、定位质量或端到端模型效率改善。原正文16/18、分层联合1/3结论不变。

## 验证

4个相关隔离测试文件，76项通过（27.77秒）：

```powershell
.\.venv\Scripts\python.exe -m pytest checks/test_html_text_edge_report.py checks/test_html_text_edge_verification.py checks/test_html_reference_localization.py checks/test_html_build_snapshot.py -q
```

涵盖：图hash/尺寸/已保存诊断失配拒绝、记录及图像不变、转录及恶意字符串转义、区域/墨迹坐标对应、无外站资源、空/未定位结果、CLI拒绝覆盖旧目录、定位入口报告hash绑定、源闭包回归。Node执行报告实际JS的最小DOM测试验证默认全部可见、筛选及4倍缩放；这是脚本逻辑检查。

浏览器核验实际返回`Local browser use is disabled in Work settings`，故浏览器排版、真实交互和人工视觉验收仍为未验证，没有用逻辑测试代替。正式审核不消费这份独立证据，无自动修正/批准/重新生成动作。

## 复现与下一步

历史记录可运行：

```powershell
.\.venv\Scripts\python.exe scripts/report_html_text_edges.py --reference <原reference.png> --record <定位result.json> --out <不存在的新目录>
```

原图hash不匹配会拒绝生成，不能用新图假冒旧案例。新机器没有本机原始图片/响应时先跑隔离回归；历史真实页报告需要私下转移对应图和记录。

接下来先在可用浏览器核验展示，然后给新真实页建立逐行独立真值，测疑似/不确定的误报、漏报和人工复核耗时；以这些数据决定是否开发“人工指出问题行→原系统Agent重定位”的有界闭环。不得自动统一扩框，也不把本轮只读入口当正式审核接入已完成。
