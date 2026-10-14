# GLM 文字与多模态模型交接

2026-10-14，工作目录 D:/software/PPT_HTML_Studio。用户授权文字规划使用 glm-5.3，后续指定多模态使用 glm-5.3-flash。已配置本机 BigModel 标准 Chat Completions 端点；密钥仅存 data/credentials.json，连接仅存凭据引用，均不提交。未更换图片生成或 TTS 连接。

## 实现与兼容

- 可选 planning 独立绑定（schema0.2），text 保持设计理解/还原/截图审核及素材辅助审阅用途；项目UI分开显示。Web/Agent/MCP/CLI共用字段，Agent API1.26.0，契约0.9.37。
- HTML阶段默认连接仅影响后续未固定的用途；既有项目fixed保留。旧客户端省略planning保留已有绑定；未配置独立planning时继续沿用text。原设计/音频/作者审批不自动修改。
- 规划专用generator与视觉generator分别冻结；身份进入生成快照、候选和恢复校验。阶段仍由原LocalJob及请求回执管理；未知外部结果不自动重发。
- GLM系列显式thinking enabled，reasoning_effort=max，连接temperature1.0；初始调用、格式回退和JSON修复均保留思考。默认文字JSON等待延长到600秒，显式调用超时保持原值。有效输出预算仍受项目64000上限约束。纯glm-5.3收到图片在本地拒绝。

## 真实连接验证

仅各一次最小请求，未启动新课程、生图或TTS。glm-5.3：2.041秒、138总tokens，返回有效JSON；glm-5.3-flash：1.465秒、174总tokens，以Base64图片正确识别红色矩形。均返回供应商request_id；cost未知。原去敏记录在本机 outputs/glm-model-connectivity-2026-10-14/summary.json。连接验证不证明复杂设计还原或逐句语义质量更好，未与豆包做相同真实任务对比。

官方依据：[GLM-5.3](https://docs.z.ai/guides/llm/glm-5.3) 仅文字；[Flash](https://docs.z.ai/guides/vlm/glm-5.3-flash) 支持image_url，多图与Base64，思考必须开启。国内实际端点用用户提供的 open.bigmodel.cn，并已上述真实调用验证。

## 后续

仍按设计Agent交接先补共享组件能力、重验设计还原，再A04语义QA与应用整课调度。模型替换不改变此前changes_requested或未知请求。当前8010没有监听服务；本轮未启动服务，服务下次从当前源码启动后使用新绑定。

## 检查记录

模型绑定和任务恢复专项的最终结果在本轮回复记录。项目模型页面已通过真实Edge/Chromium浏览器的分开选择、保存重开、冲突保留和安全标签测试。Ruff、前端质量与生成Agent文档检查通过。扩展组合曾40passed/1failed：test_html_visual_review.py旧断言要求8个图标，实际注册库含11个；对应组件目录和该断言本轮未修改，保留失败而不调整范围。另一轮恢复fixture缺回执发生于开发源码仍被修改的时间窗，最终须停止源码修改后重跑，不以旧结果声明通过。

最终停止源码修改后：模型绑定/冻结调用/任务恢复专项36passed；JSON专项新增思考修复回归后7passed（范围重叠，不累加为独立覆盖）。浏览器使用本机Edge，配置页分开选择和保存重开通过；默认Playwright浏览器缺失的首次运行保留为环境失败。Ruff、前端质量、Agent文档一致性、git diff检查通过。恢复fixture此前缺回执问题最终未复现，原恢复门禁未放宽。未跑整仓库全量；图标清单旧断言失败保持记录。
