# 交接备注：语音合成报错治理与创作配置交互修复（2026-09-27）

本轮起因是一次真实生产事故：用户在便携版上把"遴选面试"项目建在了错误的
创作账号下，一键流水线在 Step 7 逐页失败，且日志里的中文报错全部是乱码。
本文记录根因、两笔修复、验证情况与遗留事项，避免后续接手者重复排查。

## 事故时间线（便携版 `PPT视频工作台_便携版_20260917-103705`）

| 时间 | 事件 |
| --- | --- |
| 14:47:56 | 项目 `7e4feea0_144756`（遴选面试）创建，账号=夏晓华，自动套用其默认配置包"夏晓华默认创作配置"，语音连接=豆包音频生成 1.0（Seed Audio，参考音频路径指向旧 D 盘便携版） |
| 14:48:37 | 项目 `1ff15bcc_144837`（同名）创建，账号=夏文老师，配置包绑定 MiniMax（连接"夏文"，xiawenlaoshi001） |
| 15:01–15:02 | 第一个项目 Step 7 五页全部失败：Seed Audio 参考音频文件不存在，每页重试 5 次，报错在日志中显示为乱码 |
| 15:26–15:41 | 第二个项目 Step 7：slide_003~005 成功，slide_001/002 因本机代理（系统代理 127.0.0.1:2023）间歇性拒绝连接（WinError 10061）失败 |
| 16:13 | 通过 `steps/7/synthesize-async` 补齐 slide_001/002，五页音频全部就绪 |

根因结论：

1. **建错配置包**：新建项目弹窗按"当前创作账号"静默预选其默认配置包；
   两个包名字相近（夏晓华 vs 夏文老师）、两个项目同名，用户没注意到预选。
   不是绑定解析或快照的代码 bug——项目快照哈希与包内容完全一致。
2. **Seed Audio 参考音频路径失效**：连接配置保存的是 D 盘绝对路径，便携版
   搬到 C 盘后文件不存在；旧报错把"未配置"与"文件丢失"混为一条提示。
3. **报错乱码**：TTS 子进程按 Windows 代码页（GBK）写 stderr，父进程按
   UTF-8 解码（errors=replace），中文全部变问号。

## 修复一：创作配置交互（提交 `25feb41`）

- `static/creation_config_management.js`：新建配置包默认名固定"新建配置包"；
  不再自动预选文本/图片/语音的第一个启用连接；管理页打开时不再自动把账号
  默认包载入底部编辑器（此前"看似新建、实为编辑默认包"，保存会覆盖默认包）。
- `static/project_profile_extension.js`：新建项目弹窗下拉为账号默认包追加
  "（当前默认）"标注，预选不再无声。
- 已同步到便携版同名文件（便携版另有一些仓库没有的热更新，本次为定点
  替换而非整文件覆盖；替换时便携版文件行尾被统一为 LF，无功能影响）。

## 修复二：Seed Audio 报错与乱码（提交 `4ef6e45`）

- `scripts/generic_tts.py`：参考音频校验拆分为"未配置"与"文件不存在"两条
  报错；后者带出完整路径并提示到语音模型设置中重新上传关联。
- `tts_service.py`：Seed Audio 合成前预检参考音频（`_require_seed_audio_reference`），
  缺失立即返回 400 可操作报错，不再逐页空跑满重试；时间轴绑定子进程注入
  `PYTHONIOENCODING=utf-8`。
- `tts_provider_service.py`：`provider_tts_environment` 注入
  `PYTHONIOENCODING=utf-8`（仅影响子进程 stdio，不影响文件读写；MiniMax
  helper 由 generic_tts 透传环境变量，同样生效）。
- `runtime_support.py`：新增 `decode_process_output`（UTF-8 → 本机代码页 →
  替换字符），`run_subprocess_killable` 超时路径与 `run_subprocess_bounded`
  的字节解码统一走它。
- 已同步到便携版：`runtime_support.py` 整文件复制（推送前两边逐字节一致），
  其余三个文件定点替换并通过 compileall。

## 本轮实际执行过的验证

- `node --check`：仓库与便携版各两个前端文件，全部通过。
- `node checks/test_frontend_quality.js`、`node checks/test_visible_flow.js`：通过。
- `python -m compileall`：仓库与便携版的 `runtime_support.py`、
  `tts_provider_service.py`、`tts_service.py`、`scripts/generic_tts.py`，通过。
- `pytest checks/test_seed_audio_reference_contract.py checks/test_runtime_support.py
  checks/test_tts_provider_service.py checks/test_narration_tts_routes.py
  checks/test_persistent_tts_jobs.py checks/test_tts_secret_transport.py`：
  31 项全部通过（含本轮新增 6 项契约测试）。
- 真实接口验证：`steps/7/audio-status` 与 `steps/7/synthesize-async` 在便携版
  服务上实测，缺失两页音频成功补齐。

## 明确未执行的验证（不要读成"已通过"）

- 未在浏览器里重新走查新建项目/创作配置管理两个界面的实际交互（仅静态
  与语法校验）。
- 未做真实 Seed Audio 合成回归（需要有效密钥与参考音频；预检逻辑有单元
  测试覆盖，云端链路未跑）。
- 未运行 AGENTS.md 要求的完整发布校验清单（compileall 全量、agent 契约、
  Remotion tsc 等）——本轮未触及相关模块。

## 遗留事项（建议尽快处理）

1. **便携版存在未回传仓库的热修复**：便携版 `tts_provider_service.py` 为
   "重试 5 次 + 云端 5xx 指数退避"（含 `_SERVER_ERROR_MARKERS`），仓库仍是
   "重试 3 次、无 5xx 退避"。下次用仓库重打包便携版会丢掉这份修复，应先
   合并回仓库。
2. **Seed Audio 参考音频保存绝对路径**：便携版搬迁即断。短期靠本次的清晰
   报错兜底；长期应改为相对数据目录存储或在读取时按当前数据根重定位。
3. 事故项目 `7e4feea0_144756`（Seed Audio 版"遴选面试"）建议在项目库删除，
   避免与 MiniMax 版同名项目再次混淆（删除不可逆，留给用户决定）。
4. TTS 依赖系统代理：代理软件未运行时 MiniMax 合成会报 WinError 10061。
   可考虑在设置中提供"直连/代理"开关或在报错中提示检查本机代理。
