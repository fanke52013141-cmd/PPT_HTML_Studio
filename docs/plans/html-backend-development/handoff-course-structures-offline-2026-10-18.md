# 四页课程结构：离线补齐与验证

2026-10-18，契约0.9.88、Agent API1.47、操作Skill1.20。范围来自[统一阻断清单](course-delivery-blockers-2026-10-18.md)。本轮未新增规划、生图、TTS或真实生产任务；未写四页作者HTML，未修改批准记录，未换版8010服务。

## 已实现与验证边界

| 阻断 | 当前离线实现 | 验证性质 |
|---|---|---|
| 卡片白底描边、插图虚线框、全虚线无箭头标注 | card-outline、figure-frame-dashed、annotation-dashed-no-arrow；旧样式保留 | 共享renderer实际绘制、Schema、容量和图标底检查 |
| 散热、标签引线、条件与阶段连接缺明确关系 | arrow可声明from/to端点、point或图片anchorId、head及lineStyle；端点随对象运动派生；关系本身不接受空间覆盖/偏移 | 缺端点/未知对象/递归/非法坐标/类型在规划前拒绝；共享浏览器测量端点跟随。结构有效不证明语义正确 |
| 恒温阶段无代码图表 | chart的归一化points、轴标签、min/max、unit、plateau；图表自绘并派生平台值。非有限值、非递增x、假平台拒绝 | 有限固定夹具，使用示意数据；不宣称真实实验数据，不修改真实讲稿 |
| 整课末页缺完整三阶段 | process-three-stages-v1三个代码阶段卡和独立标签/关系；chart-explanation-v1及science-relations-v1共享关系模型 | 三阶段无需新图片；前两页使用内置示例图作为结构占位，绝非正式课程素材 |
| 缺关系到还原后才发现 | 权威合同可声明visual_requirements，计划以visual_coverage映射准确对象；normalize与A02均复核，显式关系模板要求端点 | 当前四页人工编写离线夹具完整覆盖；没有权威清单时不声称自动理解自然语言或自动发现一切遗漏 |

四页夹具是checks/fixtures/course-structure-plans.json，沿原normalize→A02→compile_plan→共享浏览器，生成19/17/8/11个代码/图片对象及对应动作。夹具是工程测试输入，不冒充系统模型计划、真实生产成功或人工批准。生产合同尚未加入这份需求映射；实际恢复前须显式核对权威需求清单与当前规划，而非直接重发旧失败任务。

## 已记录检查

- canonical quick通过，Agent文档/代码规范/原服务检查通过。
- 初轮大组合175项通过、1项旧提示版本断言失败；更新为实际0.3.4后，定向43项通过。数量有重叠，不累计为独立用例。后续增加非有限图表点负例，完整pytest运行中，最终结果另补。
- 共享浏览器两种后端各16组（四页×1592/1600宽×DPR1/2），结构与跳转后DOM状态32组通过；软件后端16组解码RGBA逐像素一致。
- 默认GPU后端在1592宽、DPR2时，001/002/004三页文字抗锯齿最大差1通道色值，分别658/1038/725个像素（各5705728像素）。其余组像素相同。默认GPU逐像素验收明确未通过，没有放宽既有门禁、隐去差异或用软件结果替它签收。
- 参考目录41件一致性检查通过；新代码模块、Schema/模板/布局、运行片段0.7.2和生成bundle纳入源闭包。
- 原用户接受的四页audio/text/metadata/srt/timeline共20个hash均保持，任务表无running/queued。

本机证据outputs/course-structures-offline/verification.json；software/default分别保留browser-report.json、每页实际PNG及像素差异after.png。完整日志outputs/course-structures-full-pytest.txt，快速检查outputs/course-structures-quick.txt。媒体/本地数据不入Git。

## 尚未完成与恢复条件

- 默认GPU分数缩放的逐像素问题仍保留为已知限制，不能称全设备像素完全一致。
- 当前001/002真实失败任务保持原终态，003/004仍无真实设计；不能把离线夹具保存成实际系统Agent作品。
- 原素材复用未命中的恢复路径、未知旧请求费用并未因本批被修复或查明；本轮新增调用为0。
- 只有汇总本批工程结果、审查权威需求映射，再恢复有限的逐页正式生产；继续复用原声音。HTML/A04/声音当前绑定、整课视频帧/音轨与发布仍独立验收。

## 收尾结果

完整pytest首跑：2563 passed、8 skipped、1 failed（710.04秒）；唯一失败为另一个旧0.3.3提示版本断言，已同步0.3.4。补齐chart内容/字体/关系审核维度及显式关系不可独立变体后，相关129项通过（78.26秒）；最终零长度端点与乱序key边界及兼容复跑63项通过（43.04秒）。两组覆盖重叠，不相加，也不把首跑失败隐去。日志分别为outputs/course-structures-post-review-pytest.txt与outputs/course-structures-final-pytest.txt。

补跑npm run test:visual：容量诊断通过，但旧neutral-science主题默认GPU seek截图仍失败，解码RGBA有687像素最大差1通道色值。没有放宽断言，也没有证明该现象在本批之前是否存在；默认GPU逐像素门禁保持未通过。软件固定捕获后端下的新四页16组仍严格相同。这是明确的验证边界，不宣称所有渲染验证全绿。

新增jsonschema依赖和本机已安装的传递版本已进入requirements.txt/lock；本次没有联网安装。相关依赖约束核对通过。全局pip check仍报告cozepy/video-making-platform-api等非本项目包的既有冲突，未改动其他项目环境，不记为全局检查通过。

最终离线说明outputs/course-structures-offline/report.md，实际数据verification.json。第二页夹具的两个条件及标签引线已分别绑定原对应讲稿语块，所有生成数据仍只在测试目录/ignored outputs。后续应先处理默认GPU像素门禁、素材复用及真实需求清单启用，再有限恢复课程生产；本轮不启动新的模型实验。
