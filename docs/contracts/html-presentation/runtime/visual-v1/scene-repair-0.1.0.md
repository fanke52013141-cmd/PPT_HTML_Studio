# 实例编辑与局部修复定义卡 0.1.0

细化 HPS-001/007/009/010/013—017/023—028。scene 0.5.0 增量；旧0.1—0.4读取与默认布局/字阶保持。definition theme/layout不升版；旧scene禁止新字段，编辑器显式升级后保存。

## 实例字段

非annotation节点可有 presentation：offsetX/offsetY（槽位原点相对绝对覆盖，-400—400逻辑px），width/height（20—1600/800逻辑px），typography（公开文字部位→有界字号fontSizePx 12—80、weight 400/700、lineHeight 1—1.8、align left/center/right）。部位：text/label/badge为text；header为title；card为title/body；figure为tag/note；summary为heading/from/to/term/takeaway。不得使用自由CSS；无此部位拒绝。默认不加任何覆盖。覆盖在基础布局解析后、文字测量前、动画前应用；重算图片锚点和引线。annotation坐标空间不允许覆盖。

## 修复接口

Web /api/projects/{project_id}/html-visual/{slide_id}/repair/{preview,save,evidence,generate}；Agent 同路由前缀 /api/agent/v1/projects。preview/save请求expected_revision、operations、source human|ai（默认ai）；save额外candidate_key。允许操作set_presentation（合并指定覆盖值）、set_text_style（part指定公开部位）、set_motion（现有通道的参数）、set_binding（现有动作语块）。全部为绝对赋值、重复幂等，不改文字语义、节点身份或结构。一次最多20操作。scope由调用者指定允许对象，AI只能在该scope编辑。未指定scope取操作目标；generate必须指定目标。不得让模型选source或签发key。

候选key绑定源scene/binding/resources、项目revision、操作、source/scope、共享渲染器指纹及时间检查请求。预览不写作品；保存重新验证key、revision和浏览器实测。过期409，不合法422，无效或失败不写。manual记录相对原基线变更字段，AI不得触碰已有人工保护字段；human可以显式修改。新增protected_paths只记录人工触及的字段；AI修复可继续细调自己生成的字段。旧无此字段的记录全部按人工保护处理；重规划仍保留所有已保存覆盖。保存沿用save_editor与下游失效；同值no-op保留音频。保留候选与检查记录，不声称崩溃事务或持久撤销。

## 动态证据

evidence/generate提供time_range_ms可选和overlap_pairs（调用者明确哪些对象不应重叠）；从实际共享播放器取每个动作起止前后、中心与有界均匀采样，最多240帧；高风险短区间可request step_ms下至16。报告时间、clock、可见对象测量、指定对碰撞、越界、截图路径。故意容器/主体重叠不全页误报。未请求pair不代表无遮挡。有限采样不等于全过程证明；全片默认间隔250ms，最大120s超样本预算阻断并要求缩短区间/增大步长。静态文字容量由渲染器实测；任何检查失败不保存。时钟沿用现有audio binder，作者时钟不宣称音画同步通过。

## Prompt与执行

初稿 Prompt只输出已注册plan；结构纠错包含原任务、失败JSON和诊断，最多一次。修复Prompt输入冻结scene/binding、允许目标、操作定义、用户目标、实际时间检查报告；输出candidate operations或needs_input/unsupported，不输出整页代码、哈希、批准。配置chat接口新增受run目录、PNG格式、8MB/4M像素和最多4张限制的实际截图输入；截图索引时间与测量一起发送，提供者必须支持多模态，不静默去掉附件。截图理解与审美仍须真实模型调用和独立验收。修复最多两次候选，每次运行检查；保存仍显式且验证。Skill只有实际工具执行记录才算加载验收，创建文档不等于自主Agent。

## 验收

Schema/compiler拒绝非法字段/部位与越界；浏览器验证字阶换行与动态pair遮挡；Web/Agent一致、保存重开、409、人工保护、失败不落盘、无TTS调用。真实模型必须实际连接调用，缺密钥明确阻断，不将fixture记为真实验证。
# 模型输入采样补充（2026-10-10）

html-repair Prompt 0.3.0 对直接传入原始frames的调用只发送所附截图时间对应的最多四帧几何；正常evidence服务原本已摘取末帧几何/测量、全部问题和摘要，仍使用该输入；完整有限采样轨迹继续保存在证据文件。减少重复输入不改变检查步长、候选校验、保存规则或视觉批准，不声称由此证明全部遮挡安全。
