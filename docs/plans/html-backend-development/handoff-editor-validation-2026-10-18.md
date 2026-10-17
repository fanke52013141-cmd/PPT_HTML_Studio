# 编辑器与视频优化验收交接（2026-10-18）

承接单页输出交接；契约0.9.85、Agent API1.44、repair.generate1.3、操作Skill1.17。本批包含此前P0—P3未发布增量。工程、真实模型、用户批准和整课状态分别记录。

## 已有实际证据

1. 用户明确批准《水为什么结冰》当前画面，并授权保留已有旁白、恢复项目原音色。原服务记录视觉批准；复制MiniMax连接供该项目使用原voice_id，不改共享连接或全局音色，不执行TTS。当前配置与原确认指纹完全一致。
2. 原持久视频任务首次输出发现42.7ms AAC priming延迟。修复合成：单页保留已验证分段，多页独立解码音轨、按页帧预算trim/pad后拼接。修复后任务4fd7605775ce4c34855969269f61c8ab成功，588帧/30fps/19.6秒，全量解码通过；32个动作/字幕对应帧通过，音频零偏移相关系数0.999991、延迟0ms。视频`runs/c16bc2b3_203534/videos/render_a1f3978d657d42d1b82bfa4bd7dbaa2a.mp4`，实际hash2952cec0314f3a5341eb82ee006e896577366f0c7ca6afc369934dd829eb4f71。旧延迟视频保留并标stale。
3. 真实页面/旁白隔离副本做基线、工具、Skill三组模型对照，各四例：布局、原句偏移、人工保护冲突、缺能力停止。每组4/4、误改0、均1轮/4HTTP，原内容/配音hash不变。总耗时78.88/42.10/45.34秒，报告token27324/25931/26287，费用未知null；单次小样本不能证明稳定提速或降低费用。没有生图或TTS调用。
4. 修复模型现在消费scope相关人工叶路径及祖先路径，包含布局、动作、绑定；旧保护从同一manual_protected_paths推导，候选/保存门禁不变。工具与Skill摘要分别比较，实际出站内容/响应留在忽略输出，不提交用户数据。
5. 实际cua浏览器：正式0.7编辑器六组窗口/DPR坐标回写+undo，十次重开，单iframe/辅助层通过。40代理适配层24组：窗口1280×900/1920×1080，DPR1/1.5/2，缩放0.5/1/1.5/2，坐标误差≤1作者像素；48样本输入到下一动画帧p95=12.6ms。当前生产注册模板最多33槽，40代理测试不宣称新增生产模板或40槽整页能力。
6. 多页：原正式导出检查覆盖第三页失败、前两页缓存复用、恢复、重排、缓存损坏重建；调度检查覆盖实际子进程恢复、unknown不重发、人工签收阻断。新增单/三页非静音chirp回归核验起点/各页边界/顺序，2项通过；有限采样不代替听感。

本地证据：`outputs/single-page-video/2026-10-17/real-comparison-fixed/report.json`、`outputs/editor-benchmark/2026-10-17/comparison.json`、`outputs/editor-stability/2026-10-17/`。这些运行数据、数据库备份和媒体不得提交Git。

## 验证和限制

最终组合回归590项通过（164.35秒，1条既有Starlette弃用提示）；另局部Prompt/Skill60项、新增指纹/修复17项通过。Node16项、bundle构建、前端质量、Agent同步、Python/JS语法及Remotion本地TypeScript通过。完整输出见`outputs/final-editor-regression.txt`。这些重叠测试数不相加。

canonical quick检查发现原仓库门禁失败：storyboard_service.py1368非空行>1350，文件未被本批修改。未提高阈值，未宣称全库CI通过。清理了发布检查发现的未使用导入，fixture导入改显式同名导出以保留pytest发现。

归档上游许可证及esbuild生成LEGAL/NOTICES保留原字节（含CRLF/尾空白），不为git whitespace检查改写许可证据或失配构建hash；手写代码的排除式diff检查单独执行。

**整体目标仍partial**：本机没有已生成多页HTML真实课程，已向用户请求课程主题/项目；不能把合成静音/信号或单页重复当作真实整课。真实0.7语义课程的A04模型/人工签收亦独立待验。分支发布不等于main合并或部署；整课输入和全库门禁未完成前不宣称五项全部完成。

## 发布门禁后续修复（2026-10-18）

已将手工标题/旁白页面的纯组装移入既有storyboard_planning.compose_manual_skeleton_slides，请求服务继续持有权限、数据库、最终校验和失效。视频启动依赖装配归入video_runtime.configure_video_runtime，server显式注入同一配置/回调；不移动业务政策、不改路由或公开Schema，不提高行数阈值。storyboard_service和server架构门禁均通过。新增手工组装字段/空输入反例；分镜与正式输出相关31项、架构/装配/路由等9项通过。

quick继续发现设置脱敏自检仅填充旧密钥清单，新增字段触发KeyError；夹具现在为完整SETTINGS_SECRET_KEYS填入测试值，仍要求每一项掩码。独立真实服务脱敏自检通过。最终quick日志为outputs/editor-quick-checks-final.txt，门禁最终状态以该日志为准。此前“架构失败”描述保留为发现历史，以本段后续证据更新。

