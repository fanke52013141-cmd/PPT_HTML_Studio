# 第五轮：多模态审阅任务与单对象失败回退

用户“下一步”授权继续开发。关联HPS-015、017、026–030、036；契约包0.9.7、Agent API1.15.0。直接使用现有checkout、executor和LocalJob；没有启动用户服务、数据库迁移、真实DB/runs写入、commit/push。

## 实现

- 候选POST assess严格空body，先验证候选seal，再冻结所需text模型。持久html_asset_sheet_assess，真实独立PNG与need进入多模态服务；内部ID/hash由程序管理。建议保存后既有read/UI显示，不改变人工review或接受。无可用模型/凭据在提交前阻断，不提交假成功任务。
- 单对象POST retry严格expected_revision、可选纠正need及direction（默认V05）。`html_asset_sheet_retry.py`验证原spec声明的对象，含提取失败项；拒绝已接受、修订过期和缺mask服务。固定1024×1024单槽、原asset ID、独立板ID，保留处理参数，使用原板实际图作参考，仅生成该对象。原板像素锚点不能映射到新生成几何，显式清空，采用时须重新设置真实锚点。原素材、其他对象、人工review/accepted/resources/scene/audio保持。
- 父key/asset/need/direction/版本决定重试板ID；图片快照/Prompt/处理版本/修订决定任务指纹。result/payload记录父身份，图片源缓存与候选分别保留。运行期间修订/接受变化、停止、旧attempt导致checkpoint阻断发布；已接受对象不能付费重试。
- 两任务提交冻结对应模型，凭据仅内存，安全摘要入库；复用现有executor、查询/cancel/recover，最多3attempt。list返回三种素材任务的最近活动项；重开可恢复。生成仍不自动调用审阅或自动付费重试。
- Web/Agent同request model和处理函数，MCP通用严格分派，CLI sheet-assess/sheet-retry写入均必须--file，53项capability、hash a573062229930246。UI新增AI检查、可编辑单对象重生需求及失败对象按钮，已接受锁定；任务结束保持被审阅旧候选或展示新重试候选，不跳到无关版本。

## 验证

实际FastAPI/LocalJob/候选服务、图片/多模态受控提供者覆盖：模型提交后变化、双模型凭据不入payload、去重、候选PNG实际传输、未自动批准、独立单对象新PNG/父板逐字节保留、失败槽位重试、取消、中断恢复attempt2/3、旧worker拒绝、in-flight停止、修订和接受变化阻断消费/候选发布、账号/image门禁、strict字段、缺模型阻断、七能力MCP/CLI实际Agent HTTP。

第五轮初次定向范围53 passed；最终Agent+应用+action完整回归452 passed（18.41秒，1既有Starlette warning），旧提取/清理/审阅/task/server boundaries独立范围62 passed（3.41秒），范围有部分重叠，不相加。浏览器17个检查通过、pageErrors=[]，含真实脚本在fixture API下的AI任务/单对象/失败对象/旧版本保持/接受锁定/XSS/409/项目隔离/重开/停止。定向Ruff通过（首次发现新测试未使用json导入，删除后通过）；前端质量、能力矩阵和diff检查通过。多模态请求复用原governed_llm_request，排队取得许可后再次检查取消，测试确认取消不发送请求且关闭client。

## 实际限制与下一步

本轮没有发送真实多模态或单对象生图请求；受控提供者返回不能作为实际识别准确率/生图质量/费用证据。现有模型连接还需配置可用text/image模型及凭据；专用Decisions API适配不在本轮，使用原OpenAI兼容多模态chat接口。原内置生图尺寸不服从和模型不可核验仍未解决。不能宣称已提高image2.5整体生产效率。

N00-A继续partial。下一步用真实可调用模型执行AI检查→针对多余光芒等失败对象单独重试→人工审阅→采用候选，记录每个合格素材的时间/费用/重试/人工分钟，再完成同模型批量与逐个生成对照以及课程签收。