canonical quick最终通过。首次完整检查为2500 passed/6 failed/8 skipped：失败集中于历史验收夹具没有提供当前设计理解/重建响应、缺正文/run_dir、旧UI错误文案和旧runtime Skill清单。夹具按现合同补齐，正式校验与预算未放宽；相关39项复验通过。浏览器夹具服务器从无参数独立脚本发现中排除，仍由真实编辑器验收启动；新增发现器回归。视频测试证据改写忽略outputs，避免修改历史已跟踪媒体。

CI环境先因Python3.11不兼容锁定NumPy而失败，改为3.13；随后暴露未安装引擎npm依赖。CI现为Windows完整渲染检查，安装三个锁定npm包、Chromium，显式核对Windows字体和FFmpeg。实际CI已通过这些前置，下一失败为Node20不展开测试通配符；editor_ui测试命令改显式文件名，本地16项通过并重建manifest。最新完整pytest输出为outputs/editor-pytest-final-v2.txt，未完成时不可声明全库通过。

## 真实整课候选已启动

未收到课程主题回复后，沿用已有《水为什么结冰》原文章，通过原项目/文章服务建立独立guided HTML验收项目ec60bbd4_010236，原单页不变。原课程任务html_c184f91c3fdc4ffeacb6实际调用已配置模型生成四页讲稿，随后进入画面规划。项目与任务ID写入outputs/real-course-acceptance/2026-10-18；继续前须检查原任务，不因等待或观察超时自动重发。新设计和最终作品仍需明确批准，当前不声明真实整课已完成。此段替代先前“没有整课输入”的阻塞描述。

## 最新核验

本地完整pytest最终为2506 passed、8 skipped、2 warnings（716.84秒），输出editor-pytest-final-v2.txt。远端b6dcbce完整检查为2505 passed、1 failed、8 skipped：PPTX任务构造测试启动真实后台工作线程，读取时状态已由queued变成running。测试现在隔离submit并核对唯一提交的任务ID，仍严格校验queued、账号权限和输入指纹；不改生产状态机。

真实整课的四页讲稿和画面规划已由原服务生成，但第一页语义计划两轮均被原校验拒绝，最终为SEMANTIC_ANNOTATION_TARGET（前轮为SEMANTIC_ANNOTATION_ANCHOR）。父任务html_c184f91c3fdc4ffeacb6与子任务html_996b82a3b8654636880c均failed；没有设计图、旁白或整课视频可供签收，未绕过门禁或再次发起付费尝试。中途观察脚本退出造成的本地子任务回执关联已据唯一子任务及一致快照窄修复，审计见outputs/real-course-acceptance/2026-10-18/local-child-link-recovery.json；修复后通过原HTTP入口续行，未重复第一轮请求。继续优化应先检查annotation目标/焦点约束在规划提示中的覆盖，不能把两个失败响应作为批准内容。

后续已追踪真实响应：首轮annotation.anchorId误引用文字对象，第二轮targetId也误指文字标签。运行Prompt0.3.3补清图片目标、图片内焦点及文字标签三种引用，不自动修补响应。新增实际provider入口两轮负载/诊断测试，相关34项通过，canonical quick、Agent同步与ruff通过。旧冻结任务因源码变化不能续为同一请求；原produce入口创建新任务html_7a4c3b72614c4e80be1c，快照811bcda6afa1eade0d7e0f55552aa02cd2fb910bb6ac0e080712af9fcbb191b0，06:41发起新规划。必须查此原任务当前状态，不能因为观察等待再次提交；新任务通过与否另记。旧父任务尚未完成。

该新任务已succeeded并停在design_review，input_state=current、saved.changed=false。新版真实规划首轮通过，不触发结构修复；323.17秒，供应商报告25480 tokens。随后原设计生成约51.19秒，合计2次adapter调用，图像调用未返回完整用量，整个任务费用/总token保持null，不能拿规划用量冒充总用量。没有生成旁白或替换正式场景。

第一页候选key为3aeb952adf68928daae85812d0bc1c1f7b3465352c4cb3fb915beb7ac1b09bb1，图片SHA256为96de0f0265a5e21e6906acbc43ba5d4b55c669c9c30bf5d6f15f36f6174cdb71；实际文件哈希匹配，approval_status=not_recorded。已向用户展示此图并询问设计接受，尚未收到决定。批准后须携该key沿原produce入口继续还原；普通自动继续和旧单页批准均不等于新设计接受，也不等于后续HTML/声音/A04批准。任务与费用证据保存在outputs/real-course-acceptance/2026-10-18/prompt-033-design-task.json。

源码88226fd已推送PR #2（草稿），最新核对CI 117523515123仍in_progress；日志临时HTTP502不改变任务状态，不代表测试失败或成功。后续以最新head实际检查为准。生产服务PID3904、127.0.0.1:8010在本次核验时存活，继续前核查单实例，不能仅凭历史PID启动第二份。
